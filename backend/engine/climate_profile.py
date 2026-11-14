"""Climate profile: turn daily NASA POWER data into the monthly facts the app uses.

Owner: Asif. Pure Python + pandas. No Django imports, no network calls.
Contract: plan section 7. Every key is always present; values are None when data is missing.

    build_climate_profile(daily, lat, smap=None, ndvi=None, prism=None, scenario=None,
                          zone=None, data_tier=None) -> dict

Inputs
    daily    DataFrame: date, t2m, t2m_max, t2m_min, precip, root_wetness, solar, rh
    smap     DataFrame: date, sm            (featured locations)
    ndvi     DataFrame: date, ndvi [, reliability]  (featured locations)
    prism    DataFrame: year, month, precip_mm, tmean_c, tmax_c, tmin_c  (Iowa)
    scenario {"temp_c": 0, "rain_pct": 0}

What-If rule: thresholds that define "unusual" (extreme-rain percentile, drought-year and
heat-year percentiles, soil-moisture climatology) are taken from the BASELINE data, so a
drier or hotter scenario really shows more extreme days and more flagged years.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import constants as C
from .et0 import hargreaves_et0
from .scenario import apply_scenario, is_active, normalize_scenario

MONTHS = list(range(1, 13))
CORE = ["t2m", "t2m_max", "t2m_min", "precip"]
RECENT_YEARS = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _r(x, n=2):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or math.isinf(x) else round(x, n)


def _by_month(series_by_month, n=2):
    return {str(m): _r(series_by_month.get(m, np.nan), n) for m in MONTHS}


def _runs(mask):
    """(start_index, length) of consecutive True values."""
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i - start))
            start = None
    if start is not None:
        out.append((start, len(mask) - start))
    return out


def default_zone(lat):
    return "subtropical" if abs(lat) < 35 else "temperate"


def _prepare(daily: pd.DataFrame) -> pd.DataFrame:
    df = daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    for col in ["t2m", "t2m_max", "t2m_min", "precip", "root_wetness", "solar", "rh"]:
        if col not in df:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[df[col] <= C.POWER_FILL_VALUE + 0.5, col] = np.nan
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    return df


def _monthly_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (year, month)."""
    return df.groupby(["year", "month"]).agg(
        t_mean=("t2m", "mean"), t_max=("t2m_max", "mean"), t_min=("t2m_min", "mean"),
        precip_mm=("precip", lambda s: s.sum(min_count=1)),
        root_wetness=("root_wetness", "mean"), et0_mm=("et0", "sum"),
    ).reset_index()


# ---------------------------------------------------------------------------
# Baseline reference values (do not change under a scenario)
# ---------------------------------------------------------------------------
def _baseline_reference(base: pd.DataFrame, zone: str) -> dict:
    wet = base.loc[base["precip"] >= C.WET_DAY_MM, "precip"].dropna()
    extreme_thr = float(np.percentile(wet, C.EXTREME_RAIN_PERCENTILE)) if len(wet) >= 20 else np.inf

    gs = C.GROWING_SEASON_MONTHS[zone]
    gs_rain = base[base["month"].isin(gs)].groupby("year")["precip"].sum(min_count=1).dropna()
    heat_year = (base["t2m_max"] > C.HEAT_DAY_TMAX_C).groupby(base["year"]).sum()

    ym = base.groupby(["year", "month"])["root_wetness"].mean().reset_index()
    rw_mean = ym.groupby("month")["root_wetness"].mean()
    rw_sd = ym.groupby("month")["root_wetness"].std()
    return {
        "extreme_thr": extreme_thr,
        "drought_rain_thr": float(np.percentile(gs_rain, C.DROUGHT_YEAR_PERCENTILE)) if len(gs_rain) >= 5 else None,
        "heat_year_thr": float(np.percentile(heat_year, C.HEAT_YEAR_PERCENTILE)) if len(heat_year) >= 5 else None,
        "rw_mean": rw_mean, "rw_sd": rw_sd,
    }


# ---------------------------------------------------------------------------
# Pieces of the profile
# ---------------------------------------------------------------------------
def _stress_by_month(df, years, extreme_thr):
    flags = pd.DataFrame({
        "year": df["year"], "month": df["month"],
        "heat": df["t2m_max"] > C.HEAT_DAY_TMAX_C,
        "severe_heat": df["t2m_max"] > C.SEVERE_HEAT_DAY_TMAX_C,
        "frost": df["t2m_min"] <= C.FROST_DAY_TMIN_C,
        "extreme": df["precip"] > extreme_thr,
    })
    per_m = flags.groupby(["year", "month"]).sum().groupby("month").mean()

    dry = (df["precip"] < C.WET_DAY_MM).to_numpy()  # NaN counts as not dry
    touched = set()
    for start, length in _runs(dry):
        if length >= C.DRY_SPELL_MIN_DAYS:
            seg = df.iloc[start:start + length]
            touched.update(zip(seg["year"], seg["month"]))
    n_years = max(len(years), 1)
    dry_prob = {m: sum((y, m) in touched for y in years) / n_years for m in MONTHS}

    return {
        "heat_days": _by_month(per_m["heat"], 1),
        "severe_heat_days": _by_month(per_m["severe_heat"], 1),
        "frost_days": _by_month(per_m["frost"], 1),
        "dry_spell_prob": _by_month(pd.Series(dry_prob), 2),
        "extreme_rain_days": _by_month(per_m["extreme"], 1),
    }


