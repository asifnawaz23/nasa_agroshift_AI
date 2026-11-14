"""Early-warning alerts (plan section 9). Owner: Asif.

Pure Python. Alerts are RISK PATTERNS from 20 years of history (or a What-If scenario),
not live forecasts: every alert says which variable triggered it and its basis.

    build_alerts(profile, rotation, zone, soil=None, water_availability=None, lang="en",
                 include_low=False) -> [alert]
    summarize_alerts(alerts) -> {"worst", "counts", "by_month"}   (for map pin colors, badges)

alert = {
  "type": "heat" | "drought" | "water_deficit" | "frost" | "waterlogging" | "soil_drying",
  "severity": "low" | "moderate" | "high" | "critical",
  "month": 7, "crops": ["cotton"], "stage": "flowering_boll_set",
  "triggered_by": [{"variable": "severe_heat_days", "value": 17.2, "threshold": 12.0}],
  "reason": "...", "action": "...", "basis": "historical" | "simulated", "source": "NASA POWER"
}

Rules that keep alerts meaningful in hot, irrigated places (Faisalabad: >35 C on ~29 days a
month in summer, rain << evaporation all year):
  - heat-tolerant crops (cotton, sorghum, rice...) are judged on severe heat days (>40 C)
  - heat days count double in a heat-sensitive growth stage (only for non-tolerant crops)
  - dry-spell alerts only for rainfed farms or the temperate zone
  - deficit severity is lowered for irrigated (-2 levels) / limited irrigation (-1 level)
  - frost-hardy crops get no frost alerts; medium-hardy ones only in frost-sensitive stages
  - waterlogging needs slow-draining soil (or a waterlogging-sensitive stage when soil is unknown)
"""
from __future__ import annotations

from . import constants as C
from .explain import load_text
from .knowledge import load_calendars, load_crops, stage_for, step_months

ORDER = C.SEVERITY_ORDER
# Outside the crop's sensitive stage, heat or dry spells matter much less (e.g. dry September
# helps the Iowa harvest): lower severity by two levels
NON_SENSITIVE_DOWNGRADE = 2
TYPES =["heat", "drought", "water_deficit", "frost", "waterlogging", "soil_drying"]


def severity(value, levels, direction="above"):
    """'low' below the first level, else moderate / high / critical."""
    if value is None:
        return None
    sev = "low"
    for name, lvl in zip(ORDER[1:], levels):
        if (value >= lvl) if direction == "above" else (value <= lvl):
            sev = name
    return sev


def downgrade(sev, steps):
    if sev is None:
        return None
    return ORDER[max(0, ORDER.index(sev) - steps)]


