# Rooftop Detection for Soccer Fields — Berlin

## Project Context: Building Sports Infrastructure Intelligence

This rooftop detection module is **Phase 1** of a multi-stage analysis pipeline to identify optimal locations for new soccer facilities in Berlin:

### 🎯 The Greater Vision

**Goal**: Identify high-potential locations for new rooftop soccer pitches by combining satellite imagery, building data, existing infrastructure, and demographic insights.

**Multi-Phase Approach**:

1. **Phase 1 - Rooftop Detection** (This Module) 🏗️
   - Use Sentinel-2 satellite imagery + Copernicus DEM
   - Detect suitable flat rooftops (400-10,000 m², slope < 10°, height > 10m)
   - Filter by vegetation (NDVI), size, and structural suitability
   - Output: GeoJSON with 500 best rooftop candidates

2. **Phase 2 - Building Type Classification** 🏢 (Next Step)
   - Cross-reference detected rooftops with OpenStreetMap (OSM) building data
   - Identify building types: commercial centers, shopping malls, office buildings, industrial facilities vs. residential
   - **Priority**: Commercial/public buildings (higher feasibility for sports installations)
   - **Lower priority**: Private residential buildings (more regulatory barriers)

3. **Phase 3 - Existing Infrastructure Analysis** ⚽ (Planned)
   - Map existing soccer pitches from OSM (leisure=pitch + sport=soccer)
   - Calculate proximity/density of sports facilities
   - Identify underserved areas (gaps in coverage)
   - Avoid redundancy (don't build where pitches already exist nearby)

4. **Phase 4 - Demographic & Demand Analysis** 👥 (Planned)
   - Overlay population density data
   - Analyze demographics (age groups, youth population)
   - Match demand signals (high population + low pitch density = high potential)
   - Prioritize locations with greatest community impact

5. **Phase 5 - Final Scoring & Recommendations** 📊 (Planned)
   - Combined suitability score: rooftop quality + building type + infrastructure gap + demographic demand
   - Ranked list of top locations
   - Visualization: interactive map showing priority zones
   - Export: Dataset for urban planning and decision-making

### 🔑 Why This Matters

Urban spaces are constrained. Rooftop soccer fields offer:
- **Space efficiency**: Utilize unused rooftop areas
- **Community access**: Place facilities where people live/work
- **Sustainability**: Repurpose existing infrastructure
- **Equity**: Target underserved neighborhoods

By combining satellite remote sensing with OSM data and demographics, we create an **evidence-based approach** to sports infrastructure planning.

---

## Current Implementation: Phase 1 - Rooftop Detection

Real implementation detecting suitable rooftops for soccer field installation using Copernicus satellite data.

## Datasets Used

### 1. Sentinel-2 L2A (10m resolution) with Cloud Filtering
**Collection**: `sentinel-2-l2a`

**Bands used**:
- B02 (Blue, 10m)
- B03 (Green, 10m)
- B04 (Red, 10m)
- B08 (NIR, 10m)
- SCL (Scene Classification Layer)

**Time range**: Last 90 days from current date

**Cloud filtering**: 
- SCL band filters clouds (values 3, 8, 9, 10)
- maxCloudCoverage: 30%

**Why**: L2A provides atmospherically corrected, recent imagery. Cloud filtering via SCL ensures clean rooftop detection. The 10m resolution allows detection of individual building rooftops. NIR band enables NDVI calculation to exclude vegetated roofs.

### 2. Copernicus DEM Europe (10m resolution) ✅
**Product**: Copernicus DEM (via Sentinel Hub)

**Attributes used**:
- Elevation (m)
- Derived slope (degrees via gradient calculation)

**Filtering criteria**:
- Slope < 10° (flat roofs suitable for sports)
- Height > 10m (sufficient building height for rooftop access)

**Why**: 10m DEM enables identification of flat roofs and buildings with sufficient height for structural suitability and rooftop sports installation.

### 3. OpenStreetMap (OSM) Building & Sports Data - Planned (Phase 2 & 3)
**Data sources**:
- Building footprints with tags (building=*, amenity=*, shop=*, etc.)
- Existing sports facilities (leisure=pitch, sport=soccer)

**Why**: Essential for building type classification and infrastructure gap analysis in subsequent phases.

## Output Dataset Schema

Each detected rooftop is a GeoJSON Feature with:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [[13.1604, 52.33984], [13.1604, 52.34008], ...]
    ]
  },
  "properties": {
    "id": "rooftop_123",
    "area_m2": 924.67,
    "ndvi_mean": 0.0,
    "suitability_score": 0.97,
    "mean_height_m": null,
    "slope_deg": null,
    "source_datasets": ["S2_L3_Mosaic"]
  }
}
```

**Column descriptions**:
- `id`: Unique rooftop identifier (rooftop_N)
- `area_m2`: Rooftop area in square meters (400-10,000 range)
- `ndvi_mean`: Mean NDVI value (lower = less vegetation, better for sports)
- `suitability_score`: 0-1 score (weighted: 30% NDVI + 30% size + 30% slope + 10% height)
- `mean_height_m`: Building height from DEM in meters (filtered: > 10m)
- `slope_deg`: Roof slope in degrees (filtered: < 10°)
- `source_datasets`: Copernicus datasets used (S2 L2A + COP_DEM_10m)
- `geometry`: Actual building contour polygon with WGS84 coordinates (not bounding box)

## Detection Methodology

### Step 1: Data Retrieval (via Sentinel Hub Process API)
- Authenticate with Copernicus Data Space Ecosystem
- Fetch Sentinel-2 L2A imagery for last 90 days
- Fetch Copernicus DEM (10m resolution) for elevation data
- Apply cloud filtering using SCL band (removes clouds, shadows, water)
- Process Berlin in tiles (~8-10 tiles) to maintain ~5-7m/pixel resolution
- Each tile: 2500x2500 pixels via Process API

### Step 2: Preprocessing
- Extract RGB and NIR bands from Sentinel-2 data
- Scale reflectance values (divide by 10000)
- Calculate NDVI = (NIR - Red) / (NIR + Red)
- Calculate slope from DEM using gradient method

### Step 3: Building Detection
**Intensity-based scoring**:
- Convert to grayscale (0.299*R + 0.587*G + 0.114*B)
- High intensity = potential building roofs (concrete, metal)

**NDVI-based vegetation filtering**:
- Low NDVI (< 0.3) = non-vegetated surfaces
- Penalize vegetated areas in scoring

**Combined building score**: `intensity * (1 - ndvi_normalized)`

### Step 4: Binary Segmentation
- Apply Otsu's thresholding to building score
- Morphological operations:
  - Closing (kernel 5x5) - fill small holes
  - Opening (kernel 3x3) - remove noise
  - Erosion (kernel 3x3) - separate connected buildings

### Step 5: Contour Detection & Filtering
- Find contours in binary mask (OpenCV)
- **Area filter**: 400 - 10,000 m² 
  - Min 400m²: Suitable for mini soccer field (20x20m)
  - Max 10,000m²: Realistic rooftop size
- **Aspect ratio filter**: < 4.0
  - Removes elongated shapes (roads, parking lots)
  - Keeps rectangular/square roofs

### Step 6: DEM-Based Filtering ✅
- Calculate mean slope within each rooftop contour
- **Slope filter**: < 10° (flat roofs suitable for sports)
- Calculate mean building height from DEM
- **Height filter**: > 10m (adequate structural height)

### Step 7: Polygon Extraction with Actual Building Shapes ✅
- Convert pixel contours to geographic coordinates (WGS84)
- Create polygons following actual building contours (not bounding boxes)
- Calculate actual area in m² using geographic projection

### Step 8: Suitability Scoring
**Formula** (with DEM): `0.3 × NDVI + 0.3 × Size + 0.3 × Slope + 0.1 × Height`

- **NDVI score**: 1 - abs(ndvi_mean) × 2 (lower NDVI = better, less vegetation)
- **Size score**: Normalized 0-1 (larger = better, up to 1000m²)
- **Slope score**: 1 - (slope / 10°) (flatter = better)
- **Height score**: height / 50m capped at 1.0 (taller = better structural capacity)
- Result: 0-1 score (1 = most suitable)

### Step 9: Top 500 Selection ✅
- Sort all candidates by suitability score
- Keep only top 500 rooftops
- Ensures highest-quality dataset for next phases

### Step 10: Output Generation
- GeoJSON FeatureCollection with actual building polygon geometries
- Folium interactive map with rooftop overlays
- Clickable tooltips showing ID, area, height, slope, NDVI, score

## Identification Criteria Summary

### ✅ What Makes a Rooftop Suitable?

**Size Requirements**:
- Minimum: 400 m² (20m x 20m mini soccer field)
- Maximum: 10,000 m² (realistic rooftop limit)

**Shape Requirements**:
- Aspect ratio < 4.0 (not too elongated)
- Actual building contours (not rectangular bounding boxes)

**Surface Requirements**:
- Low vegetation (NDVI < 0.3)
- High reflectance (bright roofs = concrete/metal)
- Non-vegetated surfaces only

**Structural Requirements** ✅:
- **Flat roofs**: Slope < 10° (suitable for sports installation)
- **Adequate height**: Building > 10m (structural capacity + access)

**Detection Characteristics**:
- High intensity in RGB imagery
- Clear building boundaries via contour detection
- Separated from adjacent structures

### 🎯 Suitability Score Breakdown

**Score = 0.3 × NDVI + 0.3 × Size + 0.3 × Slope + 0.1 × Height**

- **NDVI Score** (30%): Lower vegetation scores higher (1 - |NDVI| × 2)
- **Size Score** (30%): Larger roofs score higher (normalized 0-1, max at 1000m²)
- **Slope Score** (30%): Flatter roofs score higher (1 - slope/10°)
- **Height Score** (10%): Taller buildings score higher (height/50m, capped at 1.0)
- **Result**: 0.0 (unsuitable) to 1.0 (most suitable)

**Example interpretations**:
- Score > 0.8: Excellent - Large, flat, tall building, non-vegetated
- Score 0.6-0.8: Good - Meets requirements, some compromises
- Score < 0.6: Marginal - Filtered out (not in top 500)

### 🚫 What Gets Filtered Out?

- Roofs < 400 m² (too small for sports field)
- Roofs > 10,000 m² (unrealistic, likely airports/warehouses)
- Elongated shapes (aspect ratio > 4.0 = roads, paths)
- Green roofs/vegetation (NDVI > 0.3)
- Steep roofs (slope > 10°) ✅
- Low buildings (height < 10m) ✅
- Connected building clusters (separated via erosion)
- **Beyond top 500**: Lower suitability scores filtered out ✅

### 📊 Current Detection Results (Berlin Center, November 2025)

- **Total candidates detected**: ~730 rooftops
- **After DEM filtering**: 500 rooftops (top-ranked)
- **Filtered by slope**: ~230 rooftops (too steep)
- **Coverage**: Berlin Center test area
- **Processing**: Single tile at ~2.5m/pixel resolution
- **Data sources**: Sentinel-2 L2A (last 90 days) + Copernicus DEM 10m
- **Output quality**: Actual building contours with height/slope data

## Quickstart

### Install dependencies:
```powershell
pip install -r challenge-02-sports-mapping\rooftop_detection\requirements.txt
```

### Configure credentials:
Create `C:\Repos\copernicus_credentials.json`:
```json
{
  "username": "your_copernicus_username",
  "password": "your_copernicus_password"
}
```
(Or set `COPERNICUS_USERNAME` and `COPERNICUS_PASSWORD` environment variables)

### Run detection for Berlin:
```powershell
python challenge-02-sports-mapping\rooftop_detection\rooftop_detector.py --city berlin
```

### Output files:
- `results/berlin_rooftops_TIMESTAMP.geojson` - Full dataset (1,113 rooftops)
- `results/berlin_rooftops_map_TIMESTAMP.html` - Interactive map
- `results/berlin_top50_rooftops.html` - Top 50 most suitable rooftops map

### View results:
```powershell
cd challenge-02-sports-mapping\results
python -m http.server 8000
# Open http://localhost:8000/berlin_rooftops_map_TIMESTAMP.html
```

## Notes for Team

- **Data source**: Sentinel-2 L2A with SCL cloud filtering (replaced L3 mosaics due to NODATA issues)
- **Resolution strategy**: Tiling approach maintains 5-7m/pixel (single-tile would be 16m/pixel)
- **Suitability scoring**: Basic heuristic combining size + vegetation; DEM integration pending
- **Authentication**: Uses same Copernicus account as calisthenics detector
- **Performance**: ~8 tiles × 30s = ~4 minutes for full Berlin
- **Limitations**: 
  - No slope/height analysis yet (DEM TODO)
  - No OSM sports field proximity
  - No roof material classification
  - Cloud filtering may miss some areas in bad weather

## Future Improvements

1. **DEM Integration** (COP-DEM 10m):
   - Filter by slope < 5°
   - Require building height > 15m
   - Calculate relative height above ground

2. **Validation Layer**:
   - OSM sports facilities proximity
   - Building footprint validation
   - Urban planning zone restrictions

3. **Advanced Scoring**:
   - Roof material (via Sentinel-1 SAR)
   - Sun exposure analysis
   - Accessibility score (proximity to roads/transit)

4. **Export Formats**:
   - CSV for spreadsheet analysis
   - Shapefile for GIS integration
   - KML for Google Earth
