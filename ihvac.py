import argparse
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import cv2
from ultralytics import YOLO

from occupancy_state import OccupancyStore
from room_grid import PerspectiveRoomGrid


os.environ.setdefault("YOLO_CONFIG_DIR", "data/ultralytics_config")

logging.basicConfig(level=logging.INFO, format="[INFO] %(message)s")
logger = logging.getLogger(__name__)

GRID_COLUMNS = 8
GRID_ROWS = 6
GRID_TILT_DEGREES = 30.0
LIGHT_SETTLE_SECONDS = 10.0

DEFAULT_COMFORT_PROFILES = {
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


def parse_arguments():
    parser = argparse.ArgumentParser(description="iHVAC occupancy mapping.")
    parser.add_argument(
        "--source",
        default=None,
        help="camera index, stream URL, or video path; defaults to config.json url",
    )
    parser.add_argument(
        "--model",
        default="yolo26n.pt",
        help="detection model path/name",
    )
    parser.add_argument(
        "--tracker",
        default="bytetrack.yaml",
        help="Ultralytics tracker config, e.g. bytetrack.yaml or botsort.yaml",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="model inference size")
    parser.add_argument(
        "-c",
        "--confidence",
        type=float,
        default=0.45,
        help="minimum person detection confidence",
    )
    parser.add_argument("-o", "--output", default=None, help="optional output video path")
    parser.add_argument(
        "--state",
        default="data/occupancy_state.json",
        help="latest backend JSON state path",
    )
    parser.add_argument(
        "--readings-log",
        default="data/logs/occupancy_events.csv",
        help="periodic CSV readings path",
    )
    parser.add_argument(
        "--save-interval-minutes",
        type=float,
        default=30,
        help="minutes between saved CSV readings",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="run without the OpenCV preview window",
    )
    parser.add_argument(
        "--no-grid",
        action="store_true",
        help="hide the perspective room grid and occupied-cell highlights",
    )
    return parser.parse_args()


def read_config():
    config_path = Path("config.json")
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        logger.warning("Unable to read config.json; keeping the last valid settings")
        return {}
    return data if isinstance(data, dict) else {}


def grid_settings(config):
    try:
        columns = max(1, min(12, int(config.get("Grid_Columns", GRID_COLUMNS))))
        rows = max(1, min(12, int(config.get("Grid_Rows", GRID_ROWS))))
        if rows * columns > 48:
            rows, columns = GRID_ROWS, GRID_COLUMNS
        tilt = float(config.get("Grid_Tilt_Degrees", GRID_TILT_DEGREES))
        if not 1 <= tilt <= 89:
            tilt = GRID_TILT_DEGREES
    except (TypeError, ValueError):
        return GRID_COLUMNS, GRID_ROWS, GRID_TILT_DEGREES
    return columns, rows, tilt


def normalize_source(source):
    if source is None or source == "":
        return 0
    if isinstance(source, int):
        return source
    if isinstance(source, str) and source.isdigit():
        return int(source)
    return source


def open_video_source(args, config):
    source = normalize_source(args.source if args.source is not None else config.get("url", 0))
    logger.info("Starting video source: %s", source)
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")
    return capture


def maybe_connect_arduino(config):
    if not config.get("Arduino", False):
        return None

    port = config.get("Arduino_Port", "COM4")
    try:
        import pyfirmata

        board = pyfirmata.Arduino(port)
        logger.info("Arduino connected on %s", port)
        return board
    except Exception:
        logger.warning("Arduino was enabled but could not connect on %s", port)
        return None


def write_pin(board, pin, enabled):
    if board is None or pin is None:
        return
    try:
        board.digital[int(pin)].write(1 if enabled else 0)
    except Exception:
        logger.debug("Unable to update Arduino pin %s", pin, exc_info=True)


def light_key(row, column):
    return f"r{row + 1}c{column + 1}"


class GridLightController:
    def __init__(
        self,
        board,
        light_pins,
        settle_seconds=LIGHT_SETTLE_SECONDS,
        columns=GRID_COLUMNS,
        rows=GRID_ROWS,
    ):
        self.board = board
        self.light_pins = list(light_pins or [])
        self.settle_seconds = settle_seconds
        self.columns = int(columns)
        self.rows = int(rows)
        self.states = {
            light_key(row, column): False
            for row in range(self.rows)
            for column in range(self.columns)
        }
        self.pending = {}

    def update(self, occupied_cells, now=None):
        now = time.monotonic() if now is None else now
        desired = {
            light_key(row, column): (row, column) in occupied_cells
            for row in range(self.rows)
            for column in range(self.columns)
        }
        for key, desired_state in desired.items():
            if desired_state == self.states[key]:
                self.pending.pop(key, None)
                continue

            pending_state, started_at = self.pending.get(key, (None, now))
            if pending_state != desired_state:
                self.pending[key] = (desired_state, now)
                continue
            if now - started_at < self.settle_seconds:
                continue

            self.states[key] = desired_state
            self.pending.pop(key, None)
            row = int(key[1:key.index("c")]) - 1
            column = int(key[key.index("c") + 1:]) - 1
            index = row * self.columns + column
            pin = self.light_pins[index] if index < len(self.light_pins) else None
            write_pin(self.board, pin, desired_state)
        return dict(self.states)

    def switch_off(self):
        self.states = {key: False for key in self.states}
        self.pending.clear()
        for pin in self.light_pins:
            write_pin(self.board, pin, False)


def ac_settings(occupancy, config=None):
    config = config or {}
    profiles = config.get("Comfort_Profiles", {})
    profile_name = config.get("Active_Profile", "Balanced")
    profile = profiles.get(profile_name, DEFAULT_COMFORT_PROFILES["Balanced"])
    try:
        ac_on_at = max(1, int(profile.get("ac_on_at", 1)))
        busy_at = max(ac_on_at, int(profile.get("busy_at", 5)))
        empty_temperature = int(profile.get("empty_temperature", 26))
        occupied_temperature = int(profile.get("occupied_temperature", 23))
        busy_temperature = int(profile.get("busy_temperature", 21))
    except (TypeError, ValueError):
        profile = DEFAULT_COMFORT_PROFILES["Balanced"]
        ac_on_at = profile["ac_on_at"]
        busy_at = profile["busy_at"]
        empty_temperature = profile["empty_temperature"]
        occupied_temperature = profile["occupied_temperature"]
        busy_temperature = profile["busy_temperature"]

    if occupancy < ac_on_at:
        return False, empty_temperature, profile_name
    if occupancy >= busy_at:
        return True, busy_temperature, profile_name
    return True, occupied_temperature, profile_name


def tracked_people(model, frame, args):
    result = model.track(
        frame,
        persist=True,
        tracker=args.tracker,
        conf=args.confidence,
        imgsz=args.imgsz,
        classes=[0],
        verbose=False,
    )[0]

    if result.boxes is None:
        return [], None

    boxes = result.boxes.xyxy.cpu().numpy().astype("int")
    confidence_values = []
    if result.boxes.conf is not None:
        confidence_values = result.boxes.conf.cpu().numpy().tolist()
    people = []
    for start_x, start_y, end_x, end_y in boxes:
        center_x = int((start_x + end_x) / 2.0)
        center_y = int((start_y + end_y) / 2.0)
        people.append(((start_x, start_y, end_x, end_y), (center_x, center_y)))
    average_confidence = (
        sum(confidence_values) / len(confidence_values)
        if confidence_values
        else None
    )
    return people, average_confidence


def highlight_people(frame, people):
    for box, centroid in people:
        start_x, start_y, end_x, end_y = box
        cv2.rectangle(frame, (start_x, start_y), (end_x, end_y), (48, 180, 255), 2)
        cv2.circle(frame, centroid, 4, (48, 180, 255), -1)


def main():
    args = parse_arguments()
    config = read_config()
    store = OccupancyStore(
        args.state,
        args.readings_log,
        save_interval_seconds=args.save_interval_minutes * 60,
    )
    board = maybe_connect_arduino(config)
    controller_status = "connected" if board is not None else (
        "offline" if config.get("Arduino", False) else "not_configured"
    )
    ac_pin = config.get("AC_Pin")
    grid_columns, grid_rows, grid_tilt = grid_settings(config)
    light_controller = GridLightController(
        board,
        config.get("Light_Pins", []),
        columns=grid_columns,
        rows=grid_rows,
    )
    light_controller.switch_off()
    room_grid = PerspectiveRoomGrid(
        columns=grid_columns,
        rows=grid_rows,
        downward_tilt_degrees=grid_tilt,
    )
    store.set_runtime_status(
        camera_status="starting",
        controller_status=controller_status,
        recording_enabled=bool(args.output),
        grid_rows=grid_rows,
        grid_columns=grid_columns,
        force=True,
    )
    try:
        model = YOLO(args.model)
        capture = open_video_source(args, config)
    except Exception:
        store.set_runtime_status(camera_status="offline", force=True)
        raise
    writer = None
    config_path = Path("config.json")
    try:
        config_mtime = config_path.stat().st_mtime
    except OSError:
        config_mtime = 0
    last_config_check = 0

    try:
        while True:
            now = time.monotonic()
            if now - last_config_check >= 1.0:
                last_config_check = now
                try:
                    next_mtime = config_path.stat().st_mtime
                except OSError:
                    next_mtime = config_mtime
                if next_mtime != config_mtime:
                    next_config = read_config()
                    if not next_config:
                        next_config = config
                    old_geometry = grid_settings(config)
                    new_geometry = grid_settings(next_config)
                    pins_changed = next_config.get("Light_Pins", []) != config.get("Light_Pins", [])
                    if old_geometry != new_geometry or pins_changed:
                        light_controller.switch_off()
                        grid_columns, grid_rows, grid_tilt = new_geometry
                        light_controller = GridLightController(
                            board,
                            next_config.get("Light_Pins", []),
                            columns=grid_columns,
                            rows=grid_rows,
                        )
                        light_controller.switch_off()
                        room_grid = PerspectiveRoomGrid(
                            columns=grid_columns,
                            rows=grid_rows,
                            downward_tilt_degrees=grid_tilt,
                        )
                        store.set_runtime_status(
                            grid_rows=grid_rows,
                            grid_columns=grid_columns,
                        )
                    config = next_config
                    ac_pin = config.get("AC_Pin")
                    config_mtime = next_mtime

            ok, frame = capture.read()
            if not ok:
                store.set_runtime_status(camera_status="offline", force=True)
                break

            people, average_confidence = tracked_people(model, frame, args)
            store.set_visible_count(len(people))
            occupied_cells = room_grid.occupied_cells(people, frame.shape)
            light_states = light_controller.update(occupied_cells)
            ac_enabled, ac_temperature, profile_name = ac_settings(
                store.snapshot.current_occupancy,
                config,
            )
            write_pin(board, ac_pin, ac_enabled)
            store.set_device_status(light_states, ac_enabled, ac_temperature, profile_name)
            store.set_room_activity(
                [light_key(row, column) for row, column in occupied_cells],
                average_confidence,
            )
            store.set_runtime_status(
                camera_status="online",
                camera_last_frame_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                controller_status=controller_status,
                recording_enabled=bool(args.output),
                grid_rows=grid_rows,
                grid_columns=grid_columns,
            )
            if not args.no_grid:
                room_grid.draw(frame, occupied_cells)
            highlight_people(frame, people)

            if args.output and writer is None:
                height, width = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(args.output, fourcc, 30, (width, height), True)

            if writer is not None:
                writer.write(frame)

            if not args.headless:
                cv2.imshow("iHVAC", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("o"):
                    store.reset()
    finally:
        light_controller.switch_off()
        write_pin(board, ac_pin, False)
        store.set_runtime_status(camera_status="offline", force=True)
        capture.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
