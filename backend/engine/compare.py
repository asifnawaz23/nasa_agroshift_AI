"""Side-by-side comparison of the three rotation strategies (Step 6, "Final results").

Pure Python, no Django. For each strategy it pulls together, in one structured block:
crop sequence, climate suitability, water requirement, soil improvement, nitrogen fixing,
pest/disease risk, benefits, limitations, evidence and data sources.

Every number comes from the crop table (crops.csv, sourced per row), the NASA POWER climate
profile and the strategy scores already computed by engine/scoring.py. Nothing is invented here.
"""
from __future__ import annotations

from .knowledge import annual_water_need_mm, load_crops

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _level(score, good=70, fair=50):
    if score is None:
        return "unknown"
    return "good" if score >= good else "fair" if score >= fair else "poor"


def _season(sow_month: int, zone: str) -> str:
    if zone == "subtropical":
        return "Kharif (summer)" if 3 <= sow_month <= 8 else "Rabi (winter)"
    return "Summer crop" if 3 <= sow_month <= 7 else "Winter / cover crop"


def _names(slugs, crops):
    seen, out = set(), []
    for slug in slugs:
        if slug in crops and slug not in seen:
            seen.add(slug)
            out.append(crops[slug]["name"])
    return out


def build_comparison(strategy: dict, *, zone: str, annual_rain_mm: float | None,
                     current_water_mm: float | None = None, crops: dict | None = None) -> dict:
    crops = crops or load_crops()
    rotation = strategy.get("rotation") or {"cycle_years": 1, "steps": []}
    steps = [s for s in rotation.get("steps", []) if s.get("crop") in crops]
    scores = strategy.get("scores") or {}

    # --- Crop sequence -------------------------------------------------------------------
    sequence = []
    for s in steps:
        crop = crops[s["crop"]]
        sequence.append({
            "year": s.get("year"),
            "crop": s["crop"],
            "name": crop["name"],
            "name_ur": crop.get("name_ur", ""),
            "family": crop["family"],
            "n_fixing": crop["n_fixing"],
            "season": _season(s.get("sow_month", 1), zone),
            "months": f"{MONTHS[s['sow_month'] - 1]}–{MONTHS[s['harvest_month'] - 1]}"
            if s.get("sow_month") and s.get("harvest_month") else "",
        })
    sequence_text = " → ".join(item["name"].split(" (")[0] for item in sequence)

    # --- Climate suitability -------------------------------------------------------------
    heat_tolerant = _names([s["crop"] for s in steps if crops[s["crop"]]["heat_tolerance"] >= 4], crops)
    heat_sensitive = _names([s["crop"] for s in steps if crops[s["crop"]]["heat_tolerance"] <= 2], crops)
    drought_tolerant = _names([s["crop"] for s in steps if crops[s["crop"]]["drought_tolerance"] >= 4], crops)
    climate = {
        "score": scores.get("climate_risk"),
        "level": _level(scores.get("climate_risk")),
        "heat_tolerant": heat_tolerant,
        "heat_sensitive": heat_sensitive,
        "drought_tolerant": drought_tolerant,
    }

    # --- Water requirement ---------------------------------------------------------------
    need = round(annual_water_need_mm(rotation, crops)) if steps else None
    gap = round(need - annual_rain_mm) if need is not None and annual_rain_mm is not None else None
    vs_current = None
    if need is not None and current_water_mm and not strategy.get("is_current"):
        vs_current = round((need - current_water_mm) / current_water_mm * 100)
    water = {
        "need_mm_per_year": need,
        "rain_mm_per_year": round(annual_rain_mm) if annual_rain_mm is not None else None,
        "irrigation_gap_mm": max(gap, 0) if gap is not None else None,
        "vs_current_pct": vs_current,
        "score": scores.get("water_fit"),
        "level": _level(scores.get("water_fit")),
    }

    # --- Soil improvement ----------------------------------------------------------------
    soil = {
        "score": scores.get("soil_health"),
        "level": _level(scores.get("soil_health"), good=60, fair=45),
        "deep_rooted": _names([s["crop"] for s in steps if crops[s["crop"]]["root_depth"] == "deep"], crops),
        "high_residue": _names([s["crop"] for s in steps if crops[s["crop"]]["residue_om"] >= 4], crops),
        "ground_cover_crops": _names([s["crop"] for s in steps if crops[s["crop"]]["ground_cover"] >= 4], crops),
    }

    # --- Nitrogen fixing -----------------------------------------------------------------
    fixers = [s["crop"] for s in steps if crops[s["crop"]]["n_fixing"]]
    share = round(len(fixers) / len(steps), 2) if steps else 0
    nitrogen = {
        "n_fixing_crops": _names(fixers, crops),
        "share_of_seasons": share,
        "level": "strong" if share >= 0.5 else "some" if share > 0 else "none",
    }

    # --- Pest and disease risk (rotation logic only, no product advice) -----------------
    families = [crops[s["crop"]]["family"] for s in steps]
    repeats = []
    for i in range(1, len(steps)):
        if families[i] == families[i - 1]:
            repeats.append(f"{crops[steps[i - 1]['crop']]['name']} → {crops[steps[i]['crop']]['name']}")
    if steps and len(steps) > 1 and families[0] == families[-1]:
        repeats.append(f"{crops[steps[-1]['crop']]['name']} → {crops[steps[0]['crop']]['name']} (next cycle)")
    pest_score = scores.get("pest_break")
    pest_level = "low" if pest_score is not None and pest_score >= 70 else \
        "moderate" if pest_score is not None and pest_score >= 50 else "high"
    notes = []
    if repeats:
        notes.append("Crops of the same family follow each other, so their pests and diseases can carry "
                     "over in the soil and residue.")
    if len(set(families)) >= 3:
        notes.append(f"{len(set(families))} different crop families break pest and disease cycles.")
    elif len(set(families)) <= 1 and steps:
        notes.append("Only one crop family: pests and diseases build up year after year.")
    notes.append("Check local pest pressure with your extension office; follow product labels for any control.")
    pest = {
        "score": pest_score,
        "risk": pest_level,
        "families": sorted(set(families)),
        "same_family_in_a_row": repeats,
        "notes": notes,
    }

    # --- Benefits, limitations, evidence, sources ---------------------------------------
    limitations = list(strategy.get("constraint_warnings") or [])
    if water["vs_current_pct"] is not None and water["vs_current_pct"] > 5:
        limitations.append(f"Needs about {water['vs_current_pct']}% more water per year than your current rotation.")
    for item in strategy.get("info_gaps") or []:
        if len(limitations) >= 4:
            break
        if item not in limitations:
            limitations.append(item)

    evidence = [e for e in (strategy.get("evidence") or []) if isinstance(e, dict) and e.get("text")]
    sources = {e.get("source") for e in evidence if e.get("source")}
    sources.add("NASA POWER")
    crop_sources = set()
    for s in steps:
        raw = crops[s["crop"]].get("sources") or ""
        for src in (raw if isinstance(raw, list) else [raw]):
            if src:
                crop_sources.add(f"{crops[s['crop']]['name']}: {src}")

    return {
        "sequence": sequence,
        "sequence_text": sequence_text,
        "climate": climate,
        "water": water,
        "soil": soil,
        "nitrogen": nitrogen,
        "pest": pest,
        "benefits": list(strategy.get("benefits") or []),
        "limitations": limitations,
        "evidence": evidence[:4],
        "data_sources": sorted(sources),
        "crop_sources": sorted(crop_sources),
    }
