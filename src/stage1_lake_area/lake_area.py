import ee
ee.Initialize(project="glof-ras")   # you authenticated already; no need to repeat

S2_START = 2019   # first year we trust Sentinel-2 SR over this region (test earlier!)

LANDSAT = {  # collection: (green, nir, swir1) band names
    "LANDSAT/LT05/C02/T1_L2": ("SR_B2", "SR_B4", "SR_B5"),
    "LANDSAT/LE07/C02/T1_L2": ("SR_B2", "SR_B4", "SR_B5"),
    "LANDSAT/LC08/C02/T1_L2": ("SR_B3", "SR_B5", "SR_B6"),
    "LANDSAT/LC09/C02/T1_L2": ("SR_B3", "SR_B5", "SR_B6"),
}

# --- Slope from the Copernicus DEM: lakes are flat, steep snow/shadow is not
_dem_col = ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM")
DEM = _dem_col.mosaic().setDefaultProjection(_dem_col.first().projection())
SLOPE = ee.Terrain.slope(DEM)

def sentinel2(aoi, start, end):
    cs = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
           .filterBounds(aoi).filterDate(start, end)
           .linkCollection(cs, ["cs_cdf"]))
    def prep(img):
        refl = img.select(["B3", "B8", "B11"], ["GREEN", "NIR", "SWIR1"]).multiply(0.0001)
        return refl.updateMask(img.select("cs_cdf").gte(0.6))   # keep clear pixels only
    return col.map(prep), col.aggregate_mean("CLOUDY_PIXEL_PERCENTAGE"), 20

def landsat(aoi, start, end, collection_id):
    g, n, s = LANDSAT[collection_id]
    col = ee.ImageCollection(collection_id).filterBounds(aoi).filterDate(start, end)
    def prep(img):
        refl = img.select([g, n, s], ["GREEN", "NIR", "SWIR1"]).multiply(0.0000275).add(-0.2)
        bad = img.select("QA_PIXEL").bitwiseAnd(0b11110).neq(0)  # cloud, cirrus, shadow bits
        return refl.updateMask(bad.Not())
    return col.map(prep), col.aggregate_mean("CLOUD_COVER"), 30

def sensor_for(year):
    if year >= S2_START: return "S2"
    if year >= 2013: return "LANDSAT/LC08/C02/T1_L2"
    if year == 2012: return "LANDSAT/LE07/C02/T1_L2"
    return "LANDSAT/LT05/C02/T1_L2"

def water_mask(comp, mndwi_thr=0.0, nir_max=0.15, slope_max=8):
    mndwi = comp.normalizedDifference(["GREEN", "SWIR1"])
    return (mndwi.gt(mndwi_thr)
            .And(comp.select("NIR").lt(nir_max))
            .And(SLOPE.lt(slope_max)))

def composite_for(lat, lon, year, sensor=None, buffer_m=1500):
    pt = ee.Geometry.Point([lon, lat])
    aoi = pt.buffer(buffer_m).bounds()
    sensor = sensor or sensor_for(year)
    start, end = f"{year}-09-01", f"{year}-12-01"
    col, cloud, scale = (sentinel2(aoi, start, end) if sensor == "S2"
                         else landsat(aoi, start, end, sensor))
    return pt, aoi, col, cloud, scale, sensor

def lake_year(lat, lon, year, sensor=None, **thr):
    pt, aoi, col, cloud, scale, sensor = composite_for(lat, lon, year, sensor)
    n = col.size().getInfo()
    row = {"date": f"{year}-10-15", "area_km2": None,
           "cloud_cover_pct": None, "n_images": n, "source": sensor}
    if n == 0:
        return row                                  # gap: documented, not hidden
    water = water_mask(col.median(), **thr)
    polys = water.selfMask().reduceToVectors(
        geometry=aoi, scale=scale, maxPixels=1e9, geometryType="polygon")
    near = (polys.filterBounds(pt.buffer(200))      # only the water body AT the lake
            .map(lambda f: f.set("a", f.geometry().area(1))))
    area_m2 = ee.Algorithms.If(near.size().gt(0), near.aggregate_max("a"), None)
    info = ee.Dictionary({"a": area_m2, "c": cloud}).getInfo()
    row["area_km2"] = None if info["a"] is None else info["a"] / 1e6
    row["cloud_cover_pct"] = info["c"]
    return row