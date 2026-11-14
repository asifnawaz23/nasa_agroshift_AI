
import copy
import json
from pathlib import Path

import pytest

from engine.knowledge import load_calendars, load_crops, load_templates
from engine.scoring import SCORE_KEYS, score_rotation


@pytest.fixture(scope="module")
def engine_data():
    crops = load_crops()
    calendars = load_calendars()
    templates = load_templates()

    profile_path = Path(__file__).parent / "sample_profile.json"

    with profile_path.open(encoding="utf-8") as file:
        profile = json.load(file)

    return {
        "crops": crops,
        "calendars": calendars,
        "templates": templates,
        "profile": profile,
    }


@pytest.fixture
def scoring_inputs(engine_data):
    return {
        "rotation": copy.deepcopy(
            engine_data["templates"]["temperate"]["water_saver"]["rotation"]
        ),
        "profile": copy.deepcopy(engine_data["profile"]),
        "zone": "temperate",
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
    }


def test_score_rotation_returns_all_score_components(scoring_inputs):
    scores = score_rotation(**scoring_inputs)

    assert set(scores) == set(SCORE_KEYS)

    for value in scores.values():
        assert isinstance(value, (int, float))
        assert 0 <= value <= 100


def test_score_rotation_empty_rotation_returns_zero_scores(scoring_inputs):
    scoring_inputs["rotation"] = {
        "cycle_years": 1,
        "steps": [],
    }

    scores = score_rotation(**scoring_inputs)

    assert all(value == 0 for value in scores.values())


def test_score_rotation_is_deterministic(scoring_inputs):
    first_scores = score_rotation(**scoring_inputs)
    second_scores = score_rotation(**scoring_inputs)

    assert first_scores == second_scores


def test_irrigation_improves_water_fit(scoring_inputs):
    rainfed_scores = score_rotation(**scoring_inputs)

    scoring_inputs["constraints"]["water_availability"] = "irrigated"

    irrigated_scores = score_rotation(**scoring_inputs)

    assert (
        irrigated_scores["water_fit"]
        > rainfed_scores["water_fit"]
    )


def test_priorities_affect_overall_score(scoring_inputs):
    balanced_scores = score_rotation(**scoring_inputs)

    scoring_inputs["priorities"] = {
        "water": 5,
        "soil": 1,
        "income": 1,
        "erosion": 1,
        "pest": 1,
    }

    water_focused_scores = score_rotation(**scoring_inputs)

    assert (
        water_focused_scores["overall"]
        != balanced_scores["overall"]
    )


def test_scores_do_not_modify_input_rotation_or_profile(scoring_inputs):
    original_rotation = copy.deepcopy(scoring_inputs["rotation"])
    original_profile = copy.deepcopy(scoring_inputs["profile"])

    score_rotation(**scoring_inputs)

    assert scoring_inputs["rotation"] == original_rotation
    assert scoring_inputs["profile"] == original_profile


def test_invalid_cycle_years_raises_value_error(scoring_inputs):
    scoring_inputs["rotation"]["cycle_years"] = 0

    with pytest.raises(ValueError):
        score_rotation(**scoring_inputs)
