# Lake area time series (Stage 1)
- One CSV per lake, one row per year. Area is in km², from a Sept-Nov median of cloud-free Sentinel-2 images.
- Settings: MNDWI > 0, NIR < 0.15, slope < 8 degrees.
- Rows before 2019 (Landsat) are in some files but are noisy and are NOT used in later stages.
- An empty area means no usable image that year. 