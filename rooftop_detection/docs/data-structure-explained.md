# Sentinel-2 Data Structure Explained

## 📊 What Sentinel-2 Data Actually Looks Like

When you see "satellite images," you're actually looking at **multi-dimensional arrays of numerical data**. Here's the real structure:

## 🔢 Data Dimensions & Structure

### Basic Structure
```
Sentinel-2 Image = 3D Array [Height, Width, Bands]

Example dimensions:
- Height: 10,980 pixels (corresponds to ~110 km at 10m resolution)
- Width: 10,980 pixels (corresponds to ~110 km at 10m resolution)  
- Bands: 13 spectral bands (like different "colors" of light)

Total size: 10,980 × 10,980 × 13 = ~1.57 billion data points per image!
```

### Real Data Example
```python
import numpy as np

# What a Sentinel-2 image actually looks like in code:
sentinel2_image = np.array([
    # Shape: (height, width, bands)
    # Each pixel has 13 values (one per spectral band)
])

print(f"Image shape: {sentinel2_image.shape}")
# Output: Image shape: (10980, 10980, 13)

print(f"Data type: {sentinel2_image.dtype}")
# Output: Data type: uint16 (16-bit integers, 0-65535 range)

print(f"Memory size: {sentinel2_image.nbytes / 1e9:.2f} GB")
# Output: Memory size: ~2.8 GB per image
```

## 📈 The 13 "Columns" (Spectral Bands) Explained

Think of each spectral band as a **column in a massive spreadsheet** where each row is a pixel location:

| Band | Name | Wavelength (nm) | Resolution (m) | **Key for Sports Fields** | Typical Values |
|------|------|-----------------|----------------|---------------------------|----------------|
| **B02** | **Blue** | 490 | **10m** | 🏟️ **Field boundaries, water features** | 0-3000 |
| **B03** | **Green** | 560 | **10m** | 🏟️ **Vegetation health, surface color** | 0-4000 |
| **B04** | **Red** | 665 | **10m** | 🏟️ **Vegetation stress, artificial surfaces** | 0-4000 |
| **B08** | **NIR** | 842 | **10m** | 🏟️ **CRITICAL: Vegetation vs non-vegetation** | 0-8000 |
| B05 | Red Edge 1 | 705 | 20m | Vegetation health | 0-5000 |
| B06 | Red Edge 2 | 740 | 20m | Vegetation health | 0-5000 |
| B07 | Red Edge 3 | 783 | 20m | Vegetation health | 0-5000 |
| B8A | Narrow NIR | 865 | 20m | Vegetation analysis | 0-6000 |
| B09 | Water Vapor | 945 | 60m | Atmospheric correction | 0-2000 |
| B10 | Cirrus | 1375 | 60m | Cloud detection | 0-1000 |
| B11 | SWIR 1 | 1610 | 20m | Moisture content | 0-4000 |
| B12 | SWIR 2 | 2190 | 20m | Soil/vegetation separation | 0-3000 |
| **SCL** | **Scene Class** | - | **20m** | 🏟️ **CRITICAL: Cloud/shadow mask** | 0-11 |

## 🎯 Key Metrics for Sports Field Detection

### 1. **NDVI (Normalized Difference Vegetation Index)**
```python
# Most important calculated metric for sports fields
NDVI = (NIR - Red) / (NIR + Red)
NDVI = (B08 - B04) / (B08 + B04)

# What NDVI values mean for sports fields:
ndvi_interpretation = {
    0.8-1.0: "Dense vegetation (healthy grass fields)",
    0.6-0.8: "Moderate vegetation (typical grass sports fields)", # 🎯 TARGET
    0.4-0.6: "Sparse vegetation (artificial turf, worn fields)",
    0.2-0.4: "Very sparse vegetation (dirt/clay courts)",
    0.0-0.2: "No vegetation (concrete, buildings)",
    -1.0-0.0: "Water, ice, clouds"
}
```

### 2. **Scene Classification Layer (SCL)**
```python
# Critical for filtering out bad data
scl_codes = {
    0: "No Data",
    1: "Saturated or defective",
    2: "Dark Area Pixels", 
    3: "Cloud Shadows",      # 🚫 Avoid these areas
    4: "Vegetation",         # 🎯 Good for sports fields
    5: "Not Vegetated",      # 🎯 Good for artificial surfaces
    6: "Water",
    7: "Unclassified",
    8: "Cloud Medium Prob",  # 🚫 Avoid
    9: "Cloud High Prob",    # 🚫 Avoid
    10: "Thin Cirrus",       # 🚫 Avoid
    11: "Snow"               # 🚫 Avoid
}
```

### 3. **True Color Composite (Visual)**
```python
# What humans see - for validation
true_color_rgb = np.stack([B04, B03, B02], axis=2)  # Red, Green, Blue
```

### 4. **False Color Composite (Vegetation Enhanced)**
```python
# Makes vegetation pop out in red
false_color = np.stack([B08, B04, B03], axis=2)  # NIR, Red, Green
```

## 📋 Practical Data Processing Pipeline

