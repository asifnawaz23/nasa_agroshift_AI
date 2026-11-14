
"""Rotation suitability scoring.

Pure Python module. No Django imports.

Public function:
    score_rotation(rotation, profile, zone, priorities, constraints,
                   soil=None, crops=None, calendars=None) -> dict
"""

from __future__ import annotations

from statistics import mean

from . import constants as C
from .knowledge import (
    bare_fraction_by_month,
    families,
    load_calendars,
    load_crops,
    sensitive_windows,
    step_months,
)


SCORE_KEYS = (
    "overall",
    "water_fit",
    "climate_risk",
    "soil_health",
    "erosion_infiltration",
    "pest_break",
    "income",
)

WATER_STRESS_FACTORS = {
    "rainfed": 1.0,
    "limited_irrigation": 0.65,
    "irrigated": 0.35,
}

ROOT_DEPTH_SCORES = {
    "shallow": 33,
    "medium": 67,
    "deep": 100,
}


def _clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(float(value), maximum))


def _average(values, default=0.0):
    values = list(values)
    return mean(values) if values else default


def _scale_1_to_5(value):
    """Convert a crop attribute from its 1-5 range to 0-100."""
    return _clamp((value - 1) * 25)


def _month_value(data, month, default=0.0):
    return (data or {}).get(str(month), default)


def _crop_slugs(rotation, crops):
    return list(dict.fromkeys(
        step["crop"]
        for step in rotation.get("steps", [])
        if step.get("crop") in crops
    ))


def _water_fit(rotation, profile, crops, constraints):
    steps = [
        step for step in rotation.get("steps", [])
        if step.get("crop") in crops
    ]

    if not steps:
        return 0.0

    water_availability = constraints.get(
        "water_availability",
        "rainfed",
    )
    stress_factor = WATER_STRESS_FACTORS.get(
        water_availability,
        1.0,
    )

    water_balance = profile.get("water_balance_by_month", {})
    stress = profile.get("stress_by_month", {})

    monthly_stress = []

    for step in steps:
        for month in step_months(step):
            balance = water_balance.get(str(month), {})
            et0 = balance.get("et0_mm") or 0.0
            deficit = balance.get("deficit_mm") or 0.0

            deficit_ratio = (
                _clamp(deficit / et0, 0, 1)
                if et0 > 0
                else 0.0
            )

            dry_probability = _clamp(
                _month_value(
                    stress.get("dry_spell_prob"),
                    month,
                ) * 100
            ) / 100

            monthly_stress.append(
                0.65 * deficit_ratio
                + 0.35 * dry_probability
            )

    climate_supply_score = 100 * (
        1 - _average(monthly_stress) * stress_factor
    )

    drought_tolerance = _average([
        _scale_1_to_5(crops[step["crop"]]["drought_tolerance"])
        for step in steps
    ])

    annual_need = sum(
        crops[step["crop"]]["water_need_mm"]
        for step in steps
    ) / max(rotation.get("cycle_years", 1), 1)

    demand_score = 100 - _clamp(annual_need / 800 * 100)

    return _clamp(
        0.40 * climate_supply_score
        + 0.30 * drought_tolerance
        + 0.30 * demand_score
    )


