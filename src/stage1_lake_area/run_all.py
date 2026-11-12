import os, time, pandas as pd
from lake_area import lake_year

labels = pd.read_csv("data/labels/dangerous_lake_labels.csv")
LONG = {"SPECIAL_SOUTH_LHONAK", "SPECIAL_THAME",
        "I2015_GL086925E27898N", "I2015_GL086476E27861N"}   # + Imja, Rolpa
out_dir = "data/processed/lake_area_timeseries"

def safe(lat, lon, y):
    for attempt in range(3):
        try: return lake_year(lat, lon, y)
        except Exception as e:
            print("retry", y, e); time.sleep(10)
    return {"date": f"{y}-10-15", "area_km2": None, "cloud_cover_pct": None,
            "n_images": -1, "source": "error"}

for _, lk in labels.iterrows():
    path = f"{out_dir}/{lk.lake_id}.csv"
    if os.path.exists(path): continue
    years = range(1990, 2026) if lk.lake_id in LONG else range(2013, 2026)
    pd.DataFrame([safe(lk.lat, lk.lon, y) for y in years]).to_csv(path, index=False)
    print("done", lk.lake_id)