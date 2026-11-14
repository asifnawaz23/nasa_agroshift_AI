
import json
import uuid
from datasources.prepulled import load_locations


from django.http import JsonResponse
from django.utils import timezone
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt   # NEW

from .serializers import AnalyzeRequestSerializer

from datasources.cache import get_power_daily, get_soil
from datasources.errors import DataSourceError
from datasources.prepulled import find_featured, load_prepulled

from engine.alerts import build_alerts
from engine.climate_profile import build_climate_profile
from engine.constants import (
    CONFIDENCE_HIGH_MIN_CORR,
    CONFIDENCE_HIGH_MIN_YEARS,
    MAX_MISSING_FRACTION,
    SCENARIO_LOW_CONFIDENCE_RAIN_PCT,
    SCENARIO_LOW_CONFIDENCE_TEMP_C,
    MIN_YEARS_FOR_CLIMATOLOGY,
    VULNERABLE_DRY_SPELL_PROB,
    VULNERABLE_HEAT_DAYS,
)
from engine.knowledge import (
    bare_fraction_by_month,
    field_occupancy,
    load_calendars,
    load_crops,
    load_templates,
    sensitive_windows,
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


# Thresholds for the vulnerable-month view. Heat and dry-spell values come from
# engine.constants; frost and soil drying match the "moderate" alert level.
VULNERABLE_FROST_DAYS = 1.0
VULNERABLE_SOIL_MOISTURE_ANOMALY = -1.0


def _month_value(data, month):
    return (data or {}).get(str(month))


def _scenario_active(scenario):
    scenario = scenario or {}
    return scenario.get("rain_pct", 0) != 0 or scenario.get("temp_c", 0) != 0


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


def _climate_block(profile):
    """Annual summary plus the month-by-month series the charts need."""
    climatology = profile["monthly_climatology"]
    water_balance = profile["water_balance_by_month"]
    stress = profile["stress_by_month"]

    monthly = []

    for month in range(1, 13):
        clim = climatology[str(month)]
        balance = water_balance.get(str(month), {})

        monthly.append({
            "month": month,
            "t_mean": clim["t_mean"],
            "t_max": clim["t_max"],
            "t_min": clim["t_min"],
            "precip_mm": clim["precip_mm"],
            "et0_mm": clim["et0_mm"],
            "deficit_mm": balance.get("deficit_mm"),
            "root_wetness": clim["root_wetness"],
            "heat_days": _month_value(stress.get("heat_days"), month),
            "severe_heat_days": _month_value(stress.get("severe_heat_days"), month),
            "frost_days": _month_value(stress.get("frost_days"), month),
            "dry_spell_prob": _month_value(stress.get("dry_spell_prob"), month),
            "extreme_rain_days": _month_value(stress.get("extreme_rain_days"), month),
            "soil_moisture_anomaly": _month_value(
                profile.get("soil_moisture_anomaly_by_month"), month
            ),
            "ndvi": _month_value(profile.get("ndvi_by_month"), month),
        })

    return {
        **_climate_summary(profile),
        "years_covered": profile["years_covered"],
        "monthly": monthly,
        "trends": profile["trends"],
        "year_stress_flags": profile["year_stress_flags"],
        "frost_free_season": profile["frost_free_season"],
        "soil_moisture_source": profile.get("soil_moisture_source"),
        "bare_months_observed": profile.get("bare_months_observed"),
        "basis": (
            "simulated"
            if _scenario_active(profile.get("scenario_applied"))
            else "historical"
        ),
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


def _vulnerable_months(profile, rotation, zone, calendars):
    """Months where a crop is in a sensitive growth stage and a matching stress
    signal is present, with reasons, crops and stages.

    stress_by_month is keyed by indicator first ({"heat_days": {"7": 6.5}}),
    so each indicator is looked up per month.
    """
    stress = profile["stress_by_month"]
    sm_anomaly = profile.get("soil_moisture_anomaly_by_month") or {}

    crops_by_month = {month: [] for month in range(1, 13)}

    for index, crops_in_field in enumerate(field_occupancy(rotation)):
        month = index % 12 + 1
        for crop in crops_in_field:
            if crop not in crops_by_month[month]:
                crops_by_month[month].append(crop)

    stages_by_month = {}

    for window in sensitive_windows(rotation, zone, calendars):
        stages_by_month.setdefault(window["month"], []).append({
            "crop": window["crop"],
            "stage": window["stage"],
            "sensitive": window["sensitive"],
        })

    vulnerable = []

    for month in range(1, 13):
        if not crops_by_month[month]:
            continue

        heat = _month_value(stress.get("heat_days"), month) or 0
        dry = _month_value(stress.get("dry_spell_prob"), month) or 0
        frost = _month_value(stress.get("frost_days"), month) or 0
        anomaly = _month_value(sm_anomaly, month)

        # Only count a stress when a crop is in a growth stage sensitive to it
        # (same rule as engine.alerts), so hot climates are not flagged every month.
        sensitive = {
            tag
            for stage in stages_by_month.get(month, [])
            for tag in stage["sensitive"]
        }

        reasons = []

        if heat >= VULNERABLE_HEAT_DAYS and "heat" in sensitive:
            reasons.append("heat")
        if dry >= VULNERABLE_DRY_SPELL_PROB and "drought" in sensitive:
            reasons.append("dry_spell")
        if frost >= VULNERABLE_FROST_DAYS and "frost" in sensitive:
            reasons.append("frost")
        if (
            anomaly is not None
            and anomaly <= VULNERABLE_SOIL_MOISTURE_ANOMALY
            and "drought" in sensitive
        ):
            reasons.append("soil_drying")

        if reasons:
            vulnerable.append({
                "month": month,
                "crops": crops_by_month[month],
                "sensitive_stages": stages_by_month.get(month, []),
                "reasons": reasons,
                "values": {
                    "heat_days": heat,
                    "dry_spell_prob": dry,
                    "frost_days": frost,
                    "soil_moisture_anomaly": anomaly,
                },
            })

    return vulnerable


def _confidence(profile, data_tier, scenario, featured):
    """High / medium / low label (team plan, section 7)."""
    n_years = profile["n_years"]
    missing = profile["missing_fraction"] or 0
    corr = ((profile.get("validation") or {}).get("prism") or {}).get("precip_corr")

    if (
        not featured
        or missing > MAX_MISSING_FRACTION
        or abs(scenario.get("temp_c", 0)) > SCENARIO_LOW_CONFIDENCE_TEMP_C
        or abs(scenario.get("rain_pct", 0)) > SCENARIO_LOW_CONFIDENCE_RAIN_PCT
    ):
        return "low"

    if (
        data_tier == "us_enhanced"
        and n_years >= CONFIDENCE_HIGH_MIN_YEARS
        and corr is not None
        and corr > CONFIDENCE_HIGH_MIN_CORR
    ):
        return "high"

    if n_years >= CONFIDENCE_HIGH_MIN_YEARS:
        return "medium"

    return "low"


@csrf_exempt
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
        scenario_active = _scenario_active(scenario)

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
            lang=lang,
            data_tier=data_tier,
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
                "featured": bool(featured),
                "slug": featured["slug"] if featured else None,
            },
            "data_quality": {
                "status": (
                    "partial" if warnings else "complete"
                ),
                "confidence": _confidence(
                    profile, data_tier, scenario, bool(featured)
                ),
                "fallback_used": bool(power_meta.get("fallback_used")),
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
                "baseline": _climate_block(baseline_profile),
                "scenario": (
                    {
                        "rain_pct": scenario.get("rain_pct", 0),
                        "temp_c": scenario.get("temp_c", 0),
                        **_climate_block(profile),
                    }
                    if scenario_active else None
                ),
            },
            "soil": {
                "measured": soil,
                "farmer_texture_override": overrides.get("soil_texture"),
            },
            "bare_windows": _bare_windows(current_rotation),
            "vulnerable_months": _vulnerable_months(
                profile, current_rotation, zone, calendars
            ),
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

@csrf_exempt
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

@csrf_exempt
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

