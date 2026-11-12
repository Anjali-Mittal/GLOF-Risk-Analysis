import pandas as pd
l = pd.read_csv("data/raw/icimod_lakes_2015.csv"); p = pd.read_csv("data/raw/icimod_pdgl_2015.csv")
print(p.Rank.value_counts(), p.Country.value_counts(), l.Area.describe(), p.GL_ID.isin(l.GL_ID).mean())