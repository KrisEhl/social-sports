import requests
import pandas as pd

# Overpass API endpoint
overpass_url = "https://overpass-api.de/api/interpreter"

# Overpass QL query: all restaurants in Berlin (area = Wikidata Q64)
query = """
[out:json][timeout:120];
area["wikidata"="Q64"]->.searchArea;
(
  node["amenity"="restaurant"](area.searchArea);
  way["amenity"="restaurant"](area.searchArea);
  relation["amenity"="restaurant"](area.searchArea);
);
out tags center;
"""

# Fetch data
resp = requests.post(overpass_url, data={"data": query})
resp.raise_for_status()
elements = resp.json()["elements"]


# Normalize lat/lon and extract useful tags
def get_latlon(el):
    if el["type"] == "node":
        return el["lat"], el["lon"]
    c = el.get("center")
    return (c["lat"], c["lon"]) if c else (None, None)


rows = []
for el in elements:
    lat, lon = get_latlon(el)
    tags = el.get("tags", {})
    rows.append(
        {
            "osm_type": el["type"],
            "osm_id": el["id"],
            "name": tags.get("name"),
            "cuisine": tags.get("cuisine"),
            "addr:street": tags.get("addr:street"),
            "addr:housenumber": tags.get("addr:housenumber"),
            "phone": tags.get("phone"),
            "website": tags.get("website"),
            "lat": lat,
            "lon": lon,
        }
    )

# Convert to DataFrame
df = pd.DataFrame(rows)

# Save to CSV
output_file = "berlin_restaurants.csv"
df.to_csv(output_file, index=False, encoding="utf-8")

print(f"Saved {len(df)} restaurants to {output_file}")
