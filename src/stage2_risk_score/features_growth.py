"""Stage 2, step A: growth features from the Stage 1 area time series.

Reads  : data/labels/dangerous_lake_labels.csv, data/processed/lake_area_timeseries/*.csv
Writes : outputs/tables/stage2_features_growth.csv

Only Sentinel-2 years are used (2019 onward), and only up to FEATURE_END_YEAR.
FEATURE_END_YEAR = 2022 means "the model only sees what a forecaster would have
known at the end of 2022" - before South Lhonak burst (Oct 2023) and Thame (Aug 2024).
"""
import numpy as np
import pandas as pd
from scipy.stats import theilslopes

START_YEAR = 2019          # first Sentinel-2 year (see data/processed/lake_area_timeseries/README.md)
FEATURE_END_YEAR = 2022    # change this one number to re-run the whole pipeline with a different cutoff
MIN_AREA_FLOOR = 0.02      # km2. Stops tiny lakes from producing huge "relative" growth
TS_DIR = "data/processed/lake_area_timeseries"


def growth_features(ts: pd.DataFrame) -> dict:
    """ts has columns year, area_km2 (NaN = no usable image that year)."""
    w = ts[(ts.year >= START_YEAR) & (ts.year <= FEATURE_END_YEAR)].dropna(subset=["area_km2"])
    n = len(w)
    out = {"n_valid_years": n, "area_window_mean_km2": w.area_km2.mean() if n else np.nan,
           "growth_rate": np.nan, "acceleration": np.nan}
    if n < 3:
        return out                                     # not enough points to say anything
    scale = max(w.area_km2.mean(), MIN_AREA_FLOOR)     # divide by size -> "fraction of lake per year"
    # Theil-Sen = median of all pairwise slopes, so one bad year cannot drag the line
    slope = theilslopes(w.area_km2.values, w.year.values)[0]
    out["growth_rate"] = float(np.clip(slope / scale, -0.5, 0.5))
    if n >= 4:                                         # a curve needs 4+ points to mean anything
        quad = np.polyfit(w.year.values - w.year.values.mean(), w.area_km2.values, 2)[0]
        out["acceleration"] = float(np.clip(2 * quad / scale, -0.5, 0.5))
    return out


if __name__ == "__main__":
    labels = pd.read_csv("data/labels/dangerous_lake_labels.csv")
    rows = []
    for lake_id in labels.lake_id:
        ts = pd.read_csv(f"{TS_DIR}/{lake_id}.csv", parse_dates=["date"])
        ts["year"] = ts.date.dt.year
        rows.append({"lake_id": lake_id, **growth_features(ts)})
    feats = pd.DataFrame(rows)
    feats.to_csv("outputs/tables/stage2_features_growth.csv", index=False)
    print(f"{len(feats)} lakes | usable (>=3 valid years): {(feats.n_valid_years >= 3).sum()}")
    print(feats[["growth_rate", "acceleration"]].describe().round(4).to_string())