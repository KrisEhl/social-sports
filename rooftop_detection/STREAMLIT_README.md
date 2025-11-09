# Rooftop Soccer Field Detector - Streamlit App

Interactive web application for detecting suitable rooftops for soccer field installation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Features

- **Interactive City Selection**: Choose from available cities (Berlin, Düsseldorf)
- **District-Level Analysis**: Select specific districts/boroughs or analyze entire cities
- **Live Detection**: Run rooftop detection directly from the interface
- **Interactive Map**: Visualize detected rooftops with tooltips
- **Data Table**: Browse and sort all detected rooftops
- **Statistics Dashboard**: View distribution charts and metrics
- **CSV Export**: Download results for further analysis

## Available Locations

### Berlin
- Full city coverage
- Districts: Mitte, Charlottenburg, Friedrichshain, Kreuzberg, Neukölln, Pankow, Spandau, Steglitz

### Düsseldorf  
- Full city coverage
- Districts: Altstadt, Stadtmitte, Pempelfort, Oberkassel, Bilk, Unterrath, Benrath

## How to Use

1. **Select a Region** (Berlin or Düsseldorf)
2. **Choose Coverage** (Full city or specific district)
3. **Click "Start Detection"** to begin the analysis
   - Small districts: 2-5 minutes
   - Full city: 5-15 minutes
4. **View Results** in three tabs:
   - **Map**: Interactive map with clickable building polygons
   - **Data Table**: Sortable table with all rooftop metrics
   - **Statistics**: Distribution charts and aggregated metrics
4. **Download Data** as CSV for external analysis

## Detection Criteria

The app uses strict criteria to identify suitable rooftops:

- **Size**: 400-10,000 m²
- **Flatness**: Slope < 10°
- **Structure**: Height > 10m
- **Surface**: NDVI < 0.3 (non-vegetated)
- **Shape**: Aspect ratio < 4.0

## Data Sources

- **Sentinel-2 L2A**: Optical satellite imagery (10m resolution)
- **Copernicus DEM**: Digital Elevation Model (10m resolution)

## Credentials Setup

The app requires Copernicus Data Space Ecosystem credentials. You can provide them in multiple ways:

### Option 1: Credentials file (Recommended)
Create a `copernicus_credentials.json` file in one of these locations:
- Repository root: `challenge-02-sports-mapping/copernicus_credentials.json`
- User home: `~/.copernicus_credentials.json`
- Absolute path: `C:/Repos/copernicus_credentials.json`

Content:
```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

### Option 2: Environment variables
Set these environment variables:
- `COPERNICUS_CLIENT_ID`
- `COPERNICUS_CLIENT_SECRET`

### Option 3: Manual input
The app will prompt you for credentials if none are found.

## Results Caching

Results are automatically saved in the `results/` directory. When you select a city/district:
- **If results exist**: They load instantly (no processing needed)
- **If no results**: You can run detection
- **To refresh**: Use the "🔄 Re-run Detection" button to process again

This means you can:
- Share results by committing the `results/` folder
- Clone the repo and immediately view existing results
- Collaborate without re-processing every time
