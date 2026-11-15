"""ISRIC SoilGrids v2.0 point client (non-NASA, global, no API key).

Owner: Aman. Contract (plan section 4.2 / 15.3):

    fetch_soilgrids(lat, lon) -> dict      (raises DataSourceError on network/HTTP problems)
    parse_soilgrids(payload) -> dict       (pure function)

Returned dict (top 30 cm, depth-weighted mean of 0-5, 5-15, 15-30 cm):
    available         False if SoilGrids has no soil here (water, city, ice) -> all values None
    clay_pct, sand_pct, silt_pct   %
    soc_g_kg          soil organic carbon, g/kg
    organic_matter_pct  soc * 1.724 / 10 (van Bemmelen factor), %
    ph                pH in water
    texture           USDA texture class, e.g. "clay loam"
    texture_group     coarse | medium | fine
    drainage_hint     fast | moderate | slow       (from texture; heuristic)
    erodibility_hint  low | moderate | high        (from silt/clay; heuristic)
    depth, source, resolution_m

Units: SoilGrids stores integers; divide by unit_measure.d_factor (10 for these properties):
clay/sand/silt g/kg -> %, soc dg/kg -> g/kg, phh2o pH*10 -> pH.
Fair use: about 5 requests per minute, so always go through the cache.
"""
from __future__ import annotations

import time

import requests

from .errors import DataSourceBadResponse, DataSourceError, DataSourceTimeout

SOURCE = "ISRIC SoilGrids"
BASE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROPERTIES = ["clay", "sand", "silt", "soc", "phh2o"]
DEPTHS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}  # label -> thickness (weights)
TIMEOUT_S = 25
RETRIES = 1
RETRY_WAIT_S = 3.0

COARSE = {"sand", "loamy sand", "sandy loam"}
FINE = {"clay", "silty clay", "sandy clay", "clay loam", "silty clay loam"}


def usda_texture(sand: float, silt: float, clay: float) -> str:
    """USDA soil texture triangle (percentages; normalized to sum to 100)."""
    total = sand + silt + clay
    if total <= 0:
        raise ValueError("sand + silt + clay must be > 0")
    sand, silt, clay = (100 * v / total for v in (sand, silt, clay))
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 2 * clay < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52) or (clay < 7 and silt < 50):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    return "clay"


def texture_group(texture: str) -> str:
    if texture in COARSE:
        return "coarse"
    if texture in FINE:
        return "fine"
    return "medium"


def _r(x, n=1):
    return None if x is None else round(float(x), n)


def _empty(reason):
    out = {k: None for k in ["clay_pct", "sand_pct", "silt_pct", "soc_g_kg", "organic_matter_pct",
                             "ph", "texture", "texture_group", "drainage_hint", "erodibility_hint"]}
    out.update(available=False, reason=reason, depth="0-30cm", source=SOURCE, resolution_m=250)
    return out


def parse_soilgrids(payload: dict) -> dict:
    try:
        layers = payload["properties"]["layers"]
    except (KeyError, TypeError) as exc:
        raise DataSourceBadResponse(SOURCE, "response has no properties.layers") from exc

    values = {}
    for layer in layers:
        name = layer.get("name")
        factor = (layer.get("unit_measure") or {}).get("d_factor") or 1
        num = den = 0.0
        for d in layer.get("depths", []):
            w = DEPTHS.get(d.get("label"))
            v = (d.get("values") or {}).get("mean")
            if w is None or v is None:
                continue
            num += w * v / factor
            den += w
        values[name] = num / den if den else None

    if any(values.get(p) is None for p in ("clay", "sand", "silt")):
        return _empty("SoilGrids has no soil data here (water, built-up area or no data)")

    clay, sand, silt = values["clay"], values["sand"], values["silt"]
    tex = usda_texture(sand, silt, clay)
    group = texture_group(tex)
    soc = values.get("soc")
    om = soc * 1.724 / 10 if soc is not None else None
    if silt >= 50:
        erod = "high"
    elif clay >= 35:
        erod = "low"
    else:
        erod = "moderate"
    return {
        "available": True,
        "clay_pct": _r(clay), "sand_pct": _r(sand), "silt_pct": _r(silt),
        "soc_g_kg": _r(soc), "organic_matter_pct": _r(om, 2), "ph": _r(values.get("phh2o")),
        "texture": tex, "texture_group": group,
        "drainage_hint": {"coarse": "fast", "medium": "moderate", "fine": "slow"}[group],
        "erodibility_hint": erod,
        "depth": "0-30cm", "source": SOURCE, "resolution_m": 250,
    }


