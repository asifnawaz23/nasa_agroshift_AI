# backend/data — crop knowledge base

Owner: **Abdul Rehman**. Loaded into the database by `python manage.py seed_crops` (idempotent).
Check after every edit:

```bash
python tools/validate_crop_data.py
```

| File | What it holds | Model (plan section 5) |
|---|---|---|
| `crops.csv` | 14 crops with water need, tolerances (1–5), N-fixing, roots, cover, organic matter, erosion protection, income (placeholder), forage, equipment, **source per row**, Urdu name | `Crop` |
| `crop_calendars.json` | Sow/harvest windows per climate zone + **growth stages** with sensitive stages | `CropCalendar` |
| `rotation_templates.json` | `current_default`, `water_saver`, `soil_builder` per zone (+ `current_alt_rice_wheat` for Punjab) | `RotationTemplate` |

| `text/en.json`, `text/ur.json` | Sentence templates for explanations (why, evidence, benefits, info gaps, local review). **Urdu is a draft: please review.** Placeholders like `{crop}` must match in both files (a test checks this) | — |

## Loading in Python (no Django needed)
`engine/knowledge.py` reads these files: `load_crops()`, `load_calendars()`, `load_templates()`, plus helpers
`bare_months_per_year()`, `sensitive_windows()`, `annual_water_need_mm()`. `engine/explain.py` builds the
five explanation parts from them. The Django `seed_crops` command (Shayan/Abdul Rehman, once the models exist) only needs:

```python
from engine.knowledge import load_crops, load_calendars, load_templates
for c in load_crops().values():
    Crop.objects.update_or_create(slug=c["slug"], defaults={k: v for k, v in c.items() if k != "slug"})
for (slug, zone), cal in load_calendars().items():
    CropCalendar.objects.update_or_create(crop=Crop.objects.get(slug=slug), zone=zone, season_label=cal["season_label"],
        defaults={"sow_months": cal["sow_months"], "harvest_months": cal["harvest_months"], "growth_stages": cal["growth_stages"]})
for zone, items in load_templates().items():
    for key, t in items.items():
        RotationTemplate.objects.update_or_create(zone=zone, key=key,
            defaults={"name": t["name"], "description": t["description"], "steps": t["rotation"]})
```

## Crop slugs (use these exact names everywhere: frontend dropdowns, CDL mapping, scoring)

| Slug | Name | Urdu | Zones |
|---|---|---|---|
| `maize` | Maize (corn) | مکئی | temperate, subtropical |
| `soybean` | Soybean | سویابین | temperate |
| `oats` | Oats | جئی | temperate, subtropical (fodder) |
| `wheat` | Wheat | گندم | temperate (winter), subtropical (rabi) |
| `alfalfa` | Alfalfa (lucerne) | لوسرن (رجکا) | temperate, subtropical |
| `cereal_rye` | Cereal rye (cover) | سیریل رائی | temperate |
| `red_clover` | Red clover | سرخ کلاور | temperate |
| `sorghum` | Sorghum | جوار | temperate, subtropical |
| `cotton` | Cotton | کپاس | subtropical |
| `rice` | Rice (paddy) | دھان (چاول) | subtropical |
| `chickpea` | Chickpea (gram) | چنا | subtropical |
| `mungbean` | Mungbean | مونگ | subtropical |
| `berseem` | Berseem | برسیم | subtropical |
| `mustard` | Mustard (rapeseed) | سرسوں | subtropical |

## Conventions
- Months are 1–12. If `harvest_month < sow_month`, the harvest is in the next calendar year.
- Growth stages are in months after the typical sowing month; the last stage ends at the season length.
- `companion: true` in a rotation step = sown into a standing crop (red clover in oats); overlap allowed.
- `crop_calendars` is JSON instead of the CSV named in plan v1, because growth stages are nested lists.

## Data quality (say this in the app and slides)
- Water needs: FAO Irrigation & Drainage Paper 33 ranges and FAO-56 where available; others are **approximate** and labeled so in `sources`.
- Tolerance and soil scores (1–5) are expert estimates for comparing crops, not measurements.
- `income_level` is a **regional placeholder**.
- Subtropical calendars and templates are typical for Sindh and Punjab and **must be confirmed locally**.
- TODO: FAO GAEZ cross-check of suitability for the 3 pins (notes column).