### Step 1: Load and Inspect Data
```python
import rasterio
import numpy as np

# Load Sentinel-2 data
with rasterio.open('sentinel2_image.tif') as src:
    # Read all bands
    image_data = src.read()  # Shape: (bands, height, width)
    
    print(f"Image dimensions: {image_data.shape}")
    print(f"Data type: {image_data.dtype}")
    print(f"Value range: {image_data.min()} to {image_data.max()}")
    
    # Get geospatial information
    transform = src.transform  # Pixel to geographic coordinates
    crs = src.crs             # Coordinate reference system
    bounds = src.bounds       # Geographic boundaries
```

### Step 2: Extract Key Metrics for Sports Fields
```python
# Extract the 4 most important bands (10m resolution)
blue = image_data[1]    # B02
green = image_data[2]   # B03  
red = image_data[3]     # B04
nir = image_data[7]     # B08

# Calculate NDVI (most important for sports fields)
ndvi = (nir - red) / (nir + red + 1e-8)  # Add small value to avoid division by zero

# Create masks for analysis
vegetation_mask = (ndvi > 0.3) & (ndvi < 0.9)  # Likely vegetation
cloud_mask = image_data[11] > 8  # Clouds (SCL > 8)
valid_mask = ~cloud_mask  # Areas without clouds

print(f"NDVI range: {ndvi[valid_mask].min():.3f} to {ndvi[valid_mask].max():.3f}")
print(f"Vegetation pixels: {vegetation_mask.sum():,} ({vegetation_mask.mean()*100:.1f}%)")
```

### Step 3: Sports Field Candidate Selection
```python
# Define sports field criteria based on the data
sports_field_criteria = {
    'ndvi_range': (0.4, 0.8),        # Moderate to high vegetation
    'size_range': (400, 12000),       # 40m×40m to 120m×100m in pixels
    'shape': 'rectangular',           # Geometric constraint
    'context': 'near_infrastructure'  # Usually near roads/buildings
}

# Filter pixels that meet criteria
candidate_pixels = (
    (ndvi >= sports_field_criteria['ndvi_range'][0]) &
    (ndvi <= sports_field_criteria['ndvi_range'][1]) &
    valid_mask
)

print(f"Potential sports field pixels: {candidate_pixels.sum():,}")
```

## 🎯 Example: Real Sports Field Detection

### Sample Data Values for a Football Field
```python
# What a typical football field looks like in the data:
football_field_example = {
    'location': (5400, 3200),  # Pixel coordinates (row, column)
    'size': (90, 45),          # 90×45 meters → 9×4.5 pixels at 10m resolution
    'spectral_values': {
        'B02_blue': 1200,      # Low blue reflectance
        'B03_green': 2800,     # High green reflectance (grass)
        'B04_red': 2200,       # Moderate red reflectance  
        'B08_nir': 4800,       # High NIR reflectance (healthy vegetation)
    },
    'calculated_indices': {
        'ndvi': 0.72,          # (4800-2200)/(4800+2200) = 0.72
        'evi': 0.68,           # Enhanced Vegetation Index
        'brightness': 2750,    # Average of visible bands
    },
    'classification': {
        'confidence': 0.87,    # 87% confidence it's a sports field
        'field_type': 'football_field',
        'surface_type': 'natural_grass'
    }
}
```

## 📊 Data Quality Considerations

### Typical File Sizes & Processing Requirements
```python
data_requirements = {
    'single_tile': {
        'size_on_disk': '1-8 GB (compressed)',
        'size_in_memory': '2.8 GB (uncompressed)',
        'processing_time': '5-30 minutes (depends on analysis)',
        'coverage_area': '100km × 100km'
    },
    'hackathon_region': {
        'berlin_coverage': '2-4 tiles needed',
        'total_data': '4-16 GB',
        'recommended_ram': '16 GB+',
        'processing_strategy': 'Process tiles separately, merge results'
    }
}
```

### Quality Flags to Check
```python
quality_checks = {
    'cloud_coverage': 'Should be < 20% for good results',
    'acquisition_angle': 'Nadir (straight down) is best',
    'seasonal_timing': 'Growing season (Apr-Oct) for grass fields',
    'data_completeness': 'Check for missing pixels or stripes'
}
```

## 🎯 Summary: What You're Really Working With

**Think of Sentinel-2 data as a massive spreadsheet where:**
- **Each row** = one pixel location (like a 10m×10m plot of land)
- **Each column** = one spectral measurement (like measuring different colors of light)
- **Each cell** = a number from 0-65535 representing how much light was reflected

**For sports field detection, you care most about:**
1. **NDVI values** (0.4-0.8 = likely sports fields)
2. **Shape analysis** (rectangular patterns in the pixel grid)
3. **Size filtering** (400-12000 pixels = realistic sports field sizes)
4. **Cloud masking** (SCL band to avoid bad data)

The "magic" is combining these numerical patterns to automatically find rectangular, vegetated areas that match sports field characteristics!

---

**Next step:** Try downloading a small sample tile and explore the actual numbers in Python/R to get hands-on experience with the data structure.