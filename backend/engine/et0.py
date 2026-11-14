"""Reference evapotranspiration (ET0) with Hargreaves-Samani. Owner: Asif.

    ET0 [mm/day] = 0.0023 * 0.408 * Ra * (Tmean + 17.8) * sqrt(Tmax - Tmin)

Ra is extraterrestrial radiation in MJ m-2 day-1 (FAO-56 eq. 21-25); 0.408 converts it to
mm/day of evaporated water. Needs only temperature, which POWER always provides.
"""
import math

import numpy as np
import pandas as pd

from . import constants as C


def extraterrestrial_radiation(lat_deg, doy):
    """Ra [MJ m-2 day-1] for latitude (degrees) and day of year (array-like)."""
    doy = np.asarray(doy, dtype=float)
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    return (24 * 60 / np.pi) * C.SOLAR_CONSTANT * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws)
    )


def hargreaves_et0(daily: pd.DataFrame, lat: float) -> pd.Series:
    """Daily ET0 [mm/day] from columns date, t2m, t2m_max, t2m_min."""
    ra = extraterrestrial_radiation(lat, pd.to_datetime(daily["date"]).dt.dayofyear)
    trange = (daily["t2m_max"] - daily["t2m_min"]).clip(lower=0)
    et0 = C.HS_COEF * C.MJ_TO_MM * ra * (daily["t2m"] + C.HS_T_OFFSET) * np.sqrt(trange)
    return et0.clip(lower=0)
