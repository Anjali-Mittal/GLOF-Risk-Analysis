import os
folders = [
 "data/raw","data/processed/lake_area_timeseries","data/labels","data/external",
 "notebooks","src/stage1_lake_area","src/stage2_risk_score","src/stage3_volume",
 "src/stage4_discharge","src/stage5_flood_extent","src/stage6_exposure",
 "src/stage7_dashboard","src/utils","dashboard","outputs/figures","outputs/tables",
 "outputs/models","docs/synopsis","docs/literature_review","docs/report",
 "docs/presentation","tests"]
for f in folders:
    os.makedirs(f, exist_ok=True)
    open(os.path.join(f, ".gitkeep"), "a").close()