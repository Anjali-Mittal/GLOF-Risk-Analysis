"""Stage 3: stored-water volume from lake area, using four published area-volume formulas.

Reads  : data/labels/dangerous_lake_labels.csv
         data/processed/lake_area_timeseries/*.csv
         outputs/tables/stage2_predictions.csv     (risk score from Stage 2C)
Writes : outputs/tables/stage3_volume.csv

Run from the repo root:  python src/stage3_volume/volume.py

All formulas take A in m2. Volumes are returned in million m3 (MCM) for readability.
We report the SPREAD of the four formulas, never one number: Cook & Quincey (2015)
show these relations can be wrong by an order of magnitude for some lake types.

UNIT WARNING (Cook & Quincey):
  Paper text confirms O'Connor and Huggel give V in m3. The Cook & Quincey fit
  V = 7e-8 * A^1.4546, taken literally with A in m2 and V in m3, gives ~37 m3 for a
  1 km2 lake - impossible. It lands within ~10% of Huggel only if V is in MILLION m3,
  so we read it that way (CQ_V_UNIT_M3 = 1e6). Confirm against the paper's Table/Eq
  before quoting it in the report.
"""
import os

import numpy as np
import pandas as pd

AREA_YEAR = 2022            # same cutoff as Stage 2: "what a forecaster knew at end of 2022"
FLAG_THRESHOLD = 0.5        # risk_prob cut for "flagged". Scores are NOT calibrated probabilities.
CQ_V_UNIT_M3 = 1e6          # see UNIT WARNING above
TS_DIR = "data/processed/lake_area_timeseries"


def v_oconnor(a_m2):  return 3.114 * a_m2 + 0.0001685 * a_m2 ** 2            # m3
def v_huggel(a_m2):   return 0.104 * a_m2 ** 1.42                             # m3
def v_evans(a_m2):    return 0.035 * a_m2 ** 1.5                              # m3
def v_cook(a_m2):     return 7e-8 * a_m2 ** 1.4546 * CQ_V_UNIT_M3             # m3 (unit assumed, see top)

FORMULAS = {"oconnor": v_oconnor, "huggel": v_huggel, "cook_quincey": v_cook, "evans": v_evans}


def volumes_mcm(area_km2: float) -> dict:
    """Million m3 from each formula, plus min / median / max across formulas."""
    if area_km2 is None or not np.isfinite(area_km2) or area_km2 <= 0:
        return {**{k: np.nan for k in FORMULAS}, "vol_min": np.nan, "vol_median": np.nan,
                "vol_max": np.nan, "spread_ratio": np.nan}
    a = area_km2 * 1e6
    v = {k: f(a) / 1e6 for k, f in FORMULAS.items()}
    vals = np.array(list(v.values()))
    return {**v, "vol_min": vals.min(), "vol_median": float(np.median(vals)), "vol_max": vals.max(),
            "spread_ratio": vals.max() / vals.min()}


def area_for(lake_id: str, year: int = AREA_YEAR):
    """Sentinel-2 area in `year`; falls back to the nearest earlier S2 year (2019+). Returns (area, year_used)."""
    ts = pd.read_csv(f"{TS_DIR}/{lake_id}.csv", parse_dates=["date"])
    ts["year"] = ts.date.dt.year
    ok = ts[(ts.year >= 2019) & (ts.year <= year)].dropna(subset=["area_km2"])
    if ok.empty:
        return np.nan, np.nan
    r = ok.sort_values("year").iloc[-1]
    return float(r.area_km2), int(r.year)


def main():
    lab = pd.read_csv("data/labels/dangerous_lake_labels.csv")[["lake_id", "name", "basin", "area", "label"]]
    pred = pd.read_csv("outputs/tables/stage2_predictions.csv")[["lake_id", "risk_prob"]]
    d = lab.merge(pred, on="lake_id", how="left")
    rows = []
    for r in d.itertuples():
        a, y = area_for(r.lake_id)
        rows.append({"lake_id": r.lake_id, "area_s2_km2": a, "area_year": y, **volumes_mcm(a)})
    out = d.merge(pd.DataFrame(rows), on="lake_id")
    out["flagged"] = out.risk_prob >= FLAG_THRESHOLD
    out["area_ratio_s2_vs_inventory"] = out.area_s2_km2 / out.area
    out = out.sort_values("risk_prob", ascending=False)
    out.to_csv("outputs/tables/stage3_volume.csv", index=False)

    f = out[out.flagged]
    print(f"lakes {len(out)} | flagged {len(f)} | no S2 area: {out.area_s2_km2.isna().sum()}")
    print("median spread (max/min across formulas), flagged:", round(f.spread_ratio.median(), 2))
    print(f[["vol_min", "vol_median", "vol_max"]].describe().round(2).to_string())
    print(out[out.lake_id.str.startswith("SPECIAL")][
        ["lake_id", "area_s2_km2", "oconnor", "huggel", "cook_quincey", "evans", "risk_prob"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
