"""Build engine/tests/sample_profile.json from real NASA POWER data.

Prototype of build_climate_profile() (plan section 7). Asif moves this logic into
engine/climate_profile.py. Fields that need SMAP / NDVI / PRISM are filled with
clearly marked sample values until those files arrive.

Usage:
    python tools/make_sample_profile.py backend/engine/tests/sample_power_iowa.csv 42.0 temperate backend/engine/tests/sample_profile.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from engine import constants as C  # noqa: E402

MONTHS = range(1, 13)


def extraterrestrial_radiation(lat_deg, doy):
    """Ra in MJ m-2 day-1, FAO-56 eq. 21-25."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    return (24 * 60 / np.pi) * C.SOLAR_CONSTANT * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws)
    )


def hargreaves_et0(df, lat):
    ra = extraterrestrial_radiation(lat, df["date"].dt.dayofyear.to_numpy())
    trange = (df["t2m_max"] - df["t2m_min"]).clip(lower=0)
    et0 = C.HS_COEF * C.MJ_TO_MM * ra * (df["t2m"] + C.HS_T_OFFSET) * np.sqrt(trange)
    return et0.clip(lower=0)


def runs(mask):
    """Yield (start_idx, length) of consecutive True values."""
    start = None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            yield start, i - start
            start = None
    if start is not None:
        yield start, len(mask) - start


def r(x, n=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)


def build(df, lat, zone):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["et0"] = hargreaves_et0(df, lat)
    years = sorted(df["year"].unique())
    n_years = len(years)
    core = ["t2m", "t2m_max", "t2m_min", "precip"]
    missing_fraction = float(df[core].isna().mean().mean())

    # Monthly climatology: mean of each year's monthly value
    ym = df.groupby(["year", "month"]).agg(
        t_mean=("t2m", "mean"), t_max=("t2m_max", "mean"), t_min=("t2m_min", "mean"),
        precip_mm=("precip", "sum"), root_wetness=("root_wetness", "mean"), et0_mm=("et0", "sum"),
    ).reset_index()
    clim = ym.groupby("month").mean(numeric_only=True)
    monthly_climatology = {
        str(m): {k: r(clim.loc[m, k], 2 if k in ("root_wetness",) else 1)
                 for k in ["t_mean", "t_max", "t_min", "precip_mm", "root_wetness", "et0_mm"]}
        for m in MONTHS
    }

    # Trends (per decade)
    annual = df.groupby("year").agg(p=("precip", "sum"), t=("t2m", "mean"))
    yrs = annual.index.to_numpy(dtype=float)
    trends = {
        "precip_mm_per_decade": r(np.polyfit(yrs, annual["p"], 1)[0] * 10, 1),
        "t_mean_c_per_decade": r(np.polyfit(yrs, annual["t"], 1)[0] * 10, 2),
    }

    # Daily stress counts, averaged per year
    df["heat"] = df["t2m_max"] > C.HEAT_DAY_TMAX_C
    df["frost"] = df["t2m_min"] <= C.FROST_DAY_TMIN_C
    wet = df.loc[df["precip"] >= C.WET_DAY_MM, "precip"]
    extreme_thr = float(np.percentile(wet, C.EXTREME_RAIN_PERCENTILE))
    df["extreme"] = df["precip"] > extreme_thr
    per_ym = df.groupby(["year", "month"])[["heat", "frost", "extreme"]].sum()
    per_m = per_ym.groupby("month").mean()

    # Dry spell probability: share of years where a >=10-day dry run touches that month
    dry = (df["precip"] < C.WET_DAY_MM).to_numpy()
    touched = set()
    for s, length in runs(dry):
        if length >= C.DRY_SPELL_MIN_DAYS:
            seg = df.iloc[s:s + length]
            touched.update(zip(seg["year"], seg["month"]))
    dry_prob = {m: sum((y, m) in touched for y in years) / n_years for m in MONTHS}

    stress_by_month = {
        "heat_days": {str(m): r(per_m.loc[m, "heat"], 1) for m in MONTHS},
        "frost_days": {str(m): r(per_m.loc[m, "frost"], 1) for m in MONTHS},
        "dry_spell_prob": {str(m): r(dry_prob[m], 2) for m in MONTHS},
        "extreme_rain_days": {str(m): r(per_m.loc[m, "extreme"], 1) for m in MONTHS},
    }

    water_balance_by_month = {
        str(m): {
            "precip_mm": r(clim.loc[m, "precip_mm"], 1),
            "et0_mm": r(clim.loc[m, "et0_mm"], 1),
            "deficit_mm": r(max(0.0, clim.loc[m, "et0_mm"] - clim.loc[m, "precip_mm"]), 1),
        }
        for m in MONTHS
    }

    # Soil-moisture anomaly (Standard tier uses POWER root wetness):
    # mean z-score of the last 5 years vs the full-period monthly climatology.
    sd = ym.groupby("month")["root_wetness"].std()
    recent = ym[ym["year"] > years[-1] - 5].groupby("month")["root_wetness"].mean()
    sm_anom = {str(m): r((recent[m] - clim.loc[m, "root_wetness"]) / sd[m], 2) for m in MONTHS}

    # Frost-free season: longest run without frost per year
    ff = []
    for y in years:
        mask = ~df.loc[df["year"] == y, "frost"].to_numpy()
        ff.append(max((length for _, length in runs(mask)), default=0))
    frost_free = {"median_days": int(np.median(ff)), "p10": int(np.percentile(ff, 10)),
                  "p90": int(np.percentile(ff, 90))}

    # Year stress flags
    gs = C.GROWING_SEASON_MONTHS[zone]
    gs_rain = df[df["month"].isin(gs)].groupby("year")["precip"].sum()
    heat_year = df.groupby("year")["heat"].sum()
    rain_thr = np.percentile(gs_rain, C.DROUGHT_YEAR_PERCENTILE)
    heat_thr = np.percentile(heat_year, C.HEAT_YEAR_PERCENTILE)
    flags = {}
    for y in years:
        f = []
        if gs_rain[y] < rain_thr:
            f.append("drought")
        if heat_year[y] > heat_thr and heat_year[y] > 0:
            f.append("heat")
        if f:
            flags[str(y)] = f

    return {
        "years_covered": [int(years[0]), int(years[-1])],
        "n_years": n_years,
        "missing_fraction": r(missing_fraction, 3),
        "monthly_climatology": monthly_climatology,
        "trends": trends,
        "stress_by_month": stress_by_month,
        "extreme_rain_threshold_mm": r(extreme_thr, 1),
        "water_balance_by_month": water_balance_by_month,
        "soil_moisture_anomaly_by_month": sm_anom,
        "ndvi_by_month": None,
        "bare_months_observed": None,
        "frost_free_season": frost_free,
        "year_stress_flags": flags,
        "uncertainty": {"interannual_cv_precip": r(annual["p"].std() / annual["p"].mean(), 2),
                        "smap_years": None},
        "validation": None,
        "scenario_applied": {"rain_pct": 0, "temp_c": 0},
        "data_tier": "standard",
    }


