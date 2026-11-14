
# FieldShift Planner — API Contract

**Version:** 1.1 (2026-11-15: strategy explanation parts, monthly climate, vulnerable months, confidence)  
**Status:** Initial Development  
**Base URL (local):** `http://127.0.0.1:8000/api/`  
**Content-Type:** `application/json`

---

## 1. Overview

FieldShift Planner is an agricultural crop rotation planning system that helps farmers evaluate crop rotation strategies using climate, soil, crop, and location data.

The backend provides REST APIs for:

- Retrieving supported farming locations.
- Retrieving crop information.
- Analyzing existing crop rotations.
- Generating alternative crop rotation strategies.
- Evaluating climate and rainfall scenarios.
- Explaining analysis results using AI.
- Providing an AI-assisted farming conversation.

### General API conventions

- All endpoints are prefixed with `/api/`.
- Request and response bodies use JSON.
- The initial API is publicly accessible; authentication is not required.
- Coordinates use decimal degrees.
- `lat` represents latitude.
- `lon` represents longitude.
- Analysis scores range from 0 to 100.
- Dates and timestamps use ISO 8601 format.
- Missing or unavailable data must be explicitly identified.
- Simulated values must never be presented as measured observations.

---

## 2. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health/` | Check backend availability |
| GET | `/api/locations/` | Retrieve supported farming locations |
| GET | `/api/crops/` | Retrieve available crop information |
| POST | `/api/analyze/` | Generate crop rotation analysis |
| POST | `/api/explain/` | Explain analysis results |
| POST | `/api/chat/` | AI-assisted farming conversation |

---

## 3. Health Check

### GET `/api/health/`

Checks whether the backend server is running.

**Successful response: `200 OK`**

```json
{
  "status": "success",
  "message": "FieldShift Planner API is running.",
  "timestamp": "2026-11-14T07:45:03.274116+00:00"
}
```

---

## 4. Locations

### GET `/api/locations/`

Returns the supported farming locations.

Each location should contain:

| Field | Type | Description |
|---|---|---|
| `slug` | string | Unique location identifier |
| `name` | string | Location display name |
| `lat` | number | Latitude |
| `lon` | number | Longitude |
| `country` | string | Country name |
| `zone` | string | Agricultural or climate zone |
| `tier` | string | Available data tier |
| `featured` | boolean | Whether the location is featured |

**Example response:**

```json
{
  "status": "success",
  "count": 2,
  "results": [
    {
      "slug": "iowa-central",
      "name": "Central Iowa",
      "lat": 42.0,
      "lon": -93.6,
      "country": "United States",
      "zone": "Temperate",
      "tier": "featured",
      "featured": true
    },
    {
      "slug": "example-location",
      "name": "Example Farming Region",
      "lat": 31.5,
      "lon": 74.3,
      "country": "Pakistan",
      "zone": "Subtropical",
      "tier": "standard",
      "featured": false
    }
  ]
}
```

The example locations are illustrative and must not be treated as confirmed database records.

---

## 5. Crops

### GET `/api/crops/`

Returns the crop information available in the system.

Each crop may contain the following fields:

| Field | Type | Description |
|---|---|---|
| `slug` | string | Unique crop identifier |
| `name` | string | Crop name |
| `name_ur` | string/null | Urdu crop name |
| `family` | string | Botanical family |
| `role` | string | Agricultural role |
| `water_need_mm` | number/null | Estimated water requirement |
| `drought_tolerance` | number/null | Drought tolerance indicator |
| `heat_tolerance` | number/null | Heat tolerance indicator |
| `frost_tolerance` | number/null | Frost tolerance indicator |
| `n_fixing` | boolean | Whether the crop fixes nitrogen |
| `root_depth` | number/null | Root depth |
| `ground_cover` | number/null | Ground cover indicator |
| `residue_om` | number/null | Organic matter contribution |
| `erosion_protection` | number/null | Erosion protection indicator |
| `income_level` | string/null | Regional income category placeholder |
| `forage_value` | number/null | Forage value indicator |
| `special_equipment` | boolean | Whether specialized equipment is required |
| `sources` | array | Data sources |
| `notes` | string/null | Additional information |

**Example response:**

