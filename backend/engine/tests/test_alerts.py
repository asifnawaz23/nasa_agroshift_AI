from pathlib import Path

import pandas as pd
import pytest

from engine.alerts import ORDER, build_alerts, severity, summarize_alerts
from engine.climate_profile import build_climate_profile

HERE = Path(__file__).parent
CORN = {"cycle_years": 1, "steps": [{"year": 1, "crop": "maize", "sow_month": 5, "harvest_month": 10}]}
COTTON = {"cycle_years": 1, "steps": [{"year": 1, "crop": "cotton", "sow_month": 5, "harvest_month": 11}]}
CORN_SOY_SAME_YEAR = {"cycle_years": 2, "steps": [
    {"year": 1, "crop": "maize", "sow_month": 5, "harvest_month": 10},
    {"year": 2, "crop": "soybean", "sow_month": 5, "harvest_month": 10}]}


def profile(**stress):
    """Minimal profile: stress values given per month, e.g. heat_days={"7": 4}."""
    p = {"stress_by_month": {}, "water_balance_by_month": {}, "soil_moisture_anomaly_by_month": {},
         "scenario_applied": {"temp_c": 0, "rain_pct": 0}}
    for k, v in stress.items():
        if k == "deficit_mm":
            p["water_balance_by_month"] = {m: {"deficit_mm": d} for m, d in v.items()}
        elif k == "sm":
            p["soil_moisture_anomaly_by_month"] = v
        elif k == "scenario":
            p["scenario_applied"] = v
        else:
            p["stress_by_month"][k] = v
    return p


def types(alerts):
    return {(a["type"], a["month"]): a["severity"] for a in alerts}


def test_severity_levels():
    assert severity(2, (3, 7, 12)) == "low"
    assert severity(3, (3, 7, 12)) == "moderate"
    assert severity(12.5, (3, 7, 12)) == "critical"
    assert severity(-1.6, (-1, -1.5, -2), "below") == "high"


def test_heat_counts_double_in_sensitive_stage():
    # maize flowers in July: 4 heat days x 2 = 8 -> high
    a = build_alerts(profile(heat_days={"7": 4.0}), CORN, "temperate")
    assert types(a)[("heat", 7)] == "high"


def test_heat_tolerant_crop_uses_severe_heat_days():
    a = build_alerts(profile(heat_days={"7": 28.0}, severe_heat_days={"7": 1.0}), COTTON, "subtropical")
    assert ("heat", 7) not in types(a)
    a = build_alerts(profile(heat_days={"7": 28.0}, severe_heat_days={"7": 17.0}), COTTON, "subtropical")
    assert types(a)[("heat", 7)] == "critical"


def test_irrigation_lowers_deficit_severity():
    p = profile(deficit_mm={"7": 120.0})
    assert types(build_alerts(p, CORN, "temperate", water_availability="rainfed"))[("water_deficit", 7)] == "critical"
    assert types(build_alerts(p, CORN, "temperate", water_availability="irrigated"))[("water_deficit", 7)] == "moderate"


def test_dry_spells_ignored_for_irrigated_subtropical_and_outside_sensitive_stages():
    p = profile(dry_spell_prob={str(m): 0.9 for m in range(1, 13)})
    assert not any(a["type"] == "drought" for a in build_alerts(p, COTTON, "subtropical"))
    rainfed = build_alerts(p, COTTON, "subtropical", water_availability="rainfed")
    assert {a["month"] for a in rainfed if a["type"] == "drought"} == {7, 8}  # flowering/boll set only


def test_frost_respects_tolerance():
    p = profile(frost_days={str(m): 5.0 for m in range(1, 13)})
    wheat = {"cycle_years": 1, "steps": [{"year": 1, "crop": "wheat", "sow_month": 11, "harvest_month": 4}]}
    assert not any(a["type"] == "frost" for a in build_alerts(p, wheat, "subtropical") if a["month"] in (11, 12))
    assert any(a["type"] == "frost" for a in build_alerts(p, CORN, "temperate"))  # maize tolerance 1


def test_waterlogging_needs_slow_soil():
    p = profile(extreme_rain_days={"8": 2.0})
    assert not any(a["type"] == "waterlogging" for a in build_alerts(p, COTTON, "subtropical",
                                                                      soil={"drainage_hint": "moderate"}))
    a = build_alerts(p, COTTON, "subtropical", soil={"drainage_hint": "slow"})
    assert types(a)[("waterlogging", 8)] == "high"


def test_crops_merge_only_at_same_stage():
    a = build_alerts(profile(heat_days={"7": 4.0}), CORN_SOY_SAME_YEAR, "temperate")
    heat = [x for x in a if x["type"] == "heat" and x["month"] == 7]
    assert len(heat) == 1 and set(heat[0]["crops"]) == {"maize", "soybean"}


def test_every_alert_has_reason_action_and_trigger():
    a = build_alerts(profile(heat_days={"7": 4.0}, deficit_mm={"7": 70.0}), CORN, "temperate")
    for x in a:
        assert x["reason"] and x["action"] and x["triggered_by"][0]["variable"]
        assert x["basis"] == "historical" and x["severity_label"]


def test_scenario_alerts_are_marked_simulated():
    a = build_alerts(profile(heat_days={"7": 4.0}, scenario={"temp_c": 3, "rain_pct": 0}), CORN, "temperate")
    assert a and all(x["basis"] == "simulated" for x in a)


def test_summary_worst_and_by_month():
    a = build_alerts(profile(heat_days={"7": 4.0, "8": 2.0}, deficit_mm={"8": 35.0}), CORN, "temperate")
    s = summarize_alerts(a)
    assert s["worst"] == "high" and s["by_month"][7] == "high" and s["counts"]["high"] >= 1
    assert summarize_alerts([])["worst"] == "low"


def test_urdu_text():
    a = build_alerts(profile(heat_days={"7": 4.0}), CORN, "temperate", lang="ur")
    assert "جولائی" in a[0]["reason"] and a[0]["severity_label"] == "زیادہ"


def test_real_iowa_hotter_drier_scenario_is_worse():
    daily = pd.read_csv(HERE / "sample_power_iowa.csv")
    base = summarize_alerts(build_alerts(build_climate_profile(daily, 42.0, zone="temperate"), CORN_SOY_SAME_YEAR, "temperate"))
    hot = summarize_alerts(build_alerts(build_climate_profile(daily, 42.0, zone="temperate",
                                                              scenario={"temp_c": 3, "rain_pct": -30}),
                                        CORN_SOY_SAME_YEAR, "temperate"))
    assert ORDER.index(hot["worst"]) > ORDER.index(base["worst"])
    assert sum(hot["counts"].values()) >= sum(base["counts"].values())
