import json
from pathlib import Path

import pandas as pd
import pytest

from engine import knowledge as K
from engine.climate_profile import build_climate_profile
from engine.explain import build_explanations, load_text

HERE = Path(__file__).parent
CORN_SOY = {"cycle_years": 2, "steps": [
    {"year": 1, "crop": "maize", "sow_month": 5, "harvest_month": 10},
    {"year": 2, "crop": "soybean", "sow_month": 5, "harvest_month": 10}]}


@pytest.fixture(scope="module")
def iowa_profile():
    return build_climate_profile(pd.read_csv(HERE / "sample_power_iowa.csv"), 42.0, zone="temperate")


@pytest.fixture(scope="module")
def templates():
    return K.load_templates()


# --- knowledge -----------------------------------------------------------------
def test_crops_are_typed():
    crops = K.load_crops()
    assert len(crops) == 14
    assert crops["soybean"]["n_fixing"] is True and crops["maize"]["n_fixing"] is False
    assert isinstance(crops["cotton"]["water_need_mm"], int)


def test_step_months_wraps_over_new_year():
    assert K.step_months({"sow_month": 11, "harvest_month": 4}) == [11, 12, 1, 2, 3]


def test_bare_months_corn_soybean():
    assert K.bare_months(CORN_SOY) == [1, 2, 3, 4, 10, 11, 12]


def test_soil_builder_has_fewer_bare_months(templates):
    t = templates["temperate"]
    assert K.bare_months_per_year(t["current_default"]["rotation"]) == 7.0
    assert K.bare_months_per_year(t["soil_builder"]["rotation"]) < 5


def test_sensitive_windows_maize_flowers_in_july():
    w = K.sensitive_windows(CORN_SOY, "temperate")
    assert any(x["crop"] == "maize" and x["month"] == 7 and x["stage"] == "flowering" and "heat" in x["sensitive"]
               for x in w)


def test_stage_stretch_for_shorter_season():
    cal = K.load_calendars()[("maize", "temperate")]  # 5-month calendar
    step = {"sow_month": 5, "harvest_month": 9}       # 4-month rotation step
    stages = [K.stage_for(step, cal, k)["stage"] for k in range(4)]
    assert stages[0] == "establishment" and "flowering" in stages


def test_water_need_per_year(templates):
    sub = templates["subtropical"]
    assert K.annual_water_need_mm(sub["water_saver"]["rotation"]) < K.annual_water_need_mm(sub["current_default"]["rotation"])


# --- explanations ---------------------------------------------------------------
def test_all_five_parts_present(iowa_profile):
    e = build_explanations("current_default", CORN_SOY, "temperate", iowa_profile)
    assert set(e) == {"why_suggested", "evidence", "benefits", "info_gaps", "local_review"}
    assert e["why_suggested"].startswith("This is what is farmed here today")
    assert e["evidence"] and all(x["source"] and x["type"] == "observed" for x in e["evidence"])


def test_evidence_numbers_come_from_profile(iowa_profile):
    e = build_explanations("current_default", CORN_SOY, "temperate", iowa_profile)
    july = iowa_profile["water_balance_by_month"]["7"]
    deficit = next(x for x in e["evidence"] if x["kind"] == "deficit" and x["month"] == 7)
    assert f"{july['deficit_mm']:.0f} mm" in deficit["text"] and set(deficit["crops"]) == {"maize", "soybean"}


def test_alternative_compares_with_current(templates, iowa_profile):
    t = templates["temperate"]
    e = build_explanations("soil_builder", t["soil_builder"]["rotation"], "temperate", iowa_profile,
                           current_rotation=t["current_default"]["rotation"])
    assert "% more water" in e["why_suggested"] or "% less water" in e["why_suggested"]
    assert any("Nitrogen-fixing" in b for b in e["benefits"])
    assert any("buyers" in r for r in e["local_review"])


def test_scenario_and_missing_soil_are_info_gaps(iowa_profile):
    hot = build_climate_profile(pd.read_csv(HERE / "sample_power_iowa.csv"), 42.0, zone="temperate",
                                scenario={"temp_c": 3, "rain_pct": -30})
    e = build_explanations("current_default", CORN_SOY, "temperate", hot, soil={"available": False})
    gaps = " ".join(e["info_gaps"])
    assert "What-If" in gaps and "+3 °C" in gaps and "Soil data is not available" in gaps


def test_heat_tolerant_crop_judged_at_40c():
    profile = {"stress_by_month": {"heat_days": {"7": 28.0}, "severe_heat_days": {"7": 1.0}},
               "water_balance_by_month": {}, "n_years": 20}
    cotton = {"cycle_years": 1, "steps": [{"year": 1, "crop": "cotton", "sow_month": 5, "harvest_month": 11}]}
    e = build_explanations("current_default", cotton, "subtropical", profile)
    assert not any(x["kind"] == "heat" for x in e["evidence"])  # 28 days >35 C is normal for cotton


def test_urdu_output_and_same_keys_in_both_languages(iowa_profile):
    e = build_explanations("current_default", CORN_SOY, "temperate", iowa_profile, lang="ur")
    assert "جولائی" in " ".join(x["text"] for x in e["evidence"])

    def keys(d, prefix=""):
        out = set()
        for k, v in d.items():
            if k.startswith("_"):
                continue
            out |= keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {prefix + k}
        return out

    assert keys(load_text("en")) == keys(load_text("ur"))


def test_templates_placeholders_match_between_languages():
    import re
    en, ur = load_text("en"), load_text("ur")
    for section in ("why", "evidence", "benefits", "info_gaps", "local_review"):
        for k, v in en[section].items():
            if isinstance(v, str):
                assert set(re.findall(r"{(\w+)}", v)) == set(re.findall(r"{(\w+)}", ur[section][k])), (section, k)
