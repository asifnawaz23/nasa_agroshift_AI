import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.climate_profile import build_climate_profile
from engine.scenario import apply_scenario, normalize_scenario

HERE = Path(__file__).parent
REQUIRED_KEYS = {
    "years_covered", "n_years", "missing_fraction", "monthly_climatology", "trends", "stress_by_month",
    "water_balance_by_month", "soil_moisture_anomaly_by_month", "ndvi_by_month", "bare_months_observed",
    "frost_free_season", "year_stress_flags", "uncertainty", "validation", "scenario_applied", "data_tier",
}


def synthetic(years=(2020, 2021, 2022)):
    """Mild weather every day, plus known events each year:
    - July 1-5: t2m_max 41 (5 heat days, 5 severe heat days)
    - Jan 1-10: t2m_min -5 (10 frost days)
    - March 1-15: no rain (dry spell); every other day 2 mm
    """
    dates = pd.date_range(f"{years[0]}-01-01", f"{years[-1]}-12-31", freq="D")
    df = pd.DataFrame({"date": dates, "t2m": 20.0, "t2m_max": 26.0, "t2m_min": 14.0,
                       "precip": 2.0, "root_wetness": 0.5, "solar": 18.0, "rh": 60.0})
    m, d = df["date"].dt.month, df["date"].dt.day
    df.loc[(m == 7) & (d <= 5), "t2m_max"] = 41.0
    df.loc[(m == 1) & (d <= 10), "t2m_min"] = -5.0
    df.loc[(m == 3) & (d <= 15), "precip"] = 0.0
    return df


@pytest.fixture(scope="module")
def iowa():
    return pd.read_csv(HERE / "sample_power_iowa.csv")


def test_all_keys_present_and_nulls_without_satellite_data():
    p = build_climate_profile(synthetic(), lat=30.0)
    assert REQUIRED_KEYS <= set(p)
    assert p["ndvi_by_month"] is None and p["bare_months_observed"] is None and p["validation"] is None
    assert p["data_tier"] == "standard" and p["zone"] == "subtropical"


def test_known_event_counts():
    s = build_climate_profile(synthetic(), lat=30.0)["stress_by_month"]
    assert s["heat_days"]["7"] == 5.0 and s["severe_heat_days"]["7"] == 5.0
    assert s["heat_days"]["6"] == 0.0
    assert s["frost_days"]["1"] == 10.0
    assert s["dry_spell_prob"]["3"] == 1.0 and s["dry_spell_prob"]["5"] == 0.0


def test_missing_values_do_not_crash():
    df = synthetic()
    df.loc[::7, "precip"] = -999
    df.loc[::11, "t2m_max"] = np.nan
    p = build_climate_profile(df, lat=30.0)
    assert 0 < p["missing_fraction"] < 0.2
    assert p["monthly_climatology"]["7"]["t_max"] is not None


def test_iowa_et0_and_water_balance_are_realistic(iowa):
    p = build_climate_profile(iowa, lat=42.0, zone="temperate")
    july = p["water_balance_by_month"]["7"]
    assert 130 < july["et0_mm"] < 190          # ~4.5-6 mm/day in an Iowa July
    assert july["deficit_mm"] > 30
    assert p["water_balance_by_month"]["1"]["deficit_mm"] == 0.0
    assert 150 < p["frost_free_season"]["median_days"] < 200


def test_iowa_2012_flagged_as_drought(iowa):
    flags = build_climate_profile(iowa, lat=42.0, zone="temperate")["year_stress_flags"]
    assert "drought" in flags.get("2012", [])


def test_matches_committed_sample_profile(iowa):
    """The engine reproduces the numbers in sample_profile.json (made by the prototype)."""
    sample = json.loads((HERE / "sample_profile.json").read_text(encoding="utf-8"))
    p = build_climate_profile(iowa, lat=42.0, zone="temperate")
    for m in ("1", "7"):
        assert p["water_balance_by_month"][m] == sample["water_balance_by_month"][m]
        assert p["stress_by_month"]["heat_days"][m] == sample["stress_by_month"]["heat_days"][m]
        assert p["stress_by_month"]["frost_days"][m] == sample["stress_by_month"]["frost_days"][m]
    assert p["frost_free_season"] == sample["frost_free_season"]
    assert p["year_stress_flags"] == sample["year_stress_flags"]


