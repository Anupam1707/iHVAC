# iHVAC: Intelligent HVAC Occupancy Mapping

iHVAC uses a room camera to identify visible occupants, map them to a perspective room grid, and publish occupancy-driven light and AC states. The camera preview contains only person highlights and optional grid cells; readings and device states are stored in the backend.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

Configure the camera and optional controller pins in `config.json`. The default camera source is `0`.

The bundled `yolo26n.pt` checkpoint is used by default. Pass `--model path/to/model.pt` to use another detector.

## Run

Start the camera and control loop:

```bash
python3 ihvac.py
```

Start the dashboard in a separate terminal:

```bash
python3 tkinter_ui.py
```

Use another camera or video source:

```bash
python3 ihvac.py --source 1
python3 ihvac.py --source path/to/video.mp4
```

Useful options:

```bash
python3 ihvac.py --no-grid
python3 ihvac.py --headless
python3 ihvac.py --model path/to/model.pt
python3 ihvac.py --save-interval-minutes 15
```

## Operation

The camera view is represented by a configurable perspective grid. The default is 8 by 6 zones with a 30-degree downward view. Every grid cell touched by a person's detection rectangle is marked occupied. A light remains on only after its state has been stable for 10 seconds, preventing light flicker.

AC control is based on visible occupancy:

The default **Balanced** profile uses these settings:

| Visible people | AC state | Set temperature |
| --- | --- | --- |
| 0 | Off | 26 C |
| 1 to 4 | On | 23 C |
| 5 or more | On | 21 C |

The dashboard shows occupancy and lighting as separate map layers, with People, Lights, and Both views. Use the trend slider to scrub through saved zone snapshots or press play to replay them. Camera/controller health, mean detector confidence, recording status, and measured environmental signals are shown separately. Missing sensor readings are labeled as unavailable rather than estimated.

Use **Room setup** in the dashboard to name the room, calibrate the grid dimensions and camera angle, select a comfort preset, and edit its occupancy and temperature thresholds. Comfort changes are reloaded by the camera process automatically. Grid changes rebuild the map and light-zone indexing while the process is running.

### Environmental sensor input

The dashboard reads optional measured values from `data/environmental_state.json`. A sensor integration can update this file with a timestamp and any values it actually measures:

```json
{
  "updated_at": "2026-10-09 14:30:00",
  "temperature_c": 24.1,
  "humidity_percent": 48,
  "co2_ppm": 620,
  "power_w": 180,
  "energy_today_kwh": 1.26
}
```

The dashboard marks these readings stale after 90 seconds. iHVAC does not calculate energy savings; the power and energy fields require a real meter or an external sensor integration.

A sensor process can publish readings atomically through the helper:

```python
from environmental_state import write_environmental_state

write_environmental_state(
    temperature_c=24.1,
    humidity_percent=48,
    co2_ppm=620,
    power_w=180,
    energy_today_kwh=1.26,
)
```

Only pass values returned by real sensors or a meter; omitted readings stay unavailable in the dashboard.

## Hardware Configuration

```json
{
  "url": 0,
  "Arduino": false,
  "Arduino_Port": "COM4",
  "AC_Pin": 8,
  "Light_Pins": [],
  "Room_Name": "My Room",
  "Grid_Columns": 8,
  "Grid_Rows": 6,
  "Grid_Tilt_Degrees": 30,
  "Active_Profile": "Balanced"
}
```

Set `Arduino` to `true` only when the controller is connected. `AC_Pin` is the output pin for the AC relay. `Light_Pins` is an optional list of up to 48 output pins, ordered left-to-right and top-to-bottom across the configured room grid. With no light pins configured, iHVAC still tracks and displays the calculated light states without controlling relays.

## Data

`data/occupancy_state.json` stores the latest occupancy, occupied zones, light states, AC settings, camera/controller health, and detector confidence. `data/logs/occupancy_events.csv` stores occupancy readings every 30 minutes by default. `data/logs/room_history.csv` stores time-stamped zone snapshots for replay. The dashboard reads optional environmental readings from `data/environmental_state.json` when a sensor integration supplies them.
