## Installation
- Install gdal on your system
- Install python dependencies with [`uv`](https://docs.astral.sh/uv/getting-started/installation/)


## Data
To reproduce analysis done for Berlin,
- Download OSM soccer CSV via download-osm-soccer.py
- Download shape mape for Berlin districs from [this repo](https://github.com/rbb-data/berlin-lor?tab=readme-ov-file)
- Download demographics tile from [EU website](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php) around Berlin

## Setup
- Compress demographics data by running `convert-tif-to-geojson.py`:
'''
uv run python convert-tif-to-geojson.py GHS_POP_E2030_GLOBE_R2023A_54009_100_V1_0_R3_C20.tif GHS_POP_E2030_GLOBE_R2023A_54009_100_V1_0_R3_C20.geojson'
'''
- Run app `app.py` (e.g., via `just run`)