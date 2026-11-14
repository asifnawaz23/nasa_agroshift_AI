"""Load the featured pins and warm the data cache from the pre-pulled files. Owner: Abdul Rehman.

    python manage.py load_prepulled

- Location rows come from backend/data/locations.json (the single source of truth for pins).
- The offline snapshots in backend/data/prepulled/<slug>/ (power_cache.json, soil.json) are put
  into LocationCache under the same grid keys the live cache uses, so the first /api/analyze/
  call for a featured pin is instant and still works if NASA POWER or SoilGrids is down.
  Existing cache rows are left alone (they may be newer live data).
- SMAP, NDVI and PRISM files are read straight from disk by datasources.prepulled, so they only
  need to exist; this command reports which ones each pin has.

Idempotent: safe to run on every deploy (build.sh).
"""
import json

from django.core.management.base import BaseCommand
from django.db import transaction

from datasources.cache import SOIL_GRID_STEP_DEG, grid_key
from datasources.prepulled import PREPULLED_DIR, load_locations
from locations.models import Location, LocationCache

COUNTRY_NAMES = {"PK": "Pakistan", "US": "United States"}

SNAPSHOTS = (
    # (file, cache kind, grid step or None for the default climate grid, source url)
    ("power_cache.json", "power", None, "https://power.larc.nasa.gov/"),
    ("soil.json", "soilgrids", SOIL_GRID_STEP_DEG, "https://soilgrids.org/"),
)


class Command(BaseCommand):
    help = "Create featured Location rows and warm LocationCache from pre-pulled snapshots."

    @transaction.atomic
    def handle(self, *args, **options):
        pins = load_locations()
        slugs = []

        for pin in pins:
            slugs.append(pin["slug"])
            Location.objects.update_or_create(
                slug=pin["slug"],
                defaults={
                    "name": pin["name"],
                    "lat": pin["lat"],
                    "lon": pin["lon"],
                    "country": COUNTRY_NAMES.get(pin["country"], pin["country"]),
                    "zone": pin["zone"],
                    "tier": pin["tier"],
                    "featured": pin.get("featured", True),
                },
            )

            folder = PREPULLED_DIR / pin["slug"]
            warmed = []
            for filename, kind, step, source_url in SNAPSHOTS:
                path = folder / filename
                if not path.exists():
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))["payload"]
                key = (grid_key(pin["lat"], pin["lon"], step) if step
                       else grid_key(pin["lat"], pin["lon"]))
                _, created = LocationCache.objects.get_or_create(
                    kind=kind,
                    grid_key=key,
                    defaults={"payload": payload, "source_url": source_url},
                )
                warmed.append(f"{kind}{'' if created else ' (kept existing)'}")

            files = sorted(p.name for p in folder.iterdir()) if folder.exists() else []
            satellite = [name for name in ("smap.csv", "ndvi.csv", "prism_monthly.csv") if name in files]
            self.stdout.write(
                f"{pin['slug']:<20} cache: {', '.join(warmed) or 'none'} | "
                f"files: {', '.join(satellite) or 'no satellite files'}"
            )

        removed, _ = Location.objects.exclude(slug__in=slugs).delete()
        self.stdout.write(self.style.SUCCESS(
            f"load_prepulled: {len(slugs)} featured locations"
            + (f" ({removed} removed)" if removed else "")
        ))