```json
{
  "status": "success",
  "count": 2,
  "results": [
    {
      "slug": "maize",
      "name": "Maize",
      "name_ur": "مکئی",
      "family": "Poaceae",
      "role": "cash",
      "water_need_mm": 600,
      "drought_tolerance": 2,
      "heat_tolerance": 4,
      "frost_tolerance": 1,
      "n_fixing": false,
      "root_depth": 120,
      "ground_cover": 3,
      "residue_om": 3,
      "erosion_protection": 3,
      "income_level": "high",
      "forage_value": 3,
      "special_equipment": false,
      "sources": [],
      "notes": null
    },
    {
      "slug": "soybean",
      "name": "Soybean",
      "name_ur": "سویا بین",
      "family": "Fabaceae",
      "role": "legume",
      "water_need_mm": 450,
      "drought_tolerance": 3,
      "heat_tolerance": 3,
      "frost_tolerance": 1,
      "n_fixing": true,
      "root_depth": 100,
      "ground_cover": 4,
      "residue_om": 4,
      "erosion_protection": 4,
      "income_level": "medium",
      "forage_value": 2,
      "special_equipment": false,
      "sources": [],
      "notes": null
    }
  ]
}
```

Crop values are illustrative examples. Actual values must be based on documented agricultural sources.

---

## 6. Crop Rotation Analysis

### POST `/api/analyze/`

Generates a crop rotation analysis based on the farmer's location, current rotation, priorities, constraints, and optional climate scenario.

This is the primary endpoint of FieldShift Planner.

### 6.1 Request Body

```json
{
  "lat": 42.0,
  "lon": -93.6,
  "current_rotation": null,
  "priorities": {
    "water": 4,
    "soil": 5,
    "income": 3,
    "erosion": 4,
    "pest": 2
  },
  "constraints": {
    "water_availability": "rainfed",
    "equipment": "standard",
    "market_pref": "balanced"
  },
  "overrides": {
    "soil_texture": null
  },
  "scenario": {
    "rain_pct": 0,
    "temp_c": 0
  },
  "lang": "en"
}
```

### 6.2 Request Fields

#### Location

| Field | Type | Required | Description |
|---|---|---|---|
| `lat` | number | Yes | Latitude (-90 to 90) |
| `lon` | number | Yes | Longitude (-180 to 180) |

#### Current rotation

| Field | Type | Required | Description |
|---|---|---|---|
| `current_rotation` | object/array/null | Yes | Farmer's existing crop rotation information |

A `null` value indicates that the farmer has not provided an existing rotation.

The exact internal representation will be finalized with the rotation analysis implementation.

#### Priorities

All priority values must be integers from 1 to 5.

| Field | Type | Description |
|---|---|---|
| `water` | integer | Importance of water conservation |
| `soil` | integer | Importance of soil health |
| `income` | integer | Importance of economic outcomes |
| `erosion` | integer | Importance of erosion protection |
| `pest` | integer | Importance of pest and disease breaks |

#### Constraints

| Field | Allowed Values | Description |
|---|---|---|
| `water_availability` | `rainfed`, `limited_irrigation`, `irrigated` | Available water supply |
| `equipment` | `basic`, `standard`, `specialized` | Available farming equipment |
| `market_pref` | `cash`, `forage`, `balanced` | Farmer's market preference |

#### Overrides

| Field | Type | Description |
|---|---|---|
| `soil_texture` | string/null | Optional farmer-provided soil texture override |

Overrides must be clearly distinguished from measured soil data.

#### Climate scenario

| Field | Type | Allowed Range | Description |
|---|---|---|---|
| `rain_pct` | number | -50 to +30 | Percentage change in rainfall |
| `temp_c` | number | -2 to +5 | Temperature change in degrees Celsius |

A zero value indicates the baseline climate scenario.

#### Language

| Field | Allowed Values | Description |
|---|---|---|
| `lang` | `en`, `ur` | Response language: English or Urdu |

---

### 6.3 Successful Response

**Status: `200 OK`**

The analysis response contains the following top-level fields:

