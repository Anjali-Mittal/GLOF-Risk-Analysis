import pandas as pd

lakes   = pd.read_csv("data/raw/icimod_lakes_2015.csv")
pdgl    = pd.read_csv("data/raw/icimod_pdgl_2015.csv")
special = pd.read_csv("data/labels/special_lakes.csv")

N_NEG_PER_POS = 3
MIN_AREA = pdgl.Area.quantile(0.10)   # ignore lakes smaller than almost all dangerous ones

def tidy(df, label):
    out = pd.DataFrame({
        "lake_id": "I2015_" + df.GL_ID.astype(str),
        "name": "",
        "lat": df.Latitude, "lon": df.Longitude, "basin": df.Basin,
        "inventory_year": 2015, "area": df.Area, "label": label,
        "on_official_list": "Y" if label == 1 else "N",
        "hazard_rank": df["Rank"] if "Rank" in df.columns else "",
        "notes": "",
    })
    return out

pos = tidy(pdgl, 1)
pos = pos[~pos.lake_id.isin(special.lake_id)]          # special rows replace these

pool = lakes[~lakes.GL_ID.isin(pdgl.GL_ID) & (lakes.Area >= MIN_AREA)]
neg = tidy(pool, 0)
neg = neg[~neg.lake_id.isin(special.lake_id)]          # never pick Thame etc. as a negative
neg = neg.sample(n=min(len(neg), N_NEG_PER_POS * len(pos)), random_state=42)

final = pd.concat([pos, special, neg], ignore_index=True)
final.to_csv("data/labels/dangerous_lake_labels.csv", index=False)

print("Lakes per label:\n", final.label.value_counts())
print("Duplicate IDs:", final.lake_id.duplicated().sum())
print("Area by label:\n", final.groupby("label").area.describe())