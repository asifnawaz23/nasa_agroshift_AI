"""Validate the crop knowledge base and preview each rotation's field calendar.

Usage:
    python tools/validate_crop_data.py

Checks:
  - crops.csv: required columns, value ranges, unique slugs
  - crop_calendars.json: known crops, stages contiguous and ending at the season length
  - rotation_templates.json: known crops, a calendar exists for the zone, months inside the
    calendar windows (warning), no two non-companion crops in the field at the same time (error)
Prints a month-by-month occupancy line per template so bare months are easy to see.
Exit code 1 if any error.
"""
import csv
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "backend" / "data"
MONTH_ABBR = "JFMAMJJASOND"

errors, warnings = [], []


def season_len(sow, harvest):
    n = (harvest - sow) % 12
    return 12 if n == 0 else n


def load_crops():
    with open(DATA / "crops.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    required = ["slug", "name", "name_ur", "family", "role", "water_need_mm", "drought_tolerance",
                "heat_tolerance", "frost_tolerance", "n_fixing", "root_depth", "ground_cover",
                "residue_om", "erosion_protection", "income_level", "forage_value",
                "special_equipment", "sources", "notes"]
    missing = [c for c in required if c not in rows[0]]
    if missing:
        errors.append(f"crops.csv missing columns: {missing}")
    slugs = [r["slug"] for r in rows]
    if len(slugs) != len(set(slugs)):
        errors.append("crops.csv has duplicate slugs")
    for r in rows:
        s = r["slug"]
        for col in ["drought_tolerance", "heat_tolerance", "frost_tolerance", "ground_cover",
                    "residue_om", "erosion_protection", "income_level"]:
            if not 1 <= int(r[col]) <= 5:
                errors.append(f"{s}.{col}={r[col]} not in 1-5")
        if not 0 <= int(r["forage_value"]) <= 5:
            errors.append(f"{s}.forage_value not in 0-5")
        if r["role"] not in {"cash", "cover", "forage", "legume_rotation"}:
            errors.append(f"{s}.role invalid: {r['role']}")
        if r["root_depth"] not in {"shallow", "medium", "deep"}:
            errors.append(f"{s}.root_depth invalid")
        for col in ["n_fixing", "special_equipment"]:
            if r[col] not in {"true", "false"}:
                errors.append(f"{s}.{col} must be true/false")
        if not r["sources"].strip():
            errors.append(f"{s} has no source")
    return {r["slug"]: r for r in rows}


def check_calendars(crops):
    cals = json.loads((DATA / "crop_calendars.json").read_text(encoding="utf-8"))["calendars"]
    index = {}
    for c in cals:
        key = (c["crop"], c["zone"])
        if c["crop"] not in crops:
            errors.append(f"calendar for unknown crop {c['crop']}")
        if key in index:
            errors.append(f"duplicate calendar {key}")
        index[key] = c
        n = season_len(c["typical_sow_month"], c["typical_harvest_month"])
        stages = c["growth_stages"]
        if stages[0]["start"] != 0 or stages[-1]["end"] != n:
            errors.append(f"{key}: stages must run 0..{n}, got {stages[0]['start']}..{stages[-1]['end']}")
        for a, b in zip(stages, stages[1:]):
            if a["end"] != b["start"]:
                errors.append(f"{key}: gap/overlap between {a['stage']} and {b['stage']}")
        if c["typical_sow_month"] not in c["sow_months"]:
            warnings.append(f"{key}: typical_sow_month not in sow_months")
    return index


def check_templates(crops, cal_index):
    data = json.loads((DATA / "rotation_templates.json").read_text(encoding="utf-8"))["templates"]
    for t in data:
        rot, zone = t["rotation"], t["zone"]
        label = f"{zone}/{t['key']}"
        total = 12 * rot["cycle_years"]
        occ = [[] for _ in range(total)]
        for st in rot["steps"]:
            crop = st["crop"]
            if crop not in crops:
                errors.append(f"{label}: unknown crop {crop}")
                continue
            cal = cal_index.get((crop, zone))
            if cal is None:
                errors.append(f"{label}: no {zone} calendar for {crop}")
            else:
                if st["sow_month"] not in cal["sow_months"]:
                    warnings.append(f"{label}: {crop} sown in {st['sow_month']}, calendar says {cal['sow_months']}")
                if st["harvest_month"] not in cal["harvest_months"] + [cal["typical_harvest_month"]]:
                    warnings.append(f"{label}: {crop} harvested in {st['harvest_month']}, calendar says {cal['harvest_months']}")
            start = (st["year"] - 1) * 12 + st["sow_month"] - 1
            for k in range(season_len(st["sow_month"], st["harvest_month"])):
                occ[(start + k) % total].append((crop, st.get("companion", False)))
        for i, cell in enumerate(occ):
            main = [c for c, comp in cell if not comp]
            if len(main) > 1:
                errors.append(f"{label}: year {i // 12 + 1} {MONTH_ABBR[i % 12]} has {main} at the same time")
        line = " | ".join(
            "".join("#" if occ[y * 12 + m] else "." for m in range(12)) for y in range(rot["cycle_years"]))
        bare = sum(1 for cell in occ if not cell)
        print(f"{label:34s} {line}   bare {bare}/{total} months")


def main():
    crops = load_crops()
    cal_index = check_calendars(crops)
    print(f"{len(crops)} crops, {len(cal_index)} calendars\n")
    print(f"{'template':34s} {'JFMAMJJASOND per cycle year (# = crop in field)'}")
    check_templates(crops, cal_index)
    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:", e)
    print("\nOK" if not errors else f"\n{len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
