import os
import numpy as np, pandas as pd
import plotly.express as px

TS = "data/processed/lake_area_timeseries"
labels = pd.read_csv("data/labels/dangerous_lake_labels.csv")

frames = []
for _, lk in labels.iterrows():
    p = f"{TS}/{lk.lake_id}.csv"
    if os.path.exists(p):
        d = pd.read_csv(p)
        d["lake_id"], d["label"] = lk.lake_id, lk.label
        frames.append(d)
ts = pd.concat(frames)
ts["year"] = pd.to_datetime(ts.date).dt.year
ts = ts[ts.year >= 2013]                        # the window every lake has
ts["era"] = np.where(ts.source == "S2", "S2", "Landsat")

def wobble(g):                                   # typical year-to-year change, as ln(ratio)
    g = g.sort_values("year")
    a = g.area_km2.where(g.area_km2 > 0.01)
    r = np.log(a / a.shift()).abs()[g.year.diff() == 1]
    return r.median()

rows = []
for lid, g in ts.groupby("lake_id"):
    rows.append({"lake_id": lid, "label": g.label.iloc[0],
                 "valid_years": int(g.area_km2.notna().sum()), "of_years": len(g),
                 "median_images": g.n_images.median(),
                 "wobble_landsat": wobble(g[g.era == "Landsat"]),
                 "wobble_s2": wobble(g[g.era == "S2"])})
q = pd.DataFrame(rows)
q["flag"] = np.where(q.valid_years < 8, "too few years",
             np.where(q.wobble_s2 > 0.25, "unstable even with S2", ""))
os.makedirs("outputs/tables", exist_ok=True); os.makedirs("outputs/figures", exist_ok=True)
q.to_csv("outputs/tables/stage1_lake_quality.csv", index=False)

print("lakes:", len(q), "| dangerous:", (q.label == 1).sum(), "| unflagged:", (q.label == 0).sum())
print("typical year-to-year change -> Landsat: %.2f  S2: %.2f" %
      (q.wobble_landsat.median(), q.wobble_s2.median()))
print(q.flag.replace("", "ok").value_counts().to_string())

CHECK = {"South Lhonak": "SPECIAL_SOUTH_LHONAK", "Imja Tsho": "I2015_GL086925E27898N",
         "Tsho Rolpa": "I2015_GL086476E27861N", "Thame": "SPECIAL_THAME"}
parts = []
for name, lid in CHECK.items():
    p = f"{TS}/{lid}.csv"
    if os.path.exists(p):
        d = pd.read_csv(p); d["lake"] = name; d["year"] = pd.to_datetime(d.date).dt.year
        d["source"] = np.where(d.source == "S2", "S2", "Landsat"); parts.append(d)
fig = px.line(pd.concat(parts), x="year", y="area_km2", color="source", facet_col="lake",
              facet_col_wrap=2, markers=True, title="Stage 1 check lakes: area (km²)")
fig.update_yaxes(matches=None, showticklabels=True)
fig.write_html("outputs/figures/stage1_check_lakes.html")