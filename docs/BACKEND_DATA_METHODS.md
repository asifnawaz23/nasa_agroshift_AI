# FieldShift Planner: backend, data and methods

Written by the backend data team (Abdul Rehman, Aman, Asif) for the README and slides. Every number below is taken from `backend/engine/constants.py` or the data files, so it matches what the app computes.

## 1. Data sources and credits

| Source | What we use | How we get it | Where in the code |
|---|---|---|---|
| **NASA POWER** (daily, point) | Temperature (mean, max, min), rain, root-zone soil wetness, solar radiation, humidity, 2006 to 2025 | Live API `power.larc.nasa.gov`, community `AG`, cached per 0.5° grid cell | `datasources/power.py`, `cache.py` |
| **NASA SMAP** (SPL3SMP_E v006, 9 km) | Surface soil moisture, 2015 to 2025 | Earthdata AppEEARS point samples, AM retrieval with recommended quality, PM fills gaps | `prepulled/<pin>/smap.csv` |
| **NASA MODIS NDVI** (MOD13Q1 v061, 250 m, 16-day) | Greenness, bare months, crop seasons, 2006 to 2025 | Earthdata AppEEARS point samples, pixel reliability good or marginal | `prepulled/<pin>/ndvi.csv` |
| **ISRIC SoilGrids** (250 m) | Clay, sand, silt, organic carbon, pH (top 30 cm) | Live API, cached per 0.01° cell | `datasources/soilgrids.py` |
| **FAO-56, FAO Paper 33, FAO GAEZ**, Pakistan and Iowa extension guides | Crop water needs, tolerances, calendars, growth stages | Hand-built table with a source on every row | `data/crops.csv`, `crop_calendars.json` |

Credits for the app footer and slides: *NASA POWER Project (NASA Langley Research Center); NASA SMAP (NSIDC DAAC); NASA MODIS MOD13Q1 (LP DAAC), both via AppEEARS; ISRIC SoilGrids (CC BY 4.0); FAO.* Planned but not in the repo yet: USDA SSURGO, USDA NASS Cropland Data Layer and PRISM for the Iowa pin.

## 2. Featured pins

| Pin | Point | Satellite files | Why this point |
|---|---|---|---|
| Central Iowa | 42.10, −93.45 | NDVI (SMAP request submitted) | NDVI 0.21 in winter to 0.89 in July: real corn and soybean fields. The first point (42.0, −93.6) mixed with the town of Ames. |
| Punjab (Faisalabad area) | 31.30, 73.00 | NDVI, SMAP | Rural point with crop seasons (NDVI 0.30 to 0.63). The first point was the city. |
| Sindh (Hyderabad area) | 25.40, 68.40 | SMAP | No cropland point found yet (NDVI flat or always green at 4 points checked). SMAP covers a 9 km cell, so it still describes the surrounding farmland; NDVI is not used here. |

Every pin also has an offline snapshot of NASA POWER and SoilGrids (`power_cache.json`, `soil.json`), so the demo works without internet. Details and dates: `backend/data/prepulled/README.md`.

## 3. Harmonization

- Climate is daily NASA POWER for one grid cell (about 0.5°, 55 km). Monthly values are averages over 20 years; daily values are used only to count days (heat, frost, extreme rain, dry spells).
- SMAP and NDVI are averaged to the same months as POWER. SMAP has only about 10 years (since 2015), which the app states as an information gap.
- Any clicked point gets the same POWER and SoilGrids analysis (Standard tier). Featured pins add satellite files (Featured tier); Iowa is planned to add US ground data (US-enhanced tier).

## 4. Climate indicators

| Indicator | Definition |
|---|---|
| Heat-stress day | daily maximum above 35 °C (severe heat: above 40 °C, used for heat-tolerant crops such as cotton) |
| Frost day | daily minimum at or below 0 °C |
| Extreme-rain day | rain above the 95th percentile of wet days (≥ 1 mm) at that location |
| Dry spell | 10 or more days in a row with less than 1 mm of rain; reported as the share of years with one in each month |
| ET0 (evaporation demand) | Hargreaves–Samani: 0.0023 × 0.408 × Ra × (Tmean + 17.8) × √(Tmax − Tmin), Ra from latitude and day of year (FAO-56 eq. 21). The 0.408 converts MJ to mm. |
| Water deficit | ET0 minus rain, per month, when positive |
| Soil-moisture anomaly | how far a month's soil moisture is from its normal, in standard deviations (SMAP where available, otherwise POWER root-zone wetness) |
| Bare month | climatological NDVI below 0.25 |
| Drought year / heat year | growing-season rain below the 20th percentile / heat days above the 80th percentile |
| Trend | straight-line change per decade over 20 years, marked significant only when it stands out from year-to-year noise (t > 2.1, about p < 0.05). Example: Iowa rain shows −100 mm per decade but is **not** significant. |

