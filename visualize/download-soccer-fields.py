import requests
import pandas as pd

overpass_url = "https://overpass-api.de/api/interpreter"

query = r"""
[out:json][timeout:120];
area["wikidata"="Q64"]->.searchArea;

(
  node["leisure"="pitch"]["sport"~"^(soccer|football)$"](area.searchArea);
  way ["leisure"="pitch"]["sport"~"^(soccer|football)$"](area.searchArea);
  relation["leisure"="pitch"]["sport"~"^(soccer|football)$"](area.searchArea);

  node["leisure"="stadium"]["sport"~"^(soccer|football)$"](area.searchArea);
  way ["leisure"="stadium"]["sport"~"^(soccer|football)$"](area.searchArea);
  relation["leisure"="stadium"]["sport"~"^(soccer|football)$"](area.searchArea);

  node["leisure"="sports_centre"]["sport"~"^(soccer|football)$"](area.searchArea);
  way ["leisure"="sports_centre"]["sport"~"^(soccer|football)$"](area.searchArea);
  relation["leisure"="sports_centre"]["sport"~"^(soccer|football)$"](area.searchArea);
);
out tags center;
"""

resp = requests.post(overpass_url, data={"data": query})
resp.raise_for_status()
elements = resp.json()["elements"]


def get_latlon(el):
    if el["type"] == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center")
    return (c["lat"], c["lon"]) if c else (None, None)


rows = []
stadium_count = 0
for el in elements:
    tags = el.get("tags", {})
    lat, lon = get_latlon(el)
    rows.append(
        {
            "osm_type": el["type"],
            "osm_id": el["id"],
            "name": tags.get("name"),
            "leisure": tags.get("leisure"),
            "sport": tags.get("sport"),
            "surface": tags.get("surface"),
            "addr:street": tags.get("addr:street"),
            "addr:housenumber": tags.get("addr:housenumber"),
            "operator": tags.get("operator"),
            "access": tags.get("access"),
            "website": tags.get("website"),
            "lat": lat,
            "lon": lon,
            "tags": tags,  # keep all tags if you want to inspect later
        }
    )
df = pd.DataFrame(rows).dropna(subset=["lat", "lon"])
df.to_csv("berlin_soccer_fields.csv", index=False, encoding="utf-8")
print(f"Saved {len(df)} features to berlin_soccer_fields.csv")
