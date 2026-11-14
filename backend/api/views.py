
import json
import uuid
from datasources.prepulled import load_locations


from django.http import JsonResponse
from django.utils import timezone

from .serializers import AnalyzeRequestSerializer

from datasources.cache import get_power_daily, get_soil
from datasources.errors import DataSourceError
from datasources.prepulled import find_featured, load_prepulled

from engine.alerts import build_alerts
from engine.climate_profile import build_climate_profile
from engine.constants import (
    MAX_MISSING_FRACTION,
    MIN_YEARS_FOR_CLIMATOLOGY,
    VULNERABLE_DRY_SPELL_PROB,
    VULNERABLE_HEAT_DAYS,
)
from engine.knowledge import (
    bare_fraction_by_month,
    load_calendars,
    load_crops,
    load_templates,
)

from engine.strategies import build_strategies


def health_check(request):
    return JsonResponse({
        "status": "success",
        "message": "FieldShift Planner API is running.",
        "timestamp": timezone.now().isoformat(),
    })


def _error_response(message, errors=None, status=400):
    return JsonResponse({
        "status": "error",
        "message": message,
        "errors": errors or {},
    }, status=status)


def _climate_summary(profile):
    monthly = profile["monthly_climatology"]

    rainfall = sum(
        monthly[str(month)]["precip_mm"] or 0
        for month in range(1, 13)
    )

    temperatures = [
        monthly[str(month)]["t_mean"]
        for month in range(1, 13)
        if monthly[str(month)]["t_mean"] is not None
    ]

    average_temperature = (
        round(sum(temperatures) / len(temperatures), 1)
        if temperatures else None
    )

    return {
        "annual_rainfall_mm": round(rainfall, 1),
        "average_temperature_c": average_temperature,
    }


def _bare_windows(rotation):
    fractions = bare_fraction_by_month(rotation)
    months = [
        month for month, fraction in fractions.items()
        if fraction >= 0.5
    ]

    return [
        {
            "month": month,
            "bare_fraction": round(fractions[month], 2),
        }
        for month in months
    ]


def _vulnerable_months(profile):
    vulnerable = []

    for month, values in profile["stress_by_month"].items():
        if (
            (values.get("dry_spell_prob") or 0) >= VULNERABLE_DRY_SPELL_PROB
            or (values.get("heat_days") or 0) >= VULNERABLE_HEAT_DAYS
        ):
            vulnerable.append(int(month))

    return sorted(vulnerable)


