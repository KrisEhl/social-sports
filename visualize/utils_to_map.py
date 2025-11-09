import folium
from pathlib import Path
import geopandas as gpd
import pandas as pd
import json


LEISURE_TO_COLOR = {
    "pitch": "green",
    "sports_centre": "blue",
    "stadium": "orange",
}


def add_rooftops_to_map(m, filename="berlin_rooftops.geojson", assume_epsg=None):
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
    # m.fit_bounds(layer.get_bounds())

    return m


def add_soccer_fields_to_map(m):
    soccer_fields = pd.read_csv("berlin_soccer_fields.csv")
    for _, row in soccer_fields.iterrows():
        # name = row.get("name")
        # if pd.isna(name) or name == "nan":
        #     name = "Unnamed field"
        leisure = row.get("leisure")
        if pd.isna(leisure) or leisure == "nan":
            leisure = "unknown type"
        color = LEISURE_TO_COLOR.get(leisure, "grey")
        image_path = f"facility_images_brighter/{row['osm_id']}.png"
        #     {name}<br><br>
        html = f"""
            <div style="width:125px; font-size:14px; line-height:1.3">
            <b>{leisure}</b><br>
            <img src="{image_path}" alt="image" style="width:100%; height:auto; border-radius:4px;">
            </div>
        """
        # marker = folium.Marker(
        #     location=[row["lat"], row["lon"]],
        #     popup=folium.Popup(popup_html, max_width=250),
        #     tooltip=leisure,
        # )
        # marker.add_to(m)

        folium.CircleMarker(
            location=[row.lat, row.lon],
            radius=4,  # ← smaller size (default is ~10)
            color="black",
            weight=0.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(html, max_width=125),
        ).add_to(m)
    return m
