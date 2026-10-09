import csv
import json
import math
import tkinter as tk
from collections import deque
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, ttk


PROJECT_DIR = Path(__file__).resolve().parent
STATE_PATH = PROJECT_DIR / "data" / "occupancy_state.json"
READINGS_PATH = PROJECT_DIR / "data" / "logs" / "occupancy_events.csv"
HISTORY_PATH = PROJECT_DIR / "data" / "logs" / "room_history.csv"
TELEMETRY_PATH = PROJECT_DIR / "data" / "environmental_state.json"
CONFIG_PATH = PROJECT_DIR / "config.json"
GRID_COLUMNS = 8
GRID_ROWS = 6

DEFAULT_PROFILES = {
    "Balanced": {
        "ac_on_at": 1,
        "busy_at": 5,
        "empty_temperature": 26,
        "occupied_temperature": 23,
        "busy_temperature": 21,
    },
    "Focus": {
        "ac_on_at": 1,
        "busy_at": 6,
        "empty_temperature": 26,
        "occupied_temperature": 24,
        "busy_temperature": 22,
    },
    "Meeting": {
        "ac_on_at": 1,
        "busy_at": 5,
        "empty_temperature": 26,
        "occupied_temperature": 22,
        "busy_temperature": 20,
    },
    "Eco": {
        "ac_on_at": 2,
        "busy_at": 6,
        "empty_temperature": 27,
        "occupied_temperature": 25,
        "busy_temperature": 23,
    },
}

DEFAULT_CONFIG = {
    "url": 0,
    "Arduino": False,
    "Arduino_Port": "COM4",
    "AC_Pin": 8,
    "Light_Pins": [],
    "Room_Name": "My Room",
    "Grid_Columns": GRID_COLUMNS,
    "Grid_Rows": GRID_ROWS,
    "Grid_Tilt_Degrees": 30,
    "Active_Profile": "Balanced",
    "Comfort_Profiles": DEFAULT_PROFILES,
}

COLORS = {
    "app": "#f3f8f5",
    "white": "#ffffff",
    "ink": "#18332d",
    "muted": "#71827b",
    "border": "#dfe9e3",
    "green": "#18a77b",
    "green_dark": "#087c5b",
    "green_pale": "#e0f5eb",
    "mint": "#f2faf5",
    "amber": "#ffc857",
    "amber_pale": "#fff4d7",
    "off": "#e9f0ec",
    "grid": "#edf2ef",
    "red": "#d16b54",
    "red_pale": "#fff0eb",
}

DEFAULT_STATE = {
    "current_occupancy": 0,
    "peak_occupancy": 0,
    "peak_time": "",
    "light_states": {},
    "ac_state": "OFF",
    "ac_temperature": 0,
    "active_profile": "Balanced",
    "occupied_cells": [],
    "grid_rows": GRID_ROWS,
    "grid_columns": GRID_COLUMNS,
    "camera_status": "unknown",
    "camera_last_frame_at": "",
    "detection_confidence": None,
    "controller_status": "not_configured",
    "recording_enabled": False,
    "updated_at": "",
}


def read_config():
    config = DEFAULT_CONFIG.copy()
    config["Comfort_Profiles"] = {
        name: dict(values) for name, values in DEFAULT_PROFILES.items()
    }
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return config
    if not isinstance(data, dict):
        return config

    config.update(data)
    profiles = config.get("Comfort_Profiles", {})
    merged_profiles = {name: dict(values) for name, values in DEFAULT_PROFILES.items()}
    if isinstance(profiles, dict):
        for name, values in profiles.items():
            if isinstance(values, dict):
                merged_profiles.setdefault(name, {}).update(values)
    config["Comfort_Profiles"] = merged_profiles
    return config


def save_config(config):
    temporary_path = CONFIG_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(config, indent=2) + "\n")
    temporary_path.replace(CONFIG_PATH)


def read_room_history(limit=3000):
    if not HISTORY_PATH.exists():
        return []
    try:
        with HISTORY_PATH.open(newline="") as file:
            rows = list(deque(csv.DictReader(file), maxlen=limit))
    except (OSError, csv.Error):
        return []

    history = []
    for row in rows:
        try:
            occupied_cells = json.loads(row.get("occupied_cells", "[]") or "[]")
            light_states = json.loads(row.get("light_states", "{}") or "{}")
            occupancy = max(0, int(row.get("current_occupancy", 0) or 0))
            grid_rows = max(1, int(row.get("grid_rows", GRID_ROWS) or GRID_ROWS))
            grid_columns = max(1, int(row.get("grid_columns", GRID_COLUMNS) or GRID_COLUMNS))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        history.append(
            {
                "timestamp": row.get("timestamp", ""),
                "current_occupancy": occupancy,
                "occupied_cells": occupied_cells if isinstance(occupied_cells, list) else [],
                "light_states": light_states if isinstance(light_states, dict) else {},
                "ac_state": row.get("ac_state", "OFF"),
                "ac_temperature": row.get("ac_temperature", ""),
                "active_profile": row.get("active_profile", "Balanced"),
                "grid_rows": grid_rows,
                "grid_columns": grid_columns,
            }
        )
    return history


def read_environmental_state():
    try:
        data = json.loads(TELEMETRY_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}

    readings = {"updated_at": data.get("updated_at", "")}
    for key in (
        "temperature_c",
        "humidity_percent",
        "co2_ppm",
        "power_w",
        "energy_today_kwh",
    ):
        value = data.get(key)
        try:
            number = float(value) if value is not None else None
        except (TypeError, ValueError):
            number = None
        readings[key] = number if number is not None and math.isfinite(number) else None
    return readings