def add_sample_placeholders(p):
    """Fill fields that need SMAP / NDVI / PRISM with marked sample values (Iowa cropland)."""
    p["ndvi_by_month"] = {"1": 0.18, "2": 0.18, "3": 0.2, "4": 0.24, "5": 0.33, "6": 0.62,
                          "7": 0.82, "8": 0.80, "9": 0.58, "10": 0.32, "11": 0.22, "12": 0.19}
    p["bare_months_observed"] = [m for m in range(1, 13) if p["ndvi_by_month"][str(m)] < C.BARE_NDVI_THRESHOLD]
    p["uncertainty"]["smap_years"] = 10
    p["validation"] = {"prism": {"precip_corr": 0.93, "precip_bias_pct": -4.0, "tmean_bias_c": 0.3}}
    p["data_tier"] = "us_enhanced"
    p["_sample_notes"] = [
        "Computed from real NASA POWER daily data for 42.0, -93.6 (2006-2025).",
        "ndvi_by_month, bare_months_observed, uncertainty.smap_years and validation are SAMPLE values "
        "until AppEEARS (MODIS NDVI, SMAP) and PRISM files arrive.",
        "soil_moisture_anomaly_by_month uses POWER root-zone wetness: mean z-score of the last 5 years vs 2006-2025.",
    ]
    return p


if __name__ == "__main__":
    src, lat, zone, dst = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
    profile = add_sample_placeholders(build(pd.read_csv(src), lat, zone))
    Path(dst).write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(f"wrote {dst}")