def analyze(request):
    if request.method != "POST":
        return _error_response("Method not allowed.", status=405)

    try:
        request_data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response(
            "Request body must contain valid JSON.",
            {"body": ["Invalid JSON."]},
        )

    if not isinstance(request_data, dict):
        return _error_response(
            "Request body must be a JSON object.",
            {"body": ["Expected a JSON object."]},
        )

    serializer = AnalyzeRequestSerializer(data=request_data)

    if not serializer.is_valid():
        return _error_response(
            "Request validation failed.",
            serializer.errors,
        )

    data = serializer.validated_data

    lat = data["lat"]
    lon = data["lon"]
    scenario = data.get("scenario", {})
    overrides = data.get("overrides", {})
    lang = data.get("lang", "en")

    try:
        # Identify a featured location and load any available offline data.
        featured = find_featured(lat, lon)
        prepulled = (
            load_prepulled(featured["slug"])
            if featured else {}
        )

        zone = featured["zone"] if featured else (
            "subtropical" if abs(lat) < 35 else "temperate"
        )
        data_tier = featured["tier"] if featured else "standard"

        # Load climate data. Use the featured snapshot only if live loading fails.
        power_meta = {}
        try:
            daily, power_meta = get_power_daily(lat, lon)
        except DataSourceError:
            daily = prepulled.get("power")
            if daily is None:
                return _error_response(
                    "Climate data is currently unavailable for this location.",
                    {"climate": ["NASA POWER data could not be obtained."]},
                    status=503,
                )
            power_meta = {
                "cache_hit": True,
                "fallback_used": True,
                "fetched_at": None,
            }

        if daily is None or daily.empty:
            return _error_response(
                "No usable climate data is available for this location.",
                {"climate": ["Climate dataset is empty."]},
                status=503,
            )

        # Load soil data. Soil is optional for analysis.
        soil, soil_meta = get_soil(lat, lon)
        if soil is None and prepulled.get("soil") is not None:
            soil = prepulled["soil"]
            soil_meta = {
                "cache_hit": True,
                "fallback_used": True,
                "error": None,
                "fetched_at": None,
            }

        smap = prepulled.get("smap")
        ndvi = prepulled.get("ndvi")
        prism = prepulled.get("prism")

        crops = load_crops()
        calendars = load_calendars()
        templates = load_templates()

        # Build the baseline profile from the original climate data.
        baseline_profile = build_climate_profile(
            daily,
            lat,
            smap=smap,
            ndvi=ndvi,
            prism=prism,
            zone=zone,
            data_tier=data_tier,
        )

        # Build a separate scenario profile only when a change was requested.
        scenario_active = (
            scenario.get("rain_pct", 0) != 0
            or scenario.get("temp_c", 0) != 0
        )

        profile = baseline_profile

        if scenario_active:
            profile = build_climate_profile(
                daily,
                lat,
                smap=smap,
                ndvi=ndvi,
                prism=prism,
                scenario=scenario,
                zone=zone,
                data_tier=data_tier,
            )

        # Resolve the current rotation, using the zone default when none was supplied.
        current_rotation = data["current_rotation"]

        if current_rotation is None:
            current_rotation = templates[zone]["current_default"]["rotation"]

        # Generate the three rotation strategies.
        strategies = build_strategies(
            zone=zone,
            profile=profile,
            priorities=data["priorities"],
            constraints=data["constraints"],
            soil=soil,
            current_rotation=current_rotation,
            baseline_profile=baseline_profile if scenario_active else None,
            crops=crops,
            calendars=calendars,
            templates=templates,
        )

        # Generate alerts for the farmer's current rotation.
        alerts = build_alerts(
            profile=profile,
            rotation=current_rotation,
            zone=zone,
            soil=soil,
            water_availability=data["constraints"]["water_availability"],
            lang=lang,
            crops=crops,
            calendars=calendars,
        )

        missing_fraction = profile["missing_fraction"]
        n_years = profile["n_years"]

        warnings = []

        if n_years < MIN_YEARS_FOR_CLIMATOLOGY:
            warnings.append("Climate history covers fewer than the recommended years.")

        if missing_fraction > MAX_MISSING_FRACTION:
            warnings.append("Climate data has a high missing-value fraction.")

        if soil is None:
            warnings.append("Soil data is unavailable.")

        if power_meta.get("fallback_used"):
            warnings.append("Cached or offline climate data was used.")

        sources = ["NASA POWER"]

        if soil is not None:
            sources.append("SoilGrids")

        if smap is not None:
            sources.append("SMAP")

        if ndvi is not None:
            sources.append("NDVI")

        if prism is not None:
            sources.append("PRISM")

        return JsonResponse({
            "analysis_id": str(uuid.uuid4()),
            "location": {
                "lat": lat,
                "lon": lon,
                "name": featured["name"] if featured else None,
                "country": featured["country"] if featured else None,
                "zone": zone,
            },
            "data_quality": {
                "status": (
                    "partial" if warnings else "complete"
                ),
                "tier": data_tier,
                "sources": sources,
                "warnings": warnings,
                "years_covered": profile["years_covered"],
                "n_years": n_years,
                "missing_fraction": missing_fraction,
                "climate_cache": power_meta,
                "soil_cache": soil_meta,
            },
            "climate": {
                "baseline": _climate_summary(baseline_profile),
                "scenario": {
                    "rain_pct": scenario.get("rain_pct", 0),
                    "temp_c": scenario.get("temp_c", 0),
                    **_climate_summary(profile),
                },
            },
            "soil": {
                "measured": soil,
                "farmer_texture_override": overrides.get("soil_texture"),
            },
            "bare_windows": _bare_windows(current_rotation),
            "vulnerable_months": _vulnerable_months(profile),
            "alerts": alerts,
            "strategies": strategies,
            "disclaimer": (
                "FieldShift Planner provides decision-support information, "
                "not guaranteed predictions. Income scores are regional placeholders."
            ),
        })

    except (ValueError, KeyError) as exc:
        return _error_response(
            "Analysis could not be completed with the supplied data.",
            {"analysis": [str(exc)]},
            status=400,
        )

    except DataSourceError as exc:
        return _error_response(
            "A required environmental data source is unavailable.",
            {"data_source": [str(exc)]},
            status=503,
        )


