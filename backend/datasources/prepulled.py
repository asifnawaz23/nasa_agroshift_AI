"""Read featured locations and their pre-pulled files. Owner: Aman.

    load_locations()               -> [location dict]          (backend/data/locations.json)
    get_location(slug)             -> location dict | None
    find_featured(lat, lon)        -> location dict | None     (a click within ~5 km of a pin)
    load_prepulled(slug)           -> {"smap": DataFrame|None, "ndvi": DataFrame|None,
                                       "prism": DataFrame|None, "power": DataFrame|None,
                                       "soil": dict|None, "files": [names found]}

The returned DataFrames are exactly what engine.climate_profile.build_climate_profile() takes
(smap: date, sm / ndvi: date, ndvi, reliability / prism: year, month, precip_mm, tmean_c, ...).
"power" and "soil" are the offline snapshots written by tools/snapshot_power.py: /analyze uses
them only when the live service fails for a featured pin.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PREPULLED_DIR = DATA_DIR / "prepulled"
FEATURED_RADIUS_KM = 5.0


@lru_cache(maxsize=2)
def load_locations(path: str | None = None) -> list[dict]:
    p = Path(path) if path else DATA_DIR / "locations.json"
    return json.loads(p.read_text(encoding="utf-8"))["locations"]


def get_location(slug: str) -> dict | None:
    return next((loc for loc in load_locations() if loc["slug"] == slug), None)


def _km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_featured(lat: float, lon: float, radius_km: float = FEATURED_RADIUS_KM) -> dict | None:
    best = min(load_locations(), key=lambda loc: _km(lat, lon, loc["lat"], loc["lon"]), default=None)
    if best and _km(lat, lon, best["lat"], best["lon"]) <= radius_km:
        return best
    return None


def _csv(path: Path, date_col: str | None = "date"):
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if date_col and date_col in df:
        df[date_col] = pd.to_datetime(df[date_col])
    return df if len(df) else None


def load_prepulled(slug: str, base: Path | None = None) -> dict:
    folder = Path(base or PREPULLED_DIR) / slug
    out = {"smap": _csv(folder / "smap.csv"), "ndvi": _csv(folder / "ndvi.csv"),
           "prism": _csv(folder / "prism_monthly.csv", date_col=None), "power": None, "soil": None}
    snap = folder / "power_cache.json"
    if snap.exists():
        from .power import records_to_df
        out["power"] = records_to_df(json.loads(snap.read_text(encoding="utf-8"))["payload"])
    soil = folder / "soil.json"
    if soil.exists():
        out["soil"] = json.loads(soil.read_text(encoding="utf-8"))["payload"]
    out["files"] = sorted(p.name for p in folder.iterdir()) if folder.exists() else []
    return out
