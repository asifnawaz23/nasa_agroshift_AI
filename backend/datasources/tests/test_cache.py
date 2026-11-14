import datetime as dt
import json

import pytest

from datasources import cache
from datasources.errors import DataSourceTimeout


@pytest.fixture
def backend(tmp_path):
    return cache.FileCacheBackend(tmp_path)


def test_grid_key_snaps_to_half_degree():
    assert cache.grid_key(42.0, -93.6) == "42.0_-93.5"
    assert cache.grid_key(31.4, 73.1) == "31.5_73.0"
    assert cache.grid_key(25.4, 68.4) == "25.5_68.5"
    assert cache.grid_key(-0.1, 0.1) == "0.0_0.0"  # no "-0.0"


def test_miss_then_hit_calls_fetch_once_with_cell_centre(backend):
    calls = []

    def fetch(lat, lon):
        calls.append((lat, lon))
        return {"value": 1}

    p1, m1 = cache.get_or_fetch("power", 42.0, -93.6, fetch, backend=backend)
    p2, m2 = cache.get_or_fetch("power", 42.1, -93.4, fetch, backend=backend)  # same cell
    assert p1 == p2 == {"value": 1}
    assert calls == [(42.0, -93.5)]
    assert (m1["cache_hit"], m2["cache_hit"]) == (False, True)


def test_failure_with_stale_copy_uses_fallback(backend):
    cache.get_or_fetch("power", 42.0, -93.6, lambda a, b: {"v": "old"}, backend=backend)

    def broken(lat, lon):
        raise DataSourceTimeout("NASA POWER", "slow")

    payload, meta = cache.get_or_fetch("power", 42.0, -93.6, broken, backend=backend, max_age_hours=0)
    assert payload == {"v": "old"}
    assert meta["fallback_used"] is True


def test_failure_without_cache_raises(backend):
    def broken(lat, lon):
        raise DataSourceTimeout("NASA POWER", "slow")

    with pytest.raises(DataSourceTimeout):
        cache.get_or_fetch("power", 10.0, 10.0, broken, backend=backend)


def test_never_uses_another_cells_data(backend):
    cache.get_or_fetch("power", 42.0, -93.6, lambda a, b: {"v": "iowa"}, backend=backend)

    def broken(lat, lon):
        raise DataSourceTimeout("NASA POWER", "slow")

    with pytest.raises(DataSourceTimeout):
        cache.get_or_fetch("power", 43.0, -93.6, broken, backend=backend)


def test_max_age_forces_refetch(backend, tmp_path):
    cache.get_or_fetch("power", 42.0, -93.6, lambda a, b: {"v": 1}, backend=backend)
    f = tmp_path / "power__42.0_-93.5.json"
    rec = json.loads(f.read_text())
    rec["fetched_at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=48)).isoformat()
    f.write_text(json.dumps(rec))
    payload, meta = cache.get_or_fetch("power", 42.0, -93.6, lambda a, b: {"v": 2},
                                       backend=backend, max_age_hours=24)
    assert payload == {"v": 2} and meta["cache_hit"] is False


def test_get_backend_without_django_is_file_backend():
    assert isinstance(cache.get_backend(), cache.FileCacheBackend)
