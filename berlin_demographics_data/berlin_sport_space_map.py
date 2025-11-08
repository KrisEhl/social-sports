import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point
import numpy as np

# -----------------------------
# 1️⃣ Load GeoJSON (Berlin regions)
# -----------------------------
print("📂 Loading Berlin region polygons...")
regions = gpd.read_file("berlin-lor.bezirksregionen.geojson")

# Rename key column to match CSV
regions = regions.rename(columns={"SCHLUESSEL": "RAUMID"})

# Reproject to metric CRS to calculate area correctly
regions = regions.to_crs(epsg=3857)
regions["area_km2"] = regions.geometry.area / 1e6
regions = regions.to_crs(epsg=4326)  # back to lat/lon for Folium

# -----------------------------
# 2️⃣ Load demographics CSV
# -----------------------------
print("📊 Loading demographics data...")
demographics = pd.read_csv("berlin_demographics.csv")

# Merge by RAUMID
regions = regions.merge(demographics, on="RAUMID", how="left")

# Compute population density
regions["population_density"] = regions["Insgesamt"] / regions["area_km2"]

# -----------------------------
# 3️⃣ Generate mock sport facilities
# -----------------------------
print("⚽ Generating mock sport facilities...")
n_facilities = 60
minx, miny, maxx, maxy = regions.total_bounds
points = []
for _ in range(n_facilities):
    while True:
        p = Point(np.random.uniform(minx, maxx), np.random.uniform(miny, maxy))
        if regions.contains(p).any():
            points.append(p)
            break

facilities = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")
facilities["name"] = [f"Facility #{i+1}" for i in range(len(facilities))]

# -----------------------------
# 4️⃣ Create Folium map
# -----------------------------
print("🗺️ Creating interactive map...")
m = folium.Map(location=[52.52, 13.405], zoom_start=11, tiles="cartodbpositron")

# Choropleth: Population Density
folium.Choropleth(
    geo_data=regions,
    data=regions,
    columns=["RAUMID", "population_density"],
    key_on="feature.properties.RAUMID",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.3,
    legend_name="Population Density (people/km²)",
    name="Population Density",
).add_to(m)

# Choropleth: Average Age
folium.Choropleth(
    geo_data=regions,
    data=regions,
    columns=["RAUMID", "Durchschnittsalter"],
    key_on="feature.properties.RAUMID",
    fill_color="PuBu",
    fill_opacity=0.7,
    line_opacity=0.3,
    legend_name="Average Age",
    name="Average Age",
).add_to(m)

# -----------------------------
# 5️⃣ Add mock sport facilities layer
# -----------------------------
fac_layer = folium.FeatureGroup(name="Sport Facilities")
for _, row in facilities.iterrows():
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        popup=row["name"],
        icon=folium.Icon(color="green", icon="futbol-o", prefix="fa"),
    ).add_to(fac_layer)
fac_layer.add_to(m)

# -----------------------------
# 6️⃣ Add tooltips to show demographics
# -----------------------------
tooltip_fields = ["RAUMID", "Insgesamt", "Durchschnittsalter"]
tooltip_aliases = ["Region ID", "Population", "Average Age"]

folium.GeoJson(
    regions,
    name="Region Info",
    style_function=lambda x: {"fillOpacity": 0, "color": "gray", "weight": 1},
    tooltip=folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        localize=True,
        sticky=True,
    ),
).add_to(m)

# -----------------------------
# 7️⃣ Add layer control and save
# -----------------------------
folium.LayerControl(collapsed=False).add_to(m)

output_file = "berlin_sport_space_map.html"
m.save(output_file)
print(f"✅ Map saved successfully: {output_file}")
