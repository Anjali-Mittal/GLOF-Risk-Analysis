from fetch_icimod import fetch_bbox   # works because both files are in the same folder
import pandas as pd

# Search rectangles: (west longitude, south latitude, east longitude, north latitude)
SPOTS = {
    "south_lhonak": (88.10, 27.85, 88.25, 27.98),
    "thame_area":   (86.50, 27.80, 86.70, 28.00),
}
COLS = ["GLIMS_ID", "GL_ID", "Latitude", "Longitude", "Area", "Basin", "Rank"]

for name, box in SPOTS.items():
    for layer in (0, 1, 2):
        rows = fetch_bbox(layer, *box)
        print(f"\n=== {name} | layer {layer} | {len(rows)} lakes found")
        if rows:
            df = pd.DataFrame(rows)
            cols = [c for c in COLS if c in df.columns]
            print(df[cols].sort_values("Area", ascending=False).to_string(index=False))