def test_scenario_hotter_and_drier(iowa):
    base = build_climate_profile(iowa, lat=42.0, zone="temperate")
    hot_dry = build_climate_profile(iowa, lat=42.0, zone="temperate", scenario={"temp_c": 3, "rain_pct": -30})
    assert hot_dry["stress_by_month"]["heat_days"]["7"] > base["stress_by_month"]["heat_days"]["7"]
    assert hot_dry["water_balance_by_month"]["7"]["et0_mm"] > base["water_balance_by_month"]["7"]["et0_mm"]
    assert hot_dry["water_balance_by_month"]["7"]["deficit_mm"] > base["water_balance_by_month"]["7"]["deficit_mm"]
    # thresholds stay at baseline -> less rain means fewer extreme-rain days, more drought years
    assert hot_dry["stress_by_month"]["extreme_rain_days"]["6"] < base["stress_by_month"]["extreme_rain_days"]["6"]
    n_drought = lambda p: sum("drought" in f for f in p["year_stress_flags"].values())
    assert n_drought(hot_dry) > n_drought(base)
    assert hot_dry["soil_moisture_anomaly_by_month"]["7"] < base["soil_moisture_anomaly_by_month"]["7"]
    assert hot_dry["scenario_applied"] == {"temp_c": 3.0, "rain_pct": -30.0}


def test_scenario_is_clamped_and_does_not_change_input():
    df = synthetic()
    before = df.copy()
    assert normalize_scenario({"temp_c": 99, "rain_pct": -99}) == {"temp_c": 5.0, "rain_pct": -50.0}
    out = apply_scenario(df, {"temp_c": 2}, lat=30.0)
    pd.testing.assert_frame_equal(df, before)
    assert (out["t2m"] - df["t2m"]).round(6).eq(2.0).all()


def test_ndvi_bare_months_and_scaling():
    dates = pd.date_range("2020-01-01", "2021-12-31", freq="16D")
    vals = np.where(dates.month.isin([11, 12, 1, 2, 3]), 1800, 6500)  # raw MODIS integers
    p = build_climate_profile(synthetic(), lat=42.0, ndvi=pd.DataFrame({"date": dates, "ndvi": vals}))
    assert p["ndvi_by_month"]["7"] == 0.65
    assert p["bare_months_observed"] == [1, 2, 3, 11, 12]
    assert p["data_tier"] == "featured"


def test_smap_anomaly_used_when_present():
    dates = pd.date_range("2020-01-01", "2022-12-31", freq="D")
    sm = np.where(dates.year == 2022, 0.15, 0.30)  # last year much drier
    p = build_climate_profile(synthetic(), lat=30.0, smap=pd.DataFrame({"date": dates, "sm": sm}))
    assert p["soil_moisture_source"] == "smap" and p["uncertainty"]["smap_years"] == 3
    assert p["soil_moisture_anomaly_by_month"]["7"] < 0


def test_prism_validation_perfect_match(iowa):
    p0 = build_climate_profile(iowa, lat=42.0, zone="temperate")
    df = iowa.copy()
    df["date"] = pd.to_datetime(df["date"])
    prism = df.groupby([df["date"].dt.year.rename("year"), df["date"].dt.month.rename("month")]).agg(
        precip_mm=("precip", "sum"), tmean_c=("t2m", "mean")).reset_index()
    p = build_climate_profile(iowa, lat=42.0, zone="temperate", prism=prism)
    v = p["validation"]["prism"]
    assert v["precip_corr"] == 1.0 and v["precip_bias_pct"] == 0.0 and v["tmean_bias_c"] == 0.0
    assert p["data_tier"] == "us_enhanced" and p0["validation"] is None


def test_trend_significance_flags():
    import numpy as np
    from engine.climate_profile import _trend_is_significant

    years = np.arange(2006, 2026, dtype=float)
    steady_rise = 20 + 0.05 * (years - 2006)
    rng = np.random.default_rng(1)
    noise = 800 + rng.normal(0, 150, len(years))

    assert _trend_is_significant(years, steady_rise)
    assert not _trend_is_significant(years, noise)
    assert not _trend_is_significant(years[:3], steady_rise[:3])
