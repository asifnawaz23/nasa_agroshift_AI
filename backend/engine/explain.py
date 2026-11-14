"""Template explanations for each rotation strategy. Owner: Abdul Rehman.

Pure Python, no LLM, no network. Every sentence is filled from real numbers in the climate
profile, the soil summary and the crop table, so it is always grounded. This is also the
fallback text when the AI layer (/api/explain/) is unavailable.

    build_explanations(strategy_key, rotation, zone, profile, soil=None, tier=None, lang="en",
                       current_rotation=None) -> {
        "why_suggested": str,
        "evidence":      [{"text", "source", "type": "observed", "kind", "month"}],
        "benefits":      [str],
        "info_gaps":     [str],
        "local_review":  [str],
    }
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from . import constants as C
from .knowledge import (annual_water_need_mm, bare_months, bare_months_per_year, families,
                        load_calendars, load_crops, sensitive_windows)

TEXT_DIR = Path(__file__).resolve().parents[1] / "data" / "text"
MAX_EVIDENCE = 5
SEVERE_HEAT_C = getattr(C, "SEVERE_HEAT_DAY_TMAX_C", 40.0)


@lru_cache(maxsize=4)
def load_text(lang: str = "en") -> dict:
    path = TEXT_DIR / f"{lang}.json"
    if not path.exists():
        path = TEXT_DIR / "en.json"
    return json.loads(path.read_text(encoding="utf-8"))


class _T:
    """Small helper for language-aware names and lists."""

    def __init__(self, lang, crops):
        self.lang, self.t, self.crops = lang, load_text(lang), crops

    def month(self, m):
        return self.t["months"][m - 1]

    def months(self, ms):
        return self.join([self.month(m) for m in ms])

    def crop(self, slug):
        c = self.crops.get(slug, {})
        return (c.get("name_ur") if self.lang == "ur" and c.get("name_ur") else c.get("name", slug))

    def crop_list(self, slugs):
        return self.join([self.crop(s) for s in dict.fromkeys(slugs)])

    def stage(self, s):
        return self.t["evidence"]["stage"].get(s, s.replace("_", " "))

    def join(self, items):
        items = list(items)
        if len(items) <= 1:
            return "".join(items)
        sep = "، " if self.lang == "ur" else ", "
        return sep.join(items[:-1]) + f" {self.t['list_and']} " + items[-1]


def _get(d, *keys):
    for k in keys:
        if d is None:
            return None
        d = d.get(k) if isinstance(d, dict) else None
    return d


def _source(profile, kind):
    if kind == "sm_dry":
        return "NASA SMAP" if profile.get("soil_moisture_source") == "smap" else "NASA POWER (root-zone wetness)"
    return "NASA POWER"


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
def _evidence(rotation, zone, profile, soil, T, crops, calendars):
    ev = profile.get("stress_by_month", {})
    wb = profile.get("water_balance_by_month", {})
    sm = profile.get("soil_moisture_anomaly_by_month") or {}
    n_years = profile.get("n_years") or 0
    E = T.t["evidence"]
    # (kind, month) -> finding; crops at risk in the same month for the same reason are merged
    found = {}

    def add(kind, month, crop, severity, params, source=None):
        key = (kind, month)
        f = found.setdefault(key, {"kind": kind, "month": month, "crops": [], "severity": -1,
                                   "params": {}, "source": source or _source(profile, kind)})
        if crop and crop not in f["crops"]:
            f["crops"].append(crop)
        if severity > f["severity"]:
            f["severity"], f["params"] = severity, params

    for w in sensitive_windows(rotation, zone, calendars):
        m, crop, stage, sens = w["month"], w["crop"], w["stage"], w["sensitive"]
        ms, c = str(m), crops.get(crop, {})
        base = {"month": T.month(m), "stage": T.stage(stage)}
        if "heat" in sens:
            # heat-tolerant crops (cotton, sorghum, rice) are judged against severe heat (>40 C)
            tolerant = c.get("heat_tolerance", 3) >= 4
            days = _get(ev, "severe_heat_days" if tolerant else "heat_days", ms)
            thr = SEVERE_HEAT_C if tolerant else C.HEAT_DAY_TMAX_C
            if days is not None and days >= C.VULNERABLE_HEAT_DAYS:
                add(f"heat_{thr:.0f}", m, crop, days, {**base, "days": f"{days:.0f}", "threshold": f"{thr:.0f}"})
        if "drought" in sens:
            d = _get(wb, ms, "deficit_mm")
            if d is not None and d >= 30:
                add("deficit", m, crop, d / 10, {**base, "precip": f"{wb[ms]['precip_mm']:.0f}",
                                                 "et0": f"{wb[ms]['et0_mm']:.0f}", "deficit": f"{d:.0f}"})
            p = _get(ev, "dry_spell_prob", ms)
            # in subtropical (irrigated, dry most months) dry spells are normal, so only temperate
            if zone == "temperate" and p is not None and p >= C.VULNERABLE_DRY_SPELL_PROB:
                add("dry_spell", m, crop, p * 10, {**base, "pct": f"{p * 100:.0f}", "years": n_years})
            z = sm.get(ms)
            if z is not None and z <= C.SM_ANOMALY_DRY_Z:
                add("sm_dry", m, None, -z * 3, {**base, "z": f"{z:.1f}"})
        if "frost" in sens:
            f = _get(ev, "frost_days", ms)
            # frost-hardy crops (tolerance >= 3) only matter in long frosty spells
            limit = 1 if c.get("frost_tolerance", 3) <= 2 else 10
            if f is not None and f >= limit:
                add("frost", m, crop, f, {**base, "days": f"{f:.0f}"})

    bare = bare_months(rotation)
    heavy = [(m, _get(ev, "extreme_rain_days", str(m)) or 0) for m in bare]
    heavy = [(m, d) for m, d in heavy if d >= 0.3]
    total = sum(d for _, d in heavy)
    if total >= 0.5:
        add("erosion_bare", None, None, total * 2,
            {"months": T.months([m for m, _ in heavy]), "days": f"{total:.1f}"})

    drought_years = sorted(y for y, f in (profile.get("year_stress_flags") or {}).items() if "drought" in f)
    if len(drought_years) >= 2:
        add("drought_years", None, None, 1, {"years": T.join(drought_years[-4:])})

    if soil and soil.get("available", True):
        om = soil.get("organic_matter_pct")
        if om is not None and om < 2:
            add("low_om", None, None, 2, {"om": f"{om:.1f}"}, source=soil.get("source", "soil data"))
        if soil.get("erodibility_hint") == "high" and bare:
            add("high_erodibility", None, None, 1.5, {"texture": soil.get("texture", "")},
                source=soil.get("source", "soil data"))

    items = []
    for f in sorted(found.values(), key=lambda x: -x["severity"])[:MAX_EVIDENCE]:
        template = E["heat"] if f["kind"].startswith("heat_") else E[f["kind"]]
        text = template.format(crop=T.crop_list(f["crops"]), **f["params"])
        items.append({"text": text, "source": f["source"], "type": "observed",
                      "kind": f["kind"].split("_")[0] if f["kind"].startswith("heat_") else f["kind"],
                      "month": f["month"], "crops": f["crops"]})
    return items


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def build_explanations(strategy_key, rotation, zone, profile, soil=None, tier=None, lang="en",
                       current_rotation=None, crops=None, calendars=None) -> dict:
    crops = crops or load_crops()
    calendars = calendars or load_calendars()
    T = _T(lang, crops)
    W, B, G, L = T.t["why"], T.t["benefits"], T.t["info_gaps"], T.t["local_review"]
    tier = tier or profile.get("data_tier", "standard")
    is_current = current_rotation is None or strategy_key.startswith("current")
    slugs = [s["crop"] for s in rotation["steps"] if s["crop"] in crops]
    cur_slugs = [s["crop"] for s in (current_rotation or rotation)["steps"] if s["crop"] in crops]
    new_slugs = [s for s in dict.fromkeys(slugs) if s not in cur_slugs]

    # --- why suggested -------------------------------------------------------
    why_key = strategy_key if strategy_key in W else ("current" if strategy_key.startswith("current") else "custom")
    why = [W[why_key]]
    if not is_current:
        old, new = annual_water_need_mm(current_rotation, crops), annual_water_need_mm(rotation, crops)
        if old > 0 and abs(new - old) / old >= 0.05:
            pct = round(abs(new - old) / old * 100)
            why.append(W["water_change_less" if new < old else "water_change_more"].format(
                pct=pct, new=round(new), old=round(old)))
        fewer_bare = bare_months_per_year(current_rotation) - bare_months_per_year(rotation)
        if fewer_bare >= 0.5:
            why.append(W["cover_change"].format(months=f"{fewer_bare:.0f}" if fewer_bare >= 1.5 else f"{fewer_bare:.1f}"))

    # --- benefits ------------------------------------------------------------
    benefits = []
    if is_current:
        benefits.append(B["familiar"])
    nfix = [s for s in dict.fromkeys(slugs) if crops[s]["n_fixing"]]
    cover = [s for s in dict.fromkeys(slugs) if crops[s]["role"] == "cover"]
    deep = [s for s in new_slugs if crops[s]["root_depth"] == "deep"]
    dtol = [s for s in new_slugs if crops[s]["drought_tolerance"] >= 4]
    forage = [s for s in new_slugs if crops[s]["forage_value"] >= 4]
    if nfix:
        benefits.append(B["n_fixing"].format(crops=T.crop_list(nfix)))
    if cover:
        benefits.append(B["cover"].format(crops=T.crop_list(cover)))
    if deep and not is_current:
        benefits.append(B["deep_roots"].format(crops=T.crop_list(deep)))
    n_fam, n_cur = len(families(rotation, crops)), len(families(current_rotation or rotation, crops))
    if not is_current and n_fam > n_cur:
        benefits.append(B["families"].format(n=n_fam, current=n_cur))
    if dtol and not is_current:
        benefits.append(B["drought_tolerant"].format(crops=T.crop_list(dtol)))
    if forage and not is_current:
        benefits.append(B["forage"].format(crops=T.crop_list(forage)))

    # --- information gaps ----------------------------------------------------
    gaps = [G.get(f"tier_{tier}", G["tier_standard"])]
    smap_years = _get(profile, "uncertainty", "smap_years")
    if smap_years and smap_years < 15:
        gaps.append(G["smap_short"].format(years=smap_years))
    if soil is None or not soil.get("available", True):
        gaps.append(G["no_soil"])
    if zone == "subtropical":
        gaps.append(G["calendar_approx"])
    observed = profile.get("bare_months_observed")
    if is_current and observed:
        expected = bare_months(rotation)
        if set(observed) ^ set(expected) and len(set(observed) ^ set(expected)) >= 2:
            gaps.append(G["ndvi_mismatch"].format(observed=T.months(observed), expected=T.months(expected)))
    scen = profile.get("scenario_applied") or {}
    if scen.get("temp_c") or scen.get("rain_pct"):
        gaps.append(G["scenario"].format(temp=f"{scen.get('temp_c', 0):+g}", rain=f"{scen.get('rain_pct', 0):+g}"))
    gaps.append(G["income"])

    # --- needs local review ---------------------------------------------------
    review = [L["soil_test"]]
    if zone == "subtropical":
        review.append(L["planting_dates"])
    if new_slugs:
        review.append(L["market"].format(crops=T.crop_list(new_slugs)))
        review.append(L["pest_history"].format(crops=T.crop_list(new_slugs)))
    equip = [s for s in dict.fromkeys(slugs) if crops[s]["special_equipment"]]
    if equip:
        review.append(L["equipment"].format(crops=T.crop_list(equip)))
    if "rice" in slugs:
        review.append(L["rice_water"])
    if soil and soil.get("drainage_hint") == "slow":
        wet_sensitive = [s for s in dict.fromkeys(slugs)
                         if any("waterlogging" in st.get("sensitive", [])
                                for st in (calendars.get((s, zone)) or {}).get("growth_stages", []))]
        if wet_sensitive:
            review.append(L["drainage"].format(crops=T.crop_list(wet_sensitive)))
    yearly_deficit = sum((_get(profile, "water_balance_by_month", str(m), "deficit_mm") or 0) for m in range(1, 13))
    if yearly_deficit > 300:
        review.append(L["irrigation"])

    return {
        "why_suggested": " ".join(why),
        "evidence": _evidence(rotation, zone, profile, soil, T, crops, calendars),
        "benefits": benefits,
        "info_gaps": gaps,
        "local_review": review,
    }
