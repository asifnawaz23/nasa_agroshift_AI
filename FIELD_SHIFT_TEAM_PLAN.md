# FieldShift Planner — Team Plan v2 (24-hour build)

NASA Space Apps Challenge 2026 · Challenge: **Field Shift: Adapting Farms with NASA Data**
Working name: **FieldShift Planner** (rename freely)

> Rule of this doc: **a working, good project, not a complex one.** If something is not in the MUST list, it does not get built until every MUST item works end to end.
> Items marked **VERIFY** depend on external APIs or product names that change. Check them in the first hour and fall back to the manual option listed.

### What changed from v1
- Team is now **4 backend** (Shayan, Abdul Rehman, Asif, Aman) and **2 frontend** (Talha, Musab).
- Abdul Rehman (backend) now owns the crop knowledge base, Iowa ground data, seed commands, explanation text and API tests. Charts moved to Musab. Crop table moved from Musab to Abdul Rehman.
- **What-If simulation** promoted from STRETCH to MUST.
- New: **early-warning alerts** with severity levels (MUST), **AI explanation + assistant chat in English and Urdu** (SHOULD), **voice** and **photo symptom description** (STRETCH).
- Image dosage advice, fertilizer quantity calculator, pesticide advice and yield prediction are **out of scope** (safety and data reasons, see section 2).
- Fixes: ET0 formula now includes the 0.408 conversion factor; duplicate section numbers fixed; SMAP record length noted.

---

## 0. Team and roles at a glance

| Person | Team | Role | Owns |
|---|---|---|---|
| **Shayan** | Backend | Tech lead | API contract, Django project, models, scoring, strategies, `/analyze`, `/explain`, `/chat`, deployment, merges |
| **Asif** | Backend | Climate science | `engine/climate_profile.py`, What-If scenario engine, `engine/alerts.py`, POWER-vs-PRISM validation |
| **Aman** | Backend | Data engineer | NASA POWER + SoilGrids clients, cache, SMAP/NDVI pre-pull, LLM client wrapper (`ai/client.py`) |
| **Abdul Rehman** | Backend | Ground data + knowledge base | Crop table, calendars, growth stages, rotation templates, Iowa SSURGO/CDL/PRISM, `seed_crops`, `load_prepulled`, `engine/explain.py`, `/locations` + `/crops`, API tests, Urdu text |
| **Talha** | Frontend | Frontend lead | App shell, map, input form, strategy cards, What-If panel, chat panel, Vercel deploy |
| **Musab** | Frontend | Charts + polish + story | All charts, alert cards, glossary, disclaimer, responsive QA, README, slides, video |

Everyone: read sections 1 to 4, then your own section in 15.

---

## 1. What we are building

**One-liner:** a web app where a farmer picks a spot on a map, tells us their current rotation and priorities, and sees three rotation strategies compared side by side with NASA-based evidence, risk alerts, What-If simulations, and plain-language AI explanations in English or Urdu.

### The questions the app answers
1. **What is happening?** Climate and stress picture for the location (NASA POWER, SMAP, NDVI).
2. **Why is it happening?** Grounded AI explanation of the charts, from our own numbers only.
3. **What might happen next?** Historical risk patterns and early-warning alerts per month.
4. **What if conditions change?** Temperature and rainfall sliders that re-run the analysis.
5. **What should I do?** Three rotation strategies, scored and explained.
6. **Can I ask for help?** Assistant chat in English and Urdu (voice as stretch).

### User flow
1. The map shows 3 featured pins (2 in Pakistan, 1 in Iowa). The farmer clicks a pin, **or any other point**.
2. The farmer sets: current rotation (pre-filled), priorities (water, soil health, income, erosion, pest control), and constraints (water availability, equipment, market preference).
3. The farmer presses **Analyze**.
4. The app shows:
   - Data tier and confidence badge.
   - Climate and stress charts.
   - **Alerts** (Low / Moderate / High / Critical) with the trigger and a preventive action.
   - Bare-field months and vulnerable months for the current rotation, with crop growth stages.
   - **Three strategies**: *Current*, *Water-saver*, *Soil-builder*, each with a score and the five parts: **why suggested, evidence, benefits, information gaps, risks that need local review**.
   - **What-If panel**: sliders for temperature (−2 to +5 °C) and rainfall (−50% to +30%). Charts animate from baseline to scenario, and strategy scores and alerts update.
   - **"Explain this" button** on each chart and an **assistant chat** (English / اردو).
   - A reminder that the tool supports farmer judgment and does not replace local expertise.
5. Glossary tooltips explain ET, NDVI, soil-moisture anomaly, frost risk, water balance.
6. Every value is labeled **Historical**, **Simulated**, or **AI explanation**.

### What judges should take away
- Real NASA data (POWER, SMAP, MODIS/VIIRS NDVI) drives every number.
- Satellite data is compared with ground data (PRISM, SSURGO, CDL) where we have it, and we say so where we don't.
- Every score, alert and AI sentence is traceable to data.
- We state uncertainty and where local experts are needed.

---

## 2. Scope

### MUST (build first)
- Map with 3 featured pins and click-anywhere analysis.
- Live NASA POWER + SoilGrids for any point, cached in Postgres.
- SMAP soil moisture and MODIS/VIIRS NDVI, pre-pulled for the 3 featured locations.
- Climate profile with indicators (section 7).
- Crop table (12 to 15 crops) with two calendar zones and growth stages.
- Three strategies per location, scored on 6 sub-scores with explanations.
- Each strategy shows the 5 required parts.
- Bare-field and vulnerable-month view for the current rotation.
- **What-If sliders** (temperature, rainfall) re-running profile, scores and alerts, with a baseline-vs-scenario chart.
- **Alerts** with severity, trigger variables and preventive action (section 9).
- Data tier + confidence label + disclaimer.
- Glossary tooltips.
- Deployed on free tiers, with cached fallback for featured locations.

### SHOULD (after MUST works)
- **AI "Explain this"** for charts and strategies, grounded in the analysis JSON (section 10).
- **Assistant chat** (text) in English and Urdu, using the current analysis as context, with follow-up memory.
- Urdu toggle for key UI labels, alerts and glossary.
- Iowa ground data: SSURGO soil, CDL crop history, PRISM validation.
- Farmer overrides (soil texture, planting dates).
- Constraint filters (water, equipment, market).
- Month-by-year stress heatmap.
- FAO GAEZ cross-check of crop suitability.
- About-the-data panel (satellite vs ground).

### STRETCH (only if time)
- **Voice** input and output (browser Web Speech API, English + Urdu). **VERIFY** Urdu support in the first hour.
- **Photo symptom description**: farmer uploads a crop photo, the AI *describes visible symptoms and possible causes* only, always with "confirm with an expert or lab". **No dosage, product or pesticide advice.**
- Soil-moisture slider in What-If (applied to the anomaly).
- SRTM slope proxy for erosion.
- Two stress-detection methods compared on a methods slide.
- NASS QuickStats yield context for Iowa.
- IMERG comparison layer.

