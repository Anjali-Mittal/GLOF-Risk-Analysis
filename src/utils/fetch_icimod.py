import requests, pandas as pd

BASE = "https://geoapps.icimod.org/icimodarcgis/rest/services/HKH/GlacialLake/MapServer"
BBOX = (80.0, 27.4, 88.8, 30.7)   # covers layers 1 and 2

def query(layer, **params):
    p = {"f": "json", "where": "1=1", "outFields": "*",
         "returnGeometry": "false", "outSR": 4326, **params}
    r = requests.get(f"{BASE}/{layer}/query", params=p, timeout=120)
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"])
    return d

def fetch_bbox(layer, x0, y0, x1, y1):
    d = query(layer, geometry=f"{x0},{y0},{x1},{y1}",
              geometryType="esriGeometryEnvelope", inSR=4326,
              spatialRel="esriSpatialRelIntersects")
    rows = [f["attributes"] for f in d.get("features", [])]
    if d.get("exceededTransferLimit") or len(rows) >= 1000:   # cap hit: split into 4 tiles
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        rows = []
        for t in [(x0, y0, xm, ym), (xm, y0, x1, ym), (x0, ym, xm, y1), (xm, ym, x1, y1)]:
            rows += fetch_bbox(layer, *t)
    return rows

if __name__ == "__main__":
    for layer, name in [(1, "lakes_2015"), (2, "pdgl_2015")]:
        df = pd.DataFrame(fetch_bbox(layer, *BBOX)).drop_duplicates()
        df.to_csv(f"data/raw/icimod_{name}.csv", index=False)
        print(name, len(df), "rows")