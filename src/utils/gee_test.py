import ee
ee.Authenticate()   # opens browser, log in once
ee.Initialize(project="glof-ras")
img = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
       .filterDate("2023-09-01", "2023-10-01").first())
print("GEE works. Got image:", img.getInfo()["id"])