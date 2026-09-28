import argparse
import json
import logging
import os
import time
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
    with config_path.open("r") as file:
        return json.load(file)


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
    def __init__(self, board, light_pins, settle_seconds=LIGHT_SETTLE_SECONDS):
        self.board = board
        self.light_pins = list(light_pins or [])
        self.settle_seconds = settle_seconds
        self.states = {
            light_key(row, column): False
            for row in range(GRID_ROWS)
            for column in range(GRID_COLUMNS)
        }
        self.pending = {}

    def update(self, occupied_cells, now=None):
        now = time.monotonic() if now is None else now
        desired = {
            light_key(row, column): (row, column) in occupied_cells
            for row in range(GRID_ROWS)
            for column in range(GRID_COLUMNS)
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
            index = row * GRID_COLUMNS + column
            pin = self.light_pins[index] if index < len(self.light_pins) else None
            write_pin(self.board, pin, desired_state)
        return dict(self.states)

    def switch_off(self):
        self.states = {key: False for key in self.states}
        self.pending.clear()
        for pin in self.light_pins:
            write_pin(self.board, pin, False)


def ac_settings(occupancy):
    if occupancy <= 0:
        return False, 26
    if occupancy >= 5:
        return True, 21
    return True, 23


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
        return []

    boxes = result.boxes.xyxy.cpu().numpy().astype("int")
    people = []
    for start_x, start_y, end_x, end_y in boxes:
        center_x = int((start_x + end_x) / 2.0)
        center_y = int((start_y + end_y) / 2.0)
        people.append(((start_x, start_y, end_x, end_y), (center_x, center_y)))
    return people


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
    ac_pin = config.get("AC_Pin")
    light_controller = GridLightController(board, config.get("Light_Pins", []))
    room_grid = PerspectiveRoomGrid(
        columns=GRID_COLUMNS,
        rows=GRID_ROWS,
        downward_tilt_degrees=GRID_TILT_DEGREES,
    )
    model = YOLO(args.model)
    capture = open_video_source(args, config)
    writer = None

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            people = tracked_people(model, frame, args)
            store.set_visible_count(len(people))
            occupied_cells = room_grid.occupied_cells(people, frame.shape)
            light_states = light_controller.update(occupied_cells)
            ac_enabled, ac_temperature = ac_settings(store.snapshot.current_occupancy)
            write_pin(board, ac_pin, ac_enabled)
            store.set_device_status(light_states, ac_enabled, ac_temperature)
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
        capture.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
