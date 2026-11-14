"""Convert a NASA POWER daily point JSON response into the team's CSV format.

Usage:
    python tools/power_json_to_csv.py <input.json> <output.csv>

Output columns (plan section 7 / 15.3):
    date, t2m, t2m_max, t2m_min, precip, root_wetness, solar, rh
Missing values (-999 in POWER) are written as empty cells (read as NaN by pandas).
"""
import csv
import json
import sys

COLUMN_MAP = {
    "T2M": "t2m",
    "T2M_MAX": "t2m_max",
    "T2M_MIN": "t2m_min",
    "PRECTOTCORR": "precip",
    "GWETROOT": "root_wetness",
    "ALLSKY_SFC_SW_DWN": "solar",
    "RH2M": "rh",
}
FILL = -999


def main(src, dst):
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    params = data["properties"]["parameter"]
    dates = sorted(next(iter(params.values())).keys())

    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date"] + list(COLUMN_MAP.values()))
        for d in dates:
            row = [f"{d[:4]}-{d[4:6]}-{d[6:]}"]
            for key in COLUMN_MAP:
                v = params.get(key, {}).get(d)
                row.append("" if v is None or v <= FILL else v)
            w.writerow(row)
    print(f"wrote {len(dates)} rows to {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
