"""Stage 4: peak breach discharge (m3/s) from released volume, using published empirical relations.

Reads  : outputs/tables/stage3_volume.csv
Writes : outputs/tables/stage4_discharge.csv

Run from the repo root:  python src/stage4_discharge/discharge.py

Formulas (V in m3, h in m, Qp in m3/s; coefficients checked against published compilations):
  Costa 1985, volume only   Qp = 1.122 * V^0.57
  Costa 1985, volume+height Qp = 0.981 * (V*h)^0.42     (some papers print 0.763; see caveats)
  Evans 1986                Qp = 0.72  * V^0.53          (built for natural/landslide + moraine dams)
  Popov 1991                Qp = 0.0048 * V^0.896
  Froehlich 1995            Qp = 0.607 * V^0.295 * h^1.24

HEIGHT: this repo has NO dam / breach height data. Height-based formulas use a PLACEHOLDER,
h = Huggel mean depth = 0.104 * A^0.42 (A in m2). That is mean depth, not breach depth.
Treat height-based rows as weak; the volume-only rows (Costa-vol, Evans, Popov) are the primary set.

RELEASED FRACTION: RELEASE_FRACTION = 1.0 (full drainage = worst case). Thame released ~0.3 of
a ~0.38 MCM lake, so real events can be lower.
"""
import numpy as np
import pandas as pd

RELEASE_FRACTION = 1.0

def q_costa_vol(v, h):  return 1.122 * v ** 0.57
def q_costa_vh(v, h):   return 0.981 * (v * h) ** 0.42
def q_evans(v, h):      return 0.72 * v ** 0.53
def q_popov(v, h):      return 0.0048 * v ** 0.896
def q_froehlich(v, h):  return 0.607 * v ** 0.295 * h ** 1.24

QP = {"costa_vol": q_costa_vol, "evans": q_evans, "popov": q_popov,          # primary (volume only)
      "costa_vh": q_costa_vh, "froehlich": q_froehlich}                       # use height placeholder
PRIMARY = ["costa_vol", "evans", "popov"]


def depth_proxy_m(area_km2):
    return 0.104 * (area_km2 * 1e6) ** 0.42


def peaks(vol_mcm, area_km2, fraction=RELEASE_FRACTION):
    """Qp (m3/s) per formula for one lake. NaN if inputs missing."""
    if not (np.isfinite(vol_mcm) and np.isfinite(area_km2)) or vol_mcm <= 0 or area_km2 <= 0:
        return {k: np.nan for k in QP}
    v, h = vol_mcm * 1e6 * fraction, depth_proxy_m(area_km2)
    return {k: float(f(v, h)) for k, f in QP.items()}


def main():
    d = pd.read_csv("outputs/tables/stage3_volume.csv")
    rows = []
    for r in d.itertuples():
        mid = peaks(r.vol_median, r.area_s2_km2)
        lo = peaks(r.vol_min, r.area_s2_km2)       # smallest volume estimate
        hi = peaks(r.vol_max, r.area_s2_km2)       # largest volume estimate
        prim = np.array([mid[k] for k in PRIMARY])
        rows.append({"lake_id": r.lake_id, **{f"qp_{k}": v for k, v in mid.items()},
                     "qp_primary_median": float(np.median(prim)) if np.isfinite(prim).all() else np.nan,
                     "qp_low": min(lo[k] for k in PRIMARY) if np.isfinite(lo["evans"]) else np.nan,
                     "qp_high": max(hi[k] for k in PRIMARY) if np.isfinite(hi["evans"]) else np.nan,
                     "depth_proxy_m": depth_proxy_m(r.area_s2_km2) if np.isfinite(r.area_s2_km2) else np.nan})
    out = d[["lake_id", "name", "label", "risk_prob", "flagged", "area_s2_km2", "vol_min", "vol_median", "vol_max"]].merge(
        pd.DataFrame(rows), on="lake_id")
    out["release_fraction"] = RELEASE_FRACTION
    out = out.sort_values("risk_prob", ascending=False)
    out.to_csv("outputs/tables/stage4_discharge.csv", index=False)

    f = out[out.flagged & out.qp_primary_median.notna()]
    print(f"lakes {len(out)} | flagged with Qp: {len(f)}")
    print(f[["qp_primary_median", "qp_low", "qp_high"]].describe().round(0).to_string())
    print(out[out.lake_id.str.startswith("SPECIAL")][
        ["lake_id", "vol_median", "qp_costa_vol", "qp_evans", "qp_popov", "qp_costa_vh", "qp_froehlich"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