### OUT OF SCOPE (say so on the future-work slide)
| Item | Why |
|---|---|
| Fertilizer label reading + quantity calculator | Wrong doses harm crops, soil and people. Needs verified label and soil-test data we do not have. |
| Pesticide / chemical recommendations | Must follow registered labels and local law. Not safe to automate in 24 hours. |
| Disease diagnosis from images | Needs a trained, validated model. We only describe symptoms. |
| Yield prediction | No reliable training data for our pins in 24 hours. |
| Mobile push notifications | In-app alerts are enough for the demo. |
| Live weather forecasts | Our alerts are based on historical patterns and scenarios, and labeled as such. |

### FUTURE WORK (slide only, do not build)
ECOSTRESS, Landsat/Sentinel-2 field-level mapping, GRACE groundwater trends, GEDI, field-zone maps, live forecasts, push notifications, verified fertilizer calculator with soil tests, user accounts, saved scenarios, native mobile app.

---

## 3. Architecture and stack

```
 React (Vite) on Vercel  ──HTTPS──▶  Django + DRF on Render (Gunicorn)  ──▶  Postgres on Neon
                                         │
                                         ├─ datasources/ (POWER, SoilGrids live, cached)
                                         ├─ data/prepulled/ (SMAP, NDVI, SSURGO, CDL, PRISM files)
                                         ├─ engine/ (pure Python: climate profile, scenario, scoring, alerts, explanations)
                                         └─ ai/ (LLM client, grounded prompts, response cache)  ──▶  LLM API
```

- **Backend:** Python, Django, Django REST Framework, `requests`, `pandas`, `numpy`, `dj-database-url`, `whitenoise`, `django-cors-headers`, `gunicorn`, `psycopg[binary]`, plus the LLM provider SDK (for example `anthropic`).
- **Frontend:** React + Vite, `react-leaflet` (map), `recharts` (charts, animated transitions). Plain CSS or Tailwind.
- **Database:** Postgres (Neon free tier). Seeded from files in the repo.
- **LLM:** one provider, server-side only, key in `LLM_API_KEY` env var. Default model set in `settings.LLM_MODEL` (for example `claude-sonnet-5-5`). **VERIFY** free credits or budget in the first hour.
- **No** Celery, no auth, no user accounts, no microservices, no native mobile app.

### Repo layout (monorepo)
```
field-shift/
├── README.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── build.sh
│   ├── config/                 # settings.py, urls.py, wsgi.py
│   ├── crops/                  # models + admin + seed_crops (Abdul Rehman)
│   ├── locations/              # models + admin + load_prepulled (Abdul Rehman)
│   ├── datasources/            # power.py, soilgrids.py, cache.py, loaders (Aman)
│   ├── engine/                 # PURE PYTHON, no Django imports
│   │   ├── constants.py        # all thresholds (Asif)
│   │   ├── climate_profile.py  # Asif
│   │   ├── scenario.py         # Asif (What-If)
│   │   ├── alerts.py           # Asif
│   │   ├── scoring.py          # Shayan
│   │   ├── strategies.py       # Shayan
│   │   └── explain.py          # Abdul Rehman (template explanations, no LLM)
│   ├── ai/                     # client.py (Aman), prompts.py + views (Shayan)
│   ├── api/                    # views.py, serializers.py, urls.py
│   ├── tests/                  # test_api.py (Abdul Rehman)
│   └── data/
│       ├── crops.csv
│       ├── crop_calendars.csv
│       ├── rotation_templates.json
│       ├── text/en.json, ur.json     # alert, explanation and glossary strings
│       └── prepulled/<location_slug>/{smap.csv, ndvi.csv, prism_monthly.csv, cdl_sequence.csv, ssurgo.json, power_cache.json}
└── frontend/
    ├── package.json
    └── src/
        ├── api/client.js
        ├── components/         # Map, InputForm, StrategyCard, WhatIfPanel, AlertList, ChatPanel, charts, Glossary, Disclaimer
        ├── data/glossary.json
        └── App.jsx
```

**Why `engine/` has no Django imports:** Asif and Shayan can build and test it in notebooks and plain `pytest`, and the logic stays easy to explain to judges.

**Why the LLM sits in `ai/`, separate from `engine/`:** every number comes from `engine/`. The LLM only turns those numbers into words. If the LLM is down, `engine/explain.py` template text still works.

---

## 4. Data plan

### 4.1 Data tiers
| Tier | Applies to | Sources |
|---|---|---|
| **Standard** | Any clicked point | NASA POWER + SoilGrids |
| **Featured** | The 2 Pakistan pins + Iowa pin | Standard + SMAP soil moisture + MODIS/VIIRS NDVI (pre-pulled) |
| **US-enhanced** | Iowa pin | Featured + SSURGO soil + CDL crop history + PRISM climate (ground validation) |

The tier is shown in the UI and lowers the confidence label for lower tiers.

### 4.2 Sources
| Source | Gives us | How we get it | Notes |
|---|---|---|---|
| **NASA POWER** (daily, point) | T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, GWETROOT, ALLSKY_SFC_SW_DWN, RH2M | `https://power.larc.nasa.gov/api/temporal/daily/point` with `community=AG`, `latitude`, `longitude`, `start`, `end` (YYYYMMDD), `format=JSON`. Missing = `-999`. | Last 20 complete years (2006–2025). **VERIFY** parameter names and range limits (chunk by year if needed). |
| **SoilGrids** (ISRIC, non-NASA) | clay, sand, silt, soil organic carbon, pH | `https://rest.isric.org/soilgrids/v2.0/properties/query?...` | **VERIFY** unit conversion (`unit_measure` scaling). Slow at times: timeouts + cache. |
| **SMAP** soil moisture | Surface soil-moisture anomalies, dry spells | Earthdata **AppEEARS** point samples (free Earthdata login). **VERIFY** product/version. | Record starts **2015**, so anomalies use ~10 years. Say so in `info_gaps`. Submit at hour 0. |
| **MODIS/VIIRS NDVI** | Greenness, bare periods, seasonal transitions | Same AppEEARS request, or the ORNL DAAC MODIS subset service (**VERIFY**). | Monthly mean per year. |
| **SSURGO** (USDA NRCS) | Iowa soil: texture, OM, drainage, hydrologic group, Kw, water-holding capacity | Soil Data Access or Web Soil Survey, one point. **VERIFY**. | Manual export is fine. |
| **CDL / CropScape** | Actual crops at the Iowa point, ~8–10 years | CropScape tool or service, one pixel. **VERIFY**. | Manual lookup is fine. `cdl_sequence.csv` (year, crop). |
| **PRISM** | Ground-based monthly precip and temperature for Iowa | PRISM point time-series download. **VERIFY**. | POWER-vs-PRISM validation. |
| **FAO GAEZ** | Crop suitability sanity check | Manual lookup, cited in the crop table. | Not an API. |

