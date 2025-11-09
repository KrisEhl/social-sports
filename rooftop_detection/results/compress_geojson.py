"""Compress GeoJSON by simplifying geometries and reducing precision"""
import json
from pathlib import Path

input_file = Path(__file__).parent / "berlin_rooftops.geojson"
output_file = Path(__file__).parent / "berlin_rooftops_compressed.geojson"

print(f"📂 Loading {input_file.name}...")
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

original_size = input_file.stat().st_size / (1024 * 1024)
print(f"📊 Original size: {original_size:.2f} MB")
print(f"📊 Original features: {len(data['features'])}")

# Reduce coordinate precision from ~15 decimals to 6 (still ~10cm accuracy)
def round_coords(coords, precision=6):
    """Round coordinates to reduce file size"""
    if isinstance(coords[0], (int, float)):
        return [round(c, precision) for c in coords]
    return [round_coords(c, precision) for c in coords]

# Simplify properties - keep only essential info
def simplify_properties(props):
    """Keep only the most important properties"""
    return {
        'id': props.get('id'),
        'area_m2': round(props.get('area_m2', 0), 1),
        'score': round(props.get('suitability_score', 0), 3),
        'height_m': round(props.get('mean_height_m', 0), 1),
        'slope': round(props.get('slope_deg', 0), 1),
    }

# Optional: Filter out low-quality rooftops
min_score = 0.4  # Only keep rooftops with score >= 0.4
print(f"🔍 Filtering rooftops with score >= {min_score}...")

compressed_features = []
for feature in data['features']:
    score = feature['properties'].get('suitability_score', 0)
    
    if score >= min_score:
        # Simplify geometry coordinates
        feature['geometry']['coordinates'] = round_coords(
            feature['geometry']['coordinates'], 
            precision=6
        )
        
        # Simplify properties
        feature['properties'] = simplify_properties(feature['properties'])
        
        compressed_features.append(feature)

compressed_data = {
    "type": "FeatureCollection",
    "features": compressed_features
}

print(f"✅ Kept {len(compressed_features)} features (removed {len(data['features']) - len(compressed_features)})")

# Save compressed version
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(compressed_data, f, separators=(',', ':'))

compressed_size = output_file.stat().st_size / (1024 * 1024)
reduction = ((original_size - compressed_size) / original_size) * 100

print(f"✅ Compressed size: {compressed_size:.2f} MB")
print(f"📉 Size reduction: {reduction:.1f}%")

if compressed_size > 10:
    print(f"\n⚠️  Still too large! Try increasing min_score filter.")
    print(f"   Current min_score: {min_score}")
    print(f"   Suggested: 0.5 or 0.6")
else:
    print(f"✅ File is now under 10 MB!")

print(f"\n📁 Saved to: {output_file}")