def locations(request):
    if request.method != "GET":
        return _error_response("Method not allowed.", status=405)

    country_names = {
        "PK": "Pakistan",
        "US": "United States",
    }

    zone_names = {
        "subtropical": "Subtropical",
        "temperate": "Temperate",
    }

    results = []

    for location in load_locations():
        results.append({
            "slug": location["slug"],
            "name": location["name"],
            "lat": location["lat"],
            "lon": location["lon"],
            "country": country_names.get(
                location["country"], location["country"]
            ),
            "zone": zone_names.get(
                location["zone"], location["zone"]
            ),
            "tier": location["tier"],
            "featured": location["featured"],
        })

    return JsonResponse({
        "status": "success",
        "count": len(results),
        "results": results,
    })


def crops(request):
    if request.method != "GET":
        return _error_response("Method not allowed.", status=405)

    crop_data = load_crops()

    results = []

    for crop in crop_data.values():
        results.append({
            "slug": crop["slug"],
            "name": crop["name"],
            "name_ur": crop.get("name_ur"),
            "family": crop["family"],
            "role": crop["role"],
            "water_need_mm": crop.get("water_need_mm"),
            "drought_tolerance": crop.get("drought_tolerance"),
            "heat_tolerance": crop.get("heat_tolerance"),
            "frost_tolerance": crop.get("frost_tolerance"),
            "n_fixing": crop.get("n_fixing", False),
            "root_depth": crop.get("root_depth"),
            "ground_cover": crop.get("ground_cover"),
            "residue_om": crop.get("residue_om"),
            "erosion_protection": crop.get("erosion_protection"),
            "income_level": crop.get("income_level"),
            "forage_value": crop.get("forage_value"),
            "special_equipment": crop.get("special_equipment", False),
            "sources": (
                [crop["sources"]]
                if crop.get("sources") else []
            ),
            "notes": crop.get("notes") or None,
        })

    return JsonResponse({
        "status": "success",
        "count": len(results),
        "results": results,
    })


def explain(request):
    if request.method != "POST":
        return _error_response("Method not allowed.", status=405)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response(
            "Request body must contain valid JSON.",
            {"body": ["Invalid JSON."]},
        )

    if not isinstance(body, dict):
        return _error_response(
            "Request body must be a JSON object.",
            {"body": ["Expected a JSON object."]},
        )

    analysis = body.get("analysis")
    lang = body.get("lang", "en")

    if not isinstance(analysis, dict):
        return _error_response(
            "An analysis object is required.",
            {"analysis": ["Expected an analysis object."]},
        )

    if lang not in ("en", "ur"):
        return _error_response(
            "Unsupported language.",
            {"lang": ["Use en or ur."]},
        )

    strategies = analysis.get("strategies", [])

    if not isinstance(strategies, list) or not strategies:
        return _error_response(
            "Analysis does not contain strategies.",
            {"strategies": ["At least one strategy is required."]},
        )

    valid_strategies = [
        item for item in strategies
        if isinstance(item, dict)
        and isinstance(item.get("scores"), dict)
        and isinstance(item["scores"].get("overall"), (int, float))
    ]

    if not valid_strategies:
        return _error_response(
            "No valid strategy scores were supplied.",
            {"strategies": ["Overall scores are missing."]},
        )

    best = max(
        valid_strategies,
        key=lambda item: item["scores"]["overall"],
    )

    score = best["scores"]["overall"]
    name = best.get("name", best.get("key", "Recommended strategy"))

    if lang == "ur":
        explanation = (
            f"دستیاب تجزیے کے مطابق {name} کا مجموعی اسکور "
            f"{score}/100 ہے۔ یہ فراہم کردہ حکمت عملیوں میں سب سے زیادہ ہے۔ "
            "یہ اسکور فراہم کردہ آب و ہوا، مٹی، ترجیحات اور پابندیوں پر "
            "مبنی ہے۔ اسے یقینی پیداوار یا آمدنی کی پیش گوئی نہ سمجھیں۔"
        )
    else:
        explanation = (
            f"Based on the supplied analysis, {name} has the highest "
            f"overall score at {score}/100. This score is relative to "
            "the other supplied strategies and reflects the environmental "
            "data, priorities and constraints used in the analysis. "
            "It is not a guaranteed yield or income prediction."
        )

    return JsonResponse({
        "status": "success",
        "explanation": explanation,
        "recommended_strategy": best.get("key"),
        "overall_score": score,
        "source": "supplied_analysis",
        "ai_generated": False,
    })


