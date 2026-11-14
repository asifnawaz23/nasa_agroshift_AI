"""Save offline snapshots of NASA POWER and SoilGrids data for every featured pin.

Owner: Aman. Run once the pins are final (and again whenever a pin moves):

    python tools/snapshot_power.py              # all pins in backend/data/locations.json
    python tools/snapshot_power.py iowa-central # one pin

Writes backend/data/prepulled/<slug>/power_cache.json and soil.json (committed to the repo),
so the demo still works if NASA POWER, SoilGrids or the internet is down during judging.
Requests are spaced out to respect SoilGrids' fair-use limit (~5 per minute).
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from datasources.power import df_to_records, fetch_power_daily, missing_fraction  # noqa: E402
from datasources.prepulled import PREPULLED_DIR, load_locations  # noqa: E402
from datasources.soilgrids import fetch_soilgrids  # noqa: E402


def write(path, payload, source_url):
    path.write_text(json.dumps({"payload": payload, "source_url": source_url,
                                "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat()}),
                    encoding="utf-8")


def main(slugs):
    locs = [l for l in load_locations() if not slugs or l["slug"] in slugs]
    for i, loc in enumerate(locs):
        folder = PREPULLED_DIR / loc["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        t = time.time()
        df = fetch_power_daily(loc["lat"], loc["lon"])
        write(folder / "power_cache.json", df_to_records(df), "https://power.larc.nasa.gov/")
        print(f"{loc['slug']:20s} POWER {len(df)} days, missing {missing_fraction(df):.1%} ({time.time() - t:.0f}s)")
        if i:
            time.sleep(13)
        t = time.time()
        try:
            soil = fetch_soilgrids(loc["lat"], loc["lon"])
            write(folder / "soil.json", soil, "https://soilgrids.org/")
            print(f"{'':20s} soil  {soil.get('texture')} OM {soil.get('organic_matter_pct')}% "
                  f"available={soil['available']} ({time.time() - t:.0f}s)")
        except Exception as exc:  # keep going: soil is optional
            print(f"{'':20s} soil  FAILED: {exc}")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