| Field | Type | Description |
|---|---|---|
| `analysis_id` | string | Unique analysis identifier |
| `location` | object | Analyzed location information |
| `data_quality` | object | Data availability, source and quality information |
| `climate` | object | Baseline and scenario climate information |
| `soil` | object | Soil characteristics |
| `bare_windows` | array | Periods when soil may be exposed |
| `vulnerable_months` | array | Months with elevated agricultural vulnerability |
| `alerts` | array | Important warnings and scenario-related alerts |
| `strategies` | array | Recommended crop rotation strategies |
| `disclaimer` | string | Limitations of the analysis |

A full real example (Central Iowa, What-If +3 °C and −30 % rain) is in `docs/mock_analyze.json`. It was generated from the live endpoint, so the frontend can build every screen against it.

#### `location`

| Field | Type | Description |
|---|---|---|
| `lat`, `lon` | number | The analyzed point |
| `name`, `country` | string/null | Featured pin name and country, `null` for a clicked point |
| `zone` | string | `temperate` or `subtropical` |
| `featured` | boolean | `true` when the point is within 5 km of a featured pin |
| `slug` | string/null | Featured pin slug |

#### `data_quality`

| Field | Type | Description |
|---|---|---|
| `confidence` | string | `high`, `medium` or `low` (show as a badge) |
| `tier` | string | `standard`, `featured` or `us_enhanced` |
| `fallback_used` | boolean | `true` when cached/offline climate data was used: show a "using cached data" notice |
| `status` | string | `complete`, or `partial` when `warnings` is not empty |
| `warnings` | array of string | Plain-language data warnings |
| `sources` | array of string | Data sources actually used |
| `years_covered`, `n_years`, `missing_fraction` | | Climate record length and gaps |

Confidence is `low` for a clicked (non-featured) point, lots of missing data, or a What-If beyond ±3 °C / ±30 % rain. It is `high` only for the US-enhanced tier with PRISM validation above 0.85, otherwise `medium` with 15+ years of data.

#### `climate`

`climate.baseline` is always filled. `climate.scenario` is `null` when no What-If is applied; otherwise it has the same fields plus `rain_pct` and `temp_c`.

| Field | Type | Description |
|---|---|---|
| `annual_rainfall_mm`, `average_temperature_c` | number | Annual summary |
| `monthly` | array of 12 objects | One row per month, `month` 1 to 12 (chart data) |
| `trends` | object | `precip_mm_per_decade`, `t_mean_c_per_decade`, plus `precip_trend_significant` and `t_mean_trend_significant`: only call it a trend in the UI when the flag is `true` |
| `year_stress_flags` | object | `{"2012": ["drought", "heat"]}` |
| `frost_free_season` | object | `median_days`, `p10`, `p90` |
| `soil_moisture_source` | string | `smap` or `power_root_wetness` |
| `bare_months_observed` | array | Bare months seen in NDVI (empty without NDVI data) |
| `basis` | string | `historical` for baseline, `simulated` for scenario: label charts with it |

Each `monthly` row: `month`, `t_mean`, `t_max`, `t_min`, `precip_mm`, `et0_mm`, `deficit_mm`, `root_wetness`, `heat_days`, `severe_heat_days`, `frost_days`, `dry_spell_prob` (0 to 1), `extreme_rain_days`, `soil_moisture_anomaly` (standard deviations), `ndvi`. Any value can be `null` when data is missing.

#### `bare_windows`

`[{"month": 11, "bare_fraction": 1.0}]`: months when the current rotation leaves the field bare in at least half of the cycle years.

#### `vulnerable_months`

Months where a crop of the current rotation is in a growth stage sensitive to a stress that is present:

```json
{"month": 7, "crops": ["maize", "soybean"],
 "sensitive_stages": [{"crop": "maize", "stage": "flowering", "sensitive": ["heat", "drought"]}],
 "reasons": ["heat", "dry_spell", "soil_drying"],
 "values": {"heat_days": 6.8, "dry_spell_prob": 0.55, "frost_days": 0, "soil_moisture_anomaly": -1.4}}
```

`reasons` can contain `heat`, `dry_spell`, `frost`, `soil_drying`.

#### `alerts`