def chat(request):
    if request.method != "POST":
        return _error_response("Method not allowed.", status=405)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response(
            "Request body must contain valid JSON.",
            {"body": ["Invalid JSON."]},
        )

    if not isinstance(body, dict):
        return _error_response(
            "Request body must be a JSON object.",
            {"body": ["Expected a JSON object."]},
        )

    message = body.get("message")
    lang = body.get("lang", "en")
    analysis = body.get("analysis")

    if not isinstance(message, str) or not message.strip():
        return _error_response(
            "A message is required.",
            {"message": ["Enter a non-empty message."]},
        )

    if lang not in ("en", "ur"):
        return _error_response(
            "Unsupported language.",
            {"lang": ["Use en or ur."]},
        )

    if analysis is not None and not isinstance(analysis, dict):
        return _error_response(
            "Analysis must be a JSON object or null.",
            {"analysis": ["Expected an object or null."]},
        )

    question = message.strip().lower()
    answer = None

    # Answer crop-specific questions using the existing crop knowledge.
    crop_data = load_crops()

    for crop in crop_data.values():
        names = [
            crop.get("slug", "").lower(),
            crop.get("name", "").lower(),
            crop.get("name_ur", ""),
        ]

        if any(name and name in question for name in names):
            if lang == "ur":
                answer = (
                    f"{crop['name']} کے بارے میں دستیاب معلومات: "
                    f"پانی کی ضرورت تقریباً {crop.get('water_need_mm')} ملی میٹر ہے؛ "
                    f"خشک سالی برداشت {crop.get('drought_tolerance')}/5 ہے؛ "
                    f"گرمی برداشت {crop.get('heat_tolerance')}/5 ہے۔"
                )
            else:
                answer = (
                    f"{crop['name']}: water requirement is approximately "
                    f"{crop.get('water_need_mm')} mm; drought tolerance is "
                    f"{crop.get('drought_tolerance')}/5; heat tolerance is "
                    f"{crop.get('heat_tolerance')}/5. "
                    f"Source notes: {crop.get('sources') or 'Not specified.'}"
                )
            break

    # If analysis is supplied, provide its highest-scoring strategy.
    if answer is None and analysis:
        strategies = analysis.get("strategies", [])

        valid = [
            item for item in strategies
            if isinstance(item, dict)
            and isinstance(item.get("scores"), dict)
            and isinstance(item["scores"].get("overall"), (int, float))
        ] if isinstance(strategies, list) else []

        if valid:
            best = max(
                valid,
                key=lambda item: item["scores"]["overall"],
            )
            name = best.get("name", best.get("key"))
            score = best["scores"]["overall"]

            if lang == "ur":
                answer = (
                    f"آپ کے فراہم کردہ تجزیے میں {name} کا مجموعی اسکور "
                    f"{score}/100 ہے۔ یہ فراہم کردہ حکمت عملیوں میں سب سے زیادہ ہے۔"
                )
            else:
                answer = (
                    f"Your supplied analysis gives {name} the highest "
                    f"overall score: {score}/100."
                )

    # Explicit fallback: no LLM is currently configured.
    if answer is None:
        if lang == "ur":
            answer = (
                "میں فی الحال دستیاب فصلوں کی معلومات اور فراہم کردہ "
                "تجزیے کی بنیاد پر جواب دے سکتا ہوں۔ مزید مخصوص جواب کے لیے "
                "فصل کا نام یا تجزیے کی تفصیلات فراہم کریں۔"
            )
        else:
            answer = (
                "I can currently answer using the available crop knowledge "
                "and a supplied rotation analysis. Please include a crop name "
                "or analysis details for a more specific answer. "
                "The AI language model is not configured."
            )

    return JsonResponse({
        "status": "success",
        "reply": answer,
        "source": "crop_knowledge_or_supplied_analysis",
        "ai_generated": False,
    })

