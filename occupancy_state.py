import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class OccupancySnapshot:
    current_occupancy: int = 0
    peak_occupancy: int = 0
    peak_time: str = ""
    light_states: dict = None
    ac_state: str = "OFF"
    ac_temperature: int = 0
    updated_at: str = ""


class OccupancyStore:
    def __init__(self, state_path, event_log_path, save_interval_seconds=1800):
        self.state_path = Path(state_path)
        self.event_log_path = Path(event_log_path)
        self.save_interval_seconds = save_interval_seconds
        self.last_sample_at = 0
        self.snapshot = OccupancySnapshot()
        self._load()
        if self.snapshot.light_states is None:
            self.snapshot.light_states = {}

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

    def set_device_status(self, light_states, ac_enabled, ac_temperature):
        next_light_states = dict(light_states)
        next_ac_state = "ON" if ac_enabled else "OFF"
        next_ac_temperature = int(ac_temperature)
        if (
            self.snapshot.light_states == next_light_states
            and self.snapshot.ac_state == next_ac_state
            and self.snapshot.ac_temperature == next_ac_temperature
        ):
            return
        self.snapshot.light_states = next_light_states
        self.snapshot.ac_state = next_ac_state
        self.snapshot.ac_temperature = next_ac_temperature
        self._after_change("device_status", log_event=False)

    def reset(self):
        self.snapshot = OccupancySnapshot()
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

    def _append_event(self, event_type, timestamp):
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.event_log_path.exists()
        with self.event_log_path.open("a", newline="") as file:
            writer = csv.writer(file)
            if new_file:
                writer.writerow(
                    [
                        "timestamp",
                        "event",
                        "current_occupancy",
                    ]
                )
            writer.writerow(
                [
                    timestamp,
                    event_type,
                    self.snapshot.current_occupancy,
                ]
            )

    def _persist(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(asdict(self.snapshot), indent=2))