def read_state():
    state = DEFAULT_STATE.copy()
    if not STATE_PATH.exists():
        return state

    try:
        data = json.loads(STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return state

    if isinstance(data, dict):
        state.update({key: value for key, value in data.items() if key in state})
    return state


def read_readings(limit=2500):
    if not READINGS_PATH.exists():
        return []

    try:
        with READINGS_PATH.open(newline="") as file:
            return list(deque(csv.DictReader(file), maxlen=limit))
    except (OSError, csv.Error):
        return []


def parse_timestamp(value):
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def format_timestamp(value):
    parsed = parse_timestamp(value)
    if parsed is None:
        return value or "—"
    return parsed.strftime("%b %d · %I:%M %p").replace(" 0", " ")


def recent_readings(rows, limit=8):
    labels = {
        "visible_count": "Occupancy update",
        "visible_reading": "Occupancy update",
        "device_status": "Lights & climate",
        "entry": "Person entered",
        "exit": "Person left",
        "reset": "Dashboard reset",
    }
    recent = []
    for row in reversed(rows[-limit:]):
        event = row.get("event", "")
        event_label = labels.get(event, event.replace("_", " ").title() or "Reading")
        count = row.get("current_occupancy", "0") or "0"
        timestamp = row.get("timestamp", "")
        recent.append((format_timestamp(timestamp), event_label, count))
    return recent


def occupancy_trend(rows):
    samples = []
    for row in rows:
        stamp = parse_timestamp(row.get("timestamp", ""))
        if stamp is None:
            continue
        try:
            count = max(0, int(float(row.get("current_occupancy", 0) or 0)))
        except (TypeError, ValueError):
            continue
        samples.append((stamp, count))

    if not samples:
        return "Today's room rhythm", [], []

    samples.sort(key=lambda item: item[0])
    today = date.today()
    today_samples = [sample for sample in samples if sample[0].date() == today]
    if today_samples:
        positioned = [
            (sample[0].hour * 3600 + sample[0].minute * 60 + sample[0].second, sample[1])
            for sample in today_samples
        ]
        day_seconds = 24 * 60 * 60
        chart_samples = [(seconds / day_seconds, count) for seconds, count in positioned]
        ticks = [(0.0, "12a"), (0.25, "6a"), (0.5, "12p"), (0.75, "6p"), (1.0, "12a")]
        return "Today's room rhythm", chart_samples, ticks

    latest_day = samples[-1][0].date()
    latest_samples = [sample for sample in samples if sample[0].date() == latest_day]
    first_stamp = latest_samples[0][0]
    last_stamp = latest_samples[-1][0]
    span = (last_stamp - first_stamp).total_seconds()
    if span <= 0:
        chart_samples = [(0.5, latest_samples[0][1])]
        tick_labels = [(0.5, first_stamp.strftime("%I:%M %p").lstrip("0"))]
    else:
        chart_samples = [
            ((stamp - first_stamp).total_seconds() / span, count)
            for stamp, count in latest_samples
        ]
        midpoint = first_stamp + (last_stamp - first_stamp) / 2
        tick_labels = [
            (0.0, first_stamp.strftime("%I:%M %p").lstrip("0")),
            (0.5, midpoint.strftime("%I:%M %p").lstrip("0")),
            (1.0, last_stamp.strftime("%I:%M %p").lstrip("0")),
        ]
    title = f"Saved trend · {latest_day.strftime('%b %d').replace(' 0', ' ')}"
    return title, chart_samples, tick_labels


def busiest_saved_hour(rows):
    samples = []
    for row in rows:
        stamp = parse_timestamp(row.get("timestamp", ""))
        try:
            count = max(0, int(float(row.get("current_occupancy", 0) or 0)))
        except (TypeError, ValueError):
            continue
        if stamp is not None:
            samples.append((stamp, count))
    if not samples:
        return "No room rhythm yet"

    today_samples = [sample for sample in samples if sample[0].date() == date.today()]
    if today_samples:
        samples = today_samples
    else:
        latest_day = max(stamp.date() for stamp, _count in samples)
        samples = [sample for sample in samples if sample[0].date() == latest_day]
    by_hour = {}
    for stamp, count in samples:
        by_hour.setdefault(stamp.hour, []).append(count)
    hour = max(by_hour, key=lambda value: sum(by_hour[value]) / len(by_hour[value]))
    display_hour = hour % 12 or 12
    meridiem = "AM" if hour < 12 else "PM"
    return f"Busiest saved hour · {display_hour} {meridiem}"


class OccupancyDashboard:
    def __init__(self, window):
        self.window = window
        self.window.title("iHVAC · Room dashboard")
        self.window.geometry("1280x920")
        self.window.minsize(1000, 760)
        self.window.configure(background=COLORS["app"])
        self._configure_styles()

        self.config = read_config()
        self._last_room_signature = None
        self._latest_light_states = {}
        self._display_snapshot = {}
        self._live_snapshot = {}
        self._room_history = []
        self._replay_index = None
        self._replay_playing = False
        self._playback_job = None
        self._setting_slider = False
        self.map_mode = tk.StringVar(value="Both")
        self._last_people_count = None
        self._last_trend = None
        self._last_readings = None
        self._last_history_signature = None
        self._pulse_jobs = []

        self._build_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self.refresh()

    def _configure_styles(self):
        style = ttk.Style(self.window)
        style.theme_use("clam")
        style.configure("App.TFrame", background=COLORS["app"])
        style.configure("Header.TLabel", background=COLORS["app"], foreground=COLORS["ink"])
        style.configure("Subheader.TLabel", background=COLORS["app"], foreground=COLORS["muted"])
        style.configure("CardTitle.TLabel", background=COLORS["white"], foreground=COLORS["ink"])
        style.configure("CardText.TLabel", background=COLORS["white"], foreground=COLORS["muted"])
        style.configure("Small.TButton", padding=(7, 3), font=("Helvetica", 9))
        style.configure(
            "Treeview",
            background=COLORS["white"],
            fieldbackground=COLORS["white"],
            foreground=COLORS["ink"],
            rowheight=25,
            borderwidth=0,
            font=("Helvetica", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#edf4ef",
            foreground=COLORS["muted"],
            font=("Helvetica", 9, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#d8f1e4")])

    def _card(self, parent):
        return tk.Frame(
            parent,
            background=COLORS["white"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )

    def _card_heading(self, parent, title, subtitle=None):
        heading = tk.Frame(parent, background=COLORS["white"])
        heading.pack(fill="x", padx=18, pady=(14, 2))
        tk.Label(
            heading,
            text=title,
            background=COLORS["white"],
            foreground=COLORS["ink"],
            font=("Helvetica", 14, "bold"),
        ).pack(side="left", anchor="w")
        if subtitle:
            tk.Label(
                heading,
                text=subtitle,
                background=COLORS["white"],
                foreground=COLORS["muted"],
                font=("Helvetica", 9),
            ).pack(side="right", anchor="e")
        return heading

    def _build_ui(self):
        outer = ttk.Frame(self.window, style="App.TFrame", padding=(24, 18, 24, 14))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=5, minsize=235)
        outer.rowconfigure(2, weight=4, minsize=190)
        outer.rowconfigure(3, weight=2, minsize=120)

        self._build_header(outer)
        self._build_top_row(outer)
        self._build_middle_row(outer)
        self._build_activity(outer)

        self.status_value = ttk.Label(
            outer,
            style="Subheader.TLabel",
            font=("Helvetica", 9),
            anchor="w",
        )
        self.status_value.grid(row=4, column=0, sticky="ew", pady=(9, 0))

    def _build_header(self, outer):
        header = ttk.Frame(outer, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 13))

        brand = ttk.Frame(header, style="App.TFrame")
        brand.pack(side="left", fill="y")
        mark = tk.Canvas(
            brand,
            width=40,
            height=40,
            background=COLORS["app"],
            highlightthickness=0,
        )
        mark.pack(side="left", padx=(0, 10))
        mark.create_oval(2, 2, 38, 38, fill=COLORS["green_dark"], outline="")
        mark.create_oval(15, 15, 25, 25, fill="#d8f7e8", outline="")
        for angle in (0, 120, 240):
            mark.create_arc(
                8,
                8,
                32,
                32,
                start=angle,
                extent=70,
                style="arc",
                outline="#a7ebc9",
                width=2,
            )

        brand_text = ttk.Frame(brand, style="App.TFrame")
        brand_text.pack(side="left", anchor="center")
        ttk.Label(
            brand_text,
            text="iHVAC",
            style="Header.TLabel",
            font=("Helvetica", 22, "bold"),
        ).pack(anchor="w")
        self.room_subtitle = ttk.Label(
            brand_text,
            text=f"{self.config.get('Room_Name', 'My Room')} · comfort that follows the room",
            style="Subheader.TLabel",
            font=("Helvetica", 10),
        )
        self.room_subtitle.pack(anchor="w", pady=(1, 0))

        actions = tk.Frame(header, background=COLORS["app"])
        actions.pack(side="right", anchor="center", pady=(5, 0))
        self.camera_badge = self._status_pill(actions, "CAMERA · UNKNOWN", COLORS["off"], COLORS["muted"])
        self.controller_badge = self._status_pill(actions, "CONTROLLER · —", COLORS["off"], COLORS["muted"])
        self.privacy_badge = self._status_pill(actions, "LOCAL · NO VIDEO SAVED", COLORS["green_pale"], COLORS["green_dark"])
        setup_button = tk.Button(
            actions,
            text="⚙ Room setup",
            command=self._open_settings,
            background=COLORS["white"],
            foreground=COLORS["ink"],
            activebackground=COLORS["green_pale"],
            activeforeground=COLORS["green_dark"],
            relief="flat",
            bd=0,
            padx=11,
            pady=7,
            font=("Helvetica", 9, "bold"),
            cursor="hand2",
        )
        setup_button.pack(side="left", padx=(4, 0))

    def _status_pill(self, parent, text, background, foreground):
        label = tk.Label(
            parent,
            text=text,
            background=background,
            foreground=foreground,
            font=("Helvetica", 8, "bold"),
            padx=8,
            pady=6,
        )
        label.pack(side="left", padx=(0, 5))
        return label

    def _build_top_row(self, outer):
        row = ttk.Frame(outer, style="App.TFrame")
        row.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        row.columnconfigure(0, weight=5, minsize=310)
        row.columnconfigure(1, weight=9, minsize=490)
        row.rowconfigure(0, weight=1)

        self._build_occupancy_card(row)
        self._build_room_card(row)

    def _build_occupancy_card(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._card_heading(card, "Who's here?", "RIGHT NOW")

        body = tk.Frame(card, background=COLORS["white"])
        body.pack(fill="x", padx=18, pady=(1, 1))
        body.columnconfigure(0, weight=1)

        count_area = tk.Frame(body, background=COLORS["white"])
        count_area.grid(row=0, column=0, sticky="w")
        self.count_value = tk.Label(
            count_area,
            text="0",
            background=COLORS["white"],
            foreground=COLORS["green_dark"],
            font=("Helvetica", 49, "bold"),
        )
        self.count_value.pack(side="left", anchor="center")
        tk.Label(
            count_area,
            text=" people\nin the room",
            justify="left",
            background=COLORS["white"],
            foreground=COLORS["muted"],
            font=("Helvetica", 11),
        ).pack(side="left", anchor="center", padx=(7, 0), pady=(10, 0))

        self.people_canvas = tk.Canvas(
            body,
            width=118,
            height=70,
            background=COLORS["white"],
            highlightthickness=0,
        )
        self.people_canvas.grid(row=0, column=1, sticky="e", padx=(3, 0))
        self.people_canvas.bind("<Configure>", lambda _event: self._draw_people_icons(force=True))

        self.mood_label = tk.Label(
            card,
            text="The room is ready for you",
            background=COLORS["green_pale"],
            foreground=COLORS["green_dark"],
            font=("Helvetica", 10, "bold"),
            padx=10,
            pady=6,
            anchor="w",
        )
        self.mood_label.pack(fill="x", padx=18, pady=(4, 10))
        self.peak_caption = ttk.Label(
            card,
            text="Peak seen · 0 people",
            style="CardText.TLabel",
            font=("Helvetica", 9),
        )
        self.peak_caption.pack(anchor="w", padx=18, pady=(0, 12))

    def _build_room_card(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=1, sticky="nsew")
        heading = self._card_heading(card, "Room activity map", "PEOPLE + LIGHTS")
        self.zone_count = tk.Label(
            heading,
            text="0 / 48 ZONES ON",
            background=COLORS["amber_pale"],
            foreground="#815d0b",
            font=("Helvetica", 8, "bold"),
            padx=8,
            pady=4,
        )
        self.zone_count.pack(side="right", anchor="e", padx=(8, 0))

        mode_bar = tk.Frame(card, background=COLORS["white"])
        mode_bar.pack(fill="x", padx=16, pady=(2, 4))
        tk.Label(
            mode_bar,
            text="Show",
            background=COLORS["white"],
            foreground=COLORS["muted"],
            font=("Helvetica", 9),
        ).pack(side="left", padx=(0, 7))
        for label in ("People", "Lights", "Both"):
            tk.Radiobutton(
                mode_bar,
                text=label,
                value=label,
                variable=self.map_mode,
                command=self._on_map_mode_changed,
                indicatoron=False,
                selectcolor=COLORS["green_pale"],
                background=COLORS["off"],
                foreground=COLORS["ink"],
                activebackground=COLORS["green_pale"],
                activeforeground=COLORS["green_dark"],
                relief="flat",
                bd=0,
                padx=9,
                pady=4,
                font=("Helvetica", 8, "bold"),
                cursor="hand2",
            ).pack(side="left", padx=(0, 4))

        self.room_canvas = tk.Canvas(
            card,
            background=COLORS["white"],
            highlightthickness=0,
            height=160,
        )
        self.room_canvas.pack(fill="both", expand=True, padx=(8, 8), pady=(0, 1))
        self.room_canvas.bind("<Configure>", lambda _event: self._draw_room_map(force=True))
        self.room_canvas.bind("<Motion>", self._on_room_hover)
        self.room_canvas.bind("<Leave>", self._on_room_leave)

        legend = tk.Frame(card, background=COLORS["white"])
        legend.pack(fill="x", padx=18, pady=(0, 11))
        self._legend_item(legend, "#72c993", "People")
        self._legend_item(legend, COLORS["amber"], "Lights on")
        self.map_hint = tk.Label(
            legend,
            text="Hover to inspect a zone",
            background=COLORS["white"],
            foreground=COLORS["muted"],
            font=("Helvetica", 9),
        )
        self.map_hint.pack(side="right")

    def _legend_item(self, parent, color, label):
        icon = tk.Canvas(
            parent,
            width=12,
            height=12,
            background=COLORS["white"],
            highlightthickness=0,
        )
        icon.create_oval(2, 2, 10, 10, fill=color, outline="")
        icon.pack(side="left", padx=(0, 4))
        tk.Label(
            parent,
            text=label,
            background=COLORS["white"],
            foreground=COLORS["muted"],
            font=("Helvetica", 9),
        ).pack(side="left", padx=(0, 10))

    def _build_middle_row(self, outer):
        row = ttk.Frame(outer, style="App.TFrame")
        row.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        row.columnconfigure(0, weight=6, minsize=390)
        row.columnconfigure(1, weight=3, minsize=230)
        row.columnconfigure(2, weight=4, minsize=275)
        row.rowconfigure(0, weight=1)

        self._build_trend_card(row)
        self._build_climate_card(row)
        self._build_sensors_card(row)

    def _build_trend_card(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        heading = tk.Frame(card, background=COLORS["white"])
        heading.pack(fill="x", padx=18, pady=(14, 2))
        self.trend_title = tk.Label(
            heading,
            text="Today's room rhythm",
            background=COLORS["white"],
            foreground=COLORS["ink"],
            font=("Helvetica", 14, "bold"),
        )
        self.trend_title.pack(side="left", anchor="w")
        self.trend_insight = tk.Label(
            heading,
            text="SAVED OCCUPANCY",
            background=COLORS["white"],
            foreground=COLORS["green_dark"],
            font=("Helvetica", 8, "bold"),
        )
        self.trend_insight.pack(side="right", anchor="e")

        self.trend_canvas = tk.Canvas(
            card,
            background=COLORS["white"],
            highlightthickness=0,
            height=145,
        )
        self.trend_canvas.pack(fill="both", expand=True, padx=(12, 14), pady=(0, 8))
        self.trend_canvas.bind("<Configure>", lambda _event: self._draw_trend(force=True))

        replay_bar = tk.Frame(card, background=COLORS["white"])
        replay_bar.pack(fill="x", padx=14, pady=(0, 10))
        self.live_button = tk.Button(
            replay_bar,
            text="● LIVE",
            command=self._return_to_live,
            background=COLORS["green_pale"],
            foreground=COLORS["green_dark"],
            activebackground=COLORS["green_pale"],
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            font=("Helvetica", 8, "bold"),
            cursor="hand2",
        )
        self.live_button.pack(side="left", padx=(0, 5))
        self.play_button = tk.Button(
            replay_bar,
            text="▶",
            command=self._toggle_replay,
            background=COLORS["off"],
            foreground=COLORS["ink"],
            activebackground=COLORS["green_pale"],
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            font=("Helvetica", 8, "bold"),
            cursor="hand2",
        )
        self.play_button.pack(side="left", padx=(0, 7))
        self.history_slider = ttk.Scale(
            replay_bar,
            from_=0,
            to=0,
            orient="horizontal",
            command=self._on_history_seek,
        )
        self.history_slider.pack(side="left", fill="x", expand=True, padx=(0, 9))
        self.replay_time = tk.Label(
            replay_bar,
            text="Waiting for zone history",
            background=COLORS["white"],
            foreground=COLORS["muted"],
            font=("Helvetica", 8),
            width=18,
            anchor="e",
        )
        self.replay_time.pack(side="right")

    def _build_climate_card(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=1, sticky="nsew")
        heading = self._card_heading(card, "Climate", "AUTO ADJUST")
        self.ac_badge = tk.Label(
            heading,
            text="AC OFF",
            background=COLORS["off"],
            foreground=COLORS["muted"],
            font=("Helvetica", 8, "bold"),
            padx=9,
            pady=4,
        )
        self.ac_badge.pack(side="right", anchor="e", padx=(8, 0))

        temp_row = tk.Frame(card, background=COLORS["white"])
        temp_row.pack(fill="x", padx=18, pady=(9, 0))
        self.temperature_value = tk.Label(
            temp_row,
            text="26°C",
            background=COLORS["white"],
            foreground=COLORS["ink"],
            font=("Helvetica", 37, "bold"),
        )
        self.temperature_value.pack(side="left", anchor="center")
        tk.Label(
            temp_row,
            text="target\ntemperature",
            justify="left",
            background=COLORS["white"],
            foreground=COLORS["muted"],
            font=("Helvetica", 10),
        ).pack(side="left", padx=(8, 0), pady=(5, 0))

        self.climate_note = tk.Label(
            card,
            text="Waiting for people",
            background=COLORS["mint"],
            foreground=COLORS["green_dark"],
            anchor="w",
            justify="left",
            font=("Helvetica", 9),
            padx=10,
            pady=7,
        )
        self.climate_note.pack(fill="x", padx=18, pady=(8, 8))
        self.climate_footer = ttk.Label(
            card,
            text="Comfort responds to room occupancy",
            style="CardText.TLabel",
            font=("Helvetica", 9),
        )
        self.climate_footer.pack(anchor="w", padx=18, pady=(0, 11))

    def _build_sensors_card(self, parent):
        card = self._card(parent)
        card.grid(row=0, column=2, sticky="nsew")
        heading = self._card_heading(card, "Room signals", "MEASURED")
        self.environment_status = tk.Label(
            heading,
            text="NO SENSOR DATA",
            background=COLORS["off"],
            foreground=COLORS["muted"],
            font=("Helvetica", 8, "bold"),
            padx=7,
            pady=4,
        )
        self.environment_status.pack(side="right", anchor="e", padx=(8, 0))

        grid = tk.Frame(card, background=COLORS["white"])
        grid.pack(fill="both", expand=True, padx=14, pady=(7, 12))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)
        self.sensor_values = {}
        sensors = [
            ("temperature_c", "ROOM TEMP", "°C"),
            ("humidity_percent", "HUMIDITY", "%"),
            ("co2_ppm", "CO₂", "ppm"),
            ("power_w", "POWER NOW", "W"),
        ]
        for index, (key, label, unit) in enumerate(sensors):
            tile = tk.Frame(
                grid,
                background=COLORS["mint"],
                highlightbackground=COLORS["grid"],
                highlightthickness=1,
            )
            tile.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=(0 if index % 2 == 0 else 5, 5 if index % 2 == 0 else 0),
                pady=(0 if index < 2 else 5, 5 if index < 2 else 0),
            )
            tk.Label(
                tile,
                text=label,
                background=COLORS["mint"],
                foreground=COLORS["muted"],
                font=("Helvetica", 8, "bold"),
            ).pack(anchor="w", padx=9, pady=(7, 1))
            value = tk.Label(
                tile,
                text="—",
                background=COLORS["mint"],
                foreground=COLORS["ink"],
                font=("Helvetica", 17, "bold"),
            )
            value.pack(anchor="w", padx=9)
            tk.Label(
                tile,
                text=unit,
                background=COLORS["mint"],
                foreground=COLORS["muted"],
                font=("Helvetica", 8),
            ).pack(anchor="w", padx=9, pady=(0, 7))
            self.sensor_values[key] = value
        self.energy_today = ttk.Label(
            card,
            text="Energy today · — kWh",
            style="CardText.TLabel",
            font=("Helvetica", 8),
        )
        self.energy_today.pack(anchor="w", padx=16, pady=(0, 8))

    def _build_activity(self, outer):
        card = self._card(outer)
        card.grid(row=3, column=0, sticky="nsew")
        self._card_heading(card, "Recent saved readings", "FROM THE CAMERA LOG")

        table_frame = tk.Frame(card, background=COLORS["white"])
        table_frame.pack(fill="both", expand=True, padx=(14, 14), pady=(3, 11))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("timestamp", "event", "people")
        self.readings_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=4,
            selectmode="browse",
        )
        headings = {"timestamp": "TIME", "event": "EVENT", "people": "PEOPLE"}
        widths = {"timestamp": 220, "event": 260, "people": 100}
        for column in columns:
            self.readings_table.heading(column, text=headings[column])
            self.readings_table.column(
                column,
                width=widths[column],
                anchor="w" if column != "people" else "center",
                stretch=column != "people",
            )
        self.readings_table.tag_configure("even", background=COLORS["white"])
        self.readings_table.tag_configure("odd", background="#f8fbf9")
        self.readings_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.readings_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.readings_table.configure(yscrollcommand=scrollbar.set)

    def _open_settings(self):
        config = read_config()
        dialog = tk.Toplevel(self.window)
        dialog.title("Room setup")
        dialog.geometry("470x650")
        dialog.resizable(False, False)
        dialog.configure(background=COLORS["app"])
        dialog.transient(self.window)
        dialog.grab_set()

        content = tk.Frame(dialog, background=COLORS["app"], padx=22, pady=18)
        content.pack(fill="both", expand=True)
        tk.Label(
            content,
            text="Make this room yours",
            background=COLORS["app"],
            foreground=COLORS["ink"],
            font=("Helvetica", 19, "bold"),
        ).pack(anchor="w")
        tk.Label(
            content,
            text="Name the space, line up the map, and tune comfort presets.",
            background=COLORS["app"],
            foreground=COLORS["muted"],
            font=("Helvetica", 9),
        ).pack(anchor="w", pady=(3, 14))

        form = tk.Frame(content, background=COLORS["white"], padx=14, pady=12)
        form.pack(fill="x")

        def add_field(parent, label, value, width=12):
            row = tk.Frame(parent, background=COLORS["white"])
            row.pack(fill="x", pady=4)
            tk.Label(
                row,
                text=label,
                background=COLORS["white"],
                foreground=COLORS["muted"],
                font=("Helvetica", 9),
                width=22,
                anchor="w",
            ).pack(side="left")
            variable = tk.StringVar(value=str(value))
            entry = ttk.Entry(row, textvariable=variable, width=width)
            entry.pack(side="right")
            return variable

        room_name = add_field(form, "Room name", config.get("Room_Name", "My Room"), width=20)

        calibration = tk.Frame(content, background=COLORS["white"], padx=14, pady=12)
        calibration.pack(fill="x", pady=(10, 0))
        tk.Label(
            calibration,
            text="ROOM MAP CALIBRATION",
            background=COLORS["white"],
            foreground=COLORS["green_dark"],
            font=("Helvetica", 9, "bold"),
        ).pack(anchor="w", pady=(0, 5))
        rows = add_field(calibration, "Grid rows (1–12)", config.get("Grid_Rows", GRID_ROWS))
        columns = add_field(calibration, "Grid columns (1–12)", config.get("Grid_Columns", GRID_COLUMNS))
        tilt = add_field(calibration, "Camera downward angle (°)", config.get("Grid_Tilt_Degrees", 30))

        comfort = tk.Frame(content, background=COLORS["white"], padx=14, pady=12)
        comfort.pack(fill="x", pady=(10, 0))
        tk.Label(
            comfort,
            text="COMFORT PROFILE",
            background=COLORS["white"],
            foreground=COLORS["green_dark"],
            font=("Helvetica", 9, "bold"),
        ).pack(anchor="w", pady=(0, 5))
        profiles = config.get("Comfort_Profiles", DEFAULT_PROFILES)
        profile_name = tk.StringVar(value=config.get("Active_Profile", "Balanced"))
        profile_row = tk.Frame(comfort, background=COLORS["white"])
        profile_row.pack(fill="x", pady=(0, 5))
        tk.Label(
            profile_row,
            text="Active preset",
            background=COLORS["white"],
            foreground=COLORS["muted"],
            font=("Helvetica", 9),
        ).pack(side="left")
        profile_picker = ttk.Combobox(
            profile_row,
            textvariable=profile_name,
            values=tuple(DEFAULT_PROFILES),
            state="readonly",
            width=15,
        )
        profile_picker.pack(side="right")

        current_profile = profiles.get(profile_name.get(), DEFAULT_PROFILES["Balanced"])
        on_at = add_field(comfort, "Turn AC on at (people)", current_profile.get("ac_on_at", 1))
        busy_at = add_field(comfort, "Busy room at (people)", current_profile.get("busy_at", 5))
        empty_temp = add_field(comfort, "Empty room target (°C)", current_profile.get("empty_temperature", 26))
        occupied_temp = add_field(comfort, "Occupied target (°C)", current_profile.get("occupied_temperature", 23))
        busy_temp = add_field(comfort, "Busy room target (°C)", current_profile.get("busy_temperature", 21))

        def load_profile(_event=None):
            selected = profiles.get(profile_name.get(), DEFAULT_PROFILES["Balanced"])
            on_at.set(str(selected.get("ac_on_at", 1)))
            busy_at.set(str(selected.get("busy_at", 5)))
            empty_temp.set(str(selected.get("empty_temperature", 26)))
            occupied_temp.set(str(selected.get("occupied_temperature", 23)))
            busy_temp.set(str(selected.get("busy_temperature", 21)))

        profile_picker.bind("<<ComboboxSelected>>", load_profile)

        tk.Label(
            content,
            text="Comfort edits apply live. Changing map dimensions or angle rebuilds the room grid.",
            background=COLORS["app"],
            foreground=COLORS["muted"],
            justify="left",
            wraplength=410,
            font=("Helvetica", 9),
        ).pack(anchor="w", pady=(11, 7))

        buttons = tk.Frame(content, background=COLORS["app"])
        buttons.pack(fill="x", pady=(5, 0))
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=(7, 0))

        def save_settings():
            try:
                next_rows = int(rows.get())
                next_columns = int(columns.get())
                next_tilt = float(tilt.get())
                next_on_at = int(on_at.get())
                next_busy_at = int(busy_at.get())
                next_empty_temp = int(empty_temp.get())
                next_occupied_temp = int(occupied_temp.get())
                next_busy_temp = int(busy_temp.get())
            except ValueError:
                messagebox.showerror("Check the values", "Enter whole numbers for grid, thresholds, and temperatures.", parent=dialog)
                return

            if not room_name.get().strip():
                messagebox.showerror("Room name needed", "Enter a short name for this room.", parent=dialog)
                return
            if not 1 <= next_rows <= 12 or not 1 <= next_columns <= 12 or next_rows * next_columns > 48:
                messagebox.showerror("Grid size out of range", "Use 1–12 rows and columns, with no more than 48 total zones.", parent=dialog)
                return
            if not 1 <= next_tilt <= 89:
                messagebox.showerror("Angle out of range", "The downward camera angle must be between 1° and 89°.", parent=dialog)
                return
            if next_on_at < 1 or next_busy_at < next_on_at:
                messagebox.showerror("Thresholds out of order", "Busy-room occupancy must be at least the AC-on occupancy.", parent=dialog)
                return
            if any(not 16 <= value <= 30 for value in (next_empty_temp, next_occupied_temp, next_busy_temp)):
                messagebox.showerror("Temperature out of range", "Choose target temperatures from 16°C to 30°C.", parent=dialog)
                return

            profile = {
                "ac_on_at": next_on_at,
                "busy_at": next_busy_at,
                "empty_temperature": next_empty_temp,
                "occupied_temperature": next_occupied_temp,
                "busy_temperature": next_busy_temp,
            }
            config["Room_Name"] = room_name.get().strip()[:40]
            config["Grid_Rows"] = next_rows
            config["Grid_Columns"] = next_columns
            config["Grid_Tilt_Degrees"] = next_tilt
            config.setdefault("Comfort_Profiles", {}).setdefault(profile_name.get(), {}).update(profile)
            config["Active_Profile"] = profile_name.get()
            try:
                save_config(config)
            except OSError as error:
                messagebox.showerror("Could not save", str(error), parent=dialog)
                return
            self.config = read_config()
            self.room_subtitle.configure(
                text=f"{self.config['Room_Name']} · comfort that follows the room"
            )
            self._last_room_signature = None
            dialog.destroy()

        ttk.Button(buttons, text="Save room setup", command=save_settings).pack(side="right")

    def _return_to_live(self):
        self._replay_index = None
        self._replay_playing = False
        if self._playback_job is not None:
            self.window.after_cancel(self._playback_job)
            self._playback_job = None
        self._display_snapshot = dict(self._live_snapshot)
        self.live_button.configure(text="● LIVE", background=COLORS["green_pale"])
        self.play_button.configure(text="▶")
        self.replay_time.configure(text="Live room activity")
        self._last_room_signature = None
        self._draw_room_map(force=True)

    def _on_history_seek(self, value):
        if self._setting_slider or not self._room_history:
            return
        self._replay_playing = False
        if self._playback_job is not None:
            self.window.after_cancel(self._playback_job)
            self._playback_job = None
        self._replay_index = max(0, min(len(self._room_history) - 1, int(float(value))))
        self.play_button.configure(text="▶")
        self._show_history_snapshot()

    def _show_history_snapshot(self):
        if self._replay_index is None or not self._room_history:
            return
        self._replay_index = max(0, min(len(self._room_history) - 1, self._replay_index))
        self._display_snapshot = self._room_history[self._replay_index]
        stamp = format_timestamp(self._display_snapshot.get("timestamp", ""))
        self.replay_time.configure(text=stamp)
        self.live_button.configure(text="RETURN LIVE", background=COLORS["amber_pale"])
        self._last_room_signature = None
        self._draw_room_map(force=True)

    def _toggle_replay(self):
        if not self._room_history:
            return
        if self._replay_playing:
            self._replay_playing = False
            self.play_button.configure(text="▶")
            if self._playback_job is not None:
                self.window.after_cancel(self._playback_job)
                self._playback_job = None
            return
        if self._replay_index is None:
            self._replay_index = 0
        self._replay_playing = True
        self.play_button.configure(text="Ⅱ")
        self._show_history_snapshot()
        self._playback_step()

    def _playback_step(self):
        if not self._replay_playing or not self._room_history:
            return
        if self._replay_index is None or self._replay_index >= len(self._room_history) - 1:
            self._replay_playing = False
            self.play_button.configure(text="▶")
            self._playback_job = None
            return
        self._replay_index += 1
        self._setting_slider = True
        self.history_slider.set(self._replay_index)
        self._setting_slider = False
        self._show_history_snapshot()
        self._playback_job = self.window.after(650, self._playback_step)

    def _draw_people_icons(self, force=False):
        count = self._last_people_count or 0
        canvas = self.people_canvas
        width = max(canvas.winfo_width(), 118)
        height = max(canvas.winfo_height(), 60)
        signature = (count, width, height)
        if not force and getattr(self, "_people_signature", None) == signature:
            return
        self._people_signature = signature
        canvas.delete("all")

        if count <= 0:
            for index, color in enumerate(("#b8e8ce", "#d8f3e3", "#e8f8ee")):
                x = width / 2 + (index - 1) * 17
                canvas.create_oval(x - 4, height / 2 - 4, x + 4, height / 2 + 4, fill=color, outline="")
            return

        visible = min(count, 5)
        has_more = count > visible
        spacing = 22
        total_width = visible * spacing + (26 if has_more else 0)
        start_x = max(13, (width - total_width) / 2 + spacing / 2)
        center_y = height / 2 + 1
        for index in range(visible):
            x = start_x + index * spacing
            color = COLORS["green"] if index % 2 == 0 else COLORS["green_dark"]
            canvas.create_oval(x - 4, center_y - 17, x + 4, center_y - 9, fill=color, outline="")
            canvas.create_oval(x - 7, center_y - 7, x + 7, center_y + 12, fill=color, outline="")
        if has_more:
            canvas.create_text(
                start_x + visible * spacing + 1,
                center_y,
                text=f"+{count - visible}",
                anchor="w",
                fill=COLORS["muted"],
                font=("Helvetica", 9, "bold"),
            )

    def _draw_room_map(self, force=False):
        canvas = self.room_canvas
        width = max(canvas.winfo_width(), 250)
        height = max(canvas.winfo_height(), 120)
        snapshot = self._display_snapshot or self._live_snapshot
        states = snapshot.get("light_states", {})
        occupied = set(snapshot.get("occupied_cells", []))
        try:
            rows = max(1, int(snapshot.get("grid_rows", self.config.get("Grid_Rows", GRID_ROWS))))
            columns = max(1, int(snapshot.get("grid_columns", self.config.get("Grid_Columns", GRID_COLUMNS))))
        except (TypeError, ValueError):
            rows, columns = GRID_ROWS, GRID_COLUMNS
        if rows * columns > 48:
            rows, columns = GRID_ROWS, GRID_COLUMNS
        mode = self.map_mode.get()
        state_signature = tuple(
            (
                key,
                bool(states.get(key, False)),
                key in occupied,
            )
            for row in range(rows)
            for column in range(columns)
            for key in (f"r{row + 1}c{column + 1}",)
        )
        signature = (width, height, state_signature, mode, rows, columns)
        if not force and signature == self._last_room_signature:
            return
        self._last_room_signature = signature

        canvas.delete("all")
        self.map_polygons = {}
        self._map_dimensions = (rows, columns)
        left = 42
        right = width - 12
        top = 25
        bottom = height - 8
        room_width = right - left
        row_height = (bottom - top) / rows

        def room_x(normalized, row_fraction):
            fraction = 0.72 + 0.28 * row_fraction
            visible_width = room_width * fraction
            room_left = (left + right - visible_width) / 2
            return room_left + normalized * visible_width

        room_outline = [
            (room_x(0, 0), top),
            (room_x(1, 0), top),
            (room_x(1, 1), bottom),
            (room_x(0, 1), bottom),
        ]
        canvas.create_polygon(
            [coordinate for point in room_outline for coordinate in point],
            fill=COLORS["mint"],
            outline="#d5e5dc",
            width=1,
        )

        for column in range(columns):
            x = room_x((column + 0.5) / columns, 0)
            canvas.create_text(
                x,
                top - 11,
                text=chr(ord("A") + column),
                fill=COLORS["muted"],
                font=("Helvetica", 8, "bold"),
            )

        for row in range(rows):
            row_top = top + row * row_height
            row_bottom = top + (row + 1) * row_height
            top_fraction = row / rows
            bottom_fraction = (row + 1) / rows
            canvas.create_text(
                22,
                (row_top + row_bottom) / 2,
                text=str(row + 1),
                fill=COLORS["muted"],
                font=("Helvetica", 8),
            )
            for column in range(columns):
                key = f"r{row + 1}c{column + 1}"
                normalized_left = column / columns
                normalized_right = (column + 1) / columns
                polygon = [
                    (room_x(normalized_left, top_fraction), row_top),
                    (room_x(normalized_right, top_fraction), row_top),
                    (room_x(normalized_right, bottom_fraction), row_bottom),
                    (room_x(normalized_left, bottom_fraction), row_bottom),
                ]
                self.map_polygons[key] = polygon
                person_here = key in occupied
                light_on = bool(states.get(key, False))
                show_person = mode in {"People", "Both"} and person_here
                show_light = mode in {"Lights", "Both"} and light_on
                if mode == "People":
                    fill = "#ccefd9" if show_person else COLORS["off"]
                elif mode == "Lights":
                    fill = COLORS["amber"] if show_light else COLORS["off"]
                elif show_person and show_light:
                    fill = "#d7f0e3"
                elif show_person:
                    fill = "#ccefd9"
                elif show_light:
                    fill = COLORS["amber"]
                else:
                    fill = COLORS["off"]
                canvas.create_polygon(
                    [coordinate for point in polygon for coordinate in point],
                    fill=fill,
                    outline=COLORS["white"],
                    width=2,
                    tags=(key,),
                )
                if show_person or show_light:
                    center_x = sum(point[0] for point in polygon) / 4
                    center_y = sum(point[1] for point in polygon) / 4
                if show_person and show_light:
                    canvas.create_oval(
                        center_x - 6,
                        center_y - 2.6,
                        center_x - 0.5,
                        center_y + 2.6,
                        fill=COLORS["green_dark"],
                        outline="",
                        tags=(key,),
                    )
                    canvas.create_oval(
                        center_x + 0.5,
                        center_y - 2.6,
                        center_x + 6,
                        center_y + 2.6,
                        fill="#d39100",
                        outline="",
                        tags=(key,),
                    )
                elif show_person:
                    canvas.create_oval(
                        center_x - 2.5,
                        center_y - 2.5,
                        center_x + 2.5,
                        center_y + 2.5,
                        fill=COLORS["green_dark"],
                        outline="",
                        tags=(key,),
                    )
                elif show_light:
                    canvas.create_oval(
                        center_x - 2.5,
                        center_y - 2.5,
                        center_x + 2.5,
                        center_y + 2.5,
                        fill="#fff9e7",
                        outline="#d39100",
                        width=1,
                        tags=(key,),
                    )

        people_zones = sum(1 for _key, _light, person in state_signature if person)
        lit_zones = sum(1 for _key, light, _person in state_signature if light)
        self.zone_count.configure(text=f"{people_zones} PEOPLE ZONES · {lit_zones} LIGHTS")

    def _on_map_mode_changed(self):
        self._last_room_signature = None
        self._draw_room_map(force=True)

    def _update_environment(self, readings):
        formats = {
            "temperature_c": (1, "°C"),
            "humidity_percent": (0, "%"),
            "co2_ppm": (0, " ppm"),
            "power_w": (0, " W"),
        }
        available = 0
        for key, (precision, suffix) in formats.items():
            value = readings.get(key)
            if value is None:
                display = "—"
            else:
                available += 1
                display = f"{value:.{precision}f}{suffix}"
            self.sensor_values[key].configure(text=display)

        energy = readings.get("energy_today_kwh")
        if energy is not None:
            available += 1
        energy_text = "— kWh" if energy is None else f"{energy:.2f} kWh"
        self.energy_today.configure(text=f"Measured energy today · {energy_text}")

        stamp = parse_timestamp(readings.get("updated_at", ""))
        if not available and energy is None:
            label, background, foreground = "NO SENSOR DATA", COLORS["off"], COLORS["muted"]
        elif stamp is None:
            label, background, foreground = "NO TIMESTAMP", COLORS["amber_pale"], "#815d0b"
        else:
            age = (datetime.now() - stamp).total_seconds()
            if age <= 90:
                label, background, foreground = f"LIVE · {available} SIGNALS", COLORS["green_pale"], COLORS["green_dark"]
            else:
                label, background, foreground = "SENSOR DATA STALE", COLORS["amber_pale"], "#815d0b"
        self.environment_status.configure(
            text=label,
            background=background,
            foreground=foreground,
        )

    def _update_system_health(self, state):
        camera = str(state.get("camera_status", "unknown")).lower()
        frame_stamp = parse_timestamp(state.get("camera_last_frame_at", ""))
        if camera == "online" and frame_stamp is not None:
            age = (datetime.now() - frame_stamp).total_seconds()
            if age > 10:
                camera = "stale"
        camera_styles = {
            "online": ("CAMERA · ONLINE", COLORS["green_pale"], COLORS["green_dark"]),
            "stale": ("CAMERA · STALE", COLORS["amber_pale"], "#815d0b"),
            "offline": ("CAMERA · OFFLINE", COLORS["red_pale"], COLORS["red"]),
            "starting": ("CAMERA · STARTING", COLORS["amber_pale"], "#815d0b"),
        }
        camera_text, camera_bg, camera_fg = camera_styles.get(
            camera,
            ("CAMERA · UNKNOWN", COLORS["off"], COLORS["muted"]),
        )
        self.camera_badge.configure(text=camera_text, background=camera_bg, foreground=camera_fg)

        controller = str(state.get("controller_status", "not_configured")).lower()
        controller_styles = {
            "connected": ("CONTROLLER · READY", COLORS["green_pale"], COLORS["green_dark"]),
            "offline": ("CONTROLLER · OFFLINE", COLORS["red_pale"], COLORS["red"]),
            "not_configured": ("CONTROLLER · SIMULATED", COLORS["off"], COLORS["muted"]),
        }
        controller_text, controller_bg, controller_fg = controller_styles.get(
            controller,
            ("CONTROLLER · UNKNOWN", COLORS["off"], COLORS["muted"]),
        )
        self.controller_badge.configure(
            text=controller_text,
            background=controller_bg,
            foreground=controller_fg,
        )
        recording = bool(state.get("recording_enabled", False))
        self.privacy_badge.configure(
            text="LOCAL · SAVING VIDEO" if recording else "LOCAL · NO VIDEO SAVED",
            background=COLORS["amber_pale"] if recording else COLORS["green_pale"],
            foreground="#815d0b" if recording else COLORS["green_dark"],
        )

        confidence = state.get("detection_confidence")
        if confidence is None:
            confidence_text = "Detection confidence · —"
        else:
            try:
                confidence_text = f"Mean detection confidence · {float(confidence) * 100:.0f}%"
            except (TypeError, ValueError):
                confidence_text = "Mean detection confidence · —"
        last_frame = format_timestamp(state.get("camera_last_frame_at", ""))
        return camera_text, confidence_text, last_frame

    def _point_in_polygon(self, x, y, polygon):
        inside = False
        previous = polygon[-1]
        for current in polygon:
            x1, y1 = previous
            x2, y2 = current
            if (y1 > y) != (y2 > y):
                intersection = (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-9) + x1
                if x < intersection:
                    inside = not inside
            previous = current
        return inside

    def _on_room_hover(self, event):
        for key, polygon in getattr(self, "map_polygons", {}).items():
            if self._point_in_polygon(event.x, event.y, polygon):
                row = int(key[1:key.index("c")])
                column = int(key[key.index("c") + 1:])
                snapshot = self._display_snapshot or self._live_snapshot
                enabled = bool(snapshot.get("light_states", {}).get(key, False))
                occupied = key in snapshot.get("occupied_cells", [])
                people_text = "occupied" if occupied else "empty"
                state = "light on" if enabled else "light off"
                self.map_hint.configure(
                    text=f"Row {row} · {chr(ord('A') + column - 1)}  |  {people_text} · {state}"
                )
                return
        self._on_room_leave()

    def _on_room_leave(self, _event=None):
        self.map_hint.configure(text="Hover to inspect a zone")

    def _draw_trend(self, force=False):
        if self._last_trend is None:
            return
        canvas = self.trend_canvas
        width = max(canvas.winfo_width(), 240)
        height = max(canvas.winfo_height(), 105)
        signature = (width, height, self._last_trend)
        if not force and getattr(self, "_trend_signature", None) == signature:
            return
        self._trend_signature = signature
        canvas.delete("all")

        _title, samples, ticks = self._last_trend
        left, right = 38, width - 12
        top, bottom = 10, height - 25
        plot_width = max(1, right - left)
        plot_height = max(1, bottom - top)

        if not samples:
            canvas.create_line(left, bottom, right, bottom, fill=COLORS["grid"], width=1)
            canvas.create_text(
                (left + right) / 2,
                (top + bottom) / 2,
                text="Your occupancy trend will appear after the first saved reading",
                fill=COLORS["muted"],
                font=("Helvetica", 9),
            )
            return

        max_count = max(4, max(count for _position, count in samples))
        for step in range(3):
            fraction = step / 2
            y = bottom - fraction * plot_height
            value = round(fraction * max_count)
            canvas.create_line(left, y, right, y, fill=COLORS["grid"], width=1)
            canvas.create_text(
                left - 8,
                y,
                text=str(value),
                anchor="e",
                fill=COLORS["muted"],
                font=("Helvetica", 8),
            )

        points = []
        for position, count in samples:
            x = left + max(0, min(1, position)) * plot_width
            y = bottom - (count / max_count) * plot_height
            points.append((x, y))

        if len(points) > 1:
            area_coords = [points[0][0], bottom]
            area_coords.extend(coordinate for point in points for coordinate in point)
            area_coords.extend([points[-1][0], bottom])
            canvas.create_polygon(
                area_coords,
                fill=COLORS["green_pale"],
                outline="",
                smooth=True,
            )

        if len(points) > 1:
            canvas.create_line(
                [coordinate for point in points for coordinate in point],
                fill=COLORS["green"],
                width=3,
                smooth=True,
                splinesteps=16,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
        for x, y in points:
            canvas.create_oval(
                x - 3.2,
                y - 3.2,
                x + 3.2,
                y + 3.2,
                fill=COLORS["green_dark"],
                outline=COLORS["white"],
                width=1,
            )

        for position, label in ticks:
            x = left + position * plot_width
            canvas.create_text(
                x,
                height - 9,
                text=label,
                fill=COLORS["muted"],
                font=("Helvetica", 8),
                anchor="center",
            )

    def _mood_for_occupancy(self, count):
        if count <= 0:
            return "The room is ready for you", COLORS["green_pale"], COLORS["green_dark"]
        if count == 1:
            return "A little company has arrived", COLORS["green_pale"], COLORS["green_dark"]
        if count <= 4:
            return "Nice and lively in here", "#e9f6dc", "#557928"
        return "The room is buzzing", COLORS["amber_pale"], "#815d0b"

    def _pulse_occupancy_count(self):
        for job in self._pulse_jobs:
            try:
                self.window.after_cancel(job)
            except tk.TclError:
                pass
        self.count_value.configure(font=("Helvetica", 54, "bold"))
        self._pulse_jobs = [
            self.window.after(
                140,
                lambda: self.count_value.configure(font=("Helvetica", 51, "bold")),
            ),
            self.window.after(
                300,
                lambda: self.count_value.configure(font=("Helvetica", 49, "bold")),
            ),
        ]

    def refresh(self):
        self.config = read_config()
        self.room_subtitle.configure(
            text=f"{self.config.get('Room_Name', 'My Room')} · comfort that follows the room"
        )
        state = read_state()
        try:
            occupancy = max(0, int(state.get("current_occupancy", 0) or 0))
        except (TypeError, ValueError):
            occupancy = 0
        try:
            peak = max(0, int(state.get("peak_occupancy", 0) or 0))
        except (TypeError, ValueError):
            peak = 0

        self.count_value.configure(text=str(occupancy))
        people_changed = self._last_people_count is not None and occupancy != self._last_people_count
        if occupancy != self._last_people_count:
            self._last_people_count = occupancy
            self._draw_people_icons(force=True)
        else:
            self._draw_people_icons()
        if people_changed:
            self._pulse_occupancy_count()

        mood, mood_background, mood_foreground = self._mood_for_occupancy(occupancy)
        self.mood_label.configure(
            text=mood,
            background=mood_background,
            foreground=mood_foreground,
        )
        peak_time = format_timestamp(state.get("peak_time", ""))
        peak_text = f"Peak seen · {peak} people"
        if state.get("peak_time"):
            peak_text += f" · {peak_time}"
        self.peak_caption.configure(text=peak_text)

        ac_state = str(state.get("ac_state", "OFF")).upper()
        ac_enabled = ac_state == "ON"
        self.ac_badge.configure(
            text=f"AC {ac_state}",
            background=COLORS["green_pale"] if ac_enabled else COLORS["off"],
            foreground=COLORS["green_dark"] if ac_enabled else COLORS["muted"],
        )
        try:
            temperature = int(state.get("ac_temperature", 0) or 0)
        except (TypeError, ValueError):
            temperature = 0
        self.temperature_value.configure(text=f"{temperature}°C")
        profile_name = str(self.config.get("Active_Profile", state.get("active_profile", "Balanced")))
        profile = self.config.get("Comfort_Profiles", DEFAULT_PROFILES).get(
            profile_name,
            DEFAULT_PROFILES["Balanced"],
        )
        try:
            ac_on_at = int(profile.get("ac_on_at", 1))
            busy_at = int(profile.get("busy_at", 5))
        except (TypeError, ValueError):
            ac_on_at, busy_at = 1, 5
        if occupancy < ac_on_at:
            climate_text = f"AC waits for {ac_on_at} {'person' if ac_on_at == 1 else 'people'}"
            climate_footer = f"{profile_name} · target {temperature}°C when empty"
        elif occupancy < busy_at:
            climate_text = f"Comfort setting · {occupancy} in the room"
            climate_footer = f"{profile_name} · busy-room setting at {busy_at} people"
        else:
            climate_text = f"Busy room setting · {occupancy} in the room"
            climate_footer = f"{profile_name} · target {temperature}°C"
        self.climate_note.configure(text=climate_text)
        self.climate_footer.configure(text=climate_footer)

        light_states = state.get("light_states", {})
        self._latest_light_states = light_states if isinstance(light_states, dict) else {}
        try:
            if str(state.get("camera_status", "unknown")).lower() in {"online", "starting"}:
                state["grid_rows"] = int(state.get("grid_rows", self.config.get("Grid_Rows", GRID_ROWS)))
                state["grid_columns"] = int(state.get("grid_columns", self.config.get("Grid_Columns", GRID_COLUMNS)))
            else:
                state["grid_rows"] = int(self.config.get("Grid_Rows", GRID_ROWS))
                state["grid_columns"] = int(self.config.get("Grid_Columns", GRID_COLUMNS))
        except (TypeError, ValueError):
            state["grid_rows"], state["grid_columns"] = GRID_ROWS, GRID_COLUMNS
        self._live_snapshot = dict(state)

        history = read_room_history()
        history_signature = (
            len(history),
            history[-1].get("timestamp") if history else "",
            history[-1].get("current_occupancy") if history else None,
            tuple(history[-1].get("occupied_cells", [])) if history else (),
            tuple(sorted(history[-1].get("light_states", {}).items())) if history else (),
            history[-1].get("ac_state") if history else "",
            history[-1].get("ac_temperature") if history else "",
            history[-1].get("active_profile") if history else "",
        )
        history_changed = history_signature != self._last_history_signature
        self._last_history_signature = history_signature
        self._room_history = history
        if not history:
            self.history_slider.state(["disabled"])
            self.play_button.configure(state=tk.DISABLED)
            self.replay_time.configure(text="History starts with the camera backend")
            self._replay_index = None
            self._display_snapshot = dict(self._live_snapshot)
        else:
            self.history_slider.state(["!disabled"])
            self.play_button.configure(state=tk.NORMAL)
            self.history_slider.configure(to=max(0, len(history) - 1))
            if self._replay_index is None:
                self._display_snapshot = dict(self._live_snapshot)
                self._setting_slider = True
                self.history_slider.set(len(history) - 1)
                self._setting_slider = False
                self.replay_time.configure(text="Live room activity")
            else:
                self._replay_index = min(self._replay_index, len(history) - 1)
                self._setting_slider = True
                self.history_slider.set(self._replay_index)
                self._setting_slider = False
                if history_changed or self._replay_playing:
                    self._show_history_snapshot()
        self._draw_room_map()

        rows = read_readings()
        trend_rows = history if history else rows
        trend = occupancy_trend(trend_rows)
        if trend != self._last_trend:
            self._last_trend = trend
            self.trend_title.configure(text=trend[0])
            self._draw_trend(force=True)
        else:
            self._draw_trend()
        self.trend_insight.configure(text=busiest_saved_hour(trend_rows))

        latest_readings = recent_readings(rows)
        if latest_readings != self._last_readings:
            self._last_readings = latest_readings
            for item in self.readings_table.get_children():
                self.readings_table.delete(item)
            for index, reading in enumerate(latest_readings):
                self.readings_table.insert(
                    "",
                    "end",
                    values=reading,
                    tags=("even" if index % 2 == 0 else "odd",),
                )

        self._update_environment(read_environmental_state())
        camera_text, confidence_text, last_frame = self._update_system_health(state)

        updated_at = state.get("updated_at", "")
        if updated_at:
            status_text = (
                f"{camera_text} · Last frame {last_frame} · {confidence_text}"
                f"     ·     Latest state {format_timestamp(updated_at)}"
            )
        elif STATE_PATH.exists():
            status_text = f"{camera_text} · State file is ready; waiting for the camera's first update"
        else:
            status_text = "Waiting for the camera backend to create its first reading · local processing"
        self.status_value.configure(text=status_text)

        self.window.after(1000, self.refresh)


def main():
    window = tk.Tk()
    OccupancyDashboard(window)
    window.mainloop()


if __name__ == "__main__":
    main()
