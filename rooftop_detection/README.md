# 🏗️⚽ Rooftop Soccer Field Detector

**Identify suitable rooftops for soccer field installation using satellite imagery and AI**

## 🎯 Project Overview

This project uses **Copernicus Sentinel-2 satellite data** and **computer vision** to automatically detect flat, large rooftops in urban areas that could be converted into soccer fields. We analyze building height, roof slope, surface area, and vegetation to score each rooftop's suitability.

### Why Rooftop Soccer Fields?

- 🏙️ **Urban space optimization** - utilize unused rooftop space
- ⚽ **Increase sports access** - bring fields closer to communities  
- 🌱 **Sustainability** - repurpose existing structures
- 👥 **Social impact** - provide sports infrastructure in dense urban areas

## ✨ Features

- 🛰️ **Satellite-based detection** using Sentinel-2 imagery and Copernicus DEM
- 🤖 **Computer vision** for rooftop extraction and analysis
- 📊 **Suitability scoring** based on size, slope, height, and surface type
- 🗺️ **Interactive web app** built with Streamlit
- 📍 **Multi-city support** - Berlin, Düsseldorf (more coming soon)
- 🎨 **Visual analytics** with color-coded suitability maps

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Copernicus Data Space account ([register here](https://dataspace.copernicus.eu/))

### Installation

```powershell
# Clone the repository
git clone https://github.com/Chrisay-22/hackathon_nextcoder.git
cd hackathon_nextcoder/challenge-02-sports-mapping

# Install dependencies
pip install -r requirements.txt
```

### Setup Credentials

Create `copernicus_credentials.json` in the project root:

```json
{
  "username": "your_copernicus_username",
  "password": "your_copernicus_password"
}
```

Or set environment variables:
```powershell
$env:COPERNICUS_USERNAME = "your_username"
$env:COPERNICUS_PASSWORD = "your_password"
```

### Run the App

```powershell
python -m streamlit run app.py
```

The app will open at `http://localhost:8501`

## 🎨 How to Use

1. **Select a city** (Berlin or Düsseldorf)
2. **Choose coverage area** (full city or specific district)
3. **Click "Start Detection"** - processing takes 2-15 minutes depending on area size
4. **Explore results** in three tabs:
   - 🗺️ **Map**: Interactive visualization with color-coded rooftops
   - 📊 **Data Table**: Sortable table with all metrics
   - 📈 **Statistics**: Distribution charts and aggregated stats

### Understanding the Colors

Rooftops are color-coded by suitability score:

- 🟢 **Dark Green** (0.9-1.0): Excellent candidates
- 🟢 **Green** (0.8-0.9): Very good
- 🔵 **Blue** (0.7-0.8): Good
- 🟠 **Orange** (0.6-0.7): Moderate
- 🔴 **Red** (<0.6): Low suitability

## 🔧 Detection Criteria

### What Makes a Good Rooftop?

**Size Requirements:**
- Minimum: 400 m² (small pitch)
- Maximum: 10,000 m²

**Structural:**
- Height: > 5m (lowered threshold for better coverage)
- Slope: < 5° (flat surface)

**Surface:**
- NDVI < 0.3 (non-vegetated, e.g., concrete/metal)
- High reflectance
- Clear boundaries

**Shape:**
- Aspect ratio < 4.0 (not too elongated)

## 📁 Project Structure

```
challenge-02-sports-mapping/
├── app.py                          # Streamlit web application
├── requirements.txt                # Python dependencies
├── copernicus_credentials.json     # Your credentials (gitignored)
├── rooftop_detection/
│   ├── rooftop_detector.py         # Core detection logic
│   └── README.md                   # Technical documentation
├── results/
│   ├── berlin_rooftops.geojson     # Detection results (38 MB)
│   ├── berlin_rooftops_compressed.geojson  # Compressed (8 MB)
│   ├── berlin_rooftops_map.html    # Standalone map
│   ├── create_map.py               # Map generation script
│   └── compress_geojson.py         # GeoJSON compression utility
├── src/                            # Legacy detection scripts
└── docs/                           # Architecture & data docs
```

## 🛰️ Technology Stack

- **Satellite Data**: Copernicus Sentinel-2 L2A imagery, DEM (10m)
- **Computer Vision**: OpenCV for contour detection
- **Geospatial**: Shapely, GeoPandas, Rasterio
- **Web App**: Streamlit, Folium for interactive maps
- **API**: Sentinel Hub Process API

## 📊 Results

### Berlin Detection (Full City)

- 🏗️ **12,190 rooftops** detected
- 📏 Average area: ~850 m²
- 🎯 Average suitability: 0.71
- 🟢 Top candidates: 2,400+ with score > 0.8

Results available in `results/berlin_rooftops.geojson` (or compressed version at 8 MB).

## 🗺️ Available Locations

### Berlin
- Full city coverage
- Districts: Mitte, Charlottenburg, Friedrichshain, Kreuzberg, Neukölln, Pankow, Spandau, Steglitz

### Düsseldorf
- Full city coverage
- Districts: Altstadt, Stadtmitte, Pempelfort, Oberkassel, Bilk, Unterrath, Benrath

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Add more cities
- [ ] Improve detection algorithm (ML-based segmentation)
- [ ] Add structural engineering feasibility checks
- [ ] Integrate with urban planning APIs
- [ ] Cost estimation model

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **Copernicus/ESA** for satellite data access
- **OpenStreetMap** contributors
- Built for **NextCoder Hackathon 2024**

---

**Note**: This is a proof-of-concept for urban planning and sports infrastructure development. Actual rooftop conversions require structural engineering assessments, permits, and safety evaluations.