### 4.3 Harmonization (document in README and slides)
All series are aggregated to **monthly values on a ~0.5° grid cell** (about 55 km) per location. Daily values are used only for counts (heat days, frost days, extreme-rain days, dry spells). Pre-pulled satellite series use the same monthly keys.

### 4.4 Caching and fallback
- **Grid key:** round lat and lon to the nearest 0.5° (`"42.0_-93.5"`). Cache key = `(kind, grid_key)`.
- Live data is stored in Postgres (`LocationCache.payload`, JSONB).
- Pre-pulled files are loaded into Postgres by `python manage.py load_prepulled`.
- **Featured pins:** if a live call fails, serve from cache and show a "using cached data" notice.
- **Non-featured points:** if a live call fails and there is no cache, return a clear error. **Never** substitute another location's data.
- **What-If** never refetches data: it reuses the cached daily series and re-runs the engine (fast).
- **AI responses** are cached by a hash of (prompt type, analysis summary, question, language).
- Warm all caches for the 3 pins before the demo.

### 4.5 Credits
Every source is credited in the README, the slides and the app footer. Non-US-government sources (SoilGrids, PRISM, FAO) have their own data-use terms.

---

## 5. Data model (Django)

```python
# crops/models.py
class Crop(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    name_ur = models.CharField(max_length=80, blank=True)   # Urdu name
    family = models.CharField(max_length=40)          # grass, legume, brassica, malvaceae, ...
    role = models.CharField(max_length=20)            # cash | cover | forage | legume_rotation
    water_need_mm = models.IntegerField()
    drought_tolerance = models.IntegerField()         # 1-5
    heat_tolerance = models.IntegerField()            # 1-5
    frost_tolerance = models.IntegerField()           # 1-5
    n_fixing = models.BooleanField(default=False)
    root_depth = models.CharField(max_length=10)      # shallow | medium | deep
    ground_cover = models.IntegerField()              # 1-5
    residue_om = models.IntegerField()                # 1-5
    erosion_protection = models.IntegerField()        # 1-5
    income_level = models.IntegerField()              # 1-5 (regional placeholder, labeled as such)
    forage_value = models.IntegerField(default=0)     # 0-5
    special_equipment = models.BooleanField(default=False)
    sources = models.TextField(blank=True)
    notes = models.TextField(blank=True)

class CropCalendar(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="calendars")
    zone = models.CharField(max_length=20)            # subtropical | temperate
    season_label = models.CharField(max_length=20)    # main | kharif | rabi | ...
    sow_months = models.JSONField()                   # e.g. [4, 5]
    harvest_months = models.JSONField()               # e.g. [9, 10]
    growth_stages = models.JSONField(default=list)    # see below

class RotationTemplate(models.Model):
    zone = models.CharField(max_length=20)
    key = models.CharField(max_length=20)             # current_default | water_saver | soil_builder
    name = models.CharField(max_length=80)
    description = models.TextField()
    steps = models.JSONField()
```

**Growth stages format** (months after sowing, plus which stage is most sensitive):
```json
[
  {"stage": "establishment", "start": 0, "end": 1},
  {"stage": "vegetative",    "start": 1, "end": 3},
  {"stage": "flowering",     "start": 3, "end": 4, "sensitive": ["heat", "drought"]},
  {"stage": "maturity",      "start": 4, "end": 5}
]
```

```python
# locations/models.py
class Location(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    lat = models.FloatField(); lon = models.FloatField()
    country = models.CharField(max_length=40)
    zone = models.CharField(max_length=20)
    tier = models.CharField(max_length=20)            # featured | us_enhanced
    featured = models.BooleanField(default=True)

class LocationCache(models.Model):
    kind = models.CharField(max_length=20)            # power | soilgrids | smap | ndvi | ssurgo | cdl | prism | ai
    grid_key = models.CharField(max_length=64)
    payload = models.JSONField()
    source_url = models.TextField(blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("kind", "grid_key")
```

### Rotation format (shared by everyone)
```json
{
  "name": "Corn–soybean",
  "cycle_years": 2,
  "steps": [
    {"year": 1, "crop": "corn",    "sow_month": 5, "harvest_month": 10},
    {"year": 2, "crop": "soybean", "sow_month": 5, "harvest_month": 10}
  ]
}
```
A double-cropped year (cotton then wheat) is two steps in the same `year`. A cover crop is a step with a short winter window.

### Zone rule
`zone = "subtropical" if abs(lat) < 35 else "temperate"`. Featured locations set it explicitly. Clicked points use the rule and get a lower confidence label.

### Featured locations
| Slug | Name | Approx. lat, lon | Zone | Tier | Default current rotation |
|---|---|---|---|---|---|
| `sindh-hyderabad` | Sindh (Hyderabad area) | 25.4, 68.4 | subtropical | featured | cotton–wheat (confirm) |
| `punjab-faisalabad` | Punjab (Faisalabad area) | 31.4, 73.1 | subtropical | featured | cotton–wheat or rice–wheat (confirm) |
| `iowa-central` | Central Iowa (Ames) | 42.0, -93.6 | temperate | us_enhanced | corn–soybean (confirm with CDL) |

---

## 6. Strategies

| Strategy | Intent |
|---|---|
| **Current** | Existing rotation (from CDL for Iowa, otherwise the zone default, editable) |
| **Water-saver** | Lower-water and drought-tolerant crops, shorter bare periods |
| **Soil-builder** | Nitrogen-fixing legume, cover crop, deeper-rooted crops |

Strategies 2 and 3 come from `RotationTemplate` rows per zone (Abdul Rehman drafts, Shayan reviews). If constraints exclude a crop, the strategy still shows, with a warning in its risks section.

---

## 7. Climate profile and What-If (contract between Asif and Shayan)

```python
def build_climate_profile(
    daily,          # DataFrame: date, t2m, t2m_max, t2m_min, precip, root_wetness, solar, rh
    lat,
    smap=None,      # DataFrame: date, sm
    ndvi=None,      # DataFrame: date, ndvi
    prism=None,     # DataFrame: year, month, precip_mm, tmean_c, tmax_c, tmin_c
    scenario=None,  # {"rain_pct": 0, "temp_c": 0}
) -> dict:
```

### What-If scenario (`engine/scenario.py`, MUST)
`apply_scenario(daily, scenario) -> daily_copy`, called at the top of `build_climate_profile`:
- `temp_c`: add to `t2m`, `t2m_max`, `t2m_min` (range −2 to +5).
- `rain_pct`: multiply `precip` by `1 + rain_pct/100` (range −50 to +30).
- `root_wetness` and SMAP: shift by the change in monthly water balance, using a simple documented factor in `constants.py` (labeled "simplified").
- Everything downstream (ET0, stress counts, scores, alerts) recomputes automatically.
- The response contains **both** `baseline` and `scenario` profiles so charts can animate between them.

### Output (all keys required; `null` when data is missing)
```json
{
  "years_covered": [2006, 2025],
  "n_years": 20,
  "missing_fraction": 0.01,
  "monthly_climatology": {
    "1": {"t_mean": 2.1, "t_max": 7.0, "t_min": -3.2, "precip_mm": 25.0,
          "root_wetness": 0.61, "et0_mm": 18.0}
  },
  "trends": {"precip_mm_per_decade": 12.0, "t_mean_c_per_decade": 0.4},
  "stress_by_month": {
    "heat_days": {"7": 6.5},
    "frost_days": {"1": 24.0},
    "dry_spell_prob": {"7": 0.35},
    "extreme_rain_days": {"6": 1.2}
  },
  "water_balance_by_month": {"7": {"precip_mm": 110.0, "et0_mm": 150.0, "deficit_mm": 40.0}},
  "soil_moisture_anomaly_by_month": {"7": -0.8},
  "ndvi_by_month": {"1": 0.18},
  "bare_months_observed": [11, 12, 1, 2, 3],
  "frost_free_season": {"median_days": 165, "p10": 150, "p90": 180},
  "year_stress_flags": {"2012": ["drought", "heat"]},
  "uncertainty": {"interannual_cv_precip": 0.22, "smap_years": 10},
  "validation": {"prism": {"precip_corr": 0.93, "precip_bias_pct": -4.0, "tmean_bias_c": 0.3}},
  "scenario_applied": {"rain_pct": 0, "temp_c": 0},
  "data_tier": "us_enhanced"
}
```

### Indicators and default thresholds (all in `engine/constants.py`)
| Indicator | Definition |
|---|---|
| Heat-stress day | `t2m_max > 35 °C` |
| Frost day | `t2m_min <= 0 °C` |
| Extreme-rain day | daily precip above the 95th percentile of wet days (> 1 mm) at that location |
| Dry spell | 10 or more consecutive days with precip < 1 mm |
| ET0 | Hargreaves–Samani: `ET0 = 0.0023 × 0.408 × Ra × (Tmean + 17.8) × sqrt(Tmax − Tmin)` in mm/day, with `Ra` in MJ m⁻² day⁻¹ from latitude and day of year (FAO-56 eq. 21). **The 0.408 converts MJ to mm; without it ET0 is ~2.5× too high.** |
| Water balance | `precip − ET0` per month (deficit when negative) |
| Soil-moisture anomaly | monthly mean SMAP (or `root_wetness` for Standard tier) minus its long-term monthly mean, divided by its standard deviation |
| Bare month | month whose climatological NDVI is below `0.25` |
| Frost-free season | longest frost-free run per year; median, p10, p90 |
| Year stress flags | `drought` if growing-season precip < 20th percentile; `heat` if heat days > 80th percentile |

### Confidence label
- **High**: US-enhanced tier, 15+ years, validation correlation above 0.85.
- **Medium**: Featured tier, 15+ years.
- **Low**: Standard tier, a clicked point outside the pilot zones, lots of missing data, or a What-If scenario beyond ±3 °C / ±30% rain.

---

## 8. Scoring (Shayan)

```python
def score_rotation(rotation, profile, crops, calendars, priorities, constraints, zone) -> dict
```

### Six sub-scores, each 0 to 100, each with an `explain` list
| Sub-score | How it is computed (v1) |
|---|---|
| **water_fit** | Crop `water_need_mm` vs growing-season supply (precip + irrigation factor). Median year and dry year (p10). |
| **climate_risk** | Share of years where heat, frost or a dry spell falls in the crop's **sensitive growth stage**. Score = `100 × (1 − risk)`. |
| **soil_health** | Points for N-fixers, cover crops, deep roots, residue; diversity bonus. |
| **erosion_infiltration** | Bare months weighted by extreme-rain days, adjusted by ground cover, erosion protection and soil texture. |
| **pest_break** | Penalty for the same family in consecutive years; reward for 3+ families. |
| **income** | Mean `income_level`, forage bonus if preferred. Labeled "regional placeholder". |

**Overall** = weighted average; weights from the priority sliders (0 to 5), normalized. The response includes each sub-score's weighted contribution.

**Vulnerable months** (current rotation): months with a crop in the field and high heat days, dry-spell probability > 0.3, negative soil-moisture anomaly, or frost, with reasons and the growth stage affected.

**Bare windows**: months with no crop in the calendar, cross-checked against `ndvi_by_month` for featured locations. A mismatch is an information gap.

---

## 9. Early-warning alerts (Asif, MUST)

`engine/alerts.py`: `build_alerts(profile, rotation, calendars, soil) -> list`

Alerts are **pattern-based risk alerts** from 20 years of history (and the What-If scenario when active). They are **not live forecasts**, and the UI says so.

| Alert | Trigger (per month with a crop in the field) | Moderate | High | Critical |
|---|---|---|---|---|
| Drought | `dry_spell_prob` | ≥ 0.30 | ≥ 0.50 | ≥ 0.70 |
| Water deficit | `deficit_mm` | ≥ 30 | ≥ 60 | ≥ 100 |
| Heat stress | `heat_days` (doubled weight in sensitive stage) | ≥ 3 | ≥ 7 | ≥ 12 |
| Frost | `frost_days` while a frost-sensitive crop is in the field | ≥ 1 | ≥ 3 | ≥ 7 |
| Waterlogging | `extreme_rain_days` with poorly drained or clay-heavy soil | ≥ 1.0 | ≥ 1.5 | ≥ 2.5 |
| Soil drying | `soil_moisture_anomaly` | ≤ −1.0 | ≤ −1.5 | ≤ −2.0 |

Below Moderate = **Low** (shown only in the details list). All thresholds live in `constants.py`.

Each alert:
```json
{"type": "heat", "severity": "high", "month": 7, "crop": "cotton", "stage": "flowering",
 "triggered_by": [{"variable": "heat_days", "value": 8.2, "threshold": 7}],
 "reason": "Cotton flowers in July, when this area averages 8 days above 35 °C.",
 "action": "Consider earlier sowing or a more heat-tolerant variety; check with your extension office.",
 "basis": "historical", "source": "NASA POWER"}
```
`basis` is `historical` or `simulated`. Reason and action text come from `data/text/en.json` / `ur.json` (Abdul Rehman).

