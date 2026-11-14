# Field Shift Planner — Team Plan (24-hour build)

NASA Space Apps Challenge 2026 · Challenge: **Field Shift: Adapting Farms with NASA Data**
Working name: **FieldShift Planner** (rename freely)

> Rule of this doc: **a working, good project, not a complex one.** If something is not in the MUST list, it does not get built until every MUST item works end to end.
> Items marked **VERIFY** depend on external APIs or product names that change. Check them in the first hour and fall back to the manual option listed.

---

## 0. Team and roles at a glance

| Person | Role | Owns |
|---|---|---|
| **Shayan** | Tech lead + backend | API contract, Django project, models, scoring engine, `/analyze` endpoint, deployment, integration |
| **Asif** | ML / analysis | `engine/climate_profile.py`: indicators, stress detection, bare windows, uncertainty, POWER-vs-PRISM validation |
| **Aman** | Data engineer (Python) | NASA POWER + SoilGrids clients, cache layer, SMAP/NDVI pre-pull, `load_prepulled` command |
| **Abdur** | Data + frontend | Iowa ground-data pre-pulls (SSURGO, CDL, PRISM) first, then all charts, timeline, heatmap |
| **Talha** | Frontend lead (React) | Map, input form, results layout, strategy cards, API integration |
| **Musab** | Domain content + UI polish | Crop table, rotation templates, glossary and explanation copy, responsive QA, README, demo, slides, video |

Everyone: read sections 1 to 4, then your own section in 13.

---

## 1. What we are building

**One-liner:** a web app where a farmer picks a spot on a map, tells us their current rotation and priorities, and sees three rotation strategies compared side by side with NASA-based evidence, risks, and the limits of what we know.

### User flow
1. The map shows 3 featured pins (2 in Pakistan, 1 in Iowa). The farmer clicks a pin, **or clicks any other point** on the map.
2. The farmer sets: current rotation (pre-filled), priorities (water, soil health, income, erosion, pest control), and constraints (water availability, equipment, market preference).
3. The farmer presses **Analyze**.
4. The app shows:
   - A data-tier and confidence badge.
   - **Climate and stress picture** for the location.
   - **Bare-field months** and **vulnerable months** for the current rotation.
   - **Three strategies** compared: *Current*, *Water-saver*, *Soil-builder*. Each has a score and these five parts: **why suggested, evidence, benefits, information gaps, risks that need local review**.
   - A reminder that the tool supports farmer judgment and does not replace local expertise.
5. Glossary tooltips explain ET, NDVI, soil-moisture anomaly, frost risk, and water balance.

### What judges should take away
- Real NASA data (POWER, SMAP, MODIS/VIIRS NDVI) drives the results.
- Satellite data is compared with ground data (PRISM, SSURGO, CDL) where we have it, and we say so honestly where we don't.
- Every score is explainable.
- We state uncertainty and where local experts are needed.

---

## 2. Scope

### MUST (build first)
- Map with 3 featured pins and click-anywhere analysis.
- Live NASA POWER + SoilGrids for any point, cached in Postgres.
- SMAP soil moisture and MODIS/VIIRS NDVI, pre-pulled for the 3 featured locations.
- Climate profile with indicators (section 7).
- Crop table (12 to 15 crops) with two calendar zones (subtropical, temperate).
- Three strategies per location, scored on 6 sub-scores with explanations.
- Each strategy shows the 5 required parts.
- Bare-field and vulnerable-month view for the current rotation.
- Data tier + confidence label + disclaimer.
- Glossary tooltips.
- Deployed on free tiers, with cached fallback for featured locations.

### SHOULD (after MUST works)
- Iowa ground data: SSURGO soil, CDL crop history (the existing rotation comes from data), PRISM climate and POWER-vs-PRISM validation.
- Farmer overrides (soil texture, planting dates).
- Constraint filters (water, equipment, market).
- Month-by-year stress heatmap.
- FAO GAEZ cross-check of crop suitability, cited in the crop table.
- About-the-data panel (satellite vs ground).

### STRETCH (only if time)
- Scenario sliders (rain %, temperature °C).
- SRTM slope proxy for erosion.
- Two stress-detection methods compared on a methods slide.
- NASS QuickStats yield context for Iowa.
- IMERG comparison layer.
- Urdu UI toggle.

### FUTURE WORK (slide only, do not build)
ECOSTRESS, Landsat/Sentinel-2 field-level mapping, GRACE groundwater trends, GEDI, field-zone vulnerability maps, user accounts, saved scenarios, native mobile app.

---

## 3. Architecture and stack

```
 React (Vite) on Vercel  ──HTTPS──▶  Django + DRF on Render (Gunicorn)  ──▶  Postgres on Neon
                                         │
                                         ├─ datasources/ (POWER, SoilGrids live, cached)
                                         ├─ data/prepulled/ (SMAP, NDVI, SSURGO, CDL, PRISM files)
                                         └─ engine/ (pure Python: climate profile + scoring)
```

- **Backend:** Python, Django, Django REST Framework, `requests`, `pandas`, `numpy`, `dj-database-url`, `whitenoise`, `django-cors-headers`, `gunicorn`, `psycopg[binary]`.
- **Frontend:** React + Vite, `react-leaflet` (map), `recharts` (charts). Plain CSS or Tailwind, team's choice.
- **Database:** Postgres (Neon free tier). Seeded from files in the repo, so it can be rebuilt with one command.
- **No** Celery, no auth, no user accounts, no microservices, no native mobile app.

