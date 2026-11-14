# Pre-pulled data for the featured pins

Folder name = pin slug in `backend/data/locations.json`. Loaded by `datasources.prepulled.load_prepulled()`.

| Pin | Point | Files | Source and date |
|---|---|---|---|
| `punjab-faisalabad` | 31.30, 73.00 | `ndvi.csv`, `smap.csv`, `power_cache.json`, `soil.json` | NDVI: AppEEARS request `fieldshift-ndvi-faisalabad-rural` (MOD13Q1 v061, 2006 to 2025). SMAP: AppEEARS `fieldshift-smap-faisalabad-rural` (SPL3SMP_E v006, 2015 to 2025). Downloaded 2026-11-15. |
| `iowa-central` | 42.10, -93.45 | `ndvi.csv`, `power_cache.json`, `soil.json` | NDVI: AppEEARS `fieldshift-ndvi-candidates`, point `iowa-c1` (MOD13Q1 v061, 2006 to 2025). Downloaded 2026-11-15. **No SMAP yet**: the earlier SMAP request was for 42.0, -93.6 (about 15 km away) and is not used. Soil moisture falls back to NASA POWER root-zone wetness until a new SMAP request for 42.10, -93.45 is added. |
| `sindh-hyderabad` | 25.40, 68.40 (provisional) | `smap.csv`, `power_cache.json`, `soil.json` | SMAP: AppEEARS `fieldshift-smap-3pins` (SPL3SMP_E v006, 2015 to 2025), downloaded 2026-11-15. No NDVI: no point checked so far is cropland (flat, bare or always green), so NDVI would describe the wrong land. SMAP's 9 km cell covers the surrounding farmland. |

- `ndvi.csv` and `smap.csv` are made with `tools/appeears_to_prepulled.py` (quality filtering described in that file).
- `power_cache.json` and `soil.json` are offline snapshots made with `tools/snapshot_power.py` on 2026-11-15 (NASA POWER daily 2006 to 2025, ISRIC SoilGrids top 30 cm). They are used only when the live services fail.
- Raw AppEEARS CSVs are not committed (they are kept outside the repository).
- Iowa's tier is `featured` until PRISM, CDL and SSURGO files are added; then set `"tier": "us_enhanced"` in `locations.json` (its `planned_tier`).
