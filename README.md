# iHVAC: Intelligent HVAC Occupancy Mapping

iHVAC uses a room camera to identify visible occupants, map them to a perspective room grid, and publish occupancy-driven light and AC states. The camera preview contains only person highlights and optional grid cells; readings and device states are stored in the backend.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

Configure the camera and optional controller pins in `config.json`. The default camera source is `0`.

The bundled `ihvac_model.pt` checkpoint is used by default.

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

The camera view is represented by an 8 by 6 perspective grid based on a 30-degree downward view. Every grid cell touched by a person's detection rectangle is occupied. A cell remains on only after its state has been stable for 10 seconds, preventing light flicker.

AC control is based on visible occupancy:

| Visible people | AC state | Set temperature |
| --- | --- | --- |
| 0 | Off | 26 C |
| 1 to 4 | On | 23 C |
| 5 or more | On | 21 C |

The dashboard shows visible people, peak occupancy, peak time, AC state, target temperature, per-cell light status, and recent saved readings.

## Hardware Configuration

```json
{
  "url": 0,
  "Arduino": false,
  "Arduino_Port": "COM4",
  "AC_Pin": 8,
  "Light_Pins": []
}
```

Set `Arduino` to `true` only when the controller is connected. `AC_Pin` is the output pin for the AC relay. `Light_Pins` is an optional list of up to 48 output pins, ordered left-to-right and top-to-bottom across the 8 by 6 room grid. With no light pins configured, iHVAC still tracks and displays the calculated light states without controlling relays.

## Data

`data/occupancy_state.json` stores the latest occupancy, grid-light, and AC state. `data/logs/occupancy_events.csv` stores periodic occupancy readings every 30 minutes by default. Both are created and updated by the camera process.
