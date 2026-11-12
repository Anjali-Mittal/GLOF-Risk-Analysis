import sys
sys.path.insert(0, "src/stage3_volume")
import numpy as np
import pandas as pd
import volume as V


def test_formulas_match_hand_calc():
    a = 1e6  # 1 km2
    assert np.isclose(V.v_huggel(a), 0.104 * a ** 1.42)
    assert np.isclose(V.v_oconnor(a), 3.114e6 + 0.0001685 * 1e12)
    assert np.isclose(V.v_evans(a), 0.035 * 1e9)


def test_thame_anchor_within_factor_two():
    # Nepal govt / ICIMOD-cited estimate: ~0.38 MCM at 0.045 km2
    v = V.volumes_mcm(0.045)
    assert 0.38 / 2 < v["vol_min"] and v["vol_max"] < 0.38 * 2


def test_bad_area_gives_nan_not_crash():
    for bad in (None, np.nan, 0, -1):
        assert np.isnan(V.volumes_mcm(bad)["vol_median"])


def test_monotone_in_area():
    a, b = V.volumes_mcm(0.2), V.volumes_mcm(0.4)
    assert all(b[k] > a[k] for k in V.FORMULAS)


def test_output_table_sane():
    t = pd.read_csv("outputs/tables/stage3_volume.csv")
    assert t.lake_id.is_unique and len(t) == 190
    ok = t.dropna(subset=["vol_median"])
    assert (ok.vol_min <= ok.vol_median).all() and (ok.vol_median <= ok.vol_max).all()
