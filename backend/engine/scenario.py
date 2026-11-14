"""What-If scenarios: shift the daily climate before the profile is computed. Owner: Asif.

    apply_scenario(daily, scenario, lat) -> new DataFrame (input is not changed)

scenario = {"temp_c": +3, "rain_pct": -30}
- temp_c: added to t2m, t2m_max, t2m_min (clamped to SCENARIO_TEMP_RANGE_C)
- rain_pct: precip multiplied by (1 + rain_pct/100) (clamped to SCENARIO_RAIN_PCT_RANGE)
- root_wetness: SIMPLIFIED response. For each year-month, the change in water balance
  (change in rain minus change in ET0, mm) times WETNESS_PER_MM_BALANCE is added to every day
  of that month, clipped to 0..1. Labeled "simplified" in the UI.

Everything downstream (ET0, stress counts, scores, alerts) recomputes from the shifted data.
"""
import pandas as pd

from . import constants as C
from .et0 import hargreaves_et0


def normalize_scenario(scenario):
    """Clamp to allowed ranges; returns {"temp_c": float, "rain_pct": float}."""
    scenario = scenario or {}
    t = float(scenario.get("temp_c", 0) or 0)
    r = float(scenario.get("rain_pct", 0) or 0)
    t = min(max(t, C.SCENARIO_TEMP_RANGE_C[0]), C.SCENARIO_TEMP_RANGE_C[1])
    r = min(max(r, C.SCENARIO_RAIN_PCT_RANGE[0]), C.SCENARIO_RAIN_PCT_RANGE[1])
    return {"temp_c": t, "rain_pct": r}


def is_active(scenario) -> bool:
    s = normalize_scenario(scenario)
    return s["temp_c"] != 0 or s["rain_pct"] != 0


def is_extreme(scenario) -> bool:
    """Scenarios this far out lower the confidence label."""
    s = normalize_scenario(scenario)
    return (abs(s["temp_c"]) > C.SCENARIO_LOW_CONFIDENCE_TEMP_C
            or abs(s["rain_pct"]) > C.SCENARIO_LOW_CONFIDENCE_RAIN_PCT)


def apply_scenario(daily: pd.DataFrame, scenario, lat: float) -> pd.DataFrame:
    s = normalize_scenario(scenario)
    out = daily.copy()
    if not is_active(s):
        return out

    base_et0 = hargreaves_et0(daily, lat)
    for col in ("t2m", "t2m_max", "t2m_min"):
        out[col] = out[col] + s["temp_c"]
    out["precip"] = out["precip"] * (1 + s["rain_pct"] / 100.0)

    if "root_wetness" in out:
        new_et0 = hargreaves_et0(out, lat)
        delta = (out["precip"] - daily["precip"]) - (new_et0 - base_et0)
        dates = pd.to_datetime(out["date"])
        month_key = dates.dt.year * 100 + dates.dt.month
        monthly_delta = delta.groupby(month_key).transform("sum")
        out["root_wetness"] = (out["root_wetness"] + monthly_delta * C.WETNESS_PER_MM_BALANCE).clip(0, 1)
    return out
