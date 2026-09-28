import csv
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk


PROJECT_DIR = Path(__file__).resolve().parent
STATE_PATH = PROJECT_DIR / "data" / "occupancy_state.json"
READINGS_PATH = PROJECT_DIR / "data" / "logs" / "occupancy_events.csv"
GRID_COLUMNS = 8
GRID_ROWS = 6

DEFAULT_STATE = {
    "current_occupancy": 0,
    "peak_occupancy": 0,
    "peak_time": "",
    "light_states": {},
    "ac_state": "OFF",
    "ac_temperature": 0,
    "updated_at": "",
}


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


def read_recent_readings(limit=12):
    if not READINGS_PATH.exists():
        return []

    try:
        with READINGS_PATH.open(newline="") as file:
            rows = list(csv.DictReader(file))
    except (OSError, csv.Error):
        return []

    recent = []
    for row in reversed(rows[-limit:]):
        event = row.get("event", "")
        if event in {"visible_count", "visible_reading"}:
            event = "Reading"
        elif event:
            event = event.replace("_", " ").title()

        recent.append(
            (
                row.get("timestamp", ""),
                event,
                row.get("current_occupancy", "0"),
            )
        )
    return recent


class OccupancyDashboard:
    def __init__(self, window):
        self.window = window
        self.window.title("iHVAC Dashboard")
        self.window.geometry("1080x720")
        self.window.minsize(820, 560)
        self._configure_styles()
        self._build_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self.refresh()

    def _configure_styles(self):
        style = ttk.Style(self.window)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f3f5f7")
        style.configure("Header.TLabel", background="#f3f5f7", foreground="#17202a")
        style.configure("Subheader.TLabel", background="#f3f5f7", foreground="#667085")
        style.configure(
            "Card.TFrame",
            background="#ffffff",
            bordercolor="#e1e5ea",
            relief="solid",
            borderwidth=1,
        )
        style.configure("CardLabel.TLabel", background="#ffffff", foreground="#667085")
        style.configure("CardValue.TLabel", background="#ffffff", foreground="#17202a")
        style.configure("Status.TLabel", background="#f3f5f7", foreground="#667085")
        style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#17202a",
            rowheight=30,
            borderwidth=0,
        )
        style.configure("Treeview.Heading", background="#e9edf1", foreground="#344054")
        style.map("Treeview", background=[("selected", "#d9eafe")])

    def _build_ui(self):
        outer = ttk.Frame(self.window, style="App.TFrame", padding=(30, 24, 30, 26))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        ttk.Label(
            outer,
            text="iHVAC",
            style="Header.TLabel",
            font=("Helvetica", 26, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text="Intelligent HVAC Occupancy Mapping",
            style="Subheader.TLabel",
            font=("Helvetica", 12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 22))

        cards = ttk.Frame(outer, style="App.TFrame")
        cards.grid(row=2, column=0, sticky="ew")
        for column in range(3):
            cards.columnconfigure(column, weight=1)

        self.metric_values = {}
        metrics = [
            ("current_occupancy", "Visible People"),
            ("peak_occupancy", "Peak Visible"),
            ("peak_time", "Peak Time"),
            ("ac_state", "AC State"),
            ("ac_temperature", "AC Temperature"),
            ("updated_at", "Last Updated"),
        ]
        for index, (key, label) in enumerate(metrics):
            card = ttk.Frame(cards, style="Card.TFrame", padding=(18, 14, 18, 16))
            card.grid(
                row=index // 3,
                column=index % 3,
                sticky="nsew",
                padx=(0 if index % 3 == 0 else 6, 6 if index % 3 < 2 else 0),
                pady=(0 if index < 3 else 10, 0),
            )
            ttk.Label(
                card, text=label, style="CardLabel.TLabel", font=("Helvetica", 11)
            ).pack(anchor="w")
            value = ttk.Label(
                card,
                text="0",
                style="CardValue.TLabel",
                font=("Helvetica", 23, "bold"),
            )
            value.pack(anchor="w", pady=(8, 0))
            self.metric_values[key] = value

        lights_panel = ttk.Frame(outer, style="Card.TFrame", padding=16)
        lights_panel.grid(row=3, column=0, sticky="ew", pady=(24, 14))
        ttk.Label(
            lights_panel,
            text="Live Light Status",
            style="CardValue.TLabel",
            font=("Helvetica", 14, "bold"),
        ).grid(row=0, column=0, columnspan=GRID_COLUMNS, sticky="w", pady=(0, 10))
        self.light_values = {}
        for row in range(GRID_ROWS):
            for column in range(GRID_COLUMNS):
                key = f"r{row + 1}c{column + 1}"
                value = ttk.Label(
                    lights_panel,
                    text=f"L{row + 1}.{column + 1}\nOFF",
                    style="CardLabel.TLabel",
                    anchor="center",
                    padding=(6, 5),
                    relief="solid",
                    borderwidth=1,
                )
                value.grid(row=row + 1, column=column, sticky="ew", padx=2, pady=2)
                lights_panel.columnconfigure(column, weight=1)
                self.light_values[key] = value

        readings_panel = ttk.Frame(outer, style="Card.TFrame", padding=16)
        readings_panel.grid(row=4, column=0, sticky="nsew", pady=(0, 14))
        readings_panel.columnconfigure(0, weight=1)
        readings_panel.rowconfigure(1, weight=1)
        ttk.Label(
            readings_panel,
            text="Recent Saved Readings",
            style="CardValue.TLabel",
            font=("Helvetica", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        table_frame = ttk.Frame(readings_panel, style="Card.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("timestamp", "event", "people")
        self.readings_table = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=8
        )
        headings = {
            "timestamp": "Timestamp",
            "event": "Event",
            "people": "Visible People",
        }
        widths = {"timestamp": 180, "event": 150, "people": 130}
        for column in columns:
            self.readings_table.heading(column, text=headings[column])
            self.readings_table.column(column, width=widths[column], anchor="center")
        self.readings_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.readings_table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.readings_table.configure(yscrollcommand=scrollbar.set)

        self.status_value = ttk.Label(outer, style="Status.TLabel", font=("Helvetica", 10))
        self.status_value.grid(row=5, column=0, sticky="w")

    def refresh(self):
        state = read_state()
        for key, label in self.metric_values.items():
            value = state.get(key, "")
            if value in (None, ""):
                value = "Waiting" if key in {"peak_time", "updated_at"} else "0"
            label.configure(text=value)

        ac_state = str(state.get("ac_state", "OFF")).upper()
        self.metric_values["ac_state"].configure(
            text=ac_state,
            foreground="#147d45" if ac_state == "ON" else "#9a3412",
        )

        light_states = state.get("light_states", {})
        for key, label in self.light_values.items():
            enabled = bool(light_states.get(key, False))
            row = int(key[1:key.index("c")])
            column = int(key[key.index("c") + 1:])
            label.configure(
                text=f"L{row}.{column}\n{'ON' if enabled else 'OFF'}",
                foreground="#147d45" if enabled else "#667085",
            )

        for item in self.readings_table.get_children():
            self.readings_table.delete(item)
        for row in read_recent_readings():
            self.readings_table.insert("", "end", values=row)

        if STATE_PATH.exists():
            relative_log = READINGS_PATH.relative_to(PROJECT_DIR)
            self.status_value.configure(text=f"Backend: {STATE_PATH.name}    |    CSV: {relative_log}")
        else:
            self.status_value.configure(text="Waiting for the camera backend to create its first reading")

        self.window.after(1000, self.refresh)


def main():
    window = tk.Tk()
    OccupancyDashboard(window)
    window.mainloop()


if __name__ == "__main__":
    main()
