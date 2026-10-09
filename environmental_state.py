import json
import math
from datetime import datetime
from pathlib import Path


DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "environmental_state.json"
READING_FIELDS = (
    "temperature_c",
    "humidity_percent",
    "co2_ppm",
    "power_w",
    "energy_today_kwh",
)


def write_environmental_state(
    temperature_c=None,
    humidity_percent=None,
    co2_ppm=None,
    power_w=None,
    energy_today_kwh=None,
    path=DEFAULT_PATH,
):
    """Atomically publish measured room and power readings for the dashboard."""
    values = {
        "temperature_c": temperature_c,
        "humidity_percent": humidity_percent,
        "co2_ppm": co2_ppm,
        "power_w": power_w,
        "energy_today_kwh": energy_today_kwh,
    }
    readings = {"updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    for key in READING_FIELDS:
        value = values[key]
        if value is None:
            readings[key] = None
            continue
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{key} must be a finite measured number")
        readings[key] = number

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(readings, indent=2, allow_nan=False) + "\n")
    temporary.replace(destination)
    return readings
