"""Create an interactive map from Berlin rooftop GeoJSON"""
import json
import folium
from pathlib import Path

# Load the GeoJSON
results_dir = Path(__file__).parent
geojson_file = results_dir / "berlin_rooftops.geojson"

if not geojson_file.exists():
    print(f"❌ File not found: {geojson_file}")
    print("Available files:")
    for f in results_dir.glob("*.geojson"):
        print(f"  - {f.name}")
    exit(1)

print(f"📂 Loading {geojson_file.name}...")
with open(geojson_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

features = data['features']
print(f"✅ Found {len(features)} rooftops")

# Calculate center
if features:
    all_coords = []
    for feature in features:
        coords = feature['geometry']['coordinates'][0]
        for coord in coords:
            all_coords.append(coord)
    
    avg_lon = sum(c[0] for c in all_coords) / len(all_coords)
    avg_lat = sum(c[1] for c in all_coords) / len(all_coords)
else:
    avg_lat, avg_lon = 52.52, 13.405  # Berlin center

# Create map
m = folium.Map(
    location=[avg_lat, avg_lon],
    zoom_start=12,
    tiles='OpenStreetMap'
)

# Color function based on suitability
def get_color(score):
    if score >= 0.9:
        return 'darkgreen'
    elif score >= 0.8:
        return 'green'
    elif score >= 0.7:
        return 'blue'
    elif score >= 0.6:
        return 'orange'
    else:
        return 'red'

# Add legend
legend_html = '''
<div style="position: fixed; 
            top: 10px; right: 10px; width: 220px; 
            background-color: white; z-index:9999; font-size:14px;
            border:2px solid grey; border-radius: 5px; padding: 10px">
<h4 style="margin-top:0;">Rooftop Suitability ⚽</h4>
<p><i class="fa fa-square" style="color:darkgreen"></i> Excellent (0.9-1.0)</p>
<p><i class="fa fa-square" style="color:green"></i> Very Good (0.8-0.9)</p>
<p><i class="fa fa-square" style="color:blue"></i> Good (0.7-0.8)</p>
<p><i class="fa fa-square" style="color:orange"></i> Moderate (0.6-0.7)</p>
<p><i class="fa fa-square" style="color:red"></i> Low (&lt;0.6)</p>
<hr>
<p style="margin:0;"><strong>Total:</strong> ''' + str(len(features)) + ''' rooftops</p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Add rooftops to map
for feature in features:
    score = feature['properties']['suitability_score']
    
    folium.GeoJson(
        {"type": "FeatureCollection", "features": [feature]},
        style_function=lambda x, score=score: {
            'fillColor': get_color(score),
            'color': get_color(score),
            'weight': 2,
            'fillOpacity': 0.6,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['id', 'area_m2', 'suitability_score', 'mean_height_m', 'slope_deg', 'ndvi_mean'],
            aliases=['ID:', 'Area (m²):', 'Score:', 'Height (m):', 'Slope (°):', 'NDVI:'],
            localize=True
        )
    ).add_to(m)

# Save map
output_file = results_dir / "berlin_rooftops_map.html"
m.save(str(output_file))
print(f"✅ Map saved: {output_file}")
print(f"🌐 Open in browser: file:///{output_file}")
