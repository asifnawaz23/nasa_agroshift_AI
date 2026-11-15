"""engine/compare.py: the Step 6 comparison block is built from real crop data."""
from engine.compare import build_comparison
from engine.knowledge import load_crops, load_templates


def _strategy(key, zone="subtropical"):
    t = load_templates()[zone][key]
    return {"key": key, "is_current": key == "current_default", "rotation": t["rotation"],
            "scores": {"climate_risk": 72, "water_fit": 48, "soil_health": 55, "pest_break": 75},
            "benefits": ["b1"], "constraint_warnings": ["w1"], "info_gaps": ["g1", "g2"],
            "evidence": [{"text": "July is hot.", "source": "NASA POWER"}]}


def test_soil_builder_has_nitrogen_fixers_and_all_parts():
    crops = load_crops()
    comp = build_comparison(_strategy("soil_builder"), zone="subtropical", annual_rain_mm=505,
                            current_water_mm=1400, crops=crops)
    assert comp["sequence"] and " → " in comp["sequence_text"]
    assert comp["nitrogen"]["n_fixing_crops"] and comp["nitrogen"]["level"] in ("some", "strong")
    for key in ("climate", "water", "soil", "nitrogen", "pest", "benefits", "limitations",
                "evidence", "data_sources", "crop_sources"):
        assert key in comp
    assert comp["water"]["need_mm_per_year"] > 0
    assert comp["water"]["irrigation_gap_mm"] == max(comp["water"]["need_mm_per_year"] - 505, 0)
    assert comp["climate"]["level"] == "good" and comp["pest"]["risk"] == "low"
    assert "NASA POWER" in comp["data_sources"]


def test_current_rotation_has_no_vs_current_and_missing_rain_is_none():
    comp = build_comparison(_strategy("current_default"), zone="subtropical", annual_rain_mm=None,
                            current_water_mm=1400)
    assert comp["water"]["vs_current_pct"] is None
    assert comp["water"]["irrigation_gap_mm"] is None
