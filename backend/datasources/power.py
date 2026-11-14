"""NASA POWER daily point client.

Owner: Aman. Contract (plan section 4.2 / 15.3):

    fetch_power_daily(lat, lon, start=None, end=None) -> pandas.DataFrame
        columns: date (datetime64), t2m, t2m_max, t2m_min, precip, root_wetness, solar, rh
        units:   degC, degC, degC, mm/day, 0-1, MJ m-2 day-1, %
        missing values (-999 in POWER) -> NaN

Defaults to the last 20 complete calendar years. Tries the whole range in one request,
and if that fails, falls back to one request per year. No API key is needed.
"""
from __future__ import annotations

import datetime as dt
import time

import numpy as np
import pandas as pd
import requests

from .errors import DataSourceBadResponse, DataSourceError, DataSourceTimeout

SOURCE = "NASA POWER"
BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
COLUMN_MAP = {
    "T2M": "t2m",
    "T2M_MAX": "t2m_max",
    "T2M_MIN": "t2m_min",
    "PRECTOTCORR": "precip",
    "GWETROOT": "root_wetness",
    "ALLSKY_SFC_SW_DWN": "solar",
    "RH2M": "rh",
}
COLUMNS = ["date"] + list(COLUMN_MAP.values())
FILL_VALUE = -999
DEFAULT_YEARS = 20
TIMEOUT_S = 20
RETRIES = 2
RETRY_WAIT_S = 1.5


def default_range(today: dt.date | None = None, years: int = DEFAULT_YEARS):
    """Last `years` complete calendar years, e.g. 2006-01-01 .. 2025-12-31 in 2026."""
    today = today or dt.date.today()
    last = today.year - 1
    return dt.date(last - years + 1, 1, 1), dt.date(last, 12, 31)


def _as_date(value) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.datetime.strptime(str(value).replace("-", ""), "%Y%m%d").date()


def _validate_point(lat: float, lon: float):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"invalid coordinates: lat={lat}, lon={lon}")


def build_url_params(lat: float, lon: float, start: dt.date, end: dt.date) -> dict:
    return {
        "parameters": ",".join(COLUMN_MAP),
        "community": "AG",
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }


def payload_to_df(payload: dict) -> pd.DataFrame:
    """Turn a POWER JSON response into the team DataFrame. Pure function (easy to test)."""
    try:
        params = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise DataSourceBadResponse(SOURCE, "response has no properties.parameter") from exc
    first = params.get("T2M") or next(iter(params.values()), None)
    if not first:
        raise DataSourceBadResponse(SOURCE, "response has no daily values")
    dates = sorted(first.keys())
    data = {"date": pd.to_datetime(dates, format="%Y%m%d")}
    for key, col in COLUMN_MAP.items():
        series = params.get(key, {})
        data[col] = [series.get(d, np.nan) for d in dates]
    df = pd.DataFrame(data)
    num = list(COLUMN_MAP.values())
    df[num] = df[num].astype(float).where(df[num] > FILL_VALUE + 0.5)
    return df[COLUMNS]


def _get_json(params: dict, timeout: float, retries: int, session=None) -> dict:
    http = session or requests
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = http.get(BASE_URL, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            # 4xx = our request is wrong: retrying will not help
            if 400 <= resp.status_code < 500:
                raise DataSourceBadResponse(SOURCE, f"HTTP {resp.status_code}: {resp.text[:200]}")
            last_exc = DataSourceBadResponse(SOURCE, f"HTTP {resp.status_code}")
        except requests.Timeout as exc:
            last_exc = DataSourceTimeout(SOURCE, f"no answer within {timeout}s")
            last_exc.__cause__ = exc
        except requests.RequestException as exc:
            last_exc = DataSourceError(SOURCE, f"connection problem: {exc}")
        except ValueError as exc:  # invalid JSON
            last_exc = DataSourceBadResponse(SOURCE, "response is not valid JSON")
            last_exc.__cause__ = exc
        if attempt < retries:
            time.sleep(RETRY_WAIT_S * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def fetch_power_daily(lat: float, lon: float, start=None, end=None, *,
                      timeout: float = TIMEOUT_S, retries: int = RETRIES, session=None) -> pd.DataFrame:
    """Fetch daily POWER data for one point. Raises DataSourceError subclasses on failure."""
    _validate_point(lat, lon)
    if start is None or end is None:
        start, end = default_range()
    start, end = _as_date(start), _as_date(end)
    if start > end:
        raise ValueError("start must be before end")

    try:
        payload = _get_json(build_url_params(lat, lon, start, end), timeout, retries, session)
        return payload_to_df(payload)
    except DataSourceError:
        if start.year == end.year:
            raise  # nothing smaller to try

    # Fallback: one request per calendar year (smaller, more likely to succeed).
    # No retries per year: if a single year also fails, the service is down -> raise.
    frames = []
    for year in range(start.year, end.year + 1):
        y0 = max(start, dt.date(year, 1, 1))
        y1 = min(end, dt.date(year, 12, 31))
        payload = _get_json(build_url_params(lat, lon, y0, y1), timeout, 0, session)
        frames.append(payload_to_df(payload))
    return pd.concat(frames, ignore_index=True).drop_duplicates("date").reset_index(drop=True)


def df_to_records(df: pd.DataFrame) -> dict:
    """Compact JSON-safe form for the cache (column lists, NaN -> None)."""
    out = {"columns": COLUMNS, "date": df["date"].dt.strftime("%Y-%m-%d").tolist()}
    for col in COLUMNS[1:]:
        out[col] = [None if pd.isna(v) else round(float(v), 3) for v in df[col]]
    return out


def records_to_df(records: dict) -> pd.DataFrame:
    df = pd.DataFrame({c: records[c] for c in COLUMNS})
    df["date"] = pd.to_datetime(df["date"])
    df[COLUMNS[1:]] = df[COLUMNS[1:]].astype(float)
    return df


def missing_fraction(df: pd.DataFrame) -> float:
    return float(df[["t2m", "t2m_max", "t2m_min", "precip"]].isna().mean().mean())
