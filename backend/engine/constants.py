"""All tunable thresholds for the FieldShift engine, in one place.

Owner: Asif. Pure Python, no Django imports.
Changing a value here changes the climate profile, scoring and alerts everywhere.
Every value has a short note on where it comes from, so it can be explained to judges.
"""

# ---------------------------------------------------------------------------
# Data handling
# ---------------------------------------------------------------------------
POWER_FILL_VALUE = -999          # NASA POWER missing-value marker
MIN_YEARS_FOR_CLIMATOLOGY = 10   # fewer years -> confidence drops to "low"
MAX_MISSING_FRACTION = 0.10      # more missing data -> confidence drops to "low"
GRID_STEP_DEG = 0.5              # cache grid (~55 km), matches POWER's coarse resolution

# ---------------------------------------------------------------------------
# Daily stress indicators (plan section 7)
# ---------------------------------------------------------------------------
HEAT_DAY_TMAX_C = 35.0           # t2m_max above this = heat-stress day (common crop heat threshold)
FROST_DAY_TMIN_C = 0.0           # t2m_min at or below this = frost day
WET_DAY_MM = 1.0                 # a day with >= 1 mm counts as wet
EXTREME_RAIN_PERCENTILE = 95     # percentile of wet-day rain at this location
DRY_SPELL_MIN_DAYS = 10          # consecutive days with rain < WET_DAY_MM

# ---------------------------------------------------------------------------
# Evapotranspiration (Hargreaves-Samani, FAO-56 eq. 52)
# ET0 [mm/day] = HS_COEF * MJ_TO_MM * Ra * (Tmean + HS_T_OFFSET) * sqrt(Tmax - Tmin)
# Ra = extraterrestrial radiation [MJ m-2 day-1] from latitude and day of year (FAO-56 eq. 21)
# ---------------------------------------------------------------------------
HS_COEF = 0.0023
HS_T_OFFSET = 17.8
MJ_TO_MM = 0.408                 # converts MJ m-2 day-1 to mm/day of evaporated water
SOLAR_CONSTANT = 0.0820          # Gsc, MJ m-2 min-1

# ---------------------------------------------------------------------------
# Vegetation / bare field
# ---------------------------------------------------------------------------
BARE_NDVI_THRESHOLD = 0.25       # monthly NDVI below this = bare or low vegetation
NDVI_GOOD_RELIABILITY = (0, 1)   # MOD13Q1 pixel_reliability values we keep (0 good, 1 marginal)

# ---------------------------------------------------------------------------
# Soil moisture
# ---------------------------------------------------------------------------
SMAP_VALID_RANGE = (0.0, 0.6)    # m3/m3; values outside are treated as missing
SM_ANOMALY_DRY_Z = -1.0          # z-score at or below this = drier than normal

# ---------------------------------------------------------------------------
# Year stress flags
# ---------------------------------------------------------------------------
DROUGHT_YEAR_PERCENTILE = 20     # growing-season rain below this percentile = drought year
HEAT_YEAR_PERCENTILE = 80        # heat days above this percentile = heat year
GROWING_SEASON_MONTHS = {
    "temperate": [4, 5, 6, 7, 8, 9, 10],
    "subtropical": list(range(1, 13)),   # two seasons (kharif + rabi) cover the whole year
}

# ---------------------------------------------------------------------------
# What-If scenario limits (plan section 7)
# ---------------------------------------------------------------------------
SCENARIO_TEMP_RANGE_C = (-2.0, 5.0)
SCENARIO_RAIN_PCT_RANGE = (-50.0, 30.0)
SCENARIO_LOW_CONFIDENCE_TEMP_C = 3.0     # beyond +/- this, confidence label drops to "low"
SCENARIO_LOW_CONFIDENCE_RAIN_PCT = 30.0
# Simplified root-wetness response: change in wetness per mm of monthly water-balance change.
# Labeled "simplified" in the UI. Tune after looking at real data.
WETNESS_PER_MM_BALANCE = 0.001

# ---------------------------------------------------------------------------
# Vulnerable months (plan section 8)
# ---------------------------------------------------------------------------
VULNERABLE_DRY_SPELL_PROB = 0.30
VULNERABLE_HEAT_DAYS = 3.0

# ---------------------------------------------------------------------------
# Alert severity thresholds (plan section 9)
# Each entry: (moderate, high, critical). "direction" says whether bigger is worse.
# ---------------------------------------------------------------------------
ALERT_THRESHOLDS = {
    "drought":      {"variable": "dry_spell_prob",        "levels": (0.30, 0.50, 0.70), "direction": "above"},
    "water_deficit": {"variable": "deficit_mm",           "levels": (30.0, 60.0, 100.0), "direction": "above"},
    "heat":         {"variable": "heat_days",             "levels": (3.0, 7.0, 12.0),   "direction": "above"},
    "frost":        {"variable": "frost_days",            "levels": (1.0, 3.0, 7.0),    "direction": "above"},
    "waterlogging": {"variable": "extreme_rain_days",     "levels": (1.0, 1.5, 2.5),    "direction": "above"},
    "soil_drying":  {"variable": "soil_moisture_anomaly", "levels": (-1.0, -1.5, -2.0), "direction": "below"},
}
SENSITIVE_STAGE_HEAT_WEIGHT = 2.0   # heat days count double in a crop's sensitive growth stage
SEVERITY_ORDER = ["low", "moderate", "high", "critical"]

# ---------------------------------------------------------------------------
# Confidence label (plan section 7)
# ---------------------------------------------------------------------------
CONFIDENCE_HIGH_MIN_YEARS = 15
CONFIDENCE_HIGH_MIN_CORR = 0.85