def _climate_risk(rotation, profile, zone, crops, calendars):
    """Higher score means lower climate risk."""
    stress = profile.get("stress_by_month", {})
    water_balance = profile.get("water_balance_by_month", {})

    windows = {
        (window["crop"], window["year"], window["month"]):
        window["sensitive"]
        for window in sensitive_windows(rotation, zone, calendars)
    }

    risks = []

    for step in rotation.get("steps", []):
        crop = crops.get(step["crop"])

        if crop is None:
            continue

        for month in step_months(step):
            sensitive = windows.get(
                (step["crop"], step["year"], month)
            )

            if sensitive is None:
                if (step["crop"], zone) in calendars:
                    continue

                # Without a crop calendar, use all three climate hazards.
                sensitive = ["heat", "drought", "frost"]

            month_risks = []

            if "heat" in sensitive:
                heat_data = (
                    stress.get("severe_heat_days", {})
                    if crop["heat_tolerance"] >= 4
                    else stress.get("heat_days", {})
                )

                heat_days = _month_value(heat_data, month)
                heat_severity = _clamp(heat_days / 7)

                susceptibility = (
                    6 - crop["heat_tolerance"]
                ) / 5

                month_risks.append(
                    heat_severity * susceptibility
                )

            if "drought" in sensitive:
                balance = water_balance.get(str(month), {})
                et0 = balance.get("et0_mm") or 0.0
                deficit = balance.get("deficit_mm") or 0.0

                deficit_ratio = (
                    _clamp(deficit / et0, 0, 1)
                    if et0 > 0
                    else 0.0
                )

                dry_probability = _clamp(
                    _month_value(
                        stress.get("dry_spell_prob"),
                        month,
                    ) * 100
                ) / 100

                drought_severity = (
                    0.65 * deficit_ratio
                    + 0.35 * dry_probability
                )

                susceptibility = (
                    6 - crop["drought_tolerance"]
                ) / 5

                month_risks.append(
                    drought_severity * susceptibility
                )

            if "frost" in sensitive:
                frost_days = _month_value(
                    stress.get("frost_days"),
                    month,
                )

                frost_severity = _clamp(frost_days / 7)

                susceptibility = (
                    6 - crop["frost_tolerance"]
                ) / 5

                month_risks.append(
                    frost_severity * susceptibility
                )

            if month_risks:
                risks.append(_average(month_risks))

    return _clamp(100 * (1 - _average(risks, default=0.0)))


def _soil_health(rotation, crops):
    slugs = _crop_slugs(rotation, crops)

    if not slugs:
        return 0.0

    crop_scores = []

    for slug in slugs:
        crop = crops[slug]

        nitrogen_score = 100 if crop["n_fixing"] else 0
        root_score = ROOT_DEPTH_SCORES.get(
            crop["root_depth"],
            50,
        )

        crop_score = (
            0.30 * _scale_1_to_5(crop["ground_cover"])
            + 0.30 * _scale_1_to_5(crop["residue_om"])
            + 0.25 * nitrogen_score
            + 0.15 * root_score
        )

        crop_scores.append(crop_score)

    return _clamp(_average(crop_scores))


def _erosion_infiltration(rotation, crops, soil):
    slugs = _crop_slugs(rotation, crops)

    if not slugs:
        return 0.0

    erosion_scores = [
        _scale_1_to_5(crops[slug]["erosion_protection"])
        for slug in slugs
    ]

    cover_scores = [
        _scale_1_to_5(crops[slug]["ground_cover"])
        for slug in slugs
    ]

    bare_fractions = bare_fraction_by_month(rotation)
    annual_bare_fraction = _average(bare_fractions.values())

    bare_soil_score = 100 * (1 - annual_bare_fraction)

    erodibility = (
        soil.get("erodibility_hint")
        if soil and soil.get("available", False)
        else None
    )

    erodibility_factor = {
        "low": 0.75,
        "moderate": 1.0,
        "high": 1.25,
    }.get(erodibility, 1.0)

    bare_soil_score = _clamp(
        100 - (100 - bare_soil_score) * erodibility_factor
    )

    return _clamp(
        0.40 * _average(erosion_scores)
        + 0.30 * _average(cover_scores)
        + 0.30 * bare_soil_score
    )


