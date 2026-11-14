"""Load the crop knowledge base into the database. Owner: Abdul Rehman.

    python manage.py seed_crops

Sources (single source of truth, edited by hand and checked with tools/validate_crop_data.py):
    backend/data/crops.csv, crop_calendars.json, rotation_templates.json

Idempotent: rows are matched by their natural key and updated in place, so running it on
every deploy (build.sh) is safe. Rows whose slug/key is no longer in the files are removed,
so the database always matches the files.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from crops.models import Crop, CropCalendar, RotationTemplate
from engine.knowledge import load_calendars, load_crops, load_templates

CROP_FIELDS = [
    "name", "name_ur", "family", "role", "water_need_mm", "drought_tolerance",
    "heat_tolerance", "frost_tolerance", "n_fixing", "root_depth", "ground_cover",
    "residue_om", "erosion_protection", "income_level", "forage_value",
    "special_equipment", "sources", "notes",
]


class Command(BaseCommand):
    help = "Load crops, crop calendars and rotation templates from backend/data (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        crops = load_crops()
        calendars = load_calendars()
        templates = load_templates()

        crop_rows = {}
        for slug, crop in crops.items():
            defaults = {field: crop.get(field) for field in CROP_FIELDS}
            defaults["name_ur"] = defaults["name_ur"] or ""
            defaults["sources"] = defaults["sources"] or ""
            defaults["notes"] = defaults["notes"] or ""
            defaults["forage_value"] = defaults["forage_value"] or 0
            crop_rows[slug], _ = Crop.objects.update_or_create(slug=slug, defaults=defaults)
        removed_crops, _ = Crop.objects.exclude(slug__in=crop_rows).delete()

        keep_calendars = []
        for (slug, zone), cal in calendars.items():
            row, _ = CropCalendar.objects.update_or_create(
                crop=crop_rows[slug],
                zone=zone,
                defaults={
                    "season_label": cal["season_label"],
                    "sow_months": cal["sow_months"],
                    "harvest_months": cal["harvest_months"],
                    "growth_stages": cal["growth_stages"],
                },
            )
            keep_calendars.append(row.pk)
        CropCalendar.objects.exclude(pk__in=keep_calendars).delete()

        keep_templates = []
        for zone, items in templates.items():
            for key, template in items.items():
                row, _ = RotationTemplate.objects.update_or_create(
                    zone=zone,
                    key=key,
                    defaults={
                        "name": template["name"],
                        "description": template["description"],
                        "steps": template["rotation"],
                    },
                )
                keep_templates.append(row.pk)
        RotationTemplate.objects.exclude(pk__in=keep_templates).delete()

        self.stdout.write(self.style.SUCCESS(
            f"seed_crops: {len(crop_rows)} crops, {len(keep_calendars)} calendars, "
            f"{len(keep_templates)} rotation templates"
            + (f" ({removed_crops} stale rows removed)" if removed_crops else "")
        ))
