# Calisthenics Park Detection in Düsseldorf - Focused Implementation

## 🎯 Why This Focus is Brilliant for the Hackathon

### Strategic Advantages
- **Specific target:** Calisthenics parks (distinct visual signature)
- **Defined area:** Düsseldorf (manageable scope for 3 days)
- **Growing trend:** Calisthenics is exploding in popularity in Germany
- **Clear business case:** City planning for youth fitness infrastructure
- **Detectable features:** Metal equipment, rubber surfaces, geometric layouts

## 🏋️ Calisthenics Park Characteristics for Detection

### Visual/Spectral Signatures
```python
calisthenics_park_features = {
    'size': '20x20m to 40x40m typical',
    'surface': 'Rubber mats (low NDVI: 0.1-0.3)',
    'equipment': 'Metal bars (very low NDVI: 0.0-0.1)',
    'layout': 'Geometric arrangement of equipment',
    'context': 'Usually in public parks, near playgrounds',
    'surroundings': 'Grass or paved areas (contrast)'
}
```

### Spectral Characteristics
- **Equipment areas:** Very low NDVI (0.0-0.2) - metal and rubber
- **Surrounding grass:** Medium NDVI (0.4-0.7) - creates contrast
- **Size range:** Smaller than football fields, larger than playgrounds
- **Shape:** Often rectangular or L-shaped equipment arrangements

## 📍 Düsseldorf Target Area

### Geographic Bounds
```python
duesseldorf_bbox = {
    'min_longitude': 6.69,    # West boundary
    'min_latitude': 51.16,    # South boundary  
    'max_longitude': 6.95,    # East boundary
    'max_latitude': 51.30     # North boundary
}

# This covers ~25km x 15km = 375 km² area
# At 10m resolution: ~3.75 million pixels to analyze
```

### Known Calisthenics Locations (for validation)
```python
known_calisthenics_parks = [
    {'name': 'Rheinpark Düsseldorf', 'lat': 51.2217, 'lon': 6.7594},
    {'name': 'Südpark', 'lat': 51.2089, 'lon': 6.7969},
    {'name': 'Volksgarten', 'lat': 51.2186, 'lon': 6.7711},
    {'name': 'Elbsee', 'lat': 51.2847, 'lon': 6.8094},
    # Add more as we discover them
]
```