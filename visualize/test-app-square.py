# pip install geopandas shapely folium branca pandas pyogrio
import json
import pandas as pd
import geopandas as gpd
from pathlib import Path
import folium
import os
from shapely.geometry import box
import numpy as np
import branca.colormap as cm

from utils_regrid import regrid_sum_2km
from utils_to_grid import add_soccer_counts_to_grid
from utils_to_map import add_rooftops_to_map, add_soccer_fields_to_map


# ---------- CONFIG ----------
GEOJSON_IN = "GHS_POP_E2030_GLOBE_R2023A_54009_100_V1_0_R3_C20.geojson"  # input GeoJSON from your polygonize step
GEOJSON_OUT = "filtered.geojson"  # optional filtered output (for inspection)
HTML_OUT = "index.html"
VALUE_FIELD = "value"  # attribute holding your metric
BBOX = (12.9, 52.2, 13.9, 52.7)  # (min_lon, min_lat, max_lon, max_lat)

# ---------- LOAD + FILTER ----------
min_lon, min_lat, max_lon, max_lat = BBOX
bbox_poly = box(min_lon, min_lat, max_lon, max_lat)

print("[INFO] Loading features within bbox using GeoPandas…")
# If pyogrio is available (modern GeoPandas), this streams only bbox features:
if os.path.exists(GEOJSON_OUT):
    gdf = gpd.read_file(GEOJSON_OUT, bbox=BBOX)
else:
    try:
        gdf = gpd.read_file(GEOJSON_IN, bbox=BBOX)
        print(f"[INFO] Loaded {len(gdf)} features (bbox read).")
    except TypeError:
        # Fallback: load all then filter (works everywhere but uses more RAM)
        gdf = gpd.read_file(GEOJSON_IN)
        print(f"[INFO] Loaded {len(gdf)} features (full read).")
        gdf = gdf[gdf.intersects(bbox_poly)]
        print(f"[INFO] After bbox filter: {len(gdf)} features.")

    if gdf.empty:
        raise RuntimeError("No features found in the requested bounding box.")

    # Ensure WGS84
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        print("[INFO] Reprojecting to EPSG:4326 (WGS84)…")
        gdf = gdf.to_crs(4326)

    # Optional: write filtered subset for debugging/inspection
    gdf.to_file(GEOJSON_OUT, driver="GeoJSON")
    print(f"[INFO] Wrote filtered GeoJSON → {GEOJSON_OUT}")


# Keep only rows with a numeric VALUE_FIELD
if VALUE_FIELD not in gdf.columns:
    # Some exports place it inside properties; if you loaded via json, it’s already columns.
    # If it's nested, you'd promote it here. For standard GDAL export, it should already be a column.
    raise RuntimeError(f"'{VALUE_FIELD}' column not found in GeoDataFrame.")

gdf = gdf[pd.to_numeric(gdf[VALUE_FIELD], errors="coerce").notna()].copy()
gdf[VALUE_FIELD] = gdf[VALUE_FIELD].astype(float)
gdf = gdf[gdf[VALUE_FIELD].notna() & (gdf[VALUE_FIELD] != 0)]

gdf = regrid_sum_2km(gdf, tile_size_m=5_000, area_weighted=True)
gdf = add_soccer_counts_to_grid(gdf, "berlin_soccer_fields.csv")

gdf["soccer_count"] = gdf["soccer_count"].fillna(0).astype(int)

gdf["ratio"] = gdf["soccer_count"] / gdf["value"]
gdf["ratio"] /= gdf["ratio"].max()

if "fid" not in gdf.columns:
    gdf = gdf.reset_index(drop=True)
    gdf["fid"] = gdf.index.astype(int)

print("regrid to 2km grid:", gdf.head())


if gdf.empty:
    raise RuntimeError(f"No features with numeric '{VALUE_FIELD}' after filtering.")

# df_vals = gdf[["fid", VALUE_FIELD]].copy()

