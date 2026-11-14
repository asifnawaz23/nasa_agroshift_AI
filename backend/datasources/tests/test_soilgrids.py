import json
from pathlib import Path

import pytest

from datasources import cache, soilgrids
from datasources.errors import DataSourceTimeout

FIXTURE = Path(__file__).parent / "fixtures" / "soilgrids_iowa.json"


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code, self._payload, self.text = status, payload, "err"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(soilgrids, "RETRY_WAIT_S", 0)


@pytest.mark.parametrize("sand,silt,clay,expected", [
    (92, 4, 4, "sand"),
    (80, 12, 8, "loamy sand"),
    (65, 25, 10, "sandy loam"),
    (40, 40, 20, "loam"),
    (20, 70, 10, "silt loam"),
    (5, 88, 7, "silt"),
    (65, 15, 20, "sandy clay loam"),
    (30, 35, 35, "clay loam"),
    (10, 55, 35, "silty clay loam"),
    (50, 5, 45, "sandy clay"),
    (5, 50, 45, "silty clay"),
    (20, 20, 60, "clay"),
])
def test_usda_texture_triangle(sand, silt, clay, expected):
    assert soilgrids.usda_texture(sand, silt, clay) == expected


def test_parse_real_iowa_response():
    s = soilgrids.parse_soilgrids(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert s["available"] is True
    assert 25 < s["clay_pct"] < 35 and 15 < s["sand_pct"] < 30
    assert abs(s["clay_pct"] + s["sand_pct"] + s["silt_pct"] - 100) < 2
    assert 5.5 < s["ph"] < 7.5
    assert s["texture"] in {"clay loam", "silty clay loam", "loam"}
    assert s["organic_matter_pct"] > 1


def test_no_data_point_is_marked_unavailable():
    payload = {"properties": {"layers": [
        {"name": n, "unit_measure": {"d_factor": 10},
         "depths": [{"label": "0-5cm", "values": {"mean": None}}]} for n in soilgrids.PROPERTIES]}}
    s = soilgrids.parse_soilgrids(payload)
    assert s["available"] is False and s["texture"] is None


def test_retries_after_rate_limit():
    ok = json.loads(FIXTURE.read_text(encoding="utf-8"))
    session = FakeSession([FakeResponse(429), FakeResponse(200, ok)])
    s = soilgrids.fetch_soilgrids(42.0, -93.6, session=session)
    assert s["available"] and len(session.calls) == 2
    sent = dict((k, v) for k, v in session.calls[0] if k in ("lat", "lon"))
    assert sent == {"lat": 42.0, "lon": -93.6}


def test_soil_grid_is_finer_than_climate_grid():
    assert cache.grid_key(42.0012, -93.6049, cache.SOIL_GRID_STEP_DEG) == "42.00_-93.60"
    assert cache.grid_key(42.0, -93.6) == "42.0_-93.5"


def test_get_soil_returns_none_with_error_when_service_down(tmp_path, monkeypatch):
    def broken(lat, lon):
        raise DataSourceTimeout("ISRIC SoilGrids", "slow")

    monkeypatch.setattr(soilgrids, "fetch_soilgrids", broken)
    soil, meta = cache.get_soil(25.4, 68.4, backend=cache.FileCacheBackend(tmp_path))
    assert soil is None and "SoilGrids" in meta["error"]
