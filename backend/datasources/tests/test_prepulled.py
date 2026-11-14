import json

import pandas as pd

from datasources import prepulled
from datasources.power import df_to_records, payload_to_df


def test_locations_file_is_valid():
    locs = prepulled.load_locations()
    slugs = [l["slug"] for l in locs]
    assert len(slugs) == len(set(slugs)) == 3
    for l in locs:
        assert -90 <= l["lat"] <= 90 and -180 <= l["lon"] <= 180
        assert l["zone"] in {"temperate", "subtropical"} and l["tier"] in {"featured", "us_enhanced"}
        assert l["name"] and l["name_ur"] and l["default_rotation"]


def test_find_featured_near_and_far():
    iowa = prepulled.get_location("iowa-central")
    assert prepulled.find_featured(iowa["lat"] + 0.02, iowa["lon"])["slug"] == "iowa-central"  # ~2 km
    assert prepulled.find_featured(iowa["lat"] + 0.2, iowa["lon"]) is None                      # ~22 km
    assert prepulled.find_featured(0, 0) is None


def test_load_prepulled_reads_all_files(tmp_path):
    folder = tmp_path / "test-pin"
    folder.mkdir()
    pd.DataFrame({"date": ["2020-01-01", "2020-01-17"], "ndvi": [0.2, 0.3], "reliability": [0, 1]}) \
        .to_csv(folder / "ndvi.csv", index=False)
    pd.DataFrame({"date": ["2020-01-01"], "sm": [0.25]}).to_csv(folder / "smap.csv", index=False)
    pd.DataFrame({"year": [2020], "month": [1], "precip_mm": [20.0], "tmean_c": [-5.0]}) \
        .to_csv(folder / "prism_monthly.csv", index=False)
    power_payload = {"properties": {"parameter": {k: {"20200101": 1.0} for k in
                                                  ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "GWETROOT",
                                                   "ALLSKY_SFC_SW_DWN", "RH2M"]}}}
    (folder / "power_cache.json").write_text(json.dumps({"payload": df_to_records(payload_to_df(power_payload))}))
    (folder / "soil.json").write_text(json.dumps({"payload": {"available": True, "texture": "loam"}}))

    d = prepulled.load_prepulled("test-pin", base=tmp_path)
    assert list(d["ndvi"].columns) == ["date", "ndvi", "reliability"] and d["ndvi"]["date"].dtype.kind == "M"
    assert d["smap"]["sm"].iloc[0] == 0.25
    assert d["prism"]["precip_mm"].iloc[0] == 20.0
    assert len(d["power"]) == 1 and d["soil"]["texture"] == "loam"
    assert d["files"] == ["ndvi.csv", "power_cache.json", "prism_monthly.csv", "smap.csv", "soil.json"]


def test_missing_folder_gives_all_none(tmp_path):
    d = prepulled.load_prepulled("nowhere", base=tmp_path)
    assert d["smap"] is None and d["ndvi"] is None and d["power"] is None and d["files"] == []
