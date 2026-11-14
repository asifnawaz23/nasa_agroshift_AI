"""Cache layer: check stored data before calling an external API.

Owner: Aman. Contract (plan section 4.4 / 15.3):

    get_or_fetch(kind, lat, lon, fetch_fn) -> (payload, meta)

- The point is snapped to a 0.5 degree grid cell ("42.0_-93.5"); fetch_fn is called with the
  cell centre, so every click inside a cell shares one cached result.
- Cache hit -> stored payload, no network.
- Cache miss -> fetch_fn(lat, lon) -> payload stored -> returned.
- Fetch fails but an older copy exists -> that copy is returned with meta["fallback_used"] = True.
- Fetch fails and nothing is cached -> the DataSourceError is raised (-> 503 in the API).
  Never substitutes another location's data.

Storage backends:
- FileCacheBackend: JSON files on disk. Works now, before Django exists.
- DjangoCacheBackend: Shayan's LocationCache model (kind, grid_key, payload, source_url, fetched_at).
get_backend() picks Django automatically once Django is configured and the model exists.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

try:
    from engine.constants import GRID_STEP_DEG
except ImportError:  # running outside the backend folder
    GRID_STEP_DEG = 0.5

from .errors import DataSourceError

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"
# Soil varies over short distances and SoilGrids is 250 m, so soil gets a finer grid (~1 km)
SOIL_GRID_STEP_DEG = 0.01


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
def snap(value: float, step: float = GRID_STEP_DEG) -> float:
    """Nearest grid value; +0.0 avoids '-0.0' keys."""
    return round(round(value / step) * step, 4) + 0.0


def _decimals(step: float) -> int:
    text = f"{step:.6f}".rstrip("0")
    return max(1, len(text.split(".")[1]) if "." in text else 1)


def grid_key(lat: float, lon: float, step: float = GRID_STEP_DEG) -> str:
    d = _decimals(step)
    return f"{snap(lat, step):.{d}f}_{snap(lon, step):.{d}f}"


def grid_center(lat: float, lon: float, step: float = GRID_STEP_DEG):
    return snap(lat, step), snap(lon, step)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
class FileCacheBackend:
    def __init__(self, directory: str | Path | None = None):
        self.dir = Path(directory or os.environ.get("FIELDSHIFT_CACHE_DIR") or DEFAULT_CACHE_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, kind, key):
        return self.dir / f"{kind}__{key}.json"

    def get(self, kind, key):
        p = self._path(kind, key)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def set(self, kind, key, payload, source_url=""):
        record = {"payload": payload, "source_url": source_url,
                  "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        tmp = self._path(kind, key).with_suffix(".tmp")
        tmp.write_text(json.dumps(record), encoding="utf-8")
        tmp.replace(self._path(kind, key))
        return record


class DjangoCacheBackend:
    """Uses locations.models.LocationCache (plan section 5)."""

    def __init__(self):
        from locations.models import LocationCache  # imported lazily
        self.model = LocationCache

    def get(self, kind, key):
        row = self.model.objects.filter(kind=kind, grid_key=key).first()
        if row is None:
            return None
        return {"payload": row.payload, "source_url": row.source_url,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None}

    def set(self, kind, key, payload, source_url=""):
        row, _ = self.model.objects.update_or_create(
            kind=kind, grid_key=key, defaults={"payload": payload, "source_url": source_url})
        return {"payload": row.payload, "source_url": row.source_url,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None}


def get_backend():
    try:
        from django.conf import settings
        if settings.configured:
            return DjangoCacheBackend()
    except Exception:  # Django not installed / model not migrated yet
        pass
    return FileCacheBackend()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def _age_hours(record):
    ts = record.get("fetched_at")
    if not ts:
        return None
    then = dt.datetime.fromisoformat(ts)
    if then.tzinfo is None:
        then = then.replace(tzinfo=dt.timezone.utc)
    return (dt.datetime.now(dt.timezone.utc) - then).total_seconds() / 3600


def get_or_fetch(kind, lat, lon, fetch_fn, *, backend=None, max_age_hours=None, source_url="",
                 step=GRID_STEP_DEG):
    """Return (payload, meta). meta: cache_hit, fallback_used, grid_key, fetched_at.

    step: grid size in degrees. Climate uses 0.5 (POWER is coarse); soil uses SOIL_GRID_STEP_DEG.
    """
    backend = backend or get_backend()
    key = grid_key(lat, lon, step)
    cached = backend.get(kind, key)
    age = _age_hours(cached) if cached else None
    fresh = cached is not None and (max_age_hours is None or (age is not None and age <= max_age_hours))
    meta = {"grid_key": key, "cache_hit": False, "fallback_used": False, "fetched_at": None}

    if fresh:
        meta.update(cache_hit=True, fetched_at=cached.get("fetched_at"))
        return cached["payload"], meta

    clat, clon = grid_center(lat, lon, step)
    try:
        payload = fetch_fn(clat, clon)
    except DataSourceError:
        if cached is not None:  # stale copy of THIS cell is better than nothing
            meta.update(cache_hit=True, fallback_used=True, fetched_at=cached.get("fetched_at"))
            return cached["payload"], meta
        raise
    record = backend.set(kind, key, payload, source_url)
    meta["fetched_at"] = record.get("fetched_at")
    return payload, meta


def get_soil(lat, lon, *, backend=None):
    """SoilGrids summary for the grid cell, cached. Returns (dict | None, meta).

    Never raises for service problems: returns None with meta["error"] so the API can fall back
    (farmer override or a 'soil data unavailable' info gap). Soil does not change, so no max age.
    """
    from .soilgrids import fetch_soilgrids

    try:
        payload, meta = get_or_fetch("soilgrids", lat, lon, fetch_soilgrids, backend=backend,
                                     source_url="https://soilgrids.org/", step=SOIL_GRID_STEP_DEG)
        meta["error"] = None
        return payload, meta
    except DataSourceError as exc:
        return None, {"grid_key": grid_key(lat, lon, SOIL_GRID_STEP_DEG), "cache_hit": False,
                      "fallback_used": False, "fetched_at": None, "error": str(exc)}


def get_power_daily(lat, lon, *, backend=None):
    """POWER daily DataFrame for the grid cell, cached. Returns (df, meta)."""
    from .power import df_to_records, fetch_power_daily, records_to_df

    payload, meta = get_or_fetch(
        "power", lat, lon, lambda a, b: df_to_records(fetch_power_daily(a, b)),
        backend=backend, source_url="https://power.larc.nasa.gov/")
    return records_to_df(payload), meta
