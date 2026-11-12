"""Stage 2, step C: train + validate the logistic-regression risk score.

Reads  : data/labels/dangerous_lake_labels.csv
         outputs/tables/stage2_features_growth.csv
         outputs/tables/stage2_features_terrain_rain.csv
Writes : outputs/models/risk_model.joblib
         outputs/tables/stage2_cv_metrics.json
         outputs/tables/stage2_predictions.csv
         outputs/tables/stage2_coefficients.csv

Run from the repo root:  python src/stage2_risk_score/train_model.py

Design choices (each one answers a leakage / small-sample risk):
  * South Lhonak + Thame are HELD OUT of training. They are the only true
    outcome labels, so they are the honest test, not just two more rows.
  * Cross-validation is SPATIAL (grouped by 0.5 degree grid cell). Lakes in the
    same valley share rain, slope and label source; random CV would flatter us.
  * Lake size is the dominant signal (ICIMOD ranking uses size). We report the
    model WITH and WITHOUT size, plus an area-only baseline, so the gain from
    the time-series / terrain / rain features is visible.
  * Imputation + scaling live inside the Pipeline, so they are fit on train
    folds only.
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

SEED = 42
HOLDOUT_IDS = ["SPECIAL_SOUTH_LHONAK", "SPECIAL_THAME"]
GRID_DEG = 0.5
N_SPLITS = 5
N_REPEATS = 20            # repeated grouped CV with shuffled group assignment
C = 0.5                   # fairly strong L2: ~190 rows, 8 features

FEATURES_ALL = ["log_area", "growth_rate", "acceleration", "slope_ring_mean_deg",
                "steep_frac", "rain_max5d_mm", "rain_extreme_days", "rain_p95_wetday_mm"]
FEATURES_NO_AREA = [f for f in FEATURES_ALL if f != "log_area"]
FEATURES_AREA_ONLY = ["log_area"]


def load() -> pd.DataFrame:
    lab = pd.read_csv("data/labels/dangerous_lake_labels.csv")
    g = pd.read_csv("outputs/tables/stage2_features_growth.csv")
    t = pd.read_csv("outputs/tables/stage2_features_terrain_rain.csv")
    d = lab.merge(g, on="lake_id", how="left", validate="1:1").merge(t, on="lake_id", how="left", validate="1:1")
    # Use the Sentinel-2 window mean (what a forecaster measures today), fall back to inventory area.
    a = d.area_window_mean_km2.fillna(d.area)
    d["log_area"] = np.log10(a.clip(lower=0.005))
    d["cell"] = (np.floor(d.lat / GRID_DEG).astype(int).astype(str) + "_" +
                 np.floor(d.lon / GRID_DEG).astype(int).astype(str))
    return d


def make_pipeline(features) -> Pipeline:
    # add_indicator keeps "growth was missing" as a signal instead of silently hiding it
    pre = ColumnTransformer([("num", Pipeline([
        ("imp", SimpleImputer(strategy="median", add_indicator=True)),
        ("sc", StandardScaler())]), list(range(len(features))))])
    return Pipeline([("pre", pre),
                     ("clf", LogisticRegression(C=C, class_weight="balanced", max_iter=2000, random_state=SEED))])


def grouped_cv(df, features, n_repeats=N_REPEATS):
    """Repeated spatially-grouped CV. Returns per-repeat AUC / PR-AUC / Brier and out-of-fold mean prob."""
    X, y, groups = df[features].values, df.label.values, df.cell.values
    uniq = np.unique(groups)
    rng = np.random.RandomState(SEED)
    rows, oof_sum, oof_n = [], np.zeros(len(df)), np.zeros(len(df))
    for r in range(n_repeats):
        perm = dict(zip(uniq, rng.permutation(len(uniq))))     # shuffle which cells land in which fold
        g = np.array([perm[x] for x in groups])
        oof = np.full(len(df), np.nan)
        for tr, te in GroupKFold(n_splits=N_SPLITS).split(X, y, g):
            if len(np.unique(y[tr])) < 2:
                continue
            m = clone(make_pipeline(features)).fit(X[tr], y[tr])
            oof[te] = m.predict_proba(X[te])[:, 1]
        ok = ~np.isnan(oof)
        rows.append({"auc": roc_auc_score(y[ok], oof[ok]), "pr_auc": average_precision_score(y[ok], oof[ok]),
                     "brier": brier_score_loss(y[ok], oof[ok])})
        oof_sum[ok] += oof[ok]; oof_n[ok] += 1
    res = pd.DataFrame(rows)
    return res, np.where(oof_n > 0, oof_sum / np.maximum(oof_n, 1), np.nan)


def summarise(res: pd.DataFrame) -> dict:
    return {k: {"mean": round(float(res[k].mean()), 3),
                "p5": round(float(res[k].quantile(0.05)), 3),
                "p95": round(float(res[k].quantile(0.95)), 3)} for k in res.columns}


def permutation_p(df, features, observed_auc, n=100):
    """Label-shuffle test: how often does a model with no real signal reach this AUC?"""
    rng = np.random.RandomState(SEED)
    null = []
    for _ in range(n):
        d2 = df.copy()
        d2["label"] = rng.permutation(d2.label.values)          # shuffles labels, keeps spatial structure
        res, _ = grouped_cv(d2, features, n_repeats=1)
        null.append(res.auc.iloc[0])
    return float((np.sum(np.array(null) >= observed_auc) + 1) / (n + 1))


def bootstrap_coefs(df, features, n=300):
    X, y = df[features].values, df.label.values
    rng = np.random.RandomState(SEED)
    coefs = []
    for _ in range(n):
        idx = rng.choice(len(df), len(df), replace=True)
        if len(np.unique(y[idx])) < 2:
            continue
        m = make_pipeline(features).fit(X[idx], y[idx])
        coefs.append(m.named_steps["clf"].coef_[0][:len(features)])   # indicator columns are appended after
    return np.percentile(coefs, [2.5, 50, 97.5], axis=0)


def main():
    os.makedirs("outputs/models", exist_ok=True)
    d = load()
    hold = d[d.lake_id.isin(HOLDOUT_IDS)].copy()
    train = d[~d.lake_id.isin(HOLDOUT_IDS)].reset_index(drop=True)
    print(f"train {len(train)} (pos {int(train.label.sum())}) | holdout {len(hold)}")

    metrics = {"n_train": int(len(train)), "n_pos": int(train.label.sum()),
               "cv": "5-fold grouped by 0.5deg cell, 20 repeats", "models": {}}
    sets = {"all_features": FEATURES_ALL, "no_area": FEATURES_NO_AREA, "area_only": FEATURES_AREA_ONLY}
    oof_all = None
    for name, feats in sets.items():
        res, oof = grouped_cv(train, feats)
        metrics["models"][name] = summarise(res)
        if name == "all_features":
            oof_all = oof
            metrics["models"][name]["perm_p_auc"] = permutation_p(train, feats, float(res.auc.mean()))
        print(name, metrics["models"][name])

    # ---- final fit on all training lakes, then score the held-out bursts
    feats = FEATURES_ALL
    final = make_pipeline(feats).fit(train[feats].values, train.label.values)
    p_hold = final.predict_proba(hold[feats].values)[:, 1]
    p_train_oof = oof_all[train.label.values == 0]                 # out-of-fold scores of unflagged lakes
    hold_out = []
    for lid, p in zip(hold.lake_id, p_hold):
        pct = float((p_train_oof < p).mean() * 100)                # percentile vs UNFLAGGED lakes (higher = riskier)
        hold_out.append({"lake_id": lid, "risk_prob": round(float(p), 3),
                         "percentile_vs_unflagged": round(pct, 1)})
    metrics["holdout_bursts"] = hold_out
    print("holdout:", hold_out)

    # ---- no-area variant on the held-out bursts (is the signal more than size?)
    fa = make_pipeline(FEATURES_NO_AREA).fit(train[FEATURES_NO_AREA].values, train.label.values)
    metrics["holdout_bursts_no_area"] = [
        {"lake_id": l, "risk_prob": round(float(p), 3)}
        for l, p in zip(hold.lake_id, fa.predict_proba(hold[FEATURES_NO_AREA].values)[:, 1])]

    # ---- coefficients with bootstrap intervals
    names = FEATURES_ALL
    lo, med, hi = bootstrap_coefs(train, names)
    coef = final.named_steps["clf"].coef_[0][:len(names)]
    ctab = pd.DataFrame({"feature": names, "coef_std": coef.round(3), "boot_lo": lo.round(3),
                         "boot_med": med.round(3), "boot_hi": hi.round(3)})
    ctab["ci_excludes_0"] = (ctab.boot_lo > 0) | (ctab.boot_hi < 0)
    ctab.to_csv("outputs/tables/stage2_coefficients.csv", index=False)
    print(ctab.to_string(index=False))

    # ---- predictions for every lake (train rows: out-of-fold; holdout: final model)
    pred = d[["lake_id", "label", "basin", "area"]].copy()
    pred["risk_prob"] = np.nan
    pred.loc[pred.lake_id.isin(train.lake_id), "risk_prob"] = oof_all
    pred.loc[pred.lake_id.isin(hold.lake_id), "risk_prob"] = p_hold
    pred["score_type"] = np.where(pred.lake_id.isin(HOLDOUT_IDS), "holdout_final_model", "out_of_fold")
    pred.sort_values("risk_prob", ascending=False).to_csv("outputs/tables/stage2_predictions.csv", index=False)

    joblib.dump({"pipeline": final, "features": feats, "C": C, "seed": SEED,
                 "train_ids": train.lake_id.tolist()}, "outputs/models/risk_model.joblib")
    with open("outputs/tables/stage2_cv_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("saved model + tables")


if __name__ == "__main__":
    main()