### Repo layout (monorepo)
```
field-shift/
├── README.md
├── docker-compose.yml          # local Postgres (+ optional full stack)
├── .env.example
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── build.sh
│   ├── Dockerfile
│   ├── config/                 # settings.py, urls.py, wsgi.py
│   ├── crops/                  # Crop, CropCalendar, RotationTemplate models + admin + seed_crops
│   ├── locations/              # Location, LocationCache models + admin
│   ├── datasources/            # power.py, soilgrids.py, cache.py, loaders (Aman, Abdur)
│   ├── engine/                 # PURE PYTHON, no Django imports
│   │   ├── constants.py        # thresholds (tunable in one place)
│   │   ├── climate_profile.py  # Asif
│   │   ├── scoring.py          # Shayan
│   │   └── strategies.py       # Shayan
│   ├── api/                    # views.py, serializers.py, urls.py
│   └── data/
│       ├── crops.csv
│       ├── crop_calendars.csv
│       ├── rotation_templates.json
│       └── prepulled/<location_slug>/{smap.csv, ndvi.csv, prism_monthly.csv, cdl_sequence.csv, ssurgo.json}
└── frontend/
    ├── package.json
    └── src/
        ├── api/client.js
        ├── components/         # Map, InputForm, StrategyCard, charts, Glossary, Disclaimer
        ├── data/glossary.json
        └── App.jsx
```

**Why `engine/` has no Django imports:** Asif and Shayan can build and test it in notebooks and plain `pytest` without Django knowledge, and the logic stays easy to explain to judges.

---

## 4. Data plan

### 4.1 Data tiers
| Tier | Applies to | Sources |
|---|---|---|
| **Standard** | Any clicked point | NASA POWER + SoilGrids |
| **Featured** | The 2 Pakistan pins + Iowa pin | Standard + SMAP soil moisture + MODIS/VIIRS NDVI (pre-pulled) |
| **US-enhanced** | Iowa pin | Featured + SSURGO soil + CDL crop history + PRISM climate (ground validation) |

The tier is shown in the UI and lowers the confidence label for lower tiers. This is how we honestly show "where information gaps exist".

### 4.2 Sources
| Source | Gives us | How we get it | Notes |
|---|---|---|---|
| **NASA POWER** (daily, point) | T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, GWETROOT (root-zone wetness), ALLSKY_SFC_SW_DWN | `https://power.larc.nasa.gov/api/temporal/daily/point` with `community=AG`, `latitude`, `longitude`, `start`, `end` (YYYYMMDD), `format=JSON`. Missing = `-999`. | Last 20 complete years (2006–2025). **VERIFY** parameter names and date-range limits (chunk by year if needed). |
| **SoilGrids** (ISRIC, non-NASA) | clay, sand, silt, soil organic carbon, pH | `https://rest.isric.org/soilgrids/v2.0/properties/query?lon=..&lat=..&property=clay&...&depth=0-5cm&value=mean` | **VERIFY**: values need unit conversion (response has a scaling factor in `unit_measure`). Can be slow, so use timeouts and cache. |
| **SMAP** soil moisture | Surface soil moisture anomalies, dry spells | Pre-pull for the 3 pins via **Earthdata AppEEARS point samples** (needs a free Earthdata login). **VERIFY** product and version names. | Submit the request in hour 0, because processing is queued. |
| **MODIS/VIIRS NDVI** | Vegetation greenness, bare periods, seasonal transitions | Same AppEEARS request, or the ORNL DAAC MODIS subset web service (**VERIFY**). | Convert to monthly mean per year. |
| **SSURGO** (USDA NRCS) | Iowa soil: texture, organic matter, drainage, hydrologic group, erosion factors | Soil Data Access web service or Web Soil Survey, one point. **VERIFY**. | Manual Web Soil Survey export for 1 to 2 points is acceptable. |
| **CDL / CropScape** (USDA NASS) | Actual crops for the Iowa point, last ~8–10 years | CropScape web tool or service for one pixel. **VERIFY**. | Manual lookup is fine. Save as `cdl_sequence.csv` (year, crop). |
| **PRISM** (Oregon State) | Ground-based monthly precip and temperature for Iowa | PRISM point time-series download. **VERIFY**. | Used for POWER-vs-PRISM validation. |
| **FAO GAEZ** | Crop suitability sanity check | Manual lookup by Musab, cited in the crop table. | Not an API. |

