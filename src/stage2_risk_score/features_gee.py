"""Stage 2, step B: terrain slope and rainfall features, pulled from Google Earth Engine.

Reads  : data/labels/dangerous_lake_labels.csv
Writes : outputs/tables/stage2_features_terrain_rain.csv
Cache  : data/raw/chirps/{lake_id}.csv   (gitignored, so re-runs skip finished lakes)

Run from the repo root:  python src/stage2_risk_score/features_gee.py
"""
import os
import time

import ee
import numpy as np
import pandas as pd

ee.Initialize(project="glof-ras")

FEATURE_END_YEAR = 2022      # keep identical to features_growth.py
WINDOW_START = 2019          # rainfall features are averaged over WINDOW_START..FEATURE_END_YEAR
BASELINE_START = 2000        # CHIRPS history used to learn what "extreme" means at each lake
RING_WIDTH_M = 1000          # slope is measured in a 1 km ring just outside the lake edge
CACHE = "data/raw/chirps"


# ---------------------------------------------------------------- terrain slope
def slope_features(labels: pd.DataFrame) -> pd.DataFrame:
    dem_col = ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM")
    dem = dem_col.mosaic().setDefaultProjection(dem_col.first().projection())
    slope = ee.Terrain.slope(dem).rename("slope")
    img = slope.addBands(slope.gt(30).rename("steep_frac"))      # steep_frac = share of pixels > 30 degrees

    feats = []
    for r in labels.itertuples():
        pt = ee.Geometry.Point([r.lon, r.lat])
        r_in = float(np.sqrt(r.area * 1e6 / np.pi))               # lake "radius" from its inventory area (km2 -> m)
        ring = pt.buffer(r_in + RING_WIDTH_M).difference(pt.buffer(r_in), 1)
        feats.append(ee.Feature(ring, {"lake_id": r.lake_id}))
    out = img.reduceRegions(ee.FeatureCollection(feats), ee.Reducer.mean(), scale=30).getInfo()
    rows = [f["properties"] for f in out["features"]]
    df = pd.DataFrame(rows)[["lake_id", "slope", "steep_frac"]]
    return df.rename(columns={"slope": "slope_ring_mean_deg"})


# ---------------------------------------------------------------- CHIRPS rainfall
def fetch_chirps(lake_id, lat, lon) -> pd.DataFrame:
    """Daily rainfall (mm) at the lake, BASELINE_START..FEATURE_END_YEAR. Cached on disk."""
    path = f"{CACHE}/{lake_id}.csv"
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["date"])
    pt = ee.Geometry.Point([lon, lat])
    parts = []
    # two chunks, because Earth Engine refuses to return more than ~5000 images at once
    for a, b in [(f"{BASELINE_START}-01-01", "2013-01-01"), ("2013-01-01", f"{FEATURE_END_YEAR + 1}-01-01")]:
        col = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(a, b).select("precipitation")
        for attempt in range(3):
            try:
                rows = col.getRegion(pt, 5566).getInfo()
                break
            except Exception as e:                      # quota / timeout hiccups
                print("retry", lake_id, e); time.sleep(10)
        else:
            raise RuntimeError(f"CHIRPS failed for {lake_id}")
        parts.append(pd.DataFrame(rows[1:], columns=rows[0]))
    df = pd.concat(parts)
    df["date"] = pd.to_datetime(df["time"], unit="ms")
    df = df[["date", "precipitation"]].dropna().rename(columns={"precipitation": "rain_mm"})
    os.makedirs(CACHE, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def rain_features(daily: pd.DataFrame) -> dict:
    """Pure function (no Earth Engine) so it can be tested with fake data.
    daily: columns date, rain_mm."""
    d = daily.sort_values("date").set_index("date")
    base = d[d.index.year < WINDOW_START]
    wet = base.rain_mm[base.rain_mm >= 1.0]                       # wet days only, otherwise p95 is ~0
    p95 = wet.quantile(0.95) if len(wet) > 50 else np.nan

    win = d[(d.index.year >= WINDOW_START) & (d.index.year <= FEATURE_END_YEAR)]
    roll5 = win.rain_mm.rolling("5D").sum()                       # 5-day cumulative rainfall
    years = range(WINDOW_START, FEATURE_END_YEAR + 1)
    max5 = [roll5[roll5.index.year == y].max() for y in years]    # worst 5-day spell of each year
    n_ext = [(win.rain_mm[win.index.year == y] > p95).sum() for y in years]
    return {"rain_max5d_mm": float(np.nanmean(max5)),
            "rain_extreme_days": float(np.mean(n_ext)) if not np.isnan(p95) else np.nan,
            "rain_p95_wetday_mm": float(p95)}


if __name__ == "__main__":
    labels = pd.read_csv("data/labels/dangerous_lake_labels.csv")
    terrain = slope_features(labels)
    print("slope done:", len(terrain), "lakes")
    rain_rows = []
    for i, r in enumerate(labels.itertuples(), 1):
        rain_rows.append({"lake_id": r.lake_id, **rain_features(fetch_chirps(r.lake_id, r.lat, r.lon))})
        if i % 10 == 0:
            print(f"rain {i}/{len(labels)}")
    out = terrain.merge(pd.DataFrame(rain_rows), on="lake_id")
    out.to_csv("outputs/tables/stage2_features_terrain_rain.csv", index=False)
    print(out.describe().round(2).T.to_string())