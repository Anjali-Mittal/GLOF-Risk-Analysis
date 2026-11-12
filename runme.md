# RUNME

Run every command from the repo root (the folder with `src/`, `data/`, `outputs/`).

## 1. Setup (once)
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pandas numpy scikit-learn joblib plotly   # if missing from requirements
```

## 2. Quick run (no Earth Engine needed)
Stage 1 + Stage 2 features are already saved in `outputs/tables/` and `data/processed/`.
```bash
python src/stage2_risk_score/train_model.py   # Stage 2C: train + validate risk score
python src/stage3_volume/volume.py            # Stage 3: volume from 4 formulas
python src/stage4_discharge/discharge.py      # Stage 4: peak breach discharge (m3/s)
python -m pytest tests -q                     # expect: 15 passed
```
Run in that order. Each stage reads the previous stage's table.

## 3. Outputs
| File | What |
|---|---|
| `outputs/models/risk_model.joblib` | trained model |
| `outputs/tables/stage2_cv_metrics.json` | CV scores, holdout results |
| `outputs/tables/stage2_coefficients.csv` | coefficients + bootstrap CIs |
| `outputs/tables/stage2_predictions.csv` | risk score per lake |
| `outputs/tables/stage3_volume.csv` | volume per lake, 4 formulas + spread |
| `outputs/tables/stage4_discharge.csv` | peak discharge per lake, 5 formulas + low/high envelope |

Volumes are in million m³. Discharge is in m³/s.

## 4. Full rebuild (needs Earth Engine, slow)
```bash
earthengine authenticate                       # once; project id is "glof-ras"
python src/stage1_lake_area/run_all.py         # skips lakes already saved; delete a CSV to redo it
python src/stage1_lake_area/qc_report.py       # quality table + check plot
python src/stage2_risk_score/features_growth.py
python src/stage2_risk_score/features_gee.py   # terrain + CHIRPS rain
```
Then repeat section 2.

## 5. Known issues before you trust results
- Thame lake polygon is wrong (0.55 km² measured; real burst lake ~0.05 km²).
- Cook & Quincey volume unit is assumed (million m³). Verify in the paper.
- Risk scores rank lakes. They are not calibrated probabilities.
- Rain features partly encode geography, not flood triggers.

- Stage 4 has no dam height data. Height-based formulas use a placeholder (mean depth). Trust the volume-only columns.
- Stage 4 assumes 100% of volume drains. Real events can release less.
- Stage 4 values are unvalidated against observed peaks.

## 6. Troubleshooting
- `No module named ...`: activate the venv, rerun `pip install`.
- `FileNotFoundError: outputs/tables/...`: you are not in the repo root, or a step was skipped.
- Earth Engine auth error: rerun `earthengine authenticate`. Change the project id in the `ee.Initialize(...)` lines if yours differs.
- `data/raw/` is gitignored. Rebuilding labels (`src/utils/build_labels.py`) refetches it.
