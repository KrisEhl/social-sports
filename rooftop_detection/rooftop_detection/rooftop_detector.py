"""Rooftop detector for Berlin

Real implementation using:
- Sentinel Hub Process API for Sentinel-2 L3 Cloudless Mosaics
- Copernicus DEM (10m) for slope and height analysis
- Computer vision for rooftop extraction

Usage:
    python rooftop_detector.py --city berlin

See README.md for details.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import getpass

import numpy as np
import cv2 as cv
import requests
from shapely.geometry import Polygon, mapping
import geopandas as gpd
import folium
from rich.console import Console
from rich.progress import Progress

console = Console()

# Use relative paths (works when cloned)
SCRIPT_DIR = Path(__file__).parent.resolve()
RESULTS_DIR = SCRIPT_DIR.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# City bounding boxes [west, south, east, north]
CITY_BBOX = {
    # Berlin
    'berlin': [13.088, 52.338, 13.761, 52.675],
    'berlin_mitte': [13.35, 52.49, 13.45, 52.54],
    'berlin_charlottenburg': [13.23, 52.48, 13.35, 52.55],
    'berlin_friedrichshain': [13.42, 52.50, 13.48, 52.54],
    'berlin_kreuzberg': [13.38, 52.48, 13.43, 52.51],
    'berlin_neukoelln': [13.40, 52.43, 13.50, 52.49],
    'berlin_pankow': [13.37, 52.54, 13.46, 52.62],
    'berlin_spandau': [13.15, 52.52, 13.26, 52.58],
    'berlin_steglitz': [13.30, 52.42, 13.38, 52.47],
    
    # Düsseldorf
    'duesseldorf': [6.685, 51.125, 6.950, 51.330],
    'duesseldorf_altstadt': [6.76, 51.22, 6.78, 51.23],
    'duesseldorf_stadtmitte': [6.77, 51.22, 6.80, 51.24],
    'duesseldorf_pempelfort': [6.78, 51.23, 6.82, 51.25],
    'duesseldorf_oberkassel': [6.73, 51.22, 6.76, 51.25],
    'duesseldorf_bilk': [6.77, 51.21, 6.80, 51.22],
    'duesseldorf_unterrath': [6.79, 51.26, 6.84, 51.29],
    'duesseldorf_benrath': [6.87, 51.15, 6.92, 51.18],
}


class RooftopDetector:
    """Real rooftop detector using Copernicus data."""
    
    def __init__(self):
        self.auth_url = (
            "https://identity.dataspace.copernicus.eu/auth/realms/"
            "CDSE/protocol/openid-connect/token"
        )
        self.process_api_url = "https://sh.dataspace.copernicus.eu/api/v1/process"
        self.access_token = None
        
        # Detection parameters
        self.min_area_m2 = 400
        self.max_slope_deg = 5.0
        self.min_height_m = 5.0  # Lowered to capture more buildings
        self.max_ndvi = 0.3  # Exclude vegetated roofs
    
    def authenticate(self, username: str = None, password: str = None) -> bool:
        """Authenticate with Copernicus Data Space."""
        # Try to load from credentials file first
        # Check multiple locations: 1) Repo root, 2) Parent directory, 3) Absolute path
        possible_creds = [
            SCRIPT_DIR.parent / "copernicus_credentials.json",  # In repo root
            Path.home() / ".copernicus_credentials.json",  # User home
            Path("C:/Repos/copernicus_credentials.json")  # Legacy absolute path
        ]
        
        creds_file = None
        for path in possible_creds:
            if path.exists():
                creds_file = path
                break
        
        if not username and creds_file:
            try:
                with open(creds_file, 'r') as f:
                    creds = json.load(f)
                    username = creds.get('username')
                    password = creds.get('password')
                    console.print(f"📁 Loaded credentials from {creds_file}", style="dim")
            except Exception as e:
                console.print(f"⚠️ Could not load credentials file: {e}", style="yellow")
        
        if not username:
            username = os.getenv('COPERNICUS_USERNAME')
            if not username:
                username = input("Copernicus username: ")
        
        if not password:
            password = os.getenv('COPERNICUS_PASSWORD')
            if not password:
                import getpass
                password = getpass.getpass("Copernicus password: ")
        
        try:
            console.print("🔐 Authenticating with Copernicus...", style="yellow")
            
            auth_data = {
                'grant_type': 'password',
                'username': username,
                'password': password,
                'client_id': 'cdse-public'
            }
            
            response = requests.post(self.auth_url, data=auth_data, timeout=30)
            
            if response.status_code == 200:
                self.access_token = response.json()['access_token']
                console.print("✅ Authentication successful!", style="green")
                return True
            else:
                console.print(f"❌ Auth failed: {response.status_code}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Auth error: {e}", style="red")
            return False
    
    def fetch_copernicus_dem(self, bbox: List[float]) -> np.ndarray:
        """Fetch Copernicus DEM (10m) for the given bounding box."""
        console.print("🗻 Fetching Copernicus DEM...", style="yellow")
        
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: ["DEM"],
                output: { bands: 1, sampleType: "FLOAT32" }
            };
        }
        function evaluatePixel(sample) {
            return [sample.DEM];
        }
        """
        
        request_payload = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "dem",
                    "dataFilter": {}
                }]
            },
            "output": {
                "width": 2500,
                "height": 2500,
                "responses": [{
                    "identifier": "default",
                    "format": {"type": "image/tiff"}
                }]
            },
            "evalscript": evalscript
        }
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.process_api_url,
                headers=headers,
                json=request_payload,
                timeout=120
            )
            
            if response.status_code != 200:
                console.print(f"   ⚠️  DEM fetch failed: {response.status_code}", style="yellow")
                return None
            
            # Read TIFF from response
            import io
            import rasterio
            with rasterio.open(io.BytesIO(response.content)) as src:
                dem = src.read(1)  # Single band
            
            console.print(f"   DEM shape: {dem.shape}, range: [{dem.min():.1f}, {dem.max():.1f}]m", style="dim")
            console.print("✅ DEM retrieved", style="green")
            return dem
            
        except Exception as e:
            console.print(f"   ⚠️  DEM error: {e}", style="yellow")
            return None
    
    def fetch_sentinel2_cloudless_mosaic(self, bbox: List[float]) -> np.ndarray:
        """Fetch Sentinel-2 imagery using Process API.
        
        Args:
            bbox: [west, south, east, north] in WGS84
            
        Returns:
            np.ndarray with shape (height, width, 4) - RGB + NIR
        """
        console.print("🛰️ Fetching Sentinel-2 imagery...", style="cyan")
        
        # Use regular Sentinel-2 L2A (more reliable than cloudless mosaics)
        evalscript = """
        //VERSION=3
        function setup() {
          return {
            input: ["B04", "B03", "B02", "B08", "SCL", "dataMask"],
            output: { bands: 4, sampleType: "INT16" }
          };
        }
        
        function evaluatePixel(sample) {
          // Filter clouds using Scene Classification Layer
          // SCL: 4=vegetation, 5=not_vegetated, 6=water, 7=unclassified
          // Skip: 3=cloud_shadow, 8,9=cloud, 10=thin_cirrus
          if (sample.SCL == 3 || sample.SCL >= 8) {
            return [32767, 32767, 32767, 32767];  // NODATA for clouds
          }
          return [sample.B04 * 10000, sample.B03 * 10000, 
                  sample.B02 * 10000, sample.B08 * 10000];
        }
        """
        
        request_data = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{(datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')}T00:00:00Z",
                            "to": f"{datetime.now().strftime('%Y-%m-%d')}T23:59:59Z"
                        },
                        "maxCloudCoverage": 30
                    },
                    "type": "sentinel-2-l2a"
                }]
            },
            "output": {
                "width": 2500,  # Max allowed by Process API
                "height": 2500,
                "responses": [{
                    "identifier": "default",
                    "format": {"type": "image/tiff"}
                }]
            },
            "evalscript": evalscript
        }
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(self.process_api_url, json=request_data,
                                   headers=headers, timeout=60)
            
            if response.status_code == 200:
                # Save and load TIFF
                tiff_path = RESULTS_DIR / "temp_s2_mosaic.tif"
                with open(tiff_path, 'wb') as f:
                    f.write(response.content)
                
                import rasterio
                with rasterio.open(tiff_path) as src:
                    data = src.read()  # Shape: (4, height, width)
                    data = np.moveaxis(data, 0, -1)  # -> (height, width, 4)
                
                console.print(f"   Data shape: {data.shape}, dtype: {data.dtype}", style="dim")
                console.print(f"   Data range: [{data.min()}, {data.max()}]", style="dim")
                
                # Check if data is valid
                if data.max() == 0 or np.all(data == 0):
                    console.print("   ⚠️ WARNING: Data is all zeros!", style="yellow")
                    return None
                
                console.print("✅ Sentinel-2 mosaic retrieved", style="green")
                return data
            else:
                console.print(f"❌ Process API error: {response.status_code}", 
                            style="red")
                console.print(response.text)
                return None
                
        except Exception as e:
            console.print(f"❌ Sentinel-2 fetch error: {e}", style="red")
            return None


    def detect_rooftops_from_imagery(self, rgb_nir: np.ndarray, 
                                     bbox: List[float],
                                     dem: np.ndarray = None) -> List[Dict]:
        """Detect rooftop candidates from Sentinel-2 imagery.
        
        Args:
            rgb_nir: (height, width, 4) array with R, G, B, NIR bands
            bbox: [west, south, east, north] for coordinate mapping
            dem: Optional DEM array for slope/height filtering
            
        Returns:
            List of rooftop feature dicts
        """
        console.print("🔍 Detecting rooftops from imagery...", style="cyan")
        
        if rgb_nir is None:
            return []
        
        # Extract bands and normalize
        red = rgb_nir[:, :, 0].astype(float)
        green = rgb_nir[:, :, 1].astype(float)
        blue = rgb_nir[:, :, 2].astype(float)
        nir = rgb_nir[:, :, 3].astype(float)
        
        # Calculate NDVI
        ndvi = np.where((nir + red) != 0, (nir - red) / (nir + red), 0)
        
        # Multi-step approach for better building detection
        
        # 1. Use intensity (brightness) to find built-up areas
        intensity = (red + green + blue) / 3
        intensity_norm = (intensity - intensity.min()) / (intensity.max() - intensity.min() + 1e-8)
        
        # 2. Combine with NDVI (buildings = bright + low NDVI)
        building_score = intensity_norm * (1 - (ndvi + 1) / 2)  # Normalize NDVI to 0-1
        building_score = (building_score * 255).astype(np.uint8)
        
        # 3. Threshold to get building candidates
        _, binary = cv.threshold(building_score, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
        
        # 4. Morphological operations
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (5, 5))
        binary = cv.morphologyEx(binary, cv.MORPH_CLOSE, kernel, iterations=2)
        binary = cv.morphologyEx(binary, cv.MORPH_OPEN, kernel, iterations=1)
        
        # Remove small noise
        kernel_small = cv.getStructuringElement(cv.MORPH_RECT, (3, 3))
        binary = cv.morphologyEx(binary, cv.MORPH_ERODE, kernel_small, iterations=1)
        
        # Find contours
        contours, _ = cv.findContours(binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        features = []
        h, w = rgb_nir.shape[:2]
        west, south, east, north = bbox
        
        # Calculate meters per pixel (approximate)
        meters_per_pixel_x = (east - west) * 111320 * np.cos(np.radians((north + south) / 2)) / w
        meters_per_pixel_y = (north - south) * 111320 / h
        avg_meters_per_pixel = (meters_per_pixel_x + meters_per_pixel_y) / 2
        
        console.print(f"   Resolution: ~{avg_meters_per_pixel:.1f}m/pixel", style="dim")
        console.print(f"   Min rooftop size: {self.min_area_m2}m² = ~{self.min_area_m2 / (avg_meters_per_pixel ** 2):.1f} pixels", style="dim")
        console.print(f"   Total contours found: {len(contours)}", style="dim")
        
        # Calculate slope from DEM if available
        slope_map = None
        if dem is not None:
            console.print(f"   Calculating slope from DEM...", style="dim")
            # Calculate slope using gradients (rise over run)
            # Convert DEM pixel gradients to meters
            dy, dx = np.gradient(dem)
            # Slope magnitude in meters per meter
            slope_magnitude = np.sqrt(dx**2 + dy**2) / avg_meters_per_pixel
            # Convert to degrees
            slope_map = np.arctan(slope_magnitude) * 180 / np.pi
            console.print(f"   Slope range: [{np.nanmin(slope_map):.1f}°, {np.nanmax(slope_map):.1f}°]", style="dim")
        
        filtered_count = {"size": 0, "aspect": 0, "slope": 0, "height": 0, "accepted": 0}
        
        for idx, contour in enumerate(contours):
            area_pixels = cv.contourArea(contour)
            area_m2 = area_pixels * (avg_meters_per_pixel ** 2)
            
            # Filter by area (400-10000 m²)
            if area_m2 < self.min_area_m2 or area_m2 > 10000:
                filtered_count["size"] += 1
                continue
            
            # Get bounding rect
            x, y, cw, ch = cv.boundingRect(contour)
            
            # Filter by aspect ratio (avoid very elongated shapes)
            aspect_ratio = max(cw, ch) / (min(cw, ch) + 1)
            if aspect_ratio > 4:  # Too elongated
                filtered_count["aspect"] += 1
                continue
            
            # Convert contour points to lat/lon (actual building shape, not bounding box)
            contour_coords = []
            for point in contour.squeeze():
                if len(point.shape) == 0 or len(point) < 2:
                    continue
                px, py = point[0], point[1]
                lon = west + (px / w) * (east - west)
                lat = north - (py / h) * (north - south)
                contour_coords.append([lon, lat])
            
            # Close the polygon
            if len(contour_coords) > 0 and contour_coords[0] != contour_coords[-1]:
                contour_coords.append(contour_coords[0])
            
            # Skip if too few points
            if len(contour_coords) < 4:
                filtered_count["aspect"] += 1
                continue
            
            poly = Polygon(contour_coords)
            
            # Calculate mean NDVI in this region
            mask = np.zeros(ndvi.shape, dtype=np.uint8)
            cv.drawContours(mask, [contour], -1, 255, -1)
            ndvi_mean = np.mean(ndvi[mask > 0])
            
            # DEM-based filtering
            mean_height = None
            mean_slope = None
            if dem is not None and slope_map is not None:
                dem_values = dem[mask > 0]
                slope_values = slope_map[mask > 0]
                
                if len(dem_values) > 0:
                    mean_height = float(np.mean(dem_values))
                    mean_slope = float(np.mean(slope_values))
                    
                    # Filter by slope (flat roofs < 15° - relaxed from 10°)
                    if mean_slope > 15.0:
                        filtered_count["slope"] += 1
                        continue
                    
                    # Filter by height (buildings > 8m - relaxed from 10m)
                    if mean_height < 8.0:
                        filtered_count["height"] += 1
                        continue
            
            # Suitability score
            ndvi_score = max(0, 1.0 - abs(ndvi_mean) * 2)  # Low NDVI better
            size_score = min(area_m2 / 1000, 1.0)  # Bigger better (up to 1000m²)
            slope_score = 1.0 if mean_slope is None else max(0, 1.0 - mean_slope / 10.0)  # Flatter better
            height_score = 0.5 if mean_height is None else min(mean_height / 50.0, 1.0)  # Taller better (up to 50m)
            
            # Weighted score
            if mean_slope is not None:
                score = (ndvi_score * 0.3 + size_score * 0.3 + slope_score * 0.3 + height_score * 0.1)
            else:
                score = (ndvi_score * 0.5 + size_score * 0.5)
            
            sources = ["S2_L2A"]
            if dem is not None:
                sources.append("COP_DEM_10m")
            
            feature = {
                "type": "Feature",
                "properties": {
                    "id": f"rooftop_{idx}",
                    "area_m2": float(area_m2),
                    "ndvi_mean": float(ndvi_mean),
                    "suitability_score": float(score),
                    "mean_height_m": mean_height,
                    "slope_deg": mean_slope,
                    "source_datasets": sources
                },
                "geometry": mapping(poly)
            }
            features.append(feature)
            filtered_count["accepted"] += 1
        
        filter_msg = f"   Filtered: {filtered_count['size']} too small/large, {filtered_count['aspect']} wrong shape"
        if dem is not None:
            filter_msg += f", {filtered_count['slope']} too steep, {filtered_count['height']} too low"
        console.print(filter_msg, style="dim")
        
        # Sort by suitability score (no per-tile limit - will limit globally)
        features.sort(key=lambda x: x['properties']['suitability_score'], reverse=True)
        
        console.print(f"✅ Found {len(features)} rooftop candidates", style="green")
        return features


def create_visualization_map(features: List[Dict], bbox: List[float], 
                            output_path: Path):
    """Create interactive Folium map with detected rooftops."""
    console.print("🗺️ Creating visualization map...", style="cyan")
    
    # Center on bbox
    west, south, east, north = bbox
    center_lat = (south + north) / 2
    center_lon = (west + east) / 2
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    if len(features) == 0:
        # Just save empty map if no features
        console.print("   No features to display", style="dim")
        m.save(output_path)
        console.print(f"✅ Map saved to {output_path}", style="green")
        return
    
    # Add rooftops
    feature_collection = {"type": "FeatureCollection", "features": features}
    
    folium.GeoJson(
        feature_collection,
        name='Detected Rooftops',
        style_function=lambda x: {
            'fillColor': '#ff7800',
            'color': '#ff7800',
            'weight': 2,
            'fillOpacity': 0.5
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['id', 'area_m2', 'ndvi_mean', 'suitability_score'],
            aliases=['ID', 'Area (m²)', 'NDVI', 'Score']
        )
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    m.save(output_path)
    console.print(f"✅ Map saved to {output_path}", style="green")


def process_city_tiled(city: str, detector: RooftopDetector, tile_size_deg: float = 0.05) -> List[Dict]:
    """Process a city in tiles to maintain resolution."""
    bbox = CITY_BBOX[city]
    west, south, east, north = bbox
    
    # Calculate tiles
    tiles = []
    lat = south
    while lat < north:
        lon = west
        while lon < east:
            tile_bbox = [
                lon,
                lat,
                min(lon + tile_size_deg, east),
                min(lat + tile_size_deg, north)
            ]
            tiles.append(tile_bbox)
            lon += tile_size_deg
        lat += tile_size_deg
    
    console.print(f"🗺️ Processing {len(tiles)} tiles for full coverage\n", style="cyan")
    
    all_features = []
    tile_stats = []  # Track statistics per tile
    
    for i, tile_bbox in enumerate(tiles, 1):
        tile_center_lat = (tile_bbox[1] + tile_bbox[3]) / 2
        tile_center_lon = (tile_bbox[0] + tile_bbox[2]) / 2
        console.print(f"📍 Tile {i}/{len(tiles)}: Center ({tile_center_lat:.3f}, {tile_center_lon:.3f})", style="dim")
        
        # Fetch imagery for this tile
        rgb_nir = detector.fetch_sentinel2_cloudless_mosaic(tile_bbox)
        
        if rgb_nir is None:
            console.print(f"   ⚠️ Skipping tile {i} (no data/too cloudy)", style="yellow")
            tile_stats.append({
                'tile': i,
                'center': (tile_center_lat, tile_center_lon),
                'rooftops': 0,
                'status': 'no_data'
            })
            continue
        
        # Fetch DEM for this tile
        dem = detector.fetch_copernicus_dem(tile_bbox)
        
        # Detect rooftops in this tile
        features = detector.detect_rooftops_from_imagery(rgb_nir, tile_bbox, dem)
        all_features.extend(features)
        console.print(f"   ✅ Found {len(features)} rooftops in tile {i}\n", style="green")
        
        tile_stats.append({
            'tile': i,
            'center': (tile_center_lat, tile_center_lon),
            'rooftops': len(features),
            'status': 'success'
        })
    
    # Print tile summary
    console.print("\n" + "="*60, style="cyan")
    console.print("📊 TILE PROCESSING SUMMARY", style="bold cyan")
    console.print("="*60, style="cyan")
    for stat in tile_stats:
        status_icon = "✅" if stat['status'] == 'success' else "❌"
        console.print(f"{status_icon} Tile {stat['tile']}: Lat {stat['center'][0]:.3f}, "
                     f"Lon {stat['center'][1]:.3f} → {stat['rooftops']} rooftops", 
                     style="dim")
    console.print("="*60 + "\n", style="cyan")
    
    return all_features


def main():
    parser = argparse.ArgumentParser(description="Detect rooftops for soccer fields")
    parser.add_argument("--city", 
                       choices=['berlin', 'berlin_center', 'dusseldorf'],
                       default='berlin_center', 
                       help="City to analyze")
    parser.add_argument("--tile-size", 
                       type=float, 
                       default=0.05,
                       help="Tile size in degrees (default: 0.05 = ~5km)")
    args = parser.parse_args()
    
    bbox = CITY_BBOX[args.city]
    
    console.print(f"\n🏙️ Starting rooftop detection for {args.city.title()}", 
                 style="bold blue")
    console.print(f"📍 Bounding box: {bbox}\n")
    
    # Initialize detector
    detector = RooftopDetector()
    
    # Authenticate
    if not detector.authenticate():
        console.print("❌ Authentication failed. Exiting.", style="red")
        return
    
    # Process based on city size
    if args.city == 'berlin':
        # Use tiling for Berlin to maintain resolution (~10 tiles)
        features = process_city_tiled(args.city, detector, tile_size_deg=0.2)
    else:
        # Single request for small areas
        rgb_nir = detector.fetch_sentinel2_cloudless_mosaic(bbox)
        
        if rgb_nir is None:
            console.print("❌ Failed to fetch imagery. Exiting.", style="red")
            return
        
        # Fetch DEM
        dem = detector.fetch_copernicus_dem(bbox)
        
        features = detector.detect_rooftops_from_imagery(rgb_nir, bbox, dem)
    
    # Save results (fixed filenames - will replace existing)
    geojson_path = RESULTS_DIR / f"{args.city}_rooftops.geojson"
    
    feature_collection = {"type": "FeatureCollection", "features": features}
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(feature_collection, f, ensure_ascii=False, indent=2)
    
    console.print(f"💾 GeoJSON saved to {geojson_path}", style="green")
    
    # Create visualization
    map_path = RESULTS_DIR / f"{args.city}_rooftops_map.html"
    create_visualization_map(features, bbox, map_path)
    
    console.print(f"\n✅ Detection complete! Found {len(features)} rooftops", 
                 style="bold green")
    console.print(f"📄 Data: {geojson_path}")
    console.print(f"🗺️ Map: {map_path}\n")


if __name__ == "__main__":
    main()