def _g(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _crop_months(rotation, zone, calendars):
    """Yield (crop, month, stage dict) for every month a crop is in the field."""
    for st in rotation["steps"]:
        cal = calendars.get((st["crop"], zone))
        for k, m in enumerate(step_months(st)):
            stage = stage_for(st, cal, k) if cal else {"stage": "growing"}
            yield st["crop"], m, stage


def build_alerts(profile, rotation, zone, soil=None, water_availability=None, lang="en",
                 include_low=False, crops=None, calendars=None):
    crops = crops or load_crops()
    calendars = calendars or load_calendars()
    water = water_availability or C.DEFAULT_WATER_AVAILABILITY.get(zone, "rainfed")
    water_down = C.WATER_AVAILABILITY_DOWNGRADE.get(water, 0)
    stress = profile.get("stress_by_month") or {}
    wb = profile.get("water_balance_by_month") or {}
    sm = profile.get("soil_moisture_anomaly_by_month") or {}
    scen = profile.get("scenario_applied") or {}
    basis = "simulated" if (scen.get("temp_c") or scen.get("rain_pct")) else "historical"
    slow_soil = bool(soil and soil.get("available", True) and
                     (soil.get("drainage_hint") == "slow" or (soil.get("clay_pct") or 0) >= 35))
    soil_known = bool(soil and soil.get("available", True))
    T = C.ALERT_THRESHOLDS

    found = {}  # (type, month, stage) -> alert; crops are merged only when at the same stage

    def add(kind, month, crop, stage, sev, variable, value, threshold, source="NASA POWER"):
        if sev is None or (sev == "low" and not include_low):
            return
        key = (kind, month, stage["stage"])
        a = found.get(key)
        if a is None or ORDER.index(sev) > ORDER.index(a["severity"]):
            crops_so_far = a["crops"] if a else []
            found[key] = a = {"type": kind, "severity": sev, "month": month, "crops": list(crops_so_far),
                              "stage": stage["stage"],
                              "triggered_by": [{"variable": variable, "value": round(value, 2),
                                                "threshold": threshold}],
                              "basis": basis, "source": source}
        if crop and crop not in a["crops"]:
            a["crops"].append(crop)

    for crop, m, stage in _crop_months(rotation, zone, calendars):
        c, ms, sens = crops.get(crop, {}), str(m), stage.get("sensitive", [])

        # heat
        tolerant = c.get("heat_tolerance", 3) >= C.HEAT_TOLERANT_MIN
        var = "severe_heat_days" if tolerant else "heat_days"
        days = _g(stress, var, ms)
        if days is not None:
            weighted = days * (C.SENSITIVE_STAGE_HEAT_WEIGHT if ("heat" in sens and not tolerant) else 1)
            sev = severity(weighted, T["heat"]["levels"])
            if "heat" not in sens:
                sev = downgrade(sev, NON_SENSITIVE_DOWNGRADE)
            thr = C.SEVERE_HEAT_DAY_TMAX_C if tolerant else C.HEAT_DAY_TMAX_C
            add("heat", m, crop, stage, sev, var, days, thr)

        # dry spells: rainfed or temperate only, and only in drought-sensitive stages
        # (a dry January for dormant rye, or a dry September at harvest, is not a risk)
        p = _g(stress, "dry_spell_prob", ms)
        if p is not None and "drought" in sens and (zone == "temperate" or water == "rainfed"):
            sev = downgrade(severity(p, T["drought"]["levels"]), water_down)
            add("drought", m, crop, stage, sev, "dry_spell_prob", p, T["drought"]["levels"][0])

        # water deficit (rain vs evaporation demand) in drought-sensitive stages
        d = _g(wb, ms, "deficit_mm")
        if d is not None and "drought" in sens:
            sev = downgrade(severity(d, T["water_deficit"]["levels"]), water_down)
            add("water_deficit", m, crop, stage, sev, "deficit_mm", d, T["water_deficit"]["levels"][0])

        # frost
        f = _g(stress, "frost_days", ms)
        hardy = c.get("frost_tolerance", 3)
        if f is not None and hardy < C.FROST_HARDY_MIN and (hardy <= 2 or "frost" in sens):
            add("frost", m, crop, stage, severity(f, T["frost"]["levels"]), "frost_days", f,
                T["frost"]["levels"][0])

        # waterlogging
        x = _g(stress, "extreme_rain_days", ms)
        if x is not None and (slow_soil or (not soil_known and "waterlogging" in sens)):
            sev = severity(x, T["waterlogging"]["levels"])
            if not slow_soil:
                sev = downgrade(sev, 1)
            add("waterlogging", m, crop, stage, sev, "extreme_rain_days", x, T["waterlogging"]["levels"][0])

        # soil drying (observed or modelled anomaly)
        z = sm.get(ms)
        if z is not None:
            src = "NASA SMAP" if profile.get("soil_moisture_source") == "smap" else "NASA POWER (root-zone wetness)"
            add("soil_drying", m, crop, stage, severity(z, T["soil_drying"]["levels"], "below"),
                "soil_moisture_anomaly", z, T["soil_drying"]["levels"][0], source=src)

    alerts = sorted(found.values(), key=lambda a: (-ORDER.index(a["severity"]), a["month"], TYPES.index(a["type"])))
    _add_text(alerts, lang, crops)
    return alerts


def _add_text(alerts, lang, crops):
    t = load_text(lang)
    A, months = t["alerts"], t["months"]
    stage_names = t["evidence"]["stage"]
    sep = "، " if lang == "ur" else ", "
    for a in alerts:
        names = [(crops[c].get("name_ur") if lang == "ur" else None) or crops[c]["name"] for c in a["crops"]]
        crop_txt = sep.join(names[:-1]) + f" {t['list_and']} " + names[-1] if len(names) > 1 else (names[0] if names else "")
        trig = a["triggered_by"][0]
        value = trig["value"] * 100 if trig["variable"] == "dry_spell_prob" else trig["value"]
        params = {"crop": crop_txt, "month": months[a["month"] - 1],
                  "stage": stage_names.get(a["stage"], a["stage"].replace("_", " ")),
                  "value": f"{value:.0f}" if a["type"] != "soil_drying" else f"{value:.1f}",
                  "threshold": f"{trig['threshold']:.0f}"}
        a["reason"] = A["reason"][a["type"]].format(**params)
        a["action"] = A["action"][a["type"]].format(**params)
        a["severity_label"] = A["severity"][a["severity"]]


def summarize_alerts(alerts):
    """Worst severity overall and per month: for pin colors and the badge in the UI."""
    counts = {s: 0 for s in ORDER}
    by_month = {}
    for a in alerts:
        counts[a["severity"]] += 1
        cur = by_month.get(a["month"])
        if cur is None or ORDER.index(a["severity"]) > ORDER.index(cur):
            by_month[a["month"]] = a["severity"]
    worst = max((a["severity"] for a in alerts), key=ORDER.index, default="low")
    return {"worst": worst, "counts": counts, "by_month": dict(sorted(by_month.items()))}