---

## 10. AI explanation and assistant (Shayan + Aman, SHOULD)

### Principle
**The engine computes, the AI explains.** The LLM never invents numbers. It receives a trimmed copy of the analysis JSON and must only use those values.

### Grounding rules (in `ai/prompts.py`)
1. Use only facts from the provided data. If something is not in the data, say "we don't have data for that".
2. Label every point as **Observed** (from data), **Estimated cause** (reasoning), or **Prediction / scenario**.
3. Mention the confidence level and data tier.
4. Answer in the requested language. Urdu must be natural, simple farmer language, not a word-for-word translation.
5. **Never** give fertilizer or pesticide product names, doses, or quantities. Point to product labels, soil testing and the local agriculture extension office.
6. Never present a guess as a diagnosis. Recommend an expert when unsure.
7. End with the support-not-replace reminder when giving advice.

### Output format (asked from the LLM as JSON)
```json
{
  "summary": "Short plain-language answer.",
  "points": [
    {"type": "observed", "text": "July has a 35% chance of a 10-day dry spell.", "source": "NASA POWER"},
    {"type": "estimated_cause", "text": "High heat raises evaporation faster than rain refills the soil."},
    {"type": "prediction", "text": "With +3 °C, heat days in July rise from 8 to 14 (simulated)."}
  ],
  "actions": ["..."],
  "needs_expert": ["..."],
  "confidence": "medium"
}
```

### Fallback
If the LLM fails or times out (15 s), return the template text from `engine/explain.py` with `"ai_used": false`. The demo never depends on the LLM.

### Cost and safety
- Server-side only; key in env var; per-IP rate limit (for example 20 requests / 10 min).
- Responses cached (section 4.4).
- Trim the analysis JSON to what the question needs (keep the prompt small).

### Voice (STRETCH, Talha)
- Browser Web Speech API: `SpeechRecognition` with `lang = "ur-PK"` or `"en-US"`, `speechSynthesis` for reading answers aloud.
- **VERIFY in hour 0–1:** Urdu recognition in Chrome, and whether an Urdu TTS voice exists on the demo phone. If not, Urdu stays text-only.

### Photo symptom description (STRETCH, Shayan)
- Upload → LLM vision → **visible symptoms and possible causes only**, labeled "AI interpretation, not a diagnosis".
- Always: "Confirm with an agricultural expert or a lab test." Asks for a clearer photo when unsure.
- No product, dose or chemical advice (rule 5 above). Images are not stored.

---

## 11. API contract

All endpoints are public JSON, no auth. DRF uses `AllowAny` and no session authentication.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health/` | Status + DB check |
| GET | `/api/locations/` | Featured locations (pins) |
| GET | `/api/crops/` | Crop table (with Urdu names) |
| POST | `/api/analyze/` | Main analysis (with optional scenario) |
| POST | `/api/explain/` | AI explanation of one section (SHOULD) |
| POST | `/api/chat/` | Assistant Q&A with history (SHOULD) |

### POST `/api/analyze/` — request
```json
{
  "lat": 42.0,
  "lon": -93.6,
  "current_rotation": null,
  "priorities": {"water": 4, "soil": 5, "income": 3, "erosion": 4, "pest": 2},
  "constraints": {"water_availability": "rainfed", "equipment": "standard", "market_pref": "balanced"},
  "overrides": {"soil_texture": null},
  "scenario": {"rain_pct": 0, "temp_c": 0},
  "lang": "en"
}
```
- `current_rotation: null` → server fills the default.
- `water_availability`: `rainfed | limited_irrigation | irrigated`. `equipment`: `basic | standard | specialized`. `market_pref`: `cash | forage | balanced`. `lang`: `en | ur`.

### Response
```json
{
  "analysis_id": "sha1-of-request",
  "location": {"name": "Central Iowa", "lat": 42.0, "lon": -93.6, "zone": "temperate",
               "featured": true, "data_tier": "us_enhanced", "grid_key": "42.0_-93.5"},
  "data_quality": {
    "confidence": "medium",
    "fallback_used": false,
    "sources": ["NASA POWER", "SoilGrids", "SMAP", "MODIS NDVI", "SSURGO", "CDL", "PRISM"],
    "notes": ["PRISM validation: precipitation correlation 0.93", "SMAP record covers 2015–2025 only"]
  },
  "climate": {
    "baseline": {"monthly": [], "stress_by_month": {}, "water_balance": [], "trends": {}, "year_stress_flags": {}},
    "scenario": null
  },
  "soil": {"texture": "silt loam", "organic_carbon": 1.9, "ph": 6.4, "source": "SSURGO"},
  "bare_windows": {"current": [11, 12, 1, 2, 3, 4]},
  "vulnerable_months": {"current": [{"month": 7, "stage": "flowering", "reasons": ["heat", "dry spell"]}]},
  "alerts": [{"type": "heat", "severity": "high", "month": 7, "crop": "corn", "stage": "flowering",
              "triggered_by": [], "reason": "", "action": "", "basis": "historical", "source": "NASA POWER"}],
  "strategies": [
    {
      "id": "current",
      "name": "Corn–soybean (current)",
      "is_current": true,
      "rotation": {"cycle_years": 2, "steps": []},
      "scores": {"overall": 62, "water_fit": 58, "climate_risk": 66, "soil_health": 48,
                 "erosion_infiltration": 52, "pest_break": 60, "income": 80},
      "baseline_scores": null,
      "contributions": {"water": 11.6, "soil": 12.0},
      "why_suggested": "Baseline: what is farmed today.",
      "evidence": [{"text": "July soil moisture is below normal in 6 of the last 10 years", "source": "SMAP"}],
      "benefits": ["Familiar equipment and strong markets"],
      "info_gaps": ["No field-level soil sampling"],
      "local_review": ["Check tile drainage and local planting dates with an extension agent"]
    }
  ],
  "disclaimer": "This tool highlights patterns and possibilities. It does not replace farmer judgment or local agricultural expertise."
}
```
When `scenario` is non-zero: `climate.scenario` is filled, `scores` are the scenario scores, `baseline_scores` holds the baseline, and alerts carry `"basis": "simulated"`.

### POST `/api/explain/` — request / response
```json
{"section": "water_balance", "analysis": { "...trimmed analyze response..." }, "lang": "ur"}
```
`section`: `climate | water_balance | stress | alerts | strategy:<id> | scenario`. Response: the AI output format in section 10, plus `"ai_used": true|false`.

### POST `/api/chat/` — request / response
```json
{"messages": [{"role": "user", "content": "Should I irrigate in July?"}],
 "analysis": { "...trimmed analyze response..." }, "lang": "en"}