def _pest_break(rotation, crops):
    slugs = _crop_slugs(rotation, crops)

    if not slugs:
        return 0.0

    crop_families = families(rotation, crops)

    diversity_score = _clamp(
        len(crop_families) / 4 * 100
    )

    steps = sorted(
        [
            step for step in rotation.get("steps", [])
            if step.get("crop") in crops
        ],
        key=lambda step: (
            step["year"],
            step["sow_month"],
        ),
    )

    if len(steps) <= 1:
        transition_score = 0.0
    else:
        transitions = 0

        for index, step in enumerate(steps):
            next_step = steps[(index + 1) % len(steps)]

            current_family = crops[step["crop"]]["family"]
            next_family = crops[next_step["crop"]]["family"]

            if current_family != next_family:
                transitions += 1

        transition_score = (
            transitions / len(steps)
        ) * 100

    return _clamp(
        0.65 * diversity_score
        + 0.35 * transition_score
    )


def _income(rotation, crops, constraints):
    slugs = _crop_slugs(rotation, crops)

    if not slugs:
        return 0.0

    market_preference = constraints.get(
        "market_pref",
        "balanced",
    )

    scores = []

    for slug in slugs:
        crop = crops[slug]

        income_score = _scale_1_to_5(
            crop["income_level"]
        )

        if market_preference == "cash":
            market_score = (
                100 if crop["role"] == "cash" else 45
            )
        elif market_preference == "forage":
            market_score = (
                100 if crop["role"] == "forage" else 45
            )
        else:
            market_score = (
                100 if crop["role"] in {"cash", "forage"}
                else 75
            )

        scores.append(
            0.75 * income_score
            + 0.25 * market_score
        )

    return _clamp(_average(scores))


def _equipment_penalty(rotation, crops, constraints):
    equipment = constraints.get("equipment", "standard")

    if equipment == "specialized":
        return 0.0

    steps = [
        step for step in rotation.get("steps", [])
        if step.get("crop") in crops
    ]

    if not steps:
        return 0.0

    special_count = sum(
        1 for step in steps
        if crops[step["crop"]]["special_equipment"]
    )

    penalty_per_crop = {
        "basic": 20,
        "standard": 10,
    }.get(equipment, 10)

    return (
        special_count / len(steps)
    ) * penalty_per_crop


def score_rotation(
    rotation,
    profile,
    zone,
    priorities,
    constraints,
    soil=None,
    crops=None,
    calendars=None,
):
    """Calculate the seven suitability scores for a crop rotation."""
    crops = crops or load_crops()
    calendars = calendars or load_calendars()
    priorities = priorities or {}
    constraints = constraints or {}

    if not rotation or not rotation.get("steps"):
        return {key: 0.0 for key in SCORE_KEYS}

    if rotation.get("cycle_years", 0) < 1:
        raise ValueError("rotation.cycle_years must be at least 1")

    scores = {
        "water_fit": _water_fit(
            rotation, profile, crops, constraints
        ),
        "climate_risk": _climate_risk(
            rotation, profile, zone, crops, calendars
        ),
        "soil_health": _soil_health(rotation, crops),
        "erosion_infiltration": _erosion_infiltration(
            rotation, crops, soil
        ),
        "pest_break": _pest_break(rotation, crops),
        "income": _income(rotation, crops, constraints),
    }

    water_priority = _clamp(
        priorities.get("water", 3), 1, 5
    )
    soil_priority = _clamp(
        priorities.get("soil", 3), 1, 5
    )

    weights = {
        "water_fit": water_priority,
        "climate_risk": (water_priority + soil_priority) / 2,
        "soil_health": soil_priority,
        "erosion_infiltration": _clamp(
            priorities.get("erosion", 3), 1, 5
        ),
        "pest_break": _clamp(
            priorities.get("pest", 3), 1, 5
        ),
        "income": _clamp(
            priorities.get("income", 3), 1, 5
        ),
    }

    total_weight = sum(weights.values())

    overall = sum(
        scores[key] * weights[key]
        for key in weights
    ) / total_weight

    overall -= _equipment_penalty(
        rotation, crops, constraints
    )

    scores["overall"] = _clamp(overall)

    return {
        key: round(_clamp(scores[key]), 1)
        for key in SCORE_KEYS
    }
