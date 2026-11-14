"""Convert an AppEEARS point-sample results CSV into the team's pre-pulled files.

Owner: Aman. Works for both products we request:

  MOD13Q1 (NDVI)   -> backend/data/prepulled/<slug>/ndvi.csv   columns: date, ndvi, reliability
  SPL3SMP_E (SMAP) -> backend/data/prepulled/<slug>/smap.csv   columns: date, sm

The AppEEARS "ID" column is our location slug (we typed it in the request).
Quality filtering:
  NDVI: keep pixel_reliability 0 (good) and 1 (marginal), drop fill values
  SMAP: AM soil moisture where retrieval quality bit 0 is clear (recommended quality);
        PM soil moisture fills days with no good AM value; -9999 fill values dropped

Usage:
    python tools/appeears_to_prepulled.py <results.csv> [--only slug1,slug2] [--out backend/data/prepulled]

Prints a per-site summary including a "crop seasonality" check: real cropland swings from
~0.2 (bare) to 0.6+ (peak). A flat, low curve means the point is probably a town or mixed land.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "backend" / "data" / "prepulled"


def _col(df, *must):
    for c in df.columns:
        if all(m in c for m in must) and not c.endswith(("Description", "bitmask", "MODLAND")):
            return c
    return None


def convert_ndvi(df):
    ndvi, rel = _col(df, "NDVI"), _col(df, "pixel_reliability")
    out = pd.DataFrame({"slug": df["ID"], "date": pd.to_datetime(df["Date"]).dt.date,
                        "ndvi": pd.to_numeric(df[ndvi], errors="coerce"),
                        "reliability": pd.to_numeric(df[rel], errors="coerce")})
    out = out[out["reliability"].isin([0, 1]) & out["ndvi"].between(-0.2, 1.0)]
    return out, "ndvi.csv"


def convert_smap(df):
    am = _col(df, "AM_soil_moisture")
    pm = _col(df, "PM_soil_moisture_pm")
    flag = _col(df, "AM_retrieval_qual_flag")
    s = pd.DataFrame({"slug": df["ID"], "date": pd.to_datetime(df["Date"]).dt.date})
    a = pd.to_numeric(df[am], errors="coerce")
    a = a.where((a >= 0) & (a <= 0.6))
    if flag is not None:
        q = pd.to_numeric(df[flag], errors="coerce").fillna(1).astype(int)
        a = a.where((q & 1) == 0)  # bit 0 set = recommended quality NOT achieved
    if pm is not None:
        p = pd.to_numeric(df[pm], errors="coerce")
        a = a.fillna(p.where((p >= 0) & (p <= 0.6)))
    s["sm"] = a
    return s.dropna(subset=["sm"]), "smap.csv"


def seasonality(site_ndvi):
    m = site_ndvi.assign(month=pd.to_datetime(site_ndvi["date"]).dt.month).groupby("month")["ndvi"].mean()
    lo, hi = m.min(), m.max()
    if hi >= 0.65 and hi - lo >= 0.35:
        verdict = "strong crop seasons (cropland)"
    elif hi >= 0.45 and hi - lo >= 0.2:
        verdict = "MIXED: some crops, but probably mixed with town, roads or grass"
    else:
        verdict = "WEAK SEASONALITY: probably town or bare land"
    return lo, hi, verdict


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    df = pd.read_csv(args.csv)
    if _col(df, "NDVI"):
        data, name = convert_ndvi(df)
    elif _col(df, "soil_moisture"):
        data, name = convert_smap(df)
    else:
        sys.exit("unknown AppEEARS product: no NDVI or soil_moisture column")

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    for slug, site in data.groupby("slug"):
        if only and slug not in only:
            print(f"skip {slug}")
            continue
        folder = Path(args.out) / slug
        folder.mkdir(parents=True, exist_ok=True)
        cols = ["date", "ndvi", "reliability"] if name == "ndvi.csv" else ["date", "sm"]
        site[cols].sort_values("date").to_csv(folder / name, index=False)
        dates = pd.to_datetime(site["date"])
        msg = f"{slug:20s} {name:9s} {len(site):5d} rows  {dates.min().date()}..{dates.max().date()}"
        if name == "ndvi.csv":
            lo, hi, verdict = seasonality(site)
            msg += f"  monthly NDVI {lo:.2f}-{hi:.2f}  {verdict}"
        else:
            msg += f"  sm mean {site['sm'].mean():.3f}"
        print(msg)


if __name__ == "__main__":
    main()