def fetch_soilgrids(lat: float, lon: float, *, timeout: float = TIMEOUT_S,
                    retries: int = RETRIES, session=None) -> dict:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"invalid coordinates: lat={lat}, lon={lon}")
    params = [("lon", round(lon, 4)), ("lat", round(lat, 4)), ("value", "mean")]
    params += [("property", p) for p in PROPERTIES] + [("depth", d) for d in DEPTHS]
    http = session or requests
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = http.get(BASE_URL, params=params, timeout=timeout)
            if resp.status_code == 200:
                return parse_soilgrids(resp.json())
            if resp.status_code == 429:
                last_exc = DataSourceBadResponse(SOURCE, "rate limited (HTTP 429), try again in a minute")
            elif 400 <= resp.status_code < 500:
                raise DataSourceBadResponse(SOURCE, f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                last_exc = DataSourceBadResponse(SOURCE, f"HTTP {resp.status_code}")
        except requests.Timeout as exc:
            last_exc = DataSourceTimeout(SOURCE, f"no answer within {timeout}s")
            last_exc.__cause__ = exc
        except requests.RequestException as exc:
            last_exc = DataSourceError(SOURCE, f"connection problem: {exc}")
        except ValueError as exc:
            last_exc = DataSourceBadResponse(SOURCE, "response is not valid JSON")
            last_exc.__cause__ = exc
        if attempt < retries:
            time.sleep(RETRY_WAIT_S * (attempt + 1))
    raise last_exc  # type: ignore[misc]


# USDA texture classes the farmer can pick (same names usda_texture() returns).
TEXTURE_CLASSES = (
    "sand", "loamy sand", "sandy loam", "loam", "silt loam", "silt", "sandy clay loam",
    "clay loam", "silty clay loam", "sandy clay", "silty clay", "clay",
)


# Everyday names a farmer picks in the form -> the USDA texture class used by the engine.
TEXTURE_ALIASES = {
    "sandy": "sandy loam", "sandy soil": "sandy loam",
    "loamy": "loam", "loam soil": "loam",
    "clayey": "clay", "clay soil": "clay", "heavy": "clay",
    "silty": "silt loam", "silt soil": "silt loam",
}


def normalize_texture(texture: str | None) -> str | None:
    """'Sandy' -> 'sandy loam', 'Clay' -> 'clay'; unknown names are returned as typed."""
    if texture is None:
        return None
    name = " ".join(str(texture).strip().lower().replace("_", " ").split())
    if not name:
        return None
    return TEXTURE_ALIASES.get(name, name)


def apply_texture_override(soil: dict | None, texture: str | None) -> dict | None:
    """The farmer knows their field better than a 250 m map: use their texture.

    Keeps SoilGrids' organic matter and pH when available, and recomputes the texture-based
    hints (drainage, erodibility) that the alerts and erosion score use. Returns `soil`
    unchanged when no override is given.
    """
    texture = normalize_texture(texture)
    if not texture:
        return soil
    if texture not in TEXTURE_CLASSES:
        raise ValueError(f"Unknown soil texture: {texture}")
    group = texture_group(texture)
    if texture in ("silt", "silt loam"):
        erod = "high"
    elif group == "fine":
        erod = "low"
    else:
        erod = "moderate"
    out = dict(soil) if soil and soil.get("available", True) else {
        k: None for k in ("clay_pct", "sand_pct", "silt_pct", "soc_g_kg", "organic_matter_pct", "ph")}
    if soil and soil.get("texture") and soil.get("texture") != texture:
        out["measured_texture"] = soil.get("texture")
    out.update(
        available=True,
        texture=texture,
        texture_group=group,
        drainage_hint={"coarse": "fast", "medium": "moderate", "fine": "slow"}[group],
        erodibility_hint=erod,
        texture_source="farmer",
    )
    out.setdefault("source", SOURCE)
    return out
