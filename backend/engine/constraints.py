"""Farmer constraints as risk warnings on a strategy (plan section 6).

Pure Python, no Django. A strategy that clashes with the farmer's constraints is still shown,
with plain warnings in its "needs local review" part:

    constraint_warnings(rotation, profile, constraints, crops=None, lang="en") -> [str]

- water_availability: rainfed or limited irrigation, compared with the rotation's yearly water
  need and the location's average yearly rain; rice without full irrigation.
- equipment: crops that need special equipment when the farmer has basic equipment.
- market_pref: fodder crops under a cash preference, or no fodder crop under a fodder preference.
"""
from __future__ import annotations

from .explain import load_text
from .knowledge import annual_water_need_mm, load_crops

# Rainfed: warn when the yearly need is above the yearly rain.
RAINFED_NEED_TO_RAIN = 1.0
# Limited irrigation: warn when the need is more than this multiple of the rain.
LIMITED_NEED_TO_RAIN = 1.5
FORAGE_STRONG = 4          # forage_value at or above this counts as a fodder crop
STANDING_WATER_CROPS = ("rice",)


def _annual_rain(profile):
    monthly = (profile or {}).get("monthly_climatology") or {}
    values = [(monthly.get(str(m)) or {}).get("precip_mm") for m in range(1, 13)]
    values = [v for v in values if v is not None]
    return sum(values) if len(values) == 12 else None


def _crop_names(slugs, crops, lang):
    names = []
    for slug in dict.fromkeys(slugs):
        crop = crops.get(slug, {})
        names.append(crop.get("name_ur") if lang == "ur" and crop.get("name_ur") else crop.get("name", slug))
    text = load_text(lang)
    if len(names) <= 1:
        return "".join(names)
    sep = "، " if lang == "ur" else ", "
    return sep.join(names[:-1]) + f" {text['list_and']} " + names[-1]


def constraint_warnings(rotation, profile, constraints, crops=None, lang="en") -> list[str]:
    crops = crops or load_crops()
    constraints = constraints or {}
    t = load_text(lang)["constraints"]
    slugs = [s["crop"] for s in rotation.get("steps", []) if s.get("crop") in crops]
    warnings = []

    water = constraints.get("water_availability")
    need = annual_water_need_mm(rotation, crops)
    rain = _annual_rain(profile)
    if rain:
        if water == "rainfed" and need > rain * RAINFED_NEED_TO_RAIN:
            warnings.append(t["rainfed_short"].format(need=round(need), rain=round(rain)))
        elif water == "limited_irrigation" and need > rain * LIMITED_NEED_TO_RAIN:
            warnings.append(t["limited_short"].format(need=round(need), rain=round(rain),
                                                      gap=round(need - rain)))
    flooded = [s for s in slugs if s in STANDING_WATER_CROPS]
    if flooded and water in ("rainfed", "limited_irrigation"):
        warnings.append(t["rice_no_irrigation"].format(crops=_crop_names(flooded, crops, lang)))

    if constraints.get("equipment") == "basic":
        special = [s for s in slugs if crops[s].get("special_equipment")]
        if special:
            warnings.append(t["equipment_basic"].format(crops=_crop_names(special, crops, lang)))

    market = constraints.get("market_pref")
    fodder = [s for s in slugs if crops[s].get("role") == "forage"]
    if market == "cash" and fodder:
        warnings.append(t["market_cash_forage"].format(crops=_crop_names(fodder, crops, lang)))
    if market == "forage" and not any((crops[s].get("forage_value") or 0) >= FORAGE_STRONG for s in slugs):
        warnings.append(t["market_forage_none"])

    return warnings