```
The frontend keeps the message history and sends it each time (stateless server, follow-ups work). Response: section 10 format.

**Timeouts and errors:** uncached live fetches can take 10–25 s ("Fetching NASA data…"). What-If re-runs should take under 2 s from cache. Backend timeouts: 20 s data, 15 s LLM. `503` with a clear message when a non-featured point cannot be fetched.

---

## 12. Frontend spec

**One main screen.** Desktop: map and form on the left, results on the right. Phone: stacked, map first. Tabs in results: **Overview · Strategies · What-If · Ask**.

### Components
| Component | Owner | Notes |
|---|---|---|
| `Map` (Leaflet) | Talha | Featured pins, click anywhere, selected-point marker |
| `InputForm` | Talha | Rotation editor, 5 priority sliders, 3 constraint selects, soil override |
| `ResultsLayout`, `StrategyCard` | Talha | 3 cards, score bars, contributions bar, 5 collapsible sections; shows baseline → scenario score change |
| `DataBadge` | Talha | Tier, confidence, sources, "cached data" notice |
| `WhatIfPanel` | Talha | Temperature and rainfall sliders, debounced (500 ms) re-call of `/analyze`, "Reset to baseline", clear "SIMULATED" label |
| `ChatPanel` | Talha | Message list, EN/اردو toggle, RTL for Urdu, "Explain this" entry point, mic button (stretch) |
| `ClimateChart` | Musab | Rain bars + temperature line; baseline vs scenario overlay, animated |
| `RotationTimeline` | Musab | 12-month bar per strategy: in field, growth stage, bare, vulnerable |
| `AlertList` | Musab | Cards with severity (icon + word + color), trigger values, action, "historical/simulated" tag |
| `StressHeatmap` | Musab | Month × year stress flags (SHOULD) |
| `SoilMoistureNdviChart` | Musab | Featured locations only |
| `ValidationPanel` | Musab | POWER vs PRISM, or "ground validation not available here" |
| `AiAnswer` | Musab | Renders `points` with Observed / Estimated cause / Prediction badges |
| `Glossary`, `Disclaimer`, `AboutData` | Musab | Tooltips, support-not-replace banner, satellite-vs-ground explainer |

**Design rules:** plain farmer language; no jargon without a tooltip; color is never the only signal; big tap targets; loading and error states everywhere; Urdu text right-to-left with a readable Urdu font (for example Noto Nastaliq Urdu); every chart labels data as Historical or Simulated.

---

## 13. Deployment (Django on free tiers)

| Service | What | Notes |
|---|---|---|
| **Vercel** | React frontend | Auto-deploy from `main`; `VITE_API_URL` |
| **Render** | Django backend | Free tier sleeps; warm before judging |
| **Neon** | Postgres | Pooled connection string, `sslmode=require` |
| **LLM provider** | AI explanations | Key in Render env only; set a spending limit |

### Django settings essentials
```python
import os, dj_database_url
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DEBUG", "0") == "1"
SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o]

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5-5")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

DATABASES = {"default": dj_database_url.config(conn_max_age=60, ssl_require=not DEBUG)}
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}
```

### Render configuration
- **Build command:** `./build.sh`
- **Start command:** `gunicorn config.wsgi:application --workers 2 --timeout 60`
- **Env vars:** `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `DEBUG=0`, `PYTHON_VERSION`, `LLM_API_KEY`, `LLM_MODEL`

`backend/build.sh`:
```bash
#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_crops
python manage.py load_prepulled
```
All seed commands must be **idempotent**.

### Local development
`docker-compose up -d` runs Postgres. Copy `.env.example` to `.env` (never commit `.env`). The same compose file can run the full stack as a fallback demo.

### Deployment checklist
- [ ] Static files load in the admin.
- [ ] `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` match the real URLs.
- [ ] `DEBUG=0` in production.
- [ ] All NASA, SoilGrids and LLM calls happen **server-side only**.
- [ ] LLM spending limit set; app works with `LLM_API_KEY` empty (template fallback).
- [ ] `/api/health/` returns OK with a DB check.
- [ ] Render warmed 10 minutes before the demo.

---

## 14. 24-hour schedule

| Hours | Milestone | Key work |
|---|---|---|
| **Pre-clock** | Accounts and skeleton | Earthdata login (Aman), repo + invites, Vercel/Render/Neon + LLM key (Shayan), crop research (Abdul Rehman) |
| **0–1** | **M1: Contract and hello-world** | API contract + mock JSON (incl. alerts, scenario). Hello-world deployed. AppEEARS submitted. Urdu voice check (Talha). |
| **1–8** | **M2: Vertical slice** | Iowa pin, real POWER data, 3 strategies end to end, ugly UI. Crop table v1 in. |
| **8–14** | **M3: MUST complete** | All 3 pins, tiers, constraints, charts, timeline, **What-If**, **alerts**, glossary |
| **12–17** | **M4: AI layer (SHOULD)** | `/explain`, `/chat`, Urdu text, AI answer UI |
| **15–20** | **M5: Polish and harden** | Mobile, fallbacks, errors, caching, Iowa ground data, remaining SHOULD, STRETCH only if all green |
| **20** | **FEATURE FREEZE** | Bug fixes only |
| **20–22** | **M6: Submission build** | Final deploy, README, video, slides, demo run-throughs. **Submit by hour 22** |
| **22–24** | Buffer | Fix surprises, resubmit if needed, rest |

**Full-team check-ins (10 min):** hours 4, 8, 12, 16, 20.
**Backend check-ins (5 min):** hours 3, 6, 10, 14, 18.
**Sleep:** two shifts; nobody works more than ~14 hours straight.

---

## 15. Per-member instructions

### 15.1 Shayan — Tech lead, API, scoring, AI endpoints (backend)

| Hours | Task |
|---|---|
| 0–1 | Repo, protect `main`, `docs/API_CONTRACT.md` + `docs/mock_analyze.json` (include alerts and scenario fields). Django skeleton + `/api/health/`. Neon/Render/Vercel accounts; LLM key. |
| 1–3 | Models (section 5), admin, migrations. |
| 3–5 | `scoring.py` v1 against Asif's `sample_profile.json`. |
| 4–6 | `strategies.py` (3 strategies, constraints as risk warnings). |
| 6–8 | **Integration #1:** `/api/analyze/` end to end for Iowa. **M2.** |
| 8–12 | Scoring v2 (weights, contributions, growth-stage risk, vulnerable months, bare windows, confidence). Wire `scenario` → baseline + scenario profiles and scores. Wire Asif's alerts. Plug in Abdul Rehman's `explain.py`. |
| 12–16 | `ai/prompts.py` (grounding rules, section 10), `/api/explain/`, `/api/chat/` using Aman's `ai/client.py`. Trim analysis JSON per section. |
| 15–18 | Robustness: `503`s, fallbacks, rate limits on AI endpoints. Iowa tier integration. |
| 18–20 | **Integration #2** on the deployed site. |
| 20–24 | Freeze, merge fixes only, warm services, demo run-throughs. |
| Stretch | Photo symptom description endpoint (strict rules in section 10). |