# # Compute map center from bounds
minx, miny, maxx, maxy = gdf.total_bounds
center = [(miny + maxy) / 2.0, (minx + maxx) / 2.0]

m = folium.Map(location=center, zoom_start=18, tiles="cartodbpositron")


def add_ratio_fields_to_map(m, gdf):
    gj = json.loads(gdf.to_crs(4326).to_json())
    folium.Choropleth(
        geo_data=gj,
        name="Soccer fields (count)",
        data=gdf[["tile_id", "ratio"]],
        columns=["tile_id", "ratio"],
        key_on="feature.properties.tile_id",
        fill_color="OrRd",
        fill_opacity=0.6,
        line_opacity=0.1,
        legend_name="Soccer fields/Population",
    ).add_to(m)

    # Tooltip layer
    folium.GeoJson(
        gj,
        name="ratio",
        tooltip=folium.features.GeoJsonTooltip(
            fields=["ratio"],
            aliases=[f"{'ratio'}: "],
            sticky=True,
        ),
        style_function=lambda _: {"weight": 0},
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)


out = gdf.copy()
# Ignore very scarcely populated areas
gdf["ratio"] = np.where(
    (gdf["value"] > 1000) & (gdf["soccer_count"] > 0),
    gdf["soccer_count"] / gdf["value"],
    np.nan,
)
gdf["ratio"] /= gdf["ratio"].max()

# Reproject to WGS84 for Folium
gdf_wgs = gdf.to_crs(4326)

# Map center
minx, miny, maxx, maxy = gdf_wgs.total_bounds
center = [(miny + maxy) / 2.0, (minx + maxx) / 2.0]

# GeoJSON for folium
gj = json.loads(gdf_wgs.to_json())

# Compute vmin/vmax based on quantiles (to reduce outlier distortion)
valid = gdf_wgs["ratio"].replace([np.inf, -np.inf], np.nan).dropna()
if valid.empty:
    vmin, vmax = 0.0, 1.0
else:
    vmin, vmax = float(valid.quantile(0.02)), float(valid.quantile(0.98))
    if vmin == vmax:
        vmin, vmax = 0.0, float(valid.max() or 1.0)

# Create color scale
# cmap = cm.linear.magma.scale(vmin, vmax)
cmap = cm.StepColormap(
    colors=[
        "#a50026",
        "#d73027",
        "#f46d43",
        "#fdae61",
        "#fee08b",
        "#d9ef8b",
        "#a6d96a",
        "#66bd63",
        "#1a9850",
    ],
    vmin=vmin,
    vmax=vmax,
)
cmap.caption = "Soccer fields / Value (ratio)"

# cmap.colors = list(reversed(cmap.colors))

# Initialize map
m = folium.Map(location=center, zoom_start=11, tiles="cartodbpositron")


# --- style tiles manually using the colormap ---
def style_fn(feature):
    r = feature["properties"].get("ratio")
    if r is None or np.isnan(r):
        return {"fillOpacity": 0.0, "weight": 0.1, "color": "grey"}
    return {
        "fillColor": cmap(r),
        "color": "black",
        "weight": 0.1,
        "fillOpacity": 0.3,
    }


def add_soccer_ratio_to_map(m):
    folium.GeoJson(
        gj,
        name="Soccer-to-Population Ratio (normalized)",
        style_function=style_fn,
        tooltip=folium.features.GeoJsonTooltip(
            fields=["ratio", "value", "soccer_count"],
            aliases=["ratio:", "population:", "soccer fields:"],
            sticky=True,
            localize=True,
        ),
    ).add_to(m)

    # Add legend
    cmap.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


m = add_soccer_ratio_to_map(m)
m = add_soccer_fields_to_map(m)
# not really working yet
# m = add_rooftops_to_map(m)

m.save(HTML_OUT)
print(f"[DONE] Saved {HTML_OUT} with vmin={vmin:.2f}, vmax={vmax:.2f}")
