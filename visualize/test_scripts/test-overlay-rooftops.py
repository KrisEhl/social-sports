import json
import folium
import geopandas as gpd
from pathlib import Path


def add_rooftops_overlay(m, filename="../berlin_rooftops.geojson", assume_epsg=False):
    """
    Overlay polygon GeoJSON in orange, reproject to WGS84, and fit the map.
    - filename: path relative to this script (same folder by default)
    - assume_epsg: if your file has no CRS, set e.g. 25833 (Berlin UTM) or 4326
    """
    path = Path(__file__).parent / filename
    gdf = gpd.read_file(path)

    # If file has no CRS, optionally assume one (Berlin datasets often use EPSG:25833)
    if gdf.crs is None and assume_epsg:
        gdf = gdf.set_crs(assume_epsg, allow_override=True)

    # Reproject to WGS84 for Folium
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    # Fix invalid geometries (common with complex footprints)
    if not gdf.geometry.is_valid.all():
        gdf = gdf.set_geometry(gdf.buffer(0))

    # Build GeoJSON for Folium
    gj = json.loads(gdf.to_json())

    # Choose a few tooltip fields if present
    tooltip_fields = [c for c in gdf.columns if c != "geometry"][:4]

    layer = folium.GeoJson(
        data=gj,
        name="Rooftops",
        style_function=lambda f: {
            "fillColor": "#ff7f00",  # bright orange
            "color": "#b35806",  # darker outline
            "weight": 1.0,
            "fillOpacity": 0.6,  # more visible
        },
        highlight_function=lambda f: {
            "weight": 2.0,
            "color": "#000000",
            "fillOpacity": 0.75,
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=[f"{k}:" for k in tooltip_fields],
            sticky=True,
            localize=True,
        ),
        overlay=True,
        control=True,
    ).add_to(m)
    # 🔎 Ensure the map view moves to the polygons
    m.fit_bounds(layer.get_bounds())

    return m


m = folium.Map(location=[52.5, 13.4], zoom_start=12, tiles="cartodbpositron")

add_rooftops_overlay(m)

m.save("map_with_rooftops.html")
print("[DONE] Map saved as map_with_rooftops.html")