## 5. What-If scenarios

- Temperature: −2 to +5 °C added to every daily temperature.
- Rain: −50 % to +30 % applied to every daily rain value.
- Soil wetness: shifted by the change in the monthly water balance (rain change minus ET0 change) × 0.001 per mm. This is a simplified rule and labelled as such.
- Thresholds stay at the historical values, so a hotter scenario shows more heat days, not a moved goalpost.
- Everything downstream (ET0, stress counts, alerts, scores) is recomputed. Results are labelled "Simulated", and confidence drops to Low beyond ±3 °C or ±30 % rain.

## 6. Alerts (pattern-based, not forecasts)

Each month with a crop in the field is checked; the level is Moderate / High / Critical:

| Alert | Variable | Moderate | High | Critical |
|---|---|---|---|---|
| Drought | dry-spell probability | 0.30 | 0.50 | 0.70 |
| Water deficit | deficit (mm) | 30 | 60 | 100 |
| Heat | heat days (count double in a sensitive stage) | 3 | 7 | 12 |
| Frost | frost days, frost-sensitive crops only | 1 | 3 | 7 |
| Waterlogging | extreme-rain days, slow-draining soils only | 1.0 | 1.5 | 2.5 |
| Soil drying | soil-moisture anomaly | −1.0 | −1.5 | −2.0 |

Heat-tolerant crops are judged on days above 40 °C; irrigation lowers water-deficit severity; dry spells count only in drought-sensitive stages. Each alert carries the trigger value, a reason and a preventive action in English and Urdu.

**Vulnerable months** (on the timeline): a month where a crop of the current rotation is in a growth stage sensitive to a stress that is present (heat days ≥ 3, dry-spell probability ≥ 0.30, frost, or soil drying).

## 7. Crop knowledge base and strategies

- 14 crops (`maize, soybean, oats, wheat, alfalfa, cereal_rye, red_clover, sorghum, cotton, rice, chickpea, mungbean, berseem, mustard`) with water need, tolerances, nitrogen fixing, roots, ground cover, residue, erosion protection, income (regional placeholder), forage value and a source per row.
- 19 calendars (temperate, and subtropical kharif and rabi) with growth stages and the stresses each stage is sensitive to.
- Three strategies per zone: **Current**, **Water-saver**, **Soil-builder**. The subtropical soil-builder was retimed on 2026-11-15: April mungbean and July maize flowered in peak heat. A July (kharif) mungbean cut critical heat alerts from 4 to 3 in Faisalabad and from 3 to 1 in Sindh, and lowered water need from 1,550 to 1,225 mm, at the cost of about 1.5 more bare months a year.
- Every strategy shows the five required parts (why suggested, evidence, benefits, information gaps, local review), written from the real numbers by `engine/explain.py`, in English or Urdu.

## 8. AI layer

`ai/client.py` asks the LLM for a JSON answer (summary, points labelled Observed / Estimated cause / Prediction, actions, needs-expert, confidence) using only the analysis numbers it is given. With no key, a timeout, an error or a refusal it returns nothing and the app shows the template text instead, so the demo never depends on the LLM. Answers are cached. No fertilizer or pesticide doses are ever given.

## 9. Running it

```bash
cd backend
pip install -r requirements.txt          # Python 3.12 or newer (Django 6)
python manage.py migrate
python manage.py seed_crops              # crops, calendars, rotation templates (safe to repeat)
python manage.py load_prepulled          # featured pins + warm the cache from snapshots (safe to repeat)
python -m pytest -q -p no:anyio          # engine and AI client tests
python manage.py test                    # API tests (needs the database)
```

Tools: `tools/validate_crop_data.py` (checks the crop data), `tools/appeears_to_prepulled.py` (AppEEARS CSV to pin files), `tools/snapshot_power.py` (offline snapshots).

## 10. Limitations

Satellite and reanalysis data are coarse compared with one field. Alerts come from 20 years of history and simulations, not live forecasts. Crop calendars, water needs and income values are simplified regional estimates; subtropical calendars need local review. SMAP covers only 2015 onwards. Sindh has no confirmed cropland point yet. The Urdu text is a draft that needs a native speaker's review.
