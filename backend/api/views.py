
import json
import uuid
from functools import lru_cache

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .serializers import AnalyzeRequestSerializer

from datasources.cache import get_power_daily, get_soil
from datasources.errors import DataSourceError
from datasources.prepulled import find_featured, load_locations, load_prepulled
from datasources.soilgrids import apply_texture_override

from engine.alerts import build_alerts, summarize_alerts
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

from ai import prompts
from ai.client import ANSWER_SCHEMA, ai_diagnostics, ask_llm
from ai.ratelimit import ai_rate_limited

from .chat_history import save_exchange, user_from_token


def health_check(request):
    """Status + database check (plan section 11). Render's health check calls this."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except DatabaseError:
        database = "unavailable"

    body = {
        "status": "success" if database == "ok" else "degraded",
        "message": "FieldShift Planner API is running.",
        "database": database,
        "timestamp": timezone.now().isoformat(),
    }
    # /api/health/?ai=1: check the AI setup (rate limited like the AI endpoints)
    if request.GET.get("ai") == "1":
        from django.core.cache import cache
        from ai.ratelimit import client_ip

        key = f"ai-diag:{client_ip(request)}"
        cache.add(key, 0, 600)
        if cache.incr(key) <= 5:  # at most 5 checks per 10 minutes per visitor
            body["ai"] = ai_diagnostics()
        else:
            body["ai"] = {"error": "Too many AI checks, try again in 10 minutes."}
    return JsonResponse(body, status=200 if database == "ok" else 503)


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

        # The farmer's own soil texture wins over the 250 m SoilGrids estimate.
        measured_soil = soil
        soil = apply_texture_override(soil, overrides.get("soil_texture"))

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
                "measured": measured_soil,
                "used": soil,
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


@lru_cache(maxsize=16)
def _pin_alert_summary(slug, lat, zone):
    """Worst historical alert for a pin's default rotation, for the map pin colour.

    Uses the pin's offline POWER and soil snapshot, so it is fast and works without internet.
    Cached per process (snapshots only change on deploy). None when the pin has no snapshot.
    """
    try:
        prepulled = load_prepulled(slug)
        if prepulled.get("power") is None:
            return None
        profile = build_climate_profile(
            prepulled["power"], lat, smap=prepulled.get("smap"), ndvi=prepulled.get("ndvi"),
            prism=prepulled.get("prism"), zone=zone,
        )
        rotation = load_templates()[zone]["current_default"]["rotation"]
        alerts = build_alerts(profile=profile, rotation=rotation, zone=zone,
                              soil=prepulled.get("soil"))
        return summarize_alerts(alerts)
    except (KeyError, ValueError, OSError):
        return None


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
            "zone_key": location["zone"],
            "name_ur": location.get("name_ur"),
            "status": location.get("status"),
            # Pin colour: worst historical alert for the default rotation (not a forecast).
            "alert_summary": _pin_alert_summary(
                location["slug"], location["lat"], location["zone"]
            ),
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

def _read_json_body(request):
    """(body, error_response). body is a dict when error_response is None."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, _error_response("Request body must contain valid JSON.", {"body": ["Invalid JSON."]})
    if not isinstance(body, dict):
        return None, _error_response("Request body must be a JSON object.", {"body": ["Expected a JSON object."]})
    return body, None


def _ai_response(answer, ai_used, **extra):
    """Section 10 answer shape + ai_used. `explanation` repeats the summary for older clients."""
    return JsonResponse({
        "status": "success",
        **answer,
        "explanation": answer.get("summary", ""),
        "ai_used": ai_used,
        **extra,
        "disclaimer": AI_DISCLAIMER,
    })


AI_DISCLAIMER = (
    "AI explanations are generated from this analysis and may contain mistakes. They support, "
    "and do not replace, farmer judgment and local agricultural expertise."
)


