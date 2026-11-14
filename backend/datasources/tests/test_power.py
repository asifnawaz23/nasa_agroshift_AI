import datetime as dt
import math

import pytest
import requests

from datasources import power
from datasources.errors import DataSourceBadResponse, DataSourceTimeout


def make_payload(dates, value=1.0, missing_on=None):
    params = {}
    for key in power.COLUMN_MAP:
        params[key] = {d: (-999.0 if d == missing_on else value) for d in dates}
    return {"properties": {"parameter": params}}


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload
        self.text = "error"

    def json(self):
        return self._payload


class FakeSession:
    """Returns responses from a function of the request params; records every call."""

    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        return self.handler(params)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(power, "RETRY_WAIT_S", 0)


def test_payload_to_df_maps_columns_and_missing_values():
    df = power.payload_to_df(make_payload(["20240101", "20240102"], 5.0, missing_on="20240102"))
    assert list(df.columns) == power.COLUMNS
    assert df["date"].iloc[0] == dt.datetime(2024, 1, 1)
    assert df["t2m"].iloc[0] == 5.0
    assert math.isnan(df["precip"].iloc[1])


def test_payload_without_data_is_bad_response():
    with pytest.raises(DataSourceBadResponse):
        power.payload_to_df({"messages": ["oops"]})


def test_fetch_sends_ag_community_and_dates():
    session = FakeSession(lambda p: FakeResponse(200, make_payload(["20200101"])))
    df = power.fetch_power_daily(42.0, -93.6, "2020-01-01", "2020-01-01", session=session)
    assert len(df) == 1
    p = session.calls[0]
    assert p["community"] == "AG" and p["start"] == "20200101" and p["end"] == "20200101"
    assert set(p["parameters"].split(",")) == set(power.COLUMN_MAP)


def test_falls_back_to_one_request_per_year():
    def handler(p):
        if p["start"][:4] != p["end"][:4]:  # whole multi-year range fails
            return FakeResponse(503)
        year = p["start"][:4]
        return FakeResponse(200, make_payload([f"{year}0101", f"{year}1231"]))

    session = FakeSession(handler)
    df = power.fetch_power_daily(31.4, 73.1, "2020-01-01", "2022-12-31", session=session)
    assert len(df) == 6
    assert sorted({c["start"][:4] for c in session.calls[-3:]}) == ["2020", "2021", "2022"]


def test_timeout_raises_datasource_timeout():
    def handler(p):
        raise requests.Timeout()

    with pytest.raises(DataSourceTimeout):
        power.fetch_power_daily(25.4, 68.4, "2020-01-01", "2020-12-31", session=FakeSession(handler), retries=1)


def test_invalid_coordinates_rejected():
    with pytest.raises(ValueError):
        power.fetch_power_daily(95, 0, "2020-01-01", "2020-01-02")


def test_default_range_is_last_20_complete_years():
    assert power.default_range(dt.date(2026, 11, 14)) == (dt.date(2006, 1, 1), dt.date(2025, 12, 31))


def test_records_round_trip():
    df = power.payload_to_df(make_payload(["20240101", "20240102"], 2.5, missing_on="20240101"))
    back = power.records_to_df(power.df_to_records(df))
    assert back["t2m"].iloc[1] == 2.5 and math.isnan(back["t2m"].iloc[0])
    assert back["date"].iloc[1] == dt.datetime(2024, 1, 2)