### 4.3 Harmonization (document this in the README and slides)
All series are aggregated to **monthly values on a ~0.5° grid cell** per location (POWER's native resolution is coarse, so this is honest). Daily values are used only to compute counts (heat days, frost days, extreme-rain days, dry spells). Pre-pulled satellite series are aggregated to the same monthly keys.

### 4.4 Caching and fallback
- **Grid key:** round lat and lon to the nearest 0.5° (`"41.5_-93.5"`). Cache key = `(kind, grid_key)`.
- Live data (POWER, SoilGrids) is stored in Postgres (`LocationCache.payload`, JSONB).
- Pre-pulled files in `backend/data/prepulled/<slug>/` are loaded into Postgres by `python manage.py load_prepulled`.
- **Featured pins:** if a live call fails, serve from cache and show a "using cached data" notice.
- **Non-featured points:** if a live call fails and there is no cache, return a clear error. **Never** silently substitute another location's data.
- Warm the cache for all 3 pins before the demo.

### 4.4 Credits
Every source above is credited in the README, the slides, and the app footer. Note that non-US-government sources (SoilGrids, PRISM, FAO) have their own data-use terms.

---

## 5. Data model (Django)

```python
# crops/models.py
class Crop(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    family = models.CharField(max_length=40)          # grass, legume, brassica, malvaceae, ...
    role = models.CharField(max_length=20)            # cash | cover | forage | legume_rotation
    water_need_mm = models.IntegerField()             # seasonal crop water need
    drought_tolerance = models.IntegerField()         # 1-5
    heat_tolerance = models.IntegerField()            # 1-5
    frost_tolerance = models.IntegerField()           # 1-5
    n_fixing = models.BooleanField(default=False)
    root_depth = models.CharField(max_length=10)      # shallow | medium | deep
    ground_cover = models.IntegerField()              # 1-5 (soil protection during season)
    residue_om = models.IntegerField()                # 1-5 (organic matter contribution)
    erosion_protection = models.IntegerField()        # 1-5
    income_level = models.IntegerField()              # 1-5 (regional placeholder, labeled as such)
    forage_value = models.IntegerField(default=0)     # 0-5
    special_equipment = models.BooleanField(default=False)
    sources = models.TextField(blank=True)            # FAO / GAEZ / extension references
    notes = models.TextField(blank=True)

class CropCalendar(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="calendars")
    zone = models.CharField(max_length=20)            # subtropical | temperate
    season_label = models.CharField(max_length=20)    # main | kharif | rabi | ...
    sow_months = models.JSONField()                   # e.g. [4, 5]
    harvest_months = models.JSONField()               # e.g. [9, 10]

class RotationTemplate(models.Model):
    zone = models.CharField(max_length=20)
    key = models.CharField(max_length=20)             # current_default | water_saver | soil_builder
    name = models.CharField(max_length=80)
    description = models.TextField()
    steps = models.JSONField()                        # see rotation format below
```
```python
# locations/models.py
class Location(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    lat = models.FloatField(); lon = models.FloatField()
    country = models.CharField(max_length=40)
    zone = models.CharField(max_length=20)            # subtropical | temperate
    tier = models.CharField(max_length=20)            # featured | us_enhanced
    featured = models.BooleanField(default=True)

class LocationCache(models.Model):
    kind = models.CharField(max_length=20)            # power | soilgrids | smap | ndvi | ssurgo | cdl | prism
    grid_key = models.CharField(max_length=30)
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
A double-cropped year (Pakistan, for example cotton then wheat) is two steps in the same `year` with different months. A cover crop is a step with a short winter window.

### Zone rule
`zone = "subtropical" if abs(lat) < 35 else "temperate"`. This is crude, so featured locations set it explicitly in the admin. Clicked points use the rule and get a lower confidence label.

### Featured locations (starting set; Musab and Shayan confirm local rotations)
| Slug | Name | Approx. lat, lon | Zone | Tier | Default current rotation |
|---|---|---|---|---|---|
| `sindh-hyderabad` | Sindh (Hyderabad area) | 25.4, 68.4 | subtropical | featured | cotton–wheat (confirm) |
| `punjab-faisalabad` | Punjab (Faisalabad area) | 31.4, 73.1 | subtropical | featured | cotton–wheat or rice–wheat (confirm) |
| `iowa-central` | Central Iowa (e.g. Ames) | 42.0, -93.6 | temperate | us_enhanced | corn–soybean (confirm with CDL) |

Adding a featured location later takes four steps: add a `Location` row in the admin, run the pre-pull for it, run `load_prepulled`, and it appears as a pin.

---

## 6. Strategies

Every location gets three strategies:

| Strategy | Intent |
|---|---|
| **Current** | The farmer's existing rotation (from CDL for Iowa, otherwise the zone default, editable) |
| **Water-saver** | Swaps in lower-water and drought-tolerant crops, and shortens bare periods |
| **Soil-builder** | Adds a nitrogen-fixing legume, a cover crop, and deeper-rooted crops for organic matter and infiltration |

Strategies 2 and 3 come from `RotationTemplate` rows per zone (Musab drafts, Shayan reviews). If the farmer's constraints exclude a crop in a template (for example, equipment), the strategy still shows, with a warning in its risks section.

---

## 7. Climate profile (the contract between Asif and Shayan)

`engine/climate_profile.py` exposes:

```python
def build_climate_profile(
    daily,          # pandas DataFrame: date, t2m, t2m_max, t2m_min, precip, root_wetness, solar
    lat,            # float, used for ET0 (extraterrestrial radiation)
    smap=None,      # DataFrame: date, sm   (featured locations)
    ndvi=None,      # DataFrame: date, ndvi (featured locations)
    prism=None,     # DataFrame: year, month, precip_mm, tmean_c, tmax_c, tmin_c (Iowa)
    scenario=None,  # {"rain_pct": 0, "temp_c": 0}  (stretch, apply before computing)
) -> dict:
```

### Output (all keys required; use `null` when data is missing)
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
  "uncertainty": {"interannual_cv_precip": 0.22},
  "validation": {"prism": {"precip_corr": 0.93, "precip_bias_pct": -4.0, "tmean_bias_c": 0.3}},
  "data_tier": "us_enhanced"
}
```

### Indicators and default thresholds (all in `engine/constants.py`, tunable)
| Indicator | Definition |
|---|---|
| Heat-stress day | `t2m_max > 35 °C` |
| Frost day | `t2m_min <= 0 °C` |
| Extreme-rain day | daily precip above the 95th percentile of wet days (> 1 mm) at that location |
| Dry spell | 10 or more consecutive days with precip < 1 mm |
| ET0 (reference evapotranspiration) | Hargreaves–Samani: `0.0023 × Ra × (Tmean + 17.8) × sqrt(Tmax − Tmin)`, with `Ra` computed from latitude and day of year |
| Water balance | `precip − ET0` per month (deficit when negative) |
| Soil-moisture anomaly | monthly mean SMAP (or `root_wetness` for Standard tier) minus its long-term monthly mean, divided by its standard deviation |
| NDVI anomaly / bare month | month whose climatological NDVI is below `0.25` (tunable) is "observed bare/low vegetation" |
| Frost-free season | longest run of days without frost per year, then median, p10, p90 |
| Year stress flags | a year is flagged `drought` if its growing-season precip is below the 20th percentile, `heat` if heat days exceed the 80th percentile |

### Confidence label (computed by Shayan from the profile)
- **High**: US-enhanced tier, 15+ years, validation correlation above 0.85.
- **Medium**: Featured tier, 15+ years.
- **Low**: Standard tier, a clicked point outside the pilot zones, or lots of missing data.

---

## 8. Scoring (Shayan)

`engine/scoring.py` exposes:

```python
def score_rotation(rotation, profile, crops, calendars, priorities, constraints, zone) -> dict
```

### Six sub-scores, each 0 to 100, each with an `explain` list of plain-language reasons
| Sub-score | How it is computed (v1, simple and transparent) |
|---|---|
| **water_fit** | For each crop step, compare seasonal `water_need_mm` against growing-season supply (precip, plus an irrigation factor from the farmer's water availability). Score from the median year and the dry-year (p10) result. |
| **climate_risk** | Share of historical years where heat, frost, or a dry spell fall inside the crop's sensitive window (use crop tolerances). Score = `100 × (1 − risk)`. |
| **soil_health** | Points for nitrogen fixers, cover crops, deep roots, and residue/organic-matter contribution; crop diversity bonus. |
| **erosion_infiltration** | Bare months weighted by extreme-rain days, then adjusted by crop ground cover, erosion protection, and soil texture (SoilGrids, or SSURGO for Iowa). |
| **pest_break** | Penalty for the same crop family in consecutive years; reward for 3 or more families in the cycle. |
| **income** | Mean crop `income_level`, with a forage bonus if the farmer prefers forage. Labeled "regional placeholder". |

**Overall** = weighted average of the six sub-scores. Weights come from the farmer's priority sliders (0 to 5), normalized to sum to 1. The response includes each sub-score's weighted contribution so the UI can show *why* a strategy ranks where it does.

**Vulnerable months** (current rotation): months where a crop is in the field and the profile shows high heat days, a dry-spell probability above 0.3, a negative soil-moisture anomaly, or frost, with the reasons listed.

**Bare windows**: months with no crop in the calendar. For featured locations, cross-check them against `ndvi_by_month` (observed low-NDVI months). A mismatch is flagged as an information gap.

---

## 9. API contract

All endpoints are public JSON, no auth. DRF is configured with `AllowAny` and no session authentication (this avoids CSRF issues on POST).

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health/` | Status + DB check |
| GET | `/api/locations/` | Featured locations (pins) |
| GET | `/api/crops/` | Crop table (for the farmer's rotation editor) |
| POST | `/api/analyze/` | Main analysis |

### POST `/api/analyze/` — request
```json
{
  "lat": 42.0,
  "lon": -93.6,
  "current_rotation": null,
  "priorities": {"water": 4, "soil": 5, "income": 3, "erosion": 4, "pest": 2},
  "constraints": {
    "water_availability": "rainfed",
    "equipment": "standard",
    "market_pref": "balanced"
  },
  "overrides": {"soil_texture": null},
  "scenario": {"rain_pct": 0, "temp_c": 0}
}
```
- `current_rotation: null` means the server fills the default (CDL for Iowa, zone default elsewhere).
- `water_availability`: `rainfed | limited_irrigation | irrigated`. `equipment`: `basic | standard | specialized`. `market_pref`: `cash | forage | balanced`.

### Response
```json
{
  "location": {"name": "Central Iowa", "lat": 42.0, "lon": -93.6, "zone": "temperate",
               "featured": true, "data_tier": "us_enhanced", "grid_key": "42.0_-93.5"},
  "data_quality": {
    "confidence": "medium",
    "fallback_used": false,
    "sources": ["NASA POWER", "SoilGrids", "SMAP", "MODIS NDVI", "SSURGO", "CDL", "PRISM"],
    "notes": ["PRISM validation: precipitation correlation 0.93"]
  },
  "climate": {"monthly": [], "stress_by_month": {}, "water_balance": [], "trends": {}, "year_stress_flags": {}},
  "soil": {"texture": "silt loam", "organic_carbon": 1.9, "ph": 6.4, "source": "SSURGO"},
  "bare_windows": {"current": [11, 12, 1, 2, 3, 4]},
  "vulnerable_months": {"current": [{"month": 7, "reasons": ["heat", "dry spell"]}]},
  "strategies": [
    {
      "id": "current",
      "name": "Corn–soybean (current)",
      "is_current": true,
      "rotation": {"cycle_years": 2, "steps": []},
      "scores": {"overall": 62, "water_fit": 58, "climate_risk": 66, "soil_health": 48,
                 "erosion_infiltration": 52, "pest_break": 60, "income": 80},
      "contributions": {"water": 11.6, "soil": 12.0},
      "why_suggested": "Baseline: what is farmed today.",
      "evidence": [{"text": "July soil moisture is below normal in 6 of the last 20 years", "source": "SMAP"}],
      "benefits": ["Familiar equipment and strong markets"],
      "info_gaps": ["No field-level soil sampling"],
      "local_review": ["Check tile drainage and local planting dates with an extension agent"]
    }
  ],
  "disclaimer": "This tool highlights patterns and possibilities. It does not replace farmer judgment or local agricultural expertise."
}
```

**Timeouts and errors:** uncached live fetches can take 10 to 25 seconds, so the UI shows a "Fetching NASA data…" state. The backend uses 20-second timeouts, and returns `503` with a clear message if a non-featured point cannot be fetched.

---

## 10. Frontend spec

**One main screen.** Desktop: map and form on the left, results on the right. Phone: stacked, map first.

### Components
| Component | Owner | Notes |
|---|---|---|
| `Map` (Leaflet) | Talha | Featured pins, click anywhere to set a point, selected-point marker |
| `InputForm` | Talha | Rotation editor (crop dropdowns from `/api/crops/`), 5 priority sliders, 3 constraint selects, optional soil override |
| `ResultsLayout`, `StrategyCard` | Talha | Three cards side by side (stacked on phone), score bars, the 5 parts in collapsible sections |
| `DataBadge` | Talha | Tier + confidence + sources + "cached data" notice |
| `ClimateChart` | Abdur | Monthly rain (bars) + temperature (line) |
| `StressHeatmap` | Abdur | Month × year stress flags |
| `RotationTimeline` | Abdur | 12-month bar per strategy: crop in field, bare months, vulnerable months highlighted |
| `SoilMoistureNdviChart` | Abdur | Featured locations only |
| `ValidationPanel` | Abdur | POWER vs PRISM (Iowa), or "ground validation not available here" |
| `Glossary` (tooltip) | Musab | Reads `data/glossary.json` |
| `Disclaimer`, `AboutData` | Musab | Support-not-replace banner, satellite-vs-ground explainer |

**Design rules:** plain farmer language, no jargon without a tooltip, color is never the only signal (labels too), large tap targets, loading and error states everywhere.

---

## 11. Deployment (Django on free tiers)

### Services
| Service | What | Notes |
|---|---|---|
| **Vercel** | React frontend | Auto-deploy from `main`; set `VITE_API_URL` |
| **Render** | Django backend (web service) | Free tier sleeps when idle, so first request is slow. Warm it before judging |
| **Neon** | Postgres | Free tier, use the pooled connection string, `sslmode=require` |

Free-tier limits change, so check each one before relying on it. Shayan creates the accounts via GitHub sign-in in the first hour. Secrets live in the hosting dashboards only.

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
- **Environment variables:** `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `DEBUG=0`, `PYTHON_VERSION` (pin the same minor version as local)

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
All seed commands must be **idempotent** (safe to run on every deploy).

### Local development
`docker-compose up -d` runs Postgres. Copy `.env.example` to `.env` (never commit `.env`). The same compose file can run the full stack as a fallback demo if a free tier fails during judging.

### Deployment gotchas checklist
- [ ] Static files load in the admin (WhiteNoise + `collectstatic`).
- [ ] `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` match the real URLs (scheme included for the last two).
- [ ] `DEBUG=0` in production.
- [ ] All NASA, SoilGrids, and other API calls happen **server-side only**.
- [ ] `/api/health/` returns OK with a DB check.
- [ ] Render service warmed 10 minutes before the demo.

---

## 12. 24-hour schedule

Hour 0 is the official start. If the rules allow setup before the clock starts, do the "pre-clock" items first (check the event rules; account creation and repo skeleton are normally fine).

| Hours | Milestone | Key work |
|---|---|---|
| **Pre-clock** | Accounts and skeleton | Earthdata login (Aman), GitHub repo + invites, Vercel/Render/Neon accounts (Shayan), crop research started (Musab) |
| **0–1** | **M1: Contract and hello-world** | Shayan publishes the API contract with mock JSON. Hello-world Django + React deployed. Aman submits the AppEEARS requests. Everyone clones and runs locally. |
| **1–8** | **M2: Vertical slice** | One featured location, real POWER data, 3 strategies end to end, ugly UI. Crop table v1 in. |
| **8–15** | **M3: Feature complete (MUST list)** | All 3 pins, data tiers, constraints, timeline and charts, glossary, Iowa ground data if ready |
| **15–20** | **M4: Polish and harden** | Mobile layout, fallbacks, error states, caching, copy, SHOULD items |
| **20** | **FEATURE FREEZE** | Only bug fixes from here on |
| **20–22** | **M5: Submission build** | Final deploy, README, video, slides, full demo run-throughs. **Submit by hour 22** |
| **22–24** | Buffer | Fix surprises, resubmit if needed, rest |

**Check-ins (10 minutes, standing):** hours 4, 8, 12, 16, 20. Each person says what is done, what is blocked, what they need.

**Sleep:** two shifts. Nobody works more than about 14 hours straight. Shayan sleeps during hours 15 to 19 only if M3 is done.

---

## 13. Per-member instructions

### 13.1 Shayan — Tech lead and backend

**Deliverables:** Django project + models + admin, API, scoring and strategies, deployment, integration.

**Step by step**
1. **Hour 0–1 (before anything else):**
   - Create the GitHub repo, add the 5 teammates, protect `main` (PRs required, you can merge).
   - Write `docs/API_CONTRACT.md` from section 9, plus a `mock_analyze.json` file in the repo that Talha and Abdur can load immediately.
   - Commit the shared rotation format and the climate-profile output shape (sections 5 and 7) so Asif can start.
   - Create the Neon, Render, and Vercel accounts via GitHub login.
2. **Hour 0–1:** scaffold the Django project (`config`, apps `crops`, `locations`, `datasources`, `api`, folder `engine`). Add `/api/health/` and deploy the hello-world to Render. Confirm the Vercel frontend can call it (CORS works).
3. **Hour 1–3:** implement models (section 5), the admin, migrations, and `seed_crops` (reads `data/crops.csv`, `data/crop_calendars.csv`, `data/rotation_templates.json`). Use a tiny 3-crop CSV until Musab's real one lands.
4. **Hour 1–4:** write `engine/constants.py` and `engine/scoring.py` v1 against a **hand-written sample profile JSON** (do not wait for Asif). Write `engine/strategies.py` to load the templates, build the three strategies, and apply constraints.
5. **Hour 3–6:** build the `/api/analyze/` view:
   1. Validate the request; round to the grid key; determine the zone.
   2. Get data via Aman's `datasources` (cache first).
   3. Call Asif's `build_climate_profile`.
   4. Run scoring and strategy generation.
   5. Compute confidence, fill `evidence`, `info_gaps`, `local_review`, and the disclaimer.
   6. Return the contract-shaped JSON.
6. **Hour 6–8:** first end-to-end run for one featured location. Fix mismatches between modules. Tell everyone M2 is reached.
7. **Hour 8–15:** scoring v2 (constraints, overrides, explanations, contributions), templates for all 3 pins, Iowa tier integration (SSURGO soil and CDL default rotation), confidence labels, `load_prepulled` command. Add `/api/locations/` and `/api/crops/`.
8. **Hour 15–20:** performance and robustness: timeouts, cache hits, fallback behavior, `503` messages, rate limiting if easy (`django-ratelimit` or a simple per-IP counter). Bug triage list in the repo. Final deploy checks.
9. **Hour 20–24:** freeze. Merge only fixes. Run the full demo flow on the deployed site twice. Warm the Render service. Help Musab with the README and the video.
10. **Stretch (only if everything above is done):** the scenario slider backend (apply the multiplier before the profile) and the two-methods comparison with Asif.

**Rules for you**
- Do not rewrite Asif's or Aman's code. Ask, then agree on a change.
- Review PRs in batches; do not become the bottleneck.
- Any contract change is announced in the group chat and committed to `docs/API_CONTRACT.md` first.

---

### 13.2 Asif — Climate profile and analysis

**Deliverable:** `backend/engine/climate_profile.py` (pure Python and pandas, no Django imports) producing exactly the output shape in section 7, with unit tests.

**Step by step**
1. **Hour 0–1:** read sections 4 and 7. Ask Shayan for the sample POWER response; or fetch one yourself for Iowa and save it as `engine/tests/sample_power_iowa.csv`.
2. **Hour 1–3 (notebook first):** in a Jupyter notebook, load the sample daily data and compute, in this order:
   1. Monthly climatology (mean temperature, max, min, total precip, root wetness).
   2. ET0 with Hargreaves–Samani (compute `Ra` from latitude and day of year; document the formula in a comment).
   3. Monthly water balance (`precip − ET0`).
   4. Heat-stress days, frost days, extreme-rain days, dry-spell probability by month (thresholds from `constants.py`).
   5. Trends (precip and temperature per decade, simple linear regression).
3. **Hour 3–6:** move the notebook code into `build_climate_profile()`. Handle missing values (`-999` becomes NaN; report `missing_fraction`). Return the dict from section 7. **Hand Shayan a first working version by hour 6** even if some keys are `null`.
4. **Hour 6–10:** add:
   - Soil-moisture anomaly by month (use SMAP when present, otherwise `root_wetness`).
   - NDVI by month and `bare_months_observed` (months below the NDVI threshold).
   - Frost-free season (median, p10, p90).
   - `year_stress_flags` (drought and heat years).
   - `uncertainty.interannual_cv_precip` (coefficient of variation).
5. **Hour 10–14:** the Iowa validation: compare POWER monthly precip and mean temperature against `prism` (Abdur provides `prism_monthly.csv`; agree the columns `year, month, precip_mm, tmean_c, tmax_c, tmin_c`). Output correlation, percent bias for precipitation, and temperature bias in °C. Return `validation: null` where there is no PRISM data.
6. **Hour 14–17:** tests (`pytest`): a synthetic dataset with known heat days and frost days, and a check that missing-data inputs do not crash. Test all three locations' data once Aman's data is in.
7. **Hour 17–20:** support Shayan with bug fixes. Review the plain-language wording of `evidence` strings together with Musab, so that every number the UI shows is correct.
8. **Stretch:** compare two stress-year detectors (z-score vs percentile, or Isolation Forest) and produce one clear figure and a few sentences for the methods slide. Also add the scenario shift (`rain_pct`, `temp_c`) at the top of the function.

**Rules for you**
- No Django imports, no network calls in `engine/`. Inputs in, dict out.
- Every threshold lives in `constants.py`.
- If an output key is missing, return `null`, never crash.

---

### 13.3 Aman — Data sources and caching

**Deliverable:** `backend/datasources/` (`power.py`, `soilgrids.py`, `cache.py`, loaders) and the SMAP/NDVI pre-pull for the 3 featured locations.

**Step by step**
1. **Pre-clock or hour 0:** create the free NASA **Earthdata** login. Submit the **AppEEARS point-sample requests** immediately (queued processing can take a while): MODIS/VIIRS NDVI and SMAP soil moisture, the 3 pin coordinates, roughly 2015–2025 for SMAP and 2006–2025 for NDVI. **VERIFY** product names and versions in AppEEARS. If AppEEARS is slow or fails, use the ORNL DAAC MODIS subset service for NDVI and fall back to POWER `GWETROOT` for soil moisture, noting it in the data notes.
2. **Hour 1–3:** `power.py`: `fetch_power_daily(lat, lon, start, end) -> DataFrame`.
   - Parameters: `T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, GWETROOT, ALLSKY_SFC_SW_DWN`, `community=AG`, `format=JSON`.
   - 20-second timeout, 2 retries, convert `-999` to NaN, rename columns to `t2m, t2m_max, t2m_min, precip, root_wetness, solar`.
   - If a long date range fails, request one year at a time.
3. **Hour 2–4:** `cache.py`: `get_or_fetch(kind, lat, lon, fetch_fn)` which rounds to the 0.5° grid key, looks up `LocationCache`, calls the fetch function on a miss, and stores the JSON payload. Provide helpers to turn the payload back into a DataFrame.
4. **Hour 3–5:** `soilgrids.py`: `fetch_soilgrids(lat, lon) -> dict` for clay, sand, silt, soil organic carbon, pH (top ~30 cm, mean). **VERIFY** the unit conversion factor in the response. Use a 25-second timeout. Derive a simple texture class from sand/silt/clay. Return a documented `None` on failure so Shayan can apply a fallback.
5. **Hour 5–8:** when the AppEEARS results are ready, write `backend/data/prepulled/<slug>/smap.csv` and `ndvi.csv` (columns `date, sm` and `date, ndvi`) for all 3 pins. Write the loader that Shayan's `load_prepulled` command calls (reads the files, stores them in `LocationCache` with kinds `smap` and `ndvi`).
6. **Hour 8–12:** add `get_smap(slug)` and `get_ndvi(slug)` accessors. Pre-warm the POWER and SoilGrids cache for the 3 pins and commit a small cached snapshot to the repo (`prepulled/<slug>/power_cache.json`) so the demo works even if POWER is down.
7. **Hour 12–16:** error handling and logging: clear exception types (timeout, bad response), so `/analyze` can show a sensible `503`. Measure the time of an uncached fetch and report it to Shayan and Talha (for the loading message).
8. **Hour 16–20:** help Abdur with the Iowa pre-pulls or with charts if you are ahead. Test the full uncached flow for 3 random clicked points (including one in Pakistan, one in Iowa, one elsewhere) on the deployed site.

**Rules for you**
- Keep each function small and documented with the exact output columns.
- No secrets in code. The Earthdata token (if used server-side) goes in an environment variable.
- Everything must still work from cache when the internet is bad.

---

### 13.4 Abdur — Iowa ground data, then charts

**Deliverables:** (A) Iowa pre-pulls: `ssurgo.json`, `cdl_sequence.csv`, `prism_monthly.csv`; (B) charts and timeline in React.

**Part A — Iowa ground data (hours 0–6)**
1. **Hour 0–1:** read sections 4, 5, and 7. Agree the exact file formats with Shayan and Asif.
2. **Hour 1–3:** `prism_monthly.csv`: download PRISM monthly precipitation, mean/max/min temperature for the Iowa point, 2006–2025. Columns: `year, month, precip_mm, tmean_c, tmax_c, tmin_c`. **VERIFY** the PRISM point download; manual download of one point is fine.
3. **Hour 2–4:** `cdl_sequence.csv`: crops grown at the Iowa point for the last ~8–10 years from CropScape. Columns: `year, crop`. Map the CDL crop names to our crop slugs (Musab's table). This becomes the existing rotation for Iowa. If the pixel history is noisy, check a couple of nearby pixels and pick the dominant sequence.
4. **Hour 3–5:** `ssurgo.json`: soil texture, organic matter, drainage class, hydrologic soil group, erosion factor (Kw) and water-holding capacity for the Iowa point, from Soil Data Access or Web Soil Survey. **VERIFY**; a manual Web Soil Survey export is acceptable.
5. **Hour 5–6:** commit the files under `backend/data/prepulled/iowa-central/`, document the source and date of each file in `data/prepulled/README.md` (for credits).
6. Tell Shayan and Asif when each file is in. If something fails for more than 45 minutes, tell Shayan and drop that dataset to "Future work".

**Part B — Charts (hours 6–20)**
7. **Hour 6–8:** set up chart components against Shayan's `mock_analyze.json` (Talha owns the app shell; use the shared API client).
8. **Hour 8–12:** `ClimateChart` (monthly rain bars + temperature line) and `RotationTimeline` (12-month bar per strategy: crop in field, bare months, vulnerable months with reasons on hover or tap).
9. **Hour 12–16:** `StressHeatmap` (month × year), `SoilMoistureNdviChart` (featured locations), `ValidationPanel` (POWER vs PRISM, or the "ground validation not available here" message).
10. **Hour 16–20:** mobile-friendly sizing, empty and loading states, color-blind-safe palettes with labels, then help Talha and Musab with QA.

**Rules for you**
- Use only data from the API response, not hard-coded numbers.
- Every chart has a title, axis labels, a one-sentence "what this means for a farmer" caption (copy from Musab), and works on a phone.

---

### 13.5 Talha — Frontend lead

**Deliverables:** the app shell, map, input form, results layout, strategy cards, API integration, Vercel deployment.

**Step by step**
1. **Hour 0–1:** scaffold React + Vite in `/frontend`; clone, run, and push. Create `src/api/client.js` reading `VITE_API_URL`. Load `mock_analyze.json` while the backend is not ready.
2. **Hour 1–3:** `Map` with react-leaflet: base tiles, 3 featured pins from `/api/locations/` (use a hard-coded list until it exists), click-anywhere to set a point.
3. **Hour 2–5:** `InputForm`: rotation editor (crop dropdowns from `/api/crops/`, steps in order), five priority sliders (0 to 5), three constraint selects, optional soil-texture override. Plain-language labels. A **Analyze** button.
4. **Hour 4–8:** `ResultsLayout` and `StrategyCard`: strategy name, overall score, sub-score bars, then collapsible sections for **Why suggested, Evidence, Benefits, Information gaps, Needs local review**. Mark the current rotation. Show the weighted contributions as a simple stacked bar.
5. **Hour 6–8:** `DataBadge` (tier, confidence, sources, "cached data" notice), loading state ("Fetching NASA data…"), and error state for `503`.
6. **Hour 8: M2** — connect to the real `/api/analyze/` for one location.
7. **Hour 8–14:** polish layout; place Abdur's charts and the timeline into the results page; sticky disclaimer footer; wire up Musab's glossary tooltips. Make featured pins visually distinct from the clicked point.
8. **Hour 14–18:** mobile layout (map above the form, cards stacked, big tap targets). Fix state bugs: changing the location clears old results, double-click on Analyze is ignored while loading.
9. **Hour 18–20:** accessibility pass (labels, contrast, keyboard), test on a real phone, confirm the Vercel build uses the production `VITE_API_URL`.
10. **Stretch:** scenario sliders (rain %, temperature °C) that re-run `/analyze` with the `scenario` field, and an Urdu toggle for key labels.

**Rules for you**
- Build against the mock first. Never block on the backend.
- If Abdur's pre-pulls run long, take the simple charts yourself.

---

### 13.6 Musab — Domain content, UI polish, and the story

**Deliverables:** the crop table and calendars, rotation templates, glossary and explanation copy, glossary components, responsive QA, README, demo script, slides, and video.

**Step by step**
1. **Hour 0–2:** build `backend/data/crops.csv` with **12 to 15 crops** covering both zones, using the columns in section 5 (`slug, name, family, role, water_need_mm, drought_tolerance, heat_tolerance, frost_tolerance, n_fixing, root_depth, ground_cover, residue_om, erosion_protection, income_level, forage_value, special_equipment, sources, notes`).
   - Suggested coverage: Iowa: corn, soybean, oats, winter wheat, alfalfa, cereal rye (cover), red clover (cover/forage). Pakistan: wheat, cotton, rice, maize, chickpea, mungbean or other pulse, berseem or other forage legume, mustard/canola, sorghum.
   - Use FAO (for example FAO-56 and Irrigation Paper 33 for water needs), national or extension sources, and GAEZ for suitability. Put the source in the `sources` column for every crop. Mark `income_level` as a regional placeholder.
2. **Hour 2–4:** `crop_calendars.csv` for the two zones (`crop_slug, zone, season_label, sow_months, harvest_months`). Confirm the real local patterns for Sindh and Punjab (for example, kharif and rabi seasons) with whatever local knowledge or documents you can find. Flag anything uncertain.
3. **Hour 3–5:** `rotation_templates.json`: for each zone, **water_saver** and **soil_builder** templates plus a `current_default`. Review them with Shayan. Each must follow the rotation format in section 5 and include the short rationale text.
4. **Hour 4–7:** `frontend/src/data/glossary.json` with plain-language entries for: evapotranspiration, soil-moisture anomaly, NDVI, frost risk, water balance, nitrogen fixation, cover crop, deep roots, drought tolerance, erosion, infiltration, bare field, satellite vs ground observation, confidence. Two sentences each, written for a farmer.
5. **Hour 5–8:** build the `Glossary` tooltip component (a `<Term id="ndvi">NDVI</Term>` wrapper), the `Disclaimer` banner, and the `AboutData` panel (what satellites measure well, what they miss, why local knowledge matters). Ask Talha for guidance on structure.
6. **Hour 8–12:** write the explanation copy that Shayan's engine fills into strategies: one-sentence templates for the benefits of nitrogen fixers, cover crops, deep-rooting crops, and drought-tolerant crops; standard `local_review` items (soil sampling, planting dates, markets, drainage, pest history); and the `info_gaps` phrases per data tier.
7. **Hour 10–15:** GAEZ cross-check: confirm that each crop is suitable in the pilot regions, and note disagreements in the crop `notes`.
8. **Hour 14–18:** responsive QA on a real phone and a laptop: test all 3 pins and 3 clicked points, write issues into the GitHub issue list with screenshots, and verify that every number shown matches the API response.
9. **Hour 15–20:** `README.md`: what it does, how to run locally, data sources and credits, harmonization method, limitations, team. Start the slides and the demo script (below).
10. **Hour 20–22:** record the demo video (backup for judging) and finish the slides. Run the demo flow twice against the deployed site with a stopwatch.

**Demo script (about 3 to 4 minutes)**
1. The problem (shifting climate, water stress, soil decline, hard rotation choices).
2. Click the Iowa pin; show the current corn–soybean rotation from CDL.
3. Show bare and vulnerable months, and what NASA data tells us (SMAP, NDVI, POWER), with the glossary tooltips.
4. Compare the three strategies; open one card to show why, evidence, benefits, gaps, local-review items.
5. Change priorities (water vs income) and show the ranking change.
6. Show the tier, confidence, and POWER-vs-PRISM validation (satellite vs ground).
7. Click an arbitrary Pakistani point: "Standard" tier, lower confidence, honest about gaps.
8. Limitations and future work (ECOSTRESS, Landsat/Sentinel-2 field zones, GRACE groundwater, user accounts). Close with "supports, does not replace, farmer judgment".

**Rules for you**
- Every crop number needs a source, or an explicit "approximate" flag.
- Plain language only: if a farmer would not say it, rewrite it.

---

## 14. Team workflow rules

- **Branches:** `feat/<name>-<thing>`; one small PR per task; Shayan merges to `main`.
- **`main` is always deployable.** Broken `main` is the top priority for everyone.
- **Contract changes** go through Shayan: update `docs/API_CONTRACT.md` and announce.
- **No secrets in the repo.** Commit `.env.example` only.
- **Chat norms:** post blockers immediately; do not sit stuck for more than 30 minutes.
- **Definition of done:** code merged, works on the deployed site, no console errors.
- **After hour 20:** fixes only; no refactors, no new features.

---

## 15. Final checklists

### Demo readiness (hour 20–22)
- [ ] Deployed URL works on desktop and a real phone.
- [ ] All 3 pins load in under about 5 seconds from cache.
- [ ] 3 random clicked points work (including one outside the pilots) or fail with a clear message.
- [ ] Render service warmed; Neon reachable.
- [ ] A local fallback (`docker-compose`) tested at least once.
- [ ] Demo video recorded as a backup.

### Submission
- [ ] Read the official participant guide and FAQ for the exact submission requirements and the judging criteria, and any rules on AI tools, data, and code sources.
- [ ] Public repo with a clear README.
- [ ] Deployed link, slides, and video as required.
- [ ] All data sources credited (README, slides, app footer).
- [ ] Submitted by **hour 22**, leaving buffer.

---

## 16. Risks and fallbacks

| Risk | Fallback |
|---|---|
| AppEEARS (SMAP/NDVI) is slow or fails | ORNL MODIS subset service for NDVI; POWER root wetness replaces SMAP, and the notes say so |
| SSURGO, CDL, or PRISM endpoints fail | Manual downloads for the single Iowa point; drop to "Future work" after 45 minutes |
| NASA POWER or SoilGrids is slow or down during the demo | Cached snapshots for the 3 pins in the repo |
| Render free tier sleeps | Warm it before judging; docker-compose local fallback |
| Free database pauses or hits limits | Warm Neon before the demo; keep seed commands idempotent so a fresh DB rebuilds fast |
| Crop calendars wrong for Sindh or Punjab | Label them as approximate; list in `local_review`; Musab confirms with sources |
| Schedule slips | Cut STRETCH, then SHOULD, in that order. Never cut the MUST list or the disclaimer |
| Integration trouble between modules | Mock JSON and sample profile keep everyone unblocked; Shayan integrates early (hour 6–8) |

---

## 17. Standard limitation and disclaimer text

Use this wording (adapt lightly) in the app footer, README, and slides:

> FieldShift Planner highlights patterns and possibilities from NASA Earth observations and public soil and climate data. It does not replace farmer judgment or local agricultural expertise. Satellite and reanalysis data are coarse compared with a single field and can differ from what is measured on the ground. Crop calendars, water needs, and market values are simplified regional estimates. Please review any rotation idea with local farmers, extension services, or agronomists before acting on it.

---

## 18. Data credits (keep updated)

NASA POWER · NASA SMAP · NASA MODIS/VIIRS (via Earthdata AppEEARS or ORNL DAAC) · ISRIC SoilGrids · USDA NRCS SSURGO / Web Soil Survey · USDA NASS Cropland Data Layer · PRISM Climate Group (Oregon State University) · FAO GAEZ and FAO crop water guidance. Note the data-use terms of each non-NASA source in the README.
