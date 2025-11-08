# pip install folium branca pandas geopandas shapely  # geopandas optional (for centering/bounds)
import json
import pandas as pd
import folium
import branca.colormap as cm

# (Optional) for better centering on data bounds
try:
    import geopandas as gpd

    HAVE_GPD = True
except Exception:
    HAVE_GPD = False

# --- paths ---
geojson_path = (
    "GHS_POP_E2030_GLOBE_R2023A_54009_100_V1_0_R3_C19.geojson"  # change to your file
)
out_html = "tif_choropleth.html"
value_field = "value"  # the attribute written by polygonize

# 1) Load GeoJSON and inject a simple feature id (fid)
with open(geojson_path, "r", encoding="utf-8") as f:
    gj = json.load(f)

features = gj.get("features", [])
for i, feat in enumerate(features):
    # add fid property if missing
    props = feat.setdefault("properties", {})
    if "fid" not in props:
        props["fid"] = i

# 2) Build DataFrame mapping fid -> value (required by Folium.Choropleth)
rows = []
for feat in features:
    props = feat.get("properties", {})
    v = props.get(value_field, None)
    fid = props.get("fid", None)
    if fid is not None and v is not None:
        rows.append({"fid": fid, value_field: float(v)})

df_vals = pd.DataFrame(rows)

if df_vals.empty:
    raise RuntimeError("No features with numeric 'value' found in the GeoJSON.")

# 3) Choose map center (use GeoPandas to get centroid if available)
if HAVE_GPD:
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    centroid = gdf.geometry.unary_union.centroid
    center = [centroid.y, centroid.x]
else:
    # fallback: center on rough Berlin coords (or pick first feature’s first coord)
    center = [52.5200, 13.4050]

# 4) Create color scale from data range
vmin, vmax = float(df_vals[value_field].min()), float(df_vals[value_field].max())
cmap = cm.linear.Viridis_09.scale(vmin, vmax)
cmap.caption = value_field

# 5) Build map
m = folium.Map(location=center, zoom_start=12, tiles="cartodbpositron")

# 6) Choropleth layer (join by fid)
folium.Choropleth(
    geo_data=gj,  # pass the dict with injected fids
    name="Choropleth",
    data=df_vals,
    columns=["fid", value_field],  # DataFrame columns
    key_on="feature.properties.fid",  # where to find the key in GeoJSON
    fill_color="Viridis",
    fill_opacity=0.7,
    line_opacity=0.1,
    nan_fill_opacity=0.0,
    legend_name=value_field,
    smooth_factor=0.0,
    highlight=True,
).add_to(m)

# 7) Optional: tooltip showing the value per polygon
folium.GeoJson(
    gj,
    name="Values",
    tooltip=folium.features.GeoJsonTooltip(
        fields=[value_field],
        aliases=[f"{value_field}: "],
        sticky=True,
    ),
    style_function=lambda x: {"weight": 0},  # keep outlines subtle
).add_to(m)

# 8) Add colorbar and controls
cmap.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

# 9) Save
m.save(out_html)
print(f"Wrote {out_html}")