```json
{"type": "heat", "severity": "critical", "severity_label": "Critical", "month": 7,
 "crops": ["maize", "soybean"], "stage": "flowering",
 "triggered_by": [{"variable": "heat_days", "value": 6.8, "threshold": 35.0}],
 "reason": "July: ...", "action": "Consider earlier sowing ...",
 "basis": "simulated", "source": "NASA POWER"}
```

`type`: `heat`, `drought`, `water_deficit`, `frost`, `waterlogging`, `soil_drying`. `severity`: `low`, `moderate`, `high`, `critical`. `reason`, `action` and `severity_label` follow `lang`. `basis` is `historical` or `simulated`.

### 6.4 Strategy Structure

The API returns three strategies:

| Strategy Key | Name | Main Objective |
|---|---|---|
| `current` | Current Rotation | Represents the existing or baseline rotation |
| `water_saver` | Water Saver | Emphasizes water conservation and drought resilience |
| `soil_builder` | Soil Builder | Emphasizes soil health, ground cover and erosion protection |

Each strategy contains:

| Field | Type | Description |
|---|---|---|
| `key` | string | Strategy identifier |
| `name` | string | Display name |
| `description` | string | Strategy explanation |
| `is_current` | boolean | `true` for the farmer's current rotation |
| `rotation` | object | `cycle_years` and `steps` (crop slug, year, sow and harvest month) |
| `scores` | object | Current or simulated strategy scores |
| `baseline_scores` | object/null | Baseline scores for comparison |
| `why_suggested` | string | Why this strategy is suggested |
| `evidence` | array | NASA-data evidence: `{"text", "source", "type": "observed", "kind", "month", "crops"}` |
| `benefits` | array of string | Expected benefits |
| `info_gaps` | array of string | What the data cannot tell us |
| `local_review` | array of string | What to check with a local expert or extension office |

The last five fields are the challenge's required parts. They are written in the requested `lang` and every number in them comes from the analysis data (`engine/explain.py`).

### 6.5 Scoring Structure

Every strategy must expose the following scores:

| Score | Range | Description |
|---|---|---|
| `overall` | 0–100 | Overall strategy suitability |
| `water_fit` | 0–100 | Suitability for available water |
| `climate_risk` | 0–100 | Climate-related suitability/risk score |
| `soil_health` | 0–100 | Soil health contribution |
| `erosion_infiltration` | 0–100 | Erosion protection and infiltration performance |
| `pest_break` | 0–100 | Pest and disease break effectiveness |
| `income` | 0–100 | Regional income indicator |

All scores must be numeric values between 0 and 100.

**Important scoring rules:**

- Higher scores represent better suitability or performance.
- The `income` score is a regional placeholder indicator, not a prediction of actual farmer revenue.
- Scores must be generated from the analysis engine, not hardcoded in production responses.
- The scoring engine must consider the farmer's priorities and constraints.
- Simulated scores must be distinguishable from baseline scores.

### 6.6 Scenario Comparison

When a climate scenario is applied:

- `scores` contains the scenario-adjusted scores.
- `baseline_scores` contains the corresponding baseline scores.
- Alerts must identify when they are based on simulated conditions.
- The frontend can compare the baseline and scenario results.

When no scenario adjustment is applied, the API may return `baseline_scores` as `null` or use an explicitly documented baseline representation consistently.

---

## 7. Explanation Endpoint

### POST `/api/explain/`

Generates a human-readable explanation of a completed crop rotation analysis.

The explanation service must use the analysis data supplied to it.

It must not:

- Invent climate measurements.
- Invent soil measurements.
- Invent crop characteristics.
- Change analysis scores.
- Present unsupported agricultural claims as facts.

The explanation should cover:

- Why a strategy was recommended.
- How farmer priorities influenced the recommendation.
- Important climate and soil considerations.
- Differences between baseline and scenario results.
- Data limitations and uncertainties.

The exact request and response schema will be finalized during implementation of the explanation service.

---

## 8. AI Chat Endpoint

### POST `/api/chat/`

Provides an AI-assisted agricultural conversation.

The chat service should use available analysis results, crop information, and agricultural context.

The assistant should:

- Answer farming and crop rotation questions.
- Explain available analysis results.
- Discuss climate and soil considerations.
- Respect the selected response language (`en` or `ur`).
- Clearly identify uncertainty and unavailable information.
- Avoid inventing climate, soil or crop measurements.
- Avoid fertilizer and pesticide dosing instructions.
- Provide a fallback response if the language model is unavailable.

