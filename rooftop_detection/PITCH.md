# Rooftop Soccer Field Detection - Data & Methodology

For identifying suitable rooftops across Berlin, we leveraged **Copernicus Data Space Ecosystem** through the Sentinel Hub Process API:

## Datasets Used

### 1. Sentinel-2 L2A (optical satellite imagery, 10m resolution)
- Multi-spectral bands (RGB + Near-Infrared) for vegetation detection
- Cloud filtering via Scene Classification Layer (SCL)
- Last 90 days of imagery to ensure current building states

### 2. Copernicus DEM (Digital Elevation Model, 10m resolution)
- Terrain elevation data for slope calculation
- Building height estimation for structural capacity assessment

## Detection Criteria

We filtered 1,069 suitable rooftops from thousands of candidates using strict requirements:

- **Size:** 400-10,000 m² (sufficient for mini soccer fields, realistic rooftop dimensions)
- **Flatness:** Slope < 10° (safe for sports installation, accessible)
- **Structure:** Height > 10m (adequate load-bearing capacity, professional building construction)
- **Surface:** NDVI < 0.3 (non-vegetated, concrete/metal roofs ideal for conversion)
- **Shape:** Aspect ratio < 4.0 (no elongated structures, actual sports-friendly dimensions)

## Technical Approach

Computer vision pipeline combining satellite imagery analysis with terrain modeling - automatically detecting building contours, calculating vegetation indices, and cross-validating with elevation data to identify the most promising locations for urban sports infrastructure development.

## Vision

While current detection provides initial candidates (but currently probably with many wrong buildings, "false positives" and left out areas), we would be building toward perfect accuracy in rooftop area detection through additional data integration (OSM building types, existing sports infrastructure, demographic demand) and refined ML-based classification via validation. 

The end goal: deliver **actionable, data-backed recommendations to city planners** - ranked lists of specific buildings where rooftop soccer fields would have maximum social impact and technical feasibility, enabling cities to make confident investment decisions for expanding urban sports access.

## Output

- **Dataset:** `results/berlin_rooftops.geojson` (1,069 rooftops with full metrics)
- **Visualization:** `results/berlin_rooftops_map.html` (interactive map with building contours)
