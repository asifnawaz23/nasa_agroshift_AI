
"""Build the three crop-rotation strategies.

Pure Python module. No Django imports.

Public function:
    build_strategies(...) -> list[dict]
"""

from .explain import build_explanations
from .knowledge import (
    load_calendars,
    load_crops,
    load_templates,
)
from .scoring import score_rotation


STRATEGY_NAMES = {
    "current": "Current Rotation",
    "water_saver": "Water Saver",
    "soil_builder": "Soil Builder",
}


def _scenario_is_active(profile):
    scenario = profile.get("scenario_applied") or {}

    return bool(
        scenario.get("rain_pct", 0)
        or scenario.get("temp_c", 0)
    )


def _get_rotation(template):
    rotation = template.get("rotation")

    if not rotation or not rotation.get("steps"):
        raise ValueError(
            f"Template '{template.get('key')}' has no valid rotation."
        )

    return rotation


def build_strategies(
    zone,
    profile,
    priorities,
    constraints,
    soil=None,
    current_rotation=None,
    baseline_profile=None,
    crops=None,
    calendars=None,
    templates=None,
    lang="en",
    data_tier=None,
):
    """Build current, water-saver and soil-builder strategies.

    current_rotation must use the normalized rotation structure:
        {
            "cycle_years": int,
            "steps": [...]
        }

    If current_rotation is None, the zone's current_default template
    is used.

    baseline_profile is required when the supplied profile contains
    an active climate scenario.

    Each strategy also carries the five required explanation parts
    (why_suggested, evidence, benefits, info_gaps, local_review) from
    engine.explain, written in `lang` ("en" or "ur").
    """
    crops = crops or load_crops()
    calendars = calendars or load_calendars()
    templates = templates or load_templates()

    if zone not in templates:
        raise ValueError(f"Unsupported rotation zone: {zone}")

    zone_templates = templates[zone]

    required_templates = (
        "current_default",
        "water_saver",
        "soil_builder",
    )

    for key in required_templates:
        if key not in zone_templates:
            raise ValueError(
                f"Missing '{key}' template for zone '{zone}'."
            )

    scenario_active = _scenario_is_active(profile)

    if scenario_active and baseline_profile is None:
        raise ValueError(
            "baseline_profile is required when a climate "
            "scenario is active."
        )

    current_template = zone_templates["current_default"]

    if current_rotation is None:
        current_rotation = _get_rotation(current_template)
        current_description = current_template["description"]
    else:
        current_description = (
            "Represents the farmer's supplied crop rotation."
        )

    strategy_rotations = [
        {
            "key": "current",
            "name": STRATEGY_NAMES["current"],
            "description": current_description,
            "rotation": current_rotation,
        },
        {
            "key": "water_saver",
            "name": STRATEGY_NAMES["water_saver"],
            "description": zone_templates["water_saver"]["description"],
            "rotation": _get_rotation(
                zone_templates["water_saver"]
            ),
        },
        {
            "key": "soil_builder",
            "name": STRATEGY_NAMES["soil_builder"],
            "description": zone_templates["soil_builder"]["description"],
            "rotation": _get_rotation(
                zone_templates["soil_builder"]
            ),
        },
    ]

    results = []

    for strategy in strategy_rotations:
        rotation = strategy["rotation"]

        scores = score_rotation(
            rotation=rotation,
            profile=profile,
            zone=zone,
            priorities=priorities,
            constraints=constraints,
            soil=soil,
            crops=crops,
            calendars=calendars,
        )

        if scenario_active:
            baseline_scores = score_rotation(
                rotation=rotation,
                profile=baseline_profile,
                zone=zone,
                priorities=priorities,
                constraints=constraints,
                soil=soil,
                crops=crops,
                calendars=calendars,
            )
        else:
            baseline_scores = None

        explanations = build_explanations(
            strategy["key"],
            rotation,
            zone,
            profile,
            soil=soil,
            tier=data_tier,
            lang=lang,
            current_rotation=current_rotation,
            crops=crops,
            calendars=calendars,
        )

        results.append({
            "key": strategy["key"],
            "name": strategy["name"],
            "description": strategy["description"],
            "is_current": strategy["key"] == "current",
            "rotation": rotation,
            "scores": scores,
            "baseline_scores": baseline_scores,
            **explanations,
        })

    return results