The exact request and response schema will be finalized during implementation of the chat service.

---

## 9. Error Handling

All API errors should use a consistent JSON structure.

### Standard error response

```json
{
  "status": "error",
  "message": "A description of the error.",
  "errors": {}
}
```

### HTTP status codes

| Status Code | Meaning | Example |
|---|---|---|
| 200 | OK | Successful request |
| 201 | Created | Resource successfully created, if applicable |
| 400 | Bad Request | Invalid request fields |
| 404 | Not Found | Requested resource does not exist |
| 405 | Method Not Allowed | Unsupported HTTP method |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected backend error |
| 503 | Service Unavailable | Required external data service unavailable |

### Validation errors

Invalid request data should return HTTP `400`.

Example:

```json
{
  "status": "error",
  "message": "Request validation failed.",
  "errors": {
    "lat": [
      "Latitude must be between -90 and 90."
    ],
    "priorities": {
      "water": [
        "Priority must be between 1 and 5."
      ]
    }
  }
}
```

---

## 10. External Data Sources

FieldShift Planner uses different environmental data sources depending on the location and available data tier.

### Standard tier

- NASA POWER
- SoilGrids

### Featured tier

Includes Standard sources, plus:

- SMAP
- MODIS/VIIRS NDVI

### US-enhanced tier

Includes US-specific sources:

- SSURGO
- Cropland Data Layer (CDL)
- PRISM

The availability of individual sources may vary by location.

The API must communicate missing or unavailable data through `data_quality`.

---

## 11. Data Caching and Location Rules

The backend uses location-based caching to reduce external API requests and improve analysis performance.

Rules:

1. Location caching uses the nearest 0.5-degree grid.
2. Cached environmental data is stored in PostgreSQL using JSONB.
3. Cache entries must identify their data type, grid key, source URL and retrieval timestamp.
4. The same location must not silently receive environmental data from an unrelated location.
5. Featured locations may use eligible cached fallback data.
6. Non-featured locations without the required cache must return a clear data availability error.
7. What-if scenarios should reuse the relevant cached daily climate series whenever available.
8. The API must identify when cached, fallback or incomplete data is being used.

---

## 12. Climate Scenario Rules

The What-If feature allows farmers to simulate changes in rainfall and temperature.

Supported ranges:

| Parameter | Minimum | Maximum |
|---|---:|---:|
| Rainfall change | -50% | +30% |
| Temperature change | -2°C | +5°C |

Rules:

- Scenario adjustments must be applied to the baseline environmental data.
- Baseline data must remain unchanged.
- Scenario results must be clearly identified as simulated.
- Scenario alerts must indicate that they are based on simulated conditions.
- The backend should reuse cached daily climate data rather than unnecessarily requesting the same data again.

---

## 13. Security and API Access

Initial development configuration:

- Public API access.
- No authentication requirement.
- CORS restricted to approved frontend origins during development.
- Input validation on all POST endpoints.
- External API credentials stored in environment variables.
- Sensitive credentials must never be committed to Git.
- Error responses must not expose internal stack traces or secrets.

---

## 14. Agricultural Reliability and Disclaimers

FieldShift Planner provides decision-support information, not guaranteed agricultural outcomes.

The backend must:

- Distinguish measured environmental data from simulated results.
- Identify missing or incomplete datasets.
- Avoid presenting placeholder income indicators as financial forecasts.
- Avoid guaranteeing crop yields or profitability.
- Avoid unsupported fertilizer or pesticide dosing recommendations.
- Include an appropriate disclaimer in analysis responses.

---

## 15. Implementation Notes

The following implementation details are intentionally left flexible until their corresponding services are developed:

- Exact pagination behavior for locations and crops.
- Detailed `current_rotation` representation.
- Detailed `/api/explain/` request and response schema.
- Detailed `/api/chat/` request and response schema.
- Final response envelope for external data errors.

These details must be finalized consistently between the backend and frontend teams before integration.

**The API contract is the shared integration reference. Any changes to endpoint paths, field names, data types, or response structures must be communicated to the team and reflected in this document.**