**Rules:** don't rewrite others' code without agreeing first; review PRs in batches; contract changes go to `docs/API_CONTRACT.md` and the group chat first.

### 15.2 Asif — Climate engine, What-If, alerts (backend)

| Hours | Task |
|---|---|
| 0–1 | `engine/tests/sample_profile.json` (hand-made, realistic Iowa numbers) + `constants.py`. |
| 1–3 | Notebook: monthly climatology, **ET0 with ×0.408**, water balance. |
| 3–6 | Stress counts, trends → `build_climate_profile()` v1. **Hand to Shayan by hour 6.** |
| 6–8 | Fix shape mismatches with Shayan. |
| 8–10 | `engine/scenario.py` (`apply_scenario`), baseline + scenario output. |
| 10–13 | Anomalies, NDVI by month, bare months, frost-free season, stress years, uncertainty. |
| 12–15 | `engine/alerts.py` (section 9 thresholds, growth-stage aware). |
| 14–16 | POWER vs PRISM validation. |
| 16–18 | `pytest`: synthetic heat/frost data, missing data, scenario shifts change counts in the right direction. |
| 18–20 | Check every number in evidence, alerts and AI test answers against the profile. |
| 20–22 | Methods text for slides (thresholds, harmonization, scenario method, uncertainty). |
| Stretch | Soil-moisture slider; two stress-detection methods comparison. |

**Rules:** no Django imports or network calls in `engine/`; every threshold in `constants.py`; missing data returns `null`, never crashes.

### 15.3 Aman — Data sources, cache, LLM client (backend)

| Hours | Task |
|---|---|
| Pre-clock / 0 | Earthdata login. **Submit AppEEARS requests first** (SMAP 2015–2025, NDVI 2006–2025, 3 pins). Commit `engine/tests/sample_power_iowa.csv`. |
| 1–3 | `power.py`: `fetch_power_daily()` (20 s timeout, 2 retries, year-by-year fallback, `-999` → NaN, renamed columns incl. `rh`). |
| 2–4 | `cache.py`: `get_or_fetch(kind, lat, lon, fetch_fn)` with the 0.5° grid key. |
| 4–6 | `soilgrids.py` (unit conversion, texture class, `None` on failure). |
| 6–8 | Fix fetcher issues during Integration #1. |
| 8–12 | AppEEARS results → `smap.csv`, `ndvi.csv` for all 3 pins + loader functions for `load_prepulled`. |
| 12–14 | Pre-warm caches; commit `power_cache.json` snapshots for offline fallback. |
| 12–15 | `ai/client.py`: one function `ask_llm(system, messages, json_schema, timeout=15) -> dict | None`, response cache in `LocationCache(kind="ai")`, returns `None` on any failure. |
| 15–18 | Error types, logging, timing of uncached fetches and LLM calls. |
| 18–20 | Test 3 random clicked points and the What-If path on the deployed site. |
| 20–22 | Data credits section of README + `prepulled/README.md`. |
| Stretch | SRTM slope proxy. |

**Rules:** small documented functions with exact output columns; no secrets in code; everything works from cache when the internet is bad.

### 15.4 Abdul Rehman — Knowledge base, ground data, seeding, explanations, tests (backend)

| Hours | Task |
|---|---|
| 0–2 | `crops.csv`: 12–15 crops with a **source per row** (FAO-56, FAO Paper 33, GAEZ, extension guides) and Urdu names. Iowa: corn, soybean, oats, winter wheat, alfalfa, cereal rye, red clover. Pakistan: wheat, cotton, rice, maize, chickpea, mungbean, berseem, mustard, sorghum. Share slugs with Talha by **hour 2**. |
| 2–4 | `crop_calendars.csv` (subtropical kharif/rabi + temperate) **with growth stages and sensitive stages**; `rotation_templates.json` (current_default, water_saver, soil_builder per zone), reviewed with Shayan. |
| 4–7 | Iowa ground data: PRISM `prism_monthly.csv`, CDL `cdl_sequence.csv`, SSURGO `ssurgo.json` (manual downloads fine). Document source + date in `prepulled/README.md`. If behind at hour 6, Asif takes SSURGO. |
| 7–9 | `seed_crops` (idempotent) + `/api/locations/` + `/api/crops/`. |
| 9–13 | `engine/explain.py`: `build_explanations(strategy, scores, profile, tier, lang) -> {why_suggested, evidence[], benefits[], info_gaps[], local_review[]}`. Template sentences for N-fixers, cover crops, deep roots, drought tolerance; standard local-review items; info-gap phrases per tier. |
| 12–15 | `data/text/en.json` + `ur.json`: alert reasons and actions, explanation templates, glossary in Urdu (natural, simple language). `load_prepulled` command (SMAP, NDVI, PRISM, CDL, SSURGO). |
| 15–18 | `tests/test_api.py`: request validation, all 3 pins, scenario changes scores, bad point → `503`, response matches contract, AI endpoints fall back when the key is empty. |
| 18–20 | Run the test suite against production; log bugs as GitHub issues. Test Urdu AI answers for quality with Shayan. |
| 20–22 | README "Backend, data & methods" section; help with the demo. |
| Stretch | NASS QuickStats yield context for Iowa. |

**Rules:** every crop number has a source or an "approximate" flag; plain language only; Urdu written as a farmer would speak, not translated word for word.

### 15.5 Talha — Frontend lead

| Hours | Task |
|---|---|
| 0–1 | React + Vite scaffold, `client.js` (`VITE_API_URL`), load `mock_analyze.json`. **Check Urdu speech recognition + TTS on Chrome and the demo phone.** |
| 1–3 | `Map`: 3 pins + click-anywhere. |
| 2–6 | `InputForm`. |
| 4–8 | `ResultsLayout`, `StrategyCard`, `DataBadge`, loading and `503` states. |
| 8 | Switch to the real `/api/analyze/`. |
| 8–12 | `WhatIfPanel` (sliders, debounce, reset, SIMULATED label), baseline → scenario score deltas on cards. Place Musab's charts. |
| 12–16 | `ChatPanel` (EN/اردو, RTL, history sent each request), "Explain this" buttons wired to `/api/explain/`. |
| 14–18 | Mobile layout, state bugs (clear old results, block double-clicks, cancel stale What-If requests). |
| 18–20 | Accessibility pass, real-phone test, production build. |
| Stretch | Mic button + read-aloud (Web Speech API). |

**Rules:** build against the mock first; never block on the backend.

