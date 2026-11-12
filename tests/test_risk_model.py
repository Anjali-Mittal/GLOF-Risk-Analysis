"""Sanity tests for Stage 2 step C. Run from repo root: python -m pytest tests -q"""
import sys
sys.path.insert(0, "src/stage2_risk_score")
import numpy as np
import joblib
import train_model as T


def test_no_holdout_leak_into_training():
    m = joblib.load("outputs/models/risk_model.joblib")
    assert not set(T.HOLDOUT_IDS) & set(m["train_ids"])


def test_features_complete_and_finite_after_load():
    d = T.load()
    assert d.lake_id.is_unique and len(d) == 190
    assert np.isfinite(d.log_area).all()
    assert d[["slope_ring_mean_deg", "rain_max5d_mm"]].notna().all().all()


def test_spatial_folds_never_split_a_cell():
    from sklearn.model_selection import GroupKFold
    d = T.load()
    for tr, te in GroupKFold(5).split(d, d.label, d.cell):
        assert not set(d.cell.iloc[tr]) & set(d.cell.iloc[te])


def test_probabilities_valid_and_monotone_in_area():
    m = joblib.load("outputs/models/risk_model.joblib")
    d = T.load().iloc[:1]
    base = d[m["features"]].values.copy()
    big = base.copy(); big[0, 0] += 1.0                # +1 in log10 area
    p0, p1 = [m["pipeline"].predict_proba(x)[0, 1] for x in (base, big)]
    assert 0 <= p0 <= 1 and p1 > p0


def test_model_beats_shuffled_labels():
    d = T.load(); d = d[~d.lake_id.isin(T.HOLDOUT_IDS)].reset_index(drop=True)
    real, _ = T.grouped_cv(d, T.FEATURES_ALL, n_repeats=1)
    d["label"] = np.random.RandomState(0).permutation(d.label.values)
    fake, _ = T.grouped_cv(d, T.FEATURES_ALL, n_repeats=1)
    assert real.auc.iloc[0] > fake.auc.iloc[0] + 0.15
