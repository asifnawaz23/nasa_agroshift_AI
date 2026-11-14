"""Crop knowledge base loader + rotation calendar helpers. Owner: Abdul Rehman.

Pure Python (no Django). Used by scoring, explanations, alerts, and by the seed_crops
command (which just writes load_crops()/load_calendars()/load_templates() into the DB).

    load_crops()      -> {slug: crop dict with typed values}
    load_calendars()  -> {(slug, zone): calendar dict}
    load_templates()  -> {zone: {key: template dict}}

Rotation helpers (rotation = {"cycle_years": n, "steps": [{year, crop, sow_month, harvest_month}]}):
    field_occupancy(rotation)        -> list (12 * cycle_years) of crop slugs in the field each month
    bare_fraction_by_month(rotation) -> {month: share of cycle years the field is bare}
    bare_months(rotation)            -> months bare in at least half the cycle years
    sensitive_windows(rotation, zone, calendars) -> [{crop, year, month, stage, sensitive}]
    annual_water_need_mm(rotation, crops)
"""
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
INT_FIELDS = ["water_need_mm", "drought_tolerance", "heat_tolerance", "frost_tolerance", "ground_cover",
              "residue_om", "erosion_protection", "income_level", "forage_value"]
BOOL_FIELDS = ["n_fixing", "special_equipment"]


def season_length(sow: int, harvest: int) -> int:
    n = (harvest - sow) % 12
    return 12 if n == 0 else n


@lru_cache(maxsize=4)
def load_crops(data_dir: str | None = None) -> dict:
    path = Path(data_dir or DATA_DIR) / "crops.csv"
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    crops = {}
    for r in rows:
        c = dict(r)
        for k in INT_FIELDS:
            c[k] = int(c[k])
        for k in BOOL_FIELDS:
            c[k] = c[k].strip().lower() == "true"
        crops[c["slug"]] = c
    return crops


@lru_cache(maxsize=4)
def load_calendars(data_dir: str | None = None) -> dict:
    path = Path(data_dir or DATA_DIR) / "crop_calendars.json"
    cals = json.loads(path.read_text(encoding="utf-8"))["calendars"]
    return {(c["crop"], c["zone"]): c for c in cals}


@lru_cache(maxsize=4)
def load_templates(data_dir: str | None = None) -> dict:
    path = Path(data_dir or DATA_DIR) / "rotation_templates.json"
    out: dict = {}
    for t in json.loads(path.read_text(encoding="utf-8"))["templates"]:
        out.setdefault(t["zone"], {})[t["key"]] = t
    return out


# ---------------------------------------------------------------------------
# Rotation calendar helpers
# ---------------------------------------------------------------------------
def step_months(step: dict) -> list[int]:
    """Calendar months (1-12) the crop is in the field, sow month included, harvest month excluded."""
    n = season_length(step["sow_month"], step["harvest_month"])
    return [((step["sow_month"] - 1 + k) % 12) + 1 for k in range(n)]


def field_occupancy(rotation: dict) -> list[list[str]]:
    total = 12 * rotation["cycle_years"]
    occ: list[list[str]] = [[] for _ in range(total)]
    for st in rotation["steps"]:
        start = (st["year"] - 1) * 12 + st["sow_month"] - 1
        for k in range(season_length(st["sow_month"], st["harvest_month"])):
            occ[(start + k) % total].append(st["crop"])
    return occ


def bare_fraction_by_month(rotation: dict) -> dict[int, float]:
    occ, years = field_occupancy(rotation), rotation["cycle_years"]
    return {m: sum(1 for y in range(years) if not occ[y * 12 + m - 1]) / years for m in range(1, 13)}


def bare_months(rotation: dict, min_fraction: float = 0.5) -> list[int]:
    """Calendar months that are bare in at least `min_fraction` of the cycle years."""
    return [m for m, f in bare_fraction_by_month(rotation).items() if f >= min_fraction]


def bare_months_per_year(rotation: dict) -> float:
    """Average number of bare months per year over the whole cycle (use this to compare rotations)."""
    return round(sum(bare_fraction_by_month(rotation).values()), 2)


def stage_for(step: dict, calendar: dict, month_index: int) -> dict:
    """Growth stage for the k-th month after sowing.

    The calendar's stages are stretched or squeezed to the rotation's season length. If a month
    overlaps several stages, the most sensitive one wins, so a short season never skips flowering.
    """
    rot_len = season_length(step["sow_month"], step["harvest_month"])
    cal_len = season_length(calendar["typical_sow_month"], calendar["typical_harvest_month"])
    ratio = cal_len / rot_len
    lo, hi = month_index * ratio, (month_index + 1) * ratio
    overlapping = [s for s in calendar["growth_stages"] if s["start"] < hi and s["end"] > lo]
    if not overlapping:
        return calendar["growth_stages"][-1]
    return max(overlapping, key=lambda s: len(s.get("sensitive", [])))


def sensitive_windows(rotation: dict, zone: str, calendars: dict | None = None) -> list[dict]:
    calendars = calendars or load_calendars()
    out = []
    for st in rotation["steps"]:
        cal = calendars.get((st["crop"], zone))
        if cal is None:
            continue
        for k, month in enumerate(step_months(st)):
            stage = stage_for(st, cal, k)
            if stage.get("sensitive"):
                out.append({"crop": st["crop"], "year": st["year"], "month": month,
                            "stage": stage["stage"], "sensitive": list(stage["sensitive"])})
    return out


def annual_water_need_mm(rotation: dict, crops: dict | None = None) -> float:
    crops = crops or load_crops()
    total = sum(crops[s["crop"]]["water_need_mm"] for s in rotation["steps"] if s["crop"] in crops)
    return total / rotation["cycle_years"]


def families(rotation: dict, crops: dict | None = None) -> list[str]:
    crops = crops or load_crops()
    return sorted({crops[s["crop"]]["family"] for s in rotation["steps"] if s["crop"] in crops})