def _trends(df):
    annual = df.groupby("year").agg(p=("precip", lambda s: s.sum(min_count=1)), t=("t2m", "mean")).dropna()
    if len(annual) < 3:
        return {"precip_mm_per_decade": None, "t_mean_c_per_decade": None}
    yrs = annual.index.to_numpy(dtype=float)
    return {
        "precip_mm_per_decade": _r(np.polyfit(yrs, annual["p"], 1)[0] * 10, 1),
        "t_mean_c_per_decade": _r(np.polyfit(yrs, annual["t"], 1)[0] * 10, 2),
    }


def _recent_cutoff(years):
    """Years after this are 'recent': the last 5 years, but never more than half the record,
    so a short record (e.g. 3 years of SMAP) still compares recent vs normal."""
    years = sorted(set(int(y) for y in years))
    n_recent = max(1, min(RECENT_YEARS, len(years) // 2))
    return years[-1] - n_recent


def _soil_moisture_anomaly(df, ref, smap, scenario_on):
    """Mean z-score of the most recent years vs the long-term monthly normal.

    Observed SMAP is used when available and no scenario is active; otherwise POWER
    root-zone wetness (which the scenario shifts) against the BASELINE wetness normal.
    """
    if smap is not None and not scenario_on:
        s = smap.copy()
        s["date"] = pd.to_datetime(s["date"])
        s["sm"] = pd.to_numeric(s["sm"], errors="coerce")
        lo, hi = C.SMAP_VALID_RANGE
        s = s[(s["sm"] >= lo) & (s["sm"] <= hi)]
        if len(s) > 30:
            ym = s.groupby([s["date"].dt.year.rename("year"), s["date"].dt.month.rename("month")])["sm"].mean().reset_index()
            mean, sd = ym.groupby("month")["sm"].mean(), ym.groupby("month")["sm"].std()
            recent = ym[ym["year"] > _recent_cutoff(ym["year"])].groupby("month")["sm"].mean()
            z = (recent - mean) / sd.replace(0, np.nan)
            return _by_month(z, 2), "smap", int(ym["year"].nunique())

    if df["root_wetness"].notna().sum() == 0:
        return {str(m): None for m in MONTHS}, None, None
    ym = df.groupby(["year", "month"])["root_wetness"].mean().reset_index()
    recent = ym[ym["year"] > _recent_cutoff(ym["year"])].groupby("month")["root_wetness"].mean()
    z = (recent - ref["rw_mean"]) / ref["rw_sd"].replace(0, np.nan)
    return _by_month(z, 2), "power_root_wetness", None


def _ndvi(ndvi):
    if ndvi is None:
        return None, None
    n = ndvi.copy()
    n["date"] = pd.to_datetime(n["date"])
    n["ndvi"] = pd.to_numeric(n["ndvi"], errors="coerce")
    if n["ndvi"].abs().max() > 1.5:  # raw MODIS integers -> apply scale factor
        n["ndvi"] = n["ndvi"] * 0.0001
    if "reliability" in n:
        n = n[n["reliability"].isin(C.NDVI_GOOD_RELIABILITY)]
    n = n[(n["ndvi"] >= -0.2) & (n["ndvi"] <= 1.0)]
    if n.empty:
        return None, None
    ym = n.groupby([n["date"].dt.year.rename("year"), n["date"].dt.month.rename("month")])["ndvi"].mean().reset_index()
    clim = ym.groupby("month")["ndvi"].mean()
    by_month = _by_month(clim, 2)
    bare = [m for m in MONTHS if by_month[str(m)] is not None and by_month[str(m)] < C.BARE_NDVI_THRESHOLD]
    return by_month, bare


def _frost_free(df, years):
    lengths = []
    for y in years:
        frost = (df.loc[df["year"] == y, "t2m_min"] <= C.FROST_DAY_TMIN_C).to_numpy()
        if len(frost) < 300:  # incomplete year
            continue
        lengths.append(max((l for _, l in _runs(~frost)), default=0))
    if not lengths:
        return {"median_days": None, "p10": None, "p90": None}
    return {"median_days": int(np.median(lengths)), "p10": int(np.percentile(lengths, 10)),
            "p90": int(np.percentile(lengths, 90))}


def _year_flags(df, ref, zone):
    gs = C.GROWING_SEASON_MONTHS[zone]
    gs_rain = df[df["month"].isin(gs)].groupby("year")["precip"].sum(min_count=1)
    heat = (df["t2m_max"] > C.HEAT_DAY_TMAX_C).groupby(df["year"]).sum()
    flags = {}
    for y in sorted(df["year"].unique()):
        f = []
        if ref["drought_rain_thr"] is not None and pd.notna(gs_rain.get(y)) and gs_rain[y] < ref["drought_rain_thr"]:
            f.append("drought")
        if ref["heat_year_thr"] is not None and heat.get(y, 0) > ref["heat_year_thr"] and heat.get(y, 0) > 0:
            f.append("heat")
        if f:
            flags[str(int(y))] = f
    return flags


def _validation(base_monthly, prism):
    if prism is None:
        return None
    p = prism.copy()
    m = base_monthly.merge(p, on=["year", "month"], how="inner").dropna(subset=["precip_mm_x", "precip_mm_y"]) \
        if "precip_mm" in p else None
    if m is None or len(m) < 12:
        return None
    out = {
        "precip_corr": _r(np.corrcoef(m["precip_mm_x"], m["precip_mm_y"])[0, 1], 2),
        "precip_bias_pct": _r((m["precip_mm_x"].sum() - m["precip_mm_y"].sum()) / m["precip_mm_y"].sum() * 100, 1),
        "n_months": int(len(m)),
    }
    if "tmean_c" in m:
        t = m.dropna(subset=["t_mean", "tmean_c"])
        out["tmean_bias_c"] = _r((t["t_mean"] - t["tmean_c"]).mean(), 2)
        out["tmean_corr"] = _r(np.corrcoef(t["t_mean"], t["tmean_c"])[0, 1], 3) if len(t) > 2 else None
    return {"prism": out}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def build_climate_profile(daily, lat, smap=None, ndvi=None, prism=None, scenario=None,
                          zone=None, data_tier=None) -> dict:
    zone = zone or default_zone(lat)
    scen = normalize_scenario(scenario)
    scenario_on = is_active(scen)

    base = _prepare(daily)
    if base.empty:
        raise ValueError("no daily data")
    base["et0"] = hargreaves_et0(base, lat)
    ref = _baseline_reference(base, zone)

    if scenario_on:
        df = _prepare(apply_scenario(base[["date", "t2m", "t2m_max", "t2m_min", "precip",
                                            "root_wetness", "solar", "rh"]], scen, lat))
        df["et0"] = hargreaves_et0(df, lat)
    else:
        df = base

    years = sorted(int(y) for y in df["year"].unique())
    monthly = _monthly_table(df)
    clim = monthly.groupby("month").mean(numeric_only=True)

    monthly_climatology = {
        str(m): {
            "t_mean": _r(clim["t_mean"].get(m), 1), "t_max": _r(clim["t_max"].get(m), 1),
            "t_min": _r(clim["t_min"].get(m), 1), "precip_mm": _r(clim["precip_mm"].get(m), 1),
            "root_wetness": _r(clim["root_wetness"].get(m), 2), "et0_mm": _r(clim["et0_mm"].get(m), 1),
        } for m in MONTHS
    }
    water_balance = {}
    for m in MONTHS:
        p, e = clim["precip_mm"].get(m), clim["et0_mm"].get(m)
        water_balance[str(m)] = {
            "precip_mm": _r(p, 1), "et0_mm": _r(e, 1),
            "deficit_mm": _r(max(0.0, e - p), 1) if pd.notna(p) and pd.notna(e) else None,
        }

    sm_anom, sm_source, smap_years = _soil_moisture_anomaly(df, ref, smap, scenario_on)
    ndvi_by_month, bare = _ndvi(ndvi)

    annual_p = df.groupby("year")["precip"].sum(min_count=1).dropna()
    cv = annual_p.std() / annual_p.mean() if len(annual_p) > 2 and annual_p.mean() > 0 else None

    if data_tier is None:
        data_tier = "us_enhanced" if prism is not None else ("featured" if (smap is not None or ndvi is not None) else "standard")

    return {
        "years_covered": [years[0], years[-1]],
        "n_years": len(years),
        "missing_fraction": _r(base[CORE].isna().mean().mean(), 3),
        "zone": zone,
        "monthly_climatology": monthly_climatology,
        "trends": _trends(df),
        "stress_by_month": _stress_by_month(df, years, ref["extreme_thr"]),
        "extreme_rain_threshold_mm": _r(ref["extreme_thr"], 1),
        "water_balance_by_month": water_balance,
        "soil_moisture_anomaly_by_month": sm_anom,
        "soil_moisture_source": sm_source,
        "ndvi_by_month": ndvi_by_month,
        "bare_months_observed": bare,
        "frost_free_season": _frost_free(df, years),
        "year_stress_flags": _year_flags(df, ref, zone),
        "uncertainty": {"interannual_cv_precip": _r(cv, 2), "smap_years": smap_years},
        "validation": _validation(_monthly_table(base), prism),
        "scenario_applied": scen,
        "data_tier": data_tier,
    }
