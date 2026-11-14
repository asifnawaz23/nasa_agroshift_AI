
import copy
import json
from pathlib import Path

import pytest

from engine.knowledge import load_calendars, load_crops, load_templates
from engine.scoring import SCORE_KEYS
from engine.strategies import build_strategies


@pytest.fixture(scope="module")
def engine_data():
    with (Path(__file__).parent / "sample_profile.json").open(
        encoding="utf-8"
    ) as file:
        profile = json.load(file)

    return {
        "profile": profile,
        "crops": load_crops(),
        "calendars": load_calendars(),
        "templates": load_templates(),
    }


@pytest.fixture
def strategy_inputs(engine_data):
    return {
        "zone": "temperate",
        "profile": copy.deepcopy(engine_data["profile"]),
        "priorities": {
            "water": 3,
            "soil": 3,
            "income": 3,
            "erosion": 3,
            "pest": 3,
        },
        "constraints": {
            "water_availability": "rainfed",
            "equipment": "standard",
            "market_pref": "balanced",
        },
        "soil": {"available": False},
        "crops": engine_data["crops"],
        "calendars": engine_data["calendars"],
        "templates": engine_data["templates"],
    }


def test_build_strategies_returns_three_expected_strategies(strategy_inputs):
    strategies = build_strategies(**strategy_inputs)

    assert [item["key"] for item in strategies] == [
        "current",
        "water_saver",
        "soil_builder",
    ]


def test_each_strategy_has_required_fields_and_scores(strategy_inputs):
    strategies = build_strategies(**strategy_inputs)

    for strategy in strategies:
        assert strategy["name"]
        assert strategy["description"]
        assert set(strategy["scores"]) == set(SCORE_KEYS)
        assert strategy["baseline_scores"] is None

        for score in strategy["scores"].values():
            assert 0 <= score <= 100


def test_farmer_rotation_replaces_default_current_rotation(
    strategy_inputs,
):
    templates = strategy_inputs["templates"]

    farmer_rotation = copy.deepcopy(
        templates["temperate"]["water_saver"]["rotation"]
    )

    strategy_inputs["current_rotation"] = farmer_rotation

    strategies = build_strategies(**strategy_inputs)

    assert strategies[0]["key"] == "current"
    assert strategies[0]["description"] == (
        "Represents the farmer's supplied crop rotation."
    )

    assert strategies[0]["scores"] == strategies[1]["scores"]


def test_active_scenario_requires_baseline_profile(strategy_inputs):
    strategy_inputs["profile"]["scenario_applied"] = {
        "rain_pct": -20,
        "temp_c": 2,
    }

    with pytest.raises(ValueError, match="baseline_profile is required"):
        build_strategies(**strategy_inputs)


def test_scenario_returns_separate_baseline_and_adjusted_scores(
    strategy_inputs,
):
    baseline_profile = copy.deepcopy(strategy_inputs["profile"])
    scenario_profile = copy.deepcopy(baseline_profile)

    scenario_profile["scenario_applied"] = {
        "rain_pct": -20,
        "temp_c": 2,
    }

    for month in scenario_profile["water_balance_by_month"].values():
        month["deficit_mm"] += 20

    for month, value in scenario_profile["stress_by_month"][
        "heat_days"
    ].items():
        scenario_profile["stress_by_month"]["heat_days"][month] = (
            value + 2
        )

    strategy_inputs["profile"] = scenario_profile
    strategy_inputs["baseline_profile"] = baseline_profile

    strategies = build_strategies(**strategy_inputs)

    for strategy in strategies:
        assert strategy["baseline_scores"] is not None
        assert set(strategy["baseline_scores"]) == set(SCORE_KEYS)
        assert set(strategy["scores"]) == set(SCORE_KEYS)


def test_unsupported_zone_raises_value_error(strategy_inputs):
    strategy_inputs["zone"] = "unsupported"

    with pytest.raises(ValueError, match="Unsupported rotation zone"):
        build_strategies(**strategy_inputs)


def test_input_profile_is_not_modified(strategy_inputs):
    original_profile = copy.deepcopy(strategy_inputs["profile"])

    build_strategies(**strategy_inputs)

    assert strategy_inputs["profile"] == original_profile


EXPLANATION_PARTS = (
    "why_suggested",
    "evidence",
    "benefits",
    "info_gaps",
    "local_review",
)


def test_each_strategy_has_the_five_explanation_parts(strategy_inputs):
    strategies = build_strategies(**strategy_inputs)

    for strategy in strategies:
        for part in EXPLANATION_PARTS:
            assert part in strategy, f"{strategy['key']} is missing {part}"

        assert isinstance(strategy["why_suggested"], str)
        assert strategy["why_suggested"].strip()
        assert strategy["info_gaps"], "every strategy states its information gaps"
        assert strategy["local_review"], "every strategy lists local review items"
        assert strategy["rotation"]["steps"]

    assert [s["is_current"] for s in strategies] == [True, False, False]


def test_explanations_follow_requested_language(strategy_inputs):
    english = build_strategies(**strategy_inputs, lang="en")
    urdu = build_strategies(**strategy_inputs, lang="ur")

    assert english[1]["why_suggested"] != urdu[1]["why_suggested"]
    # Urdu text uses Arabic-script characters.
    assert any("\u0600" <= ch <= "\u06ff" for ch in urdu[1]["why_suggested"])