@csrf_exempt
@ai_rate_limited
def explain(request):
    """POST {section, analysis, lang} -> grounded explanation of one part of the analysis."""
    if request.method != "POST":
        return _error_response("Method not allowed.", status=405)

    body, error = _read_json_body(request)
    if error:
        return error

    analysis = body.get("analysis")
    lang = body.get("lang", "en")
    section = body.get("section", "overview")

    if not isinstance(analysis, dict):
        return _error_response("An analysis object is required.",
                               {"analysis": ["Expected the /api/analyze/ response object."]})
    if lang not in prompts.SUPPORTED_LANGS:
        return _error_response("Unsupported language.",
                               {"lang": [f"Use one of {', '.join(prompts.SUPPORTED_LANGS)}."]})
    if not prompts.is_valid_section(section):
        return _error_response(
            "Unknown section.",
            {"section": [f"Use one of {', '.join(prompts.SECTIONS)} or strategy:<key>."]},
        )

    trimmed = prompts.trim_analysis(analysis, section)
    answer = ask_llm(prompts.system_prompt(trimmed, lang), prompts.explain_messages(section),
                     ANSWER_SCHEMA)
    ai_used = answer is not None
    if not ai_used:
        answer = prompts.template_answer(analysis, section, lang)

    best = prompts.best_strategy(analysis)
    return _ai_response(
        answer, ai_used, section=section,
        recommended_strategy=best.get("key") if best else None,
        overall_score=best["scores"]["overall"] if best else None,
    )


@csrf_exempt
@ai_rate_limited
def chat(request):
    """POST {messages: [{role, content}], analysis, lang} -> answer to the latest question.

    The frontend keeps the history and sends it every time (stateless server). A single
    {"message": "..."} is also accepted.
    """
    if request.method != "POST":
        return _error_response("Method not allowed.", status=405)

    body, error = _read_json_body(request)
    if error:
        return error

    lang = body.get("lang", "en")
    analysis = body.get("analysis")
    messages = body.get("messages")
    if messages is None and isinstance(body.get("message"), str):
        messages = [{"role": "user", "content": body["message"]}]

    if lang not in prompts.SUPPORTED_LANGS:
        return _error_response("Unsupported language.",
                               {"lang": [f"Use one of {', '.join(prompts.SUPPORTED_LANGS)}."]})
    if analysis is not None and not isinstance(analysis, dict):
        return _error_response("Analysis must be a JSON object or null.",
                               {"analysis": ["Expected an object or null."]})
    history = prompts.clean_chat_history(messages)
    if history is None:
        return _error_response(
            "A question is required.",
            {"messages": ["Send [{\"role\": \"user\", \"content\": \"...\"}], ending with the farmer's question."]},
        )

    analysis = analysis or {}
    trimmed = prompts.trim_analysis(analysis, "overview")
    # Chat rules allow general farming knowledge (any crop/soil/water/pest question);
    # farm-specific facts still come only from the analysis.
    answer = ask_llm(prompts.chat_system_prompt(trimmed, lang), history, ANSWER_SCHEMA)
    ai_used = answer is not None
    if not ai_used:
        question = history[-1]["content"]
        # Crop facts only answer "tell me about X" / water / tolerance questions —
        # not e.g. "how do I control aphids on cotton?", which needs the AI.
        answer = (prompts.crop_fact_answer(question, lang)
                  if prompts.is_basic_crop_question(question) else None)
        if answer is None:
            # Be honest that the AI is off instead of returning an unrelated summary
            answer = prompts.no_ai_answer(lang)

    # Logged-in users: save the question + answer so the chat can be reopened later.
    # Saving must never break the answer itself, so database problems are ignored here.
    conversation_id = None
    user = user_from_token(request)
    if user is not None:
        try:
            conversation_id = save_exchange(
                user, body.get("conversation_id"), history[-1]["content"], answer["summary"], lang
            )
        except DatabaseError:
            conversation_id = None

    return _ai_response(answer, ai_used, reply=answer["summary"], conversation_id=conversation_id)
