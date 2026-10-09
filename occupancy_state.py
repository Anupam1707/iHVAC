import csv
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class OccupancySnapshot:
    current_occupancy: int = 0
    peak_occupancy: int = 0
    peak_time: str = ""
    occupied_cells: list = None
    light_states: dict = None
    ac_state: str = "OFF"
    ac_temperature: int = 0
    active_profile: str = "Balanced"
    grid_rows: int = 6
    grid_columns: int = 8
    camera_status: str = "starting"
    camera_last_frame_at: str = ""
    detection_confidence: float = None
    controller_status: str = "not_configured"
    recording_enabled: bool = False
    updated_at: str = ""


class OccupancyStore:
    def __init__(
        self,
        state_path,
        event_log_path,
        save_interval_seconds=1800,
        history_path=None,
    ):
        self.state_path = Path(state_path)
        self.event_log_path = Path(event_log_path)
        self.history_path = Path(history_path) if history_path else self.event_log_path.with_name("room_history.csv")
        self.save_interval_seconds = save_interval_seconds
        self.last_sample_at = 0
        self._last_dynamic_persist_at = 0
        self._last_health_persist_at = 0
        self._last_history_at = 0
        self._last_history_signature = None
        self.snapshot = OccupancySnapshot()
        self._load()
        if self.snapshot.light_states is None:
            self.snapshot.light_states = {}
        if self.snapshot.occupied_cells is None:
            self.snapshot.occupied_cells = []

    def _load(self):
        if not self.state_path.exists():
            self._persist()
            return

        try:
            data = json.loads(self.state_path.read_text())
        except (json.JSONDecodeError, OSError):
            self._persist()
            return

        fields = OccupancySnapshot.__dataclass_fields__
        filtered = {key: value for key, value in data.items() if key in fields}
        self.snapshot = OccupancySnapshot(**filtered)

    def set_visible_count(self, count):
        count = max(0, int(count))
        changed = count != self.snapshot.current_occupancy
        self.snapshot.current_occupancy = count
        now = time.time()
        should_sample = (
            self.last_sample_at == 0
            or now - self.last_sample_at >= self.save_interval_seconds
        )

        if changed or should_sample:
            self._after_change("visible_reading", log_event=should_sample)
            if should_sample:
                self.last_sample_at = now

    def set_device_status(self, light_states, ac_enabled, ac_temperature, profile="Balanced"):
        next_light_states = dict(light_states)
        next_ac_state = "ON" if ac_enabled else "OFF"
        next_ac_temperature = int(ac_temperature)
        changed = (
            self.snapshot.light_states != next_light_states
            or self.snapshot.ac_state != next_ac_state
            or self.snapshot.ac_temperature != next_ac_temperature
            or self.snapshot.active_profile != profile
        )
        if not changed:
            return
        self.snapshot.light_states = next_light_states
        self.snapshot.ac_state = next_ac_state
        self.snapshot.ac_temperature = next_ac_temperature
        self.snapshot.active_profile = str(profile)
        self._after_change("device_status", log_event=False)

    def set_room_activity(self, occupied_cells, detection_confidence=None):
        occupied = sorted({str(cell) for cell in occupied_cells})
        confidence = None
        if detection_confidence is not None:
            try:
                value = float(detection_confidence)
                confidence = max(0.0, min(1.0, value)) if math.isfinite(value) else None
            except (TypeError, ValueError):
                confidence = None

        changed = (
            self.snapshot.occupied_cells != occupied
            or self.snapshot.detection_confidence != confidence
        )
        if not changed:
            self._record_history()
            return

        self.snapshot.occupied_cells = occupied
        self.snapshot.detection_confidence = confidence
        self._record_history()
        now = time.time()
        if now - self._last_dynamic_persist_at >= 1.0:
            self._persist()
            self._last_dynamic_persist_at = now

    def set_runtime_status(
        self,
        camera_status=None,
        camera_last_frame_at=None,
        controller_status=None,
        recording_enabled=None,
        grid_rows=None,
        grid_columns=None,
        force=False,
    ):
        if camera_status is not None:
            self.snapshot.camera_status = str(camera_status)
        if camera_last_frame_at is not None:
            self.snapshot.camera_last_frame_at = str(camera_last_frame_at)
        if controller_status is not None:
            self.snapshot.controller_status = str(controller_status)
        if recording_enabled is not None:
            self.snapshot.recording_enabled = bool(recording_enabled)
        if grid_rows is not None:
            self.snapshot.grid_rows = int(grid_rows)
        if grid_columns is not None:
            self.snapshot.grid_columns = int(grid_columns)

        now = time.time()
        if force or now - self._last_health_persist_at >= 1.0:
            self.snapshot.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._persist()
            self._last_health_persist_at = now

    def reset(self):
        self.snapshot.current_occupancy = 0
        self.snapshot.peak_occupancy = 0
        self.snapshot.peak_time = ""
        self.snapshot.occupied_cells = []
        self.snapshot.light_states = {}
        self.snapshot.ac_state = "OFF"
        self.snapshot.ac_temperature = 0
        self._after_change("reset", log_event=True)

    def _after_change(self, event_type, log_event):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.snapshot.updated_at = now

        if self.snapshot.current_occupancy > self.snapshot.peak_occupancy:
            self.snapshot.peak_occupancy = self.snapshot.current_occupancy
            self.snapshot.peak_time = now

        if log_event:
            self._append_event(event_type, now)
        self._persist()

    def _record_history(self):
        now = time.time()
        signature = (
            self.snapshot.current_occupancy,
            tuple(self.snapshot.occupied_cells or []),
            tuple(sorted((self.snapshot.light_states or {}).items())),
            self.snapshot.ac_state,
            self.snapshot.ac_temperature,
            self.snapshot.active_profile,
            self.snapshot.grid_rows,
            self.snapshot.grid_columns,
        )
        previous = self._last_history_signature
        force_event = previous is None or (
            previous[0] != signature[0]
            or previous[2:] != signature[2:]
        )
        cells_changed = previous is not None and previous[1] != signature[1]
        sample_due = now - self._last_history_at >= 60
        movement_due = cells_changed and now - self._last_history_at >= 5
        if not (force_event or sample_due or movement_due):
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.history_path.exists()
        with self.history_path.open("a", newline="") as file:
            writer = csv.writer(file)
            if new_file:
                writer.writerow(
                    [
                        "timestamp",
                        "current_occupancy",
                        "occupied_cells",
                        "light_states",
                        "ac_state",
                        "ac_temperature",
                        "active_profile",
                        "grid_rows",
                        "grid_columns",
                        "detection_confidence",
                    ]
                )
            writer.writerow(
                [
                    timestamp,
                    self.snapshot.current_occupancy,
                    json.dumps(self.snapshot.occupied_cells or []),
                    json.dumps(self.snapshot.light_states or {}, sort_keys=True),
                    self.snapshot.ac_state,
                    self.snapshot.ac_temperature,
                    self.snapshot.active_profile,
                    self.snapshot.grid_rows,
                    self.snapshot.grid_columns,
                    "" if self.snapshot.detection_confidence is None else self.snapshot.detection_confidence,
                ]
            )
        self._last_history_signature = signature
        self._last_history_at = now

    def _append_event(self, event_type, timestamp):
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.event_log_path.exists()
        if new_file:
            fieldnames = ["timestamp", "event", "current_occupancy"]
        else:
            try:
                with self.event_log_path.open(newline="") as existing_file:
                    fieldnames = next(csv.reader(existing_file), [])
            except (OSError, csv.Error):
                fieldnames = []
            if not fieldnames:
                fieldnames = ["timestamp", "event", "current_occupancy"]

        with self.event_log_path.open("a", newline="") as file:
            if new_file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
            else:
                writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
            event = {
                "timestamp": timestamp,
                "event": event_type,
                "current_occupancy": self.snapshot.current_occupancy,
                "track_id": "camera",
            }
            writer.writerow({key: event.get(key, "") for key in fieldnames})

    def _persist(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary_path.write_text(json.dumps(asdict(self.snapshot), indent=2) + "\n")
        temporary_path.replace(self.state_path)
