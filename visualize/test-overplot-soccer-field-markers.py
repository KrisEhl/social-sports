import folium
import overpass
import pandas as pd


def main():
    restaurants = pd.read_csv("berlin_soccer_fields.csv")
    m = folium.Map(location=(52.4813076, 13.4381063), zoom_start=12)
    for _, row in restaurants.iterrows():
        name = row.get("name") or "Unnamed field"
        leisure = row.get("leisure") or "unknown type"
        popup_html = f"<b>{leisure}</b><br>{name}"
        marker = folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=leisure,
        )
        marker.add_to(m)
    m.save("index.html")


if __name__ == "__main__":
    main()
