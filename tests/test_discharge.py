import sys
sys.path.insert(0, "src/stage4_discharge")
import numpy as np
import pandas as pd
import discharge as D


def test_formulas_hand_calc():
    v = 1e6
    assert np.isclose(D.q_costa_vol(v, 5), 1.122 * v ** 0.57)
    assert np.isclose(D.q_evans(v, 5), 0.72 * v ** 0.53)
    assert np.isclose(D.q_costa_vh(v, 10), 0.981 * (1e7) ** 0.42)


def test_evans_known_value():
    # 1 MCM -> 0.72 * (1e6)^0.53 ~ 1.1e3 m3/s
    assert 1000 < D.q_evans(1e6, 1) < 1300


def test_missing_inputs_nan():
    assert all(np.isnan(v) for v in D.peaks(np.nan, 0.5).values())
    assert all(np.isnan(v) for v in D.peaks(5.0, 0).values())


def test_monotone_in_volume_and_fraction():
    a, b = D.peaks(1.0, 0.1), D.peaks(10.0, 0.1)
    assert all(b[k] > a[k] for k in D.QP)
    half = D.peaks(10.0, 0.1, fraction=0.5)
    assert all(half[k] < b[k] for k in D.QP)


def test_output_table():
    t = pd.read_csv("outputs/tables/stage4_discharge.csv")
    assert t.lake_id.is_unique and len(t) == 190
    ok = t.dropna(subset=["qp_primary_median"])
    assert (ok.qp_low <= ok.qp_primary_median + 1e-6).all() and (ok.qp_primary_median <= ok.qp_high + 1e-6).all()