### 15.6 Musab — Charts, alerts UI, polish and story

| Hours | Task |
|---|---|
| 0–1 | recharts setup, components folder, start `glossary.json` (14 terms, 2 farmer-friendly sentences each, EN + UR from Abdul Rehman later). |
| 1–4 | `ClimateChart` from the mock, with a baseline-vs-scenario overlay and animated transitions. |
| 2–6 | `RotationTimeline` (in field, growth stage, bare, vulnerable). |
| 4–8 | `Glossary` tooltip (`<Term id="ndvi">`), `Disclaimer` banner. |
| 8 | Switch to the real API. |
| 8–12 | `AlertList` (severity icon + word + color, triggers, action, historical/simulated tag), `SoilMoistureNdviChart`. |
| 12–16 | `AiAnswer` (Observed / Estimated cause / Prediction badges), `ValidationPanel`, `AboutData`, `StressHeatmap`. |
| 16–20 | QA on phone and laptop: 3 pins, 3 random points, What-If extremes, Urdu chat. Check every number against the API. |
| 20–22 | README, slides, demo video (backend team writes its sections). |

**Cut order if behind:** `StressHeatmap` → `SoilMoistureNdviChart` → `AboutData`. Never cut: map, form, cards, timeline, What-If, alerts, disclaimer.

### Demo script (about 4 minutes)
1. The problem: shifting climate, water stress, soil decline, hard rotation choices.
2. Click the Iowa pin; current corn–soybean rotation from CDL.
3. Alerts and vulnerable months, with what NASA data shows (POWER, SMAP, NDVI) and glossary tooltips.
4. Compare the three strategies; open one card: why, evidence, benefits, gaps, local review.
5. **What-If:** +3 °C and −30% rain. Charts animate, alerts escalate, rankings change.
6. **"Explain this"** on the water-balance chart: observed vs estimated cause vs prediction.
7. Switch to a Pakistan pin, ask the assistant in Urdu: "بارش کم ہو تو میری گندم پر کیا اثر ہوگا؟"
8. Tier, confidence, and POWER-vs-PRISM validation (satellite vs ground).
9. Limitations, safety choices (no dosage advice), future work. Close with "supports, does not replace, farmer judgment".

---

## 16. Team workflow rules

- **Branches:** `feat/<name>-<thing>`; one small PR per task.
- **Shayan merges to `main`**; every PR needs a quick 👍 from one other member of the same team.
- **Backend merge order on day 1:** skeleton + contracts → `power.py` / `cache.py` → `seed_crops` → climate profile v1 → `/analyze` → scenario → alerts → AI.
- **`main` is always deployable** and passes `python manage.py check` + `pytest`. Broken `main` is everyone's top priority.
- **Pull `main`** before each new task. Announce changes to shared files (`requirements.txt`, `constants.py`, the contract) in chat first.
- **The frontend–backend interface is `docs/mock_analyze.json` + the contract.** Shayan updates the mock first whenever the shape changes.
- **No secrets in the repo.** Commit `.env.example` only.
- **Blockers:** post immediately; never sit stuck for more than 30 minutes.
- **Definition of done:** merged, works on the deployed site, no console errors.
- **After hour 20:** fixes only.

---

## 17. Final checklists

### Backend done
- [ ] `/analyze` works for 3 pins in under 5 s from cache; What-If re-runs in under 2 s.
- [ ] Clear `503` for unreachable points.
- [ ] Every strategy has 6 scores, contributions, and the 5 explanation parts.
- [ ] Alerts have severity, triggers, reason, action and basis.
- [ ] AI endpoints answer only from data, label point types, and fall back to templates when the LLM fails.
- [ ] `pytest` passes (engine + API).
- [ ] `build.sh` rebuilds a fresh database with one command.

### Demo readiness (hour 20–22)
- [ ] Deployed URL works on desktop and a real phone.
- [ ] 3 random clicked points work or fail clearly.
- [ ] Urdu chat tested on the demo device.
- [ ] Render and Neon warmed; local `docker-compose` fallback tested once.
- [ ] Demo video recorded as a backup.

### Submission
- [ ] Read the official participant guide and FAQ: submission requirements, judging criteria, and rules on AI tools, data and code.
- [ ] Public repo with a clear README.
- [ ] Deployed link, slides, and video as required.
- [ ] All data sources and the AI provider credited.
- [ ] Submitted by **hour 22**.

---

## 18. Risks and fallbacks

| Risk | Fallback |
|---|---|
| AppEEARS slow or fails | ORNL MODIS subset for NDVI; POWER root wetness replaces SMAP, noted in data notes |
| SSURGO, CDL, PRISM endpoints fail | Manual downloads for the single Iowa point; drop to Future work after 45 minutes |
| POWER or SoilGrids down during demo | Cached snapshots for the 3 pins in the repo |
| LLM down, slow, or out of credits | Template explanations from `engine/explain.py`; chat shows "AI unavailable, here is the summary" |
| LLM gives an unsafe or wrong answer | Grounding rules + JSON output + no-dosage rule; test 10 tricky questions (EN + UR) before freeze |
| Urdu voice unsupported on the demo device | Urdu text only; voice in English or skipped |
| Render sleeps / Neon pauses | Warm before judging; `docker-compose` local fallback |
| Crop calendars wrong for Sindh or Punjab | Label as approximate; list in `local_review` |
| Schedule slips | Cut STRETCH, then SHOULD (AI last of SHOULD to cut, since it is a strong demo point). Never cut MUST or the disclaimer |
| Integration trouble | Mock JSON and sample profile keep everyone unblocked; integrate at hours 6–8 and 18–20 |

---

## 19. Standard limitation and disclaimer text

> FieldShift Planner highlights patterns and possibilities from NASA Earth observations and public soil and climate data. It does not replace farmer judgment or local agricultural expertise. Satellite and reanalysis data are coarse compared with a single field and can differ from what is measured on the ground. Alerts are based on historical patterns and simulations, not live forecasts. AI explanations are generated from our data and may contain mistakes. Crop calendars, water needs, and market values are simplified regional estimates. The app does not give fertilizer or pesticide doses: follow product labels, soil tests and your local agriculture extension office. Please review any rotation idea with local farmers, extension services, or agronomists before acting on it.

Urdu version: Abdul Rehman writes it in `data/text/ur.json`.

---

## 20. Data credits (keep updated)

NASA POWER · NASA SMAP · NASA MODIS/VIIRS (via Earthdata AppEEARS or ORNL DAAC) · ISRIC SoilGrids · USDA NRCS SSURGO / Web Soil Survey · USDA NASS Cropland Data Layer · PRISM Climate Group (Oregon State University) · FAO GAEZ and FAO crop water guidance · LLM provider used for explanations. Note the data-use terms of each non-NASA source in the README.
