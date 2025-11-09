# --- CONFIG ---
METRIC_GEOJSON = "filtered.geojson"  # your metric polygons already filtered to bbox (from earlier step)
REGIONS_GEOJSON = "lor_bezirksregionen.geojson"  # LOR Bezirksregionen (EPSG:25833)
SOCCER_CSV = (
    "berlin_soccer_fields.csv"  # your OSM soccer CSV (lon/lat columns: lon, lat)
)
ROOFTOPS_GEOJSON = "berlin_rooftops.geojson"  # optional overlay
VALUE_FIELD = "value"  # metric attribute in METRIC_GEOJSON
HTML_OUT = "index.html"

import json
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point
from pathlib import Path
import branca.colormap as cm
from utils_to_map import add_soccer_fields_to_map

here = Path(__file__).parent

# ---------- 1) LOAD REGIONS (EPSG:25833) ----------
regions = gpd.read_file(here / REGIONS_GEOJSON)
if regions.crs is None:
    # LOR file declares EPSG:25833 in your snippet; set if missing
    regions = regions.set_crs(25833, allow_override=True)
elif regions.crs.to_epsg() != 25833:
    regions = regions.to_crs(25833)

# ---------- 2) LOAD METRIC POLYGONS & AREA-WEIGHTED SUM BY REGION ----------
poly = gpd.read_file(here / METRIC_GEOJSON)
if poly.crs is None:
    # If unknown, assume WGS84 (common for GeoJSON). Change if your file says otherwise.
    poly = poly.set_crs(4326, allow_override=True)
# ensure numeric metric
poly = poly.copy()
poly[VALUE_FIELD] = pd.to_numeric(poly[VALUE_FIELD], errors="coerce")
poly = poly[poly[VALUE_FIELD].notna() & (poly[VALUE_FIELD] != 0)]
# project metric polygons to same CRS as regions (meters) for area weights
poly = poly.to_crs(regions.crs)
poly["poly_area"] = poly.geometry.area

# intersection
inter = gpd.overlay(
    poly[["geometry", VALUE_FIELD, "poly_area"]],
    regions[["geometry"] + [c for c in regions.columns if c != "geometry"]],
    how="intersection",
    keep_geom_type=False,
)
if inter.empty:
    raise RuntimeError("No overlap between metric polygons and LOR regions.")

inter["inter_area"] = inter.geometry.area
inter = inter[inter["poly_area"] > 0]
inter["weighted_value"] = inter[VALUE_FIELD] * (
    inter["inter_area"] / inter["poly_area"]
)

# choose a stable region key (use BEZIRKSREG + BEZIRKSNAM by default)
region_key = "region_name"
inter[region_key] = (
    inter.get("BEZIRKSREG", "").astype(str)
    + " ("
    + inter.get("BEZIRKSNAM", "").astype(str)
    + ")"
)

value_by_region = (
    inter.groupby(region_key, as_index=False)["weighted_value"]
    .sum()
    .rename(columns={"weighted_value": "value"})
)

# ---------- 3) LOAD SOCCER POINTS & COUNT PER REGION ----------
df = pd.read_csv(here / SOCCER_CSV)
# filter to soccer rows if column exists
if "sport" in df.columns:
    df = df[df["sport"].astype(str).str.contains("soccer", case=False, na=False)]
# dedupe by OSM id if present
if {"osm_type", "osm_id"}.issubset(df.columns):
    df = df.drop_duplicates(subset=["osm_type", "osm_id"])

# build points (CSV is lon/lat in WGS84)
if not {"lon", "lat"}.issubset(df.columns):
    raise KeyError("CSV must contain 'lon' and 'lat' columns.")
pts = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs=4326
).to_crs(regions.crs)

# spatial join: which region each point falls in
join_pts = gpd.sjoin(
    pts[["geometry"]],
    regions.assign(
        **{
            region_key: regions.get("BEZIRKSREG", "").astype(str)
            + " ("
            + regions.get("BEZIRKSNAM", "").astype(str)
            + ")"
        }
    ),
    how="left",
    predicate="within",
)
soccer_counts = (
    join_pts.groupby(region_key, as_index=False)
    .size()
    .rename(columns={"size": "soccer_count"})
)

# ---------- 4) MERGE METRIC + SOCCER & COMPUTE RATIO ----------
regions_out = regions.assign(
    **{
        region_key: regions.get("BEZIRKSREG", "").astype(str)
        + " ("
        + regions.get("BEZIRKSNAM", "").astype(str)
        + ")"
    }
)
out = regions_out[[region_key, "geometry"]].merge(
    value_by_region, on=region_key, how="left"
)
out = out.merge(soccer_counts, on=region_key, how="left")
out["value"] = out["value"].fillna(0.0)
out["soccer_count"] = out["soccer_count"].fillna(0).astype(int)
out["ratio"] = np.where(out["value"] > 0, out["soccer_count"] / out["value"], np.nan)
out["ratio"] = out["ratio"] / out["ratio"].max()


# ---------- 5) FOLIUM MAP (RdYlGn: red→yellow→green) ----------
# bounds & reproject to WGS84 for folium
out_wgs = out.to_crs(4326)
minx, miny, maxx, maxy = out_wgs.total_bounds
center = [(miny + maxy) / 2, (minx + maxx) / 2]

# robust vmin/vmax (clip outliers)
valid = out_wgs["ratio"].replace([np.inf, -np.inf], np.nan).dropna()
if valid.empty:
    vmin, vmax = 0.0, 1.0
else:
    vmin, vmax = float(valid.quantile(0.02)), float(valid.quantile(0.8))
    if vmin == vmax:
        vmin, vmax = 0.0, float(valid.max() or 1.0)

# ColorBrewer RdYlGn continuous
cmap = cm.LinearColormap(
    colors=["#a50026", "#fdae61", "#ffffbf", "#a6d96a", "#1a9850"],  # red→yellow→green
    vmin=vmin,
    vmax=vmax,
)
cmap.caption = "Soccer fields / Population (ratio)"

m = folium.Map(location=center, zoom_start=12, tiles="cartodbpositron")

gj = json.loads(out_wgs.to_json())


def style_fn(feat):
    r = feat["properties"].get("ratio")
    if r is None or (isinstance(r, float) and np.isnan(r)):
        return {"fillOpacity": 0.0, "color": "#999", "weight": 0.8}
    return {"fillColor": cmap(r), "color": "#333", "weight": 0.8, "fillOpacity": 0.55}


folium.GeoJson(
    gj,
    name="Ratio: soccer / Population",
    style_function=style_fn,
    highlight_function=lambda _: {"weight": 2, "color": "#000", "fillOpacity": 0.75},
    tooltip=folium.features.GeoJsonTooltip(
        fields=[region_key, "value", "soccer_count", "ratio"],
        aliases=["Region:", "Value:", "Soccer fields:", "Ratio:"],
        sticky=True,
        localize=True,
        labels=True,
        toLocaleString=True,
    ),
).add_to(m)

cmap.add_to(m)


folium.LayerControl(collapsed=False).add_to(m)
m = add_soccer_fields_to_map(m)
m.fit_bounds([[miny, minx], [maxy, maxx]])
m.save(HTML_OUT)
print(f"[DONE] Saved {HTML_OUT}")
