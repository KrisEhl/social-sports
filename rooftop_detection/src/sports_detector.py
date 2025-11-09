"""
Sports Field Detection using Sentinel-2 Data
============================================

This module demonstrates how to detect sports fields from Copernicus Sentinel-2 satellite imagery.
Designed for the CASSINI Hackathon Challenge #2: Mapping the Future of Sports in Public Spaces.

Requirements:
- Copernicus Data Space Ecosystem account
- Python 3.9+ with geospatial libraries
- Internet connection for API access
"""

import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import box, Polygon
import requests
from datetime import datetime, timedelta
import json
from typing import List, Tuple, Dict, Optional
import cv2
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import folium

class SentinelSportsDetector:
    """
    Main class for detecting sports fields in Sentinel-2 satellite imagery.
    
    This class provides methods to:
    1. Access Copernicus Sentinel-2 data
    2. Preprocess imagery for sports field detection
    3. Apply detection algorithms
    4. Validate and filter results
    5. Export detected facilities
    """
    
    def __init__(self, copernicus_token: str):
        """
        Initialize the sports field detector.
        
        Args:
            copernicus_token: Authentication token for Copernicus Data Space Ecosystem
        """
        self.token = copernicus_token
        self.base_url = "https://sh.dataspace.copernicus.eu"
        self.session = self._setup_session()
        
        # Sports field characteristics for detection
        self.field_specs = {
            'football_field': {
                'min_area': 4000,  # ~90x45m = 4050 m²
                'max_area': 12000,  # ~120x80m = 9600 m²
                'aspect_ratio_range': (1.3, 2.0),
                'expected_ndvi': (0.6, 0.8)  # Grass fields
            },
            'tennis_court': {
                'min_area': 200,   # ~23x11m = 253 m²
                'max_area': 600,   # Including run-off areas
                'aspect_ratio_range': (2.0, 2.6),
                'expected_ndvi': (0.2, 0.6)  # Often artificial surface
            },
            'athletics_track': {
                'min_area': 8000,  # ~120x80m inner area
                'max_area': 20000, # Including outer areas
                'aspect_ratio_range': (1.2, 1.8),
                'expected_ndvi': (0.5, 0.8)  # Inner grass field
            }
        }
    
    def _setup_session(self) -> requests.Session:
        """Setup authenticated session for Copernicus API."""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        })
        return session
    
    def get_sentinel2_data(self, 
                          bbox: Tuple[float, float, float, float],
                          start_date: str,
                          end_date: str,
                          max_cloud_coverage: int = 20) -> Dict:
        """
        Retrieve Sentinel-2 data for specified area and time range.
        
        Args:
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            max_cloud_coverage: Maximum acceptable cloud coverage percentage
            
        Returns:
            Dictionary containing image data and metadata
        """
        # This is a simplified example - actual implementation would use
        # Sentinel Hub API or Copernicus Data Space Ecosystem APIs
        
        evalscript = """
        //VERSION=3
        function setup() {
            return {
                input: ["B02", "B03", "B04", "B08", "SCL"],
                output: { 
                    bands: 5,
                    sampleType: "UINT16"
                }
            };
        }
        
        function evaluatePixel(sample) {
            // Return Blue, Green, Red, NIR, Scene Classification
            return [
                sample.B02 * 10000,
                sample.B03 * 10000, 
                sample.B04 * 10000,
                sample.B08 * 10000,
                sample.SCL
            ];
        }
        """
        
        request_payload = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{start_date}T00:00:00Z",
                            "to": f"{end_date}T23:59:59Z"
                        },
                        "maxCloudCoverage": max_cloud_coverage
                    }
                }]
            },
            "output": {
                "width": 512,
                "height": 512,
                "responses": [{
                    "identifier": "default",
                    "format": {"type": "image/tiff"}
                }]
            },
            "evalscript": evalscript
        }
        
        # Note: This is a template - you'll need to implement actual API call
        return self._make_api_request(request_payload)
    
    def preprocess_image(self, image_data: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Preprocess Sentinel-2 image for sports field detection.
        
        Args:
            image_data: Raw Sentinel-2 image data (bands: B, G, R, NIR, SCL)
            
        Returns:
            Dictionary containing processed bands and indices
        """
        blue, green, red, nir, scl = image_data[..., 0], image_data[..., 1], \
                                     image_data[..., 2], image_data[..., 3], image_data[..., 4]
        
        # Convert to reflectance values (0-1)
        blue = blue / 10000.0
        green = green / 10000.0
        red = red / 10000.0
        nir = nir / 10000.0
        
        # Calculate vegetation indices
        ndvi = np.divide(nir - red, nir + red, 
                        out=np.zeros_like(nir), where=(nir + red) != 0)
        
        # Enhanced Vegetation Index
        evi = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)
        
        # Create cloud mask (SCL values: 8,9,10 = clouds, 11 = snow)
        cloud_mask = np.isin(scl, [8, 9, 10, 11])
        
        # True color composite for visualization
        rgb = np.stack([red, green, blue], axis=2)
        rgb = np.clip(rgb * 2.5, 0, 1)  # Enhance brightness
        
        return {
            'rgb': rgb,
            'ndvi': ndvi,
            'evi': evi,
            'cloud_mask': cloud_mask,
            'red': red,
            'green': green,
            'blue': blue,
            'nir': nir
        }
    
    def detect_rectangular_objects(self, 
                                 ndvi: np.ndarray,
                                 min_area: int = 1000,
                                 max_area: int = 50000) -> List[Dict]:
        """
        Detect rectangular objects that could be sports fields.
        
        Args:
            ndvi: NDVI image array
            min_area: Minimum area in pixels
            max_area: Maximum area in pixels
            
        Returns:
            List of detected rectangular objects with properties
        """
        # Threshold NDVI to identify vegetation
        vegetation_mask = (ndvi > 0.3) & (ndvi < 0.9)
        
        # Convert to uint8 for OpenCV
        mask_uint8 = (vegetation_mask * 255).astype(np.uint8)
        
        # Find contours
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_objects = []
        
        for contour in contours:
            # Calculate area
            area = cv2.contourArea(contour)
            
            if min_area <= area <= max_area:
                # Approximate contour to polygon
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Check if roughly rectangular (4-6 vertices after approximation)
                if 4 <= len(approx) <= 6:
                    # Get bounding rectangle
                    rect = cv2.minAreaRect(contour)
                    (center_x, center_y), (width, height), angle = rect
                    
                    # Calculate aspect ratio
                    aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 0
                    
                    # Get average NDVI within the contour
                    mask = np.zeros(ndvi.shape, dtype=np.uint8)
                    cv2.fillPoly(mask, [contour], 255)
                    avg_ndvi = np.mean(ndvi[mask > 0])
                    
                    detected_objects.append({
                        'contour': contour,
                        'center': (center_x, center_y),
                        'dimensions': (width, height),
                        'angle': angle,
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'avg_ndvi': avg_ndvi,
                        'confidence': self._calculate_confidence(area, aspect_ratio, avg_ndvi)
                    })
        
        return detected_objects
    
    def _calculate_confidence(self, area: float, aspect_ratio: float, avg_ndvi: float) -> float:
        """Calculate confidence score for detected object being a sports field."""
        confidence = 0.0
        
        # Check against known sports field specifications
        for field_type, specs in self.field_specs.items():
            if (specs['min_area'] <= area <= specs['max_area'] and
                specs['aspect_ratio_range'][0] <= aspect_ratio <= specs['aspect_ratio_range'][1] and
                specs['expected_ndvi'][0] <= avg_ndvi <= specs['expected_ndvi'][1]):
                confidence = max(confidence, 0.8)
                break
        
        # Additional confidence factors
        if 0.5 <= avg_ndvi <= 0.8:  # Good vegetation health
            confidence += 0.1
            
        if 1.3 <= aspect_ratio <= 2.5:  # Typical sports field ratios
            confidence += 0.1
            
        return min(confidence, 1.0)
    
    def classify_sports_fields(self, detected_objects: List[Dict]) -> List[Dict]:
        """
        Classify detected objects into specific sports field types.
        
        Args:
            detected_objects: List of detected rectangular objects
            
        Returns:
            List of classified sports fields with type predictions
        """
        classified_fields = []
        
        for obj in detected_objects:
            if obj['confidence'] < 0.5:
                continue
                
            area = obj['area']
            aspect_ratio = obj['aspect_ratio']
            avg_ndvi = obj['avg_ndvi']
            
            # Classify based on specifications
            field_type = 'unknown'
            type_confidence = 0.0
            
            for ftype, specs in self.field_specs.items():
                if (specs['min_area'] <= area <= specs['max_area'] and
                    specs['aspect_ratio_range'][0] <= aspect_ratio <= specs['aspect_ratio_range'][1]):
                    
                    # Calculate type-specific confidence
                    ndvi_match = 1.0 - abs(avg_ndvi - np.mean(specs['expected_ndvi'])) / 0.3
                    area_match = 1.0 - abs(area - np.mean([specs['min_area'], specs['max_area']])) / specs['max_area']
                    
                    current_confidence = (ndvi_match + area_match) / 2
                    
                    if current_confidence > type_confidence:
                        field_type = ftype
                        type_confidence = current_confidence
            
            if type_confidence > 0.6:  # Only include confident classifications
                obj['field_type'] = field_type
                obj['type_confidence'] = type_confidence
                classified_fields.append(obj)
        
        return classified_fields
    
    def create_detection_map(self, 
                           classified_fields: List[Dict],
                           center_lat: float,
                           center_lon: float,
                           zoom: int = 15) -> folium.Map:
        """
        Create an interactive map showing detected sports fields.
        
        Args:
            classified_fields: List of classified sports fields
            center_lat: Center latitude for map
            center_lon: Center longitude for map
            zoom: Initial zoom level
            
        Returns:
            Folium map object with sports field markers
        """
        # Create base map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
        
        # Color mapping for different field types
        colors = {
            'football_field': 'green',
            'tennis_court': 'blue',
            'athletics_track': 'red',
            'unknown': 'gray'
        }
        
        for field in classified_fields:
            # Convert pixel coordinates to lat/lon (this would need proper georeference)
            # For demo purposes, using approximate conversion
            lat = center_lat + (field['center'][1] - 256) * 0.0001
            lon = center_lon + (field['center'][0] - 256) * 0.0001
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                popup=f"""
                <b>{field['field_type'].replace('_', ' ').title()}</b><br>
                Area: {field['area']:.0f} pixels<br>
                Confidence: {field['confidence']:.2f}<br>
                NDVI: {field['avg_ndvi']:.2f}<br>
                Aspect Ratio: {field['aspect_ratio']:.1f}
                """,
                color=colors.get(field['field_type'], 'gray'),
                fillColor=colors.get(field['field_type'], 'gray'),
                fillOpacity=0.7
            ).add_to(m)
        
        return m
    
    def export_results(self, classified_fields: List[Dict], output_file: str):
        """
        Export detection results to GeoJSON format.
        
        Args:
            classified_fields: List of classified sports fields
            output_file: Path to output GeoJSON file
        """
        features = []
        
        for field in classified_fields:
            # Convert contour to polygon (simplified)
            # In practice, you'd need proper coordinate transformation
            coords = [(float(point[0][0]), float(point[0][1])) for point in field['contour']]
            if len(coords) >= 3:
                polygon = Polygon(coords)
                
                feature = {
                    "type": "Feature",
                    "geometry": polygon.__geo_interface__,
                    "properties": {
                        "field_type": field['field_type'],
                        "area": field['area'],
                        "confidence": field['confidence'],
                        "type_confidence": field['type_confidence'],
                        "avg_ndvi": field['avg_ndvi'],
                        "aspect_ratio": field['aspect_ratio']
                    }
                }
                features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_file, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"Exported {len(features)} sports fields to {output_file}")
    
    def _make_api_request(self, payload: Dict) -> Dict:
        """Make API request to Copernicus services (placeholder)."""
        # This is a placeholder for actual API implementation
        print("API request would be made here with payload:")
        print(json.dumps(payload, indent=2))
        return {"status": "placeholder"}


# Example usage and demo functions
def demo_sports_detection():
    """
    Demonstration of sports field detection workflow.
    This would be used in a Jupyter notebook or script during the hackathon.
    """
    
    # Initialize detector (you'll need a real Copernicus token)
    detector = SentinelSportsDetector("your_copernicus_token_here")
    
    # Define area of interest (example: Munich Olympic Park)
    munich_olympic_bbox = (11.5459, 48.1699, 11.5559, 48.1799)  # Rough coordinates
    
    print("🛰️  Fetching Sentinel-2 data...")
    # Get recent cloud-free imagery
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    image_data = detector.get_sentinel2_data(
        bbox=munich_olympic_bbox,
        start_date=start_date,
        end_date=end_date,
        max_cloud_coverage=20
    )
    
    print("🔄 Preprocessing imagery...")
    # Note: In real implementation, image_data would contain actual satellite imagery
    # For demo, we'll simulate some processing steps
    
    print("🎯 Detecting potential sports fields...")
    # Simulated detection results
    demo_detections = [
        {
            'center': (300, 200),
            'area': 5000,
            'aspect_ratio': 1.6,
            'avg_ndvi': 0.75,
            'confidence': 0.85,
            'field_type': 'football_field',
            'type_confidence': 0.90
        },
        {
            'center': (150, 350),
            'area': 400,
            'aspect_ratio': 2.3,
            'avg_ndvi': 0.45,
            'confidence': 0.78,
            'field_type': 'tennis_court',
            'type_confidence': 0.82
        }
    ]
    
    print(f"✅ Found {len(demo_detections)} potential sports fields!")
    
    # Create results map
    print("🗺️  Creating interactive map...")
    results_map = detector.create_detection_map(
        demo_detections,
        center_lat=48.1749,  # Munich Olympic Park
        center_lon=11.5509,
        zoom=16
    )
    
    # Save map
    results_map.save("sports_fields_detection_results.html")
    print("📁 Results saved to sports_fields_detection_results.html")
    
    # Export to GeoJSON
    print("💾 Exporting results...")
    detector.export_results(demo_detections, "detected_sports_fields.geojson")
    
    return demo_detections


if __name__ == "__main__":
    print("🏟️  Sports Field Detection Demo")
    print("=" * 50)
    
    # Run demonstration
    results = demo_sports_detection()
    
    print("\n📊 Detection Summary:")
    for i, field in enumerate(results, 1):
        print(f"{i}. {field['field_type'].replace('_', ' ').title()}")
        print(f"   Confidence: {field['confidence']:.2f}")
        print(f"   Area: {field['area']} pixels")
        print(f"   NDVI: {field['avg_ndvi']:.2f}")
        print()
    
    print("🚀 Ready for hackathon implementation!")
    print("Next steps:")
    print("1. Get Copernicus Data Space Ecosystem account")
    print("2. Implement actual API calls") 
    print("3. Test with real satellite imagery")
    print("4. Validate against ground truth data")