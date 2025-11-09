"""
Calisthenics Park Detection in Düsseldorf
========================================

Focused implementation for CASSINI Hackathon Challenge #2
Target: Detect calisthenics parks using Sentinel-2 satellite data in Düsseldorf area

Author: Christopher George
Date: November 2025
"""

import numpy as np
import requests
import json
from datetime import datetime, timedelta
import folium
import geopandas as gpd
from shapely.geometry import Point, Polygon, box
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_bounds, reproject
import cv2
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class CalisthenicsDetectorDusseldorf:
    """
    Specialized detector for calisthenics parks in Düsseldorf using Sentinel-2 data.
    """
    
    def __init__(self):
        # Düsseldorf bounding box
        self.study_area = {
            'min_lon': 6.69,
            'min_lat': 51.16, 
            'max_lon': 6.95,
            'max_lat': 51.30
        }
        
        # Known calisthenics parks for validation (corrected locations)
        self.known_parks = [
            {'name': 'Volksgarten Calisthenics Park', 'lat': 51.2186, 'lon': 6.7711, 'verified': True, 'description': 'Established calisthenics area in Volksgarten'},
            {'name': 'Florapark Calisthenics Area', 'lat': 51.2547, 'lon': 6.7858, 'verified': True, 'description': 'Outdoor fitness equipment in Florapark'}, 
            {'name': 'Düsseldorf Hauptbahnhof Area', 'lat': 51.2203, 'lon': 6.7947, 'verified': True, 'description': 'Calisthenics park near main train station'},
        ]
        
        # Calisthenics park detection parameters (updated with realistic sizes)
        self.detection_params = {
            'min_area_pixels': 0.5,      # ~50m² at 10m resolution (0.5 pixels)
            'max_area_pixels': 4.0,      # ~400m² at 10m resolution (4 pixels)
            'min_area_m2': 50,           # Minimum 50 square meters
            'max_area_m2': 400,          # Maximum 400 square meters
            'ndvi_threshold_low': 0.0,   # Equipment areas (metal/rubber)
            'ndvi_threshold_high': 0.3,  # Mixed equipment + some vegetation
            'aspect_ratio_min': 0.5,     # Not too elongated
            'aspect_ratio_max': 4.0,     # Allow rectangular layouts (updated for linear parks)
            'compactness_min': 0.2,      # Relaxed for smaller areas
        }
    
    def get_sentinel2_data_mock(self) -> Dict:
        """
        Mock function to simulate Sentinel-2 data retrieval for Düsseldorf.
        In real implementation, this would use Copernicus Data Space Ecosystem APIs.
        """
        print("📡 Simulating Sentinel-2 data retrieval for Düsseldorf...")
        
        # Simulate image dimensions for Düsseldorf area
        height, width = 1400, 2600  # Approx dimensions for the bbox at 10m resolution
        
        # Create mock data that simulates real patterns
        mock_data = {
            'red': np.random.randint(1500, 3500, (height, width)),
            'green': np.random.randint(1800, 4000, (height, width)),
            'blue': np.random.randint(1200, 3000, (height, width)),
            'nir': np.random.randint(2000, 6000, (height, width)),
            'scl': np.random.randint(2, 8, (height, width)),  # Scene classification
            'bbox': self.study_area,
            'pixel_size': 10,  # 10m resolution
        }
        
        # Add some synthetic calisthenics park signatures
        self._add_synthetic_parks(mock_data)
        
        print(f"✅ Retrieved mock data: {height}x{width} pixels, 4 bands")
        return mock_data
    
    def _add_synthetic_parks(self, data: Dict):
        """Add synthetic calisthenics park signatures to mock data."""
        height, width = data['red'].shape
        
        # Add 5-10 synthetic parks with characteristic signatures
        num_parks = np.random.randint(5, 10)
        
        for _ in range(num_parks):
            # Random location within image
            center_y = np.random.randint(50, height - 50)
            center_x = np.random.randint(50, width - 50)
            
            # Park size (2-6 pixels = 20-60m at 10m resolution)
            park_size = np.random.randint(2, 6)
            
            # Create rectangular park area
            y1, y2 = center_y - park_size, center_y + park_size
            x1, x2 = center_x - park_size, center_x + park_size
            
            # Calisthenics signature: low reflectance (metal equipment, rubber surfaces)
            data['red'][y1:y2, x1:x2] = np.random.randint(800, 1500)    # Low red
            data['green'][y1:y2, x1:x2] = np.random.randint(900, 1600)  # Low green  
            data['blue'][y1:y2, x1:x2] = np.random.randint(700, 1400)   # Low blue
            data['nir'][y1:y2, x1:x2] = np.random.randint(1000, 2000)   # Low NIR (no vegetation)
    
    def calculate_indices(self, data: Dict) -> Dict:
        """Calculate vegetation indices and other metrics for analysis."""
        print("🔄 Calculating vegetation indices...")
        
        red = data['red'].astype(np.float32)
        green = data['green'].astype(np.float32)
        blue = data['blue'].astype(np.float32)
        nir = data['nir'].astype(np.float32)
        
        # NDVI - key for detecting non-vegetated areas
        ndvi = (nir - red) / (nir + red + 1e-8)
        
        # Enhanced Vegetation Index
        evi = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)
        
        # Normalized Difference Built-up Index (for urban areas)
        ndbi = (data['nir'] - nir) / (data['nir'] + nir + 1e-8)  # Simplified
        
        # Brightness (total reflectance)
        brightness = (red + green + blue + nir) / 4
        
        return {
            'ndvi': ndvi,
            'evi': evi, 
            'ndbi': ndbi,
            'brightness': brightness,
            'red': red,
            'green': green,
            'blue': blue,
            'nir': nir
        }
    
    def detect_calisthenics_candidates(self, indices: Dict) -> List[Dict]:
        """
        Detect potential calisthenics park locations based on spectral and spatial characteristics.
        """
        print("🎯 Detecting calisthenics park candidates...")
        
        ndvi = indices['ndvi']
        brightness = indices['brightness']
        
        # Create candidate mask: low NDVI (non-vegetated) but not too dark
        candidate_mask = (
            (ndvi >= self.detection_params['ndvi_threshold_low']) &
            (ndvi <= self.detection_params['ndvi_threshold_high']) &
            (brightness > 1500) &  # Not too dark (avoid shadows)
            (brightness < 4000)    # Not too bright (avoid buildings)
        )
        
        # Convert to uint8 for OpenCV
        mask_uint8 = (candidate_mask * 255).astype(np.uint8)
        
        # Find contours
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        
        for contour in contours:
            # Calculate properties
            area = cv2.contourArea(contour)
            
            # Convert area to square meters for realistic filtering
            area_m2 = area * 100  # Each pixel = 100 m² at 10m resolution
            
            if (self.detection_params['min_area_m2'] <= area_m2 <= 
                self.detection_params['max_area_m2']):
                
                # Get bounding rectangle
                rect = cv2.minAreaRect(contour)
                (center_x, center_y), (width, height), angle = rect
                
                # Calculate metrics
                aspect_ratio = max(width, height) / max(min(width, height), 1)
                perimeter = cv2.arcLength(contour, True)
                compactness = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                
                # Get average NDVI within contour
                mask = np.zeros(ndvi.shape, dtype=np.uint8)
                cv2.fillPoly(mask, [contour], 255)
                avg_ndvi = np.mean(ndvi[mask > 0])
                avg_brightness = np.mean(brightness[mask > 0])
                
                # Apply filters
                if (self.detection_params['aspect_ratio_min'] <= aspect_ratio <= 
                    self.detection_params['aspect_ratio_max'] and
                    compactness >= self.detection_params['compactness_min']):
                    
                    # Convert pixel coordinates to lat/lon (approximate)
                    lat, lon = self._pixel_to_latlon(center_y, center_x)
                    
                    candidate = {
                        'center_pixel': (center_x, center_y),
                        'center_latlon': (lat, lon),
                        'area_pixels': area,
                        'area_m2': area * 100,  # 10m x 10m pixels = 100 m² per pixel
                        'dimensions': (width * 10, height * 10),  # Convert to meters
                        'aspect_ratio': aspect_ratio,
                        'compactness': compactness,
                        'avg_ndvi': avg_ndvi,
                        'avg_brightness': avg_brightness,
                        'confidence': self._calculate_confidence(area, avg_ndvi, compactness),
                        'contour': contour
                    }
                    
                    candidates.append(candidate)
        
        print(f"✅ Found {len(candidates)} calisthenics park candidates")
        return candidates
    
    def _pixel_to_latlon(self, pixel_y: float, pixel_x: float) -> Tuple[float, float]:
        """Convert pixel coordinates to lat/lon (simplified transformation)."""
        # Simple linear transformation for Düsseldorf bbox
        lat_range = self.study_area['max_lat'] - self.study_area['min_lat']
        lon_range = self.study_area['max_lon'] - self.study_area['min_lon']
        
        # Assume image dimensions based on bbox (this would be precise in real implementation)
        height, width = 1400, 2600
        
        lat = self.study_area['max_lat'] - (pixel_y / height) * lat_range
        lon = self.study_area['min_lon'] + (pixel_x / width) * lon_range
        
        return lat, lon
    
    def _calculate_confidence(self, area: float, avg_ndvi: float, compactness: float) -> float:
        """Calculate confidence score for calisthenics park detection."""
        confidence = 0.0
        
        # Size score (ideal size around 100-200 m² for typical calisthenics parks)
        area_m2 = area * 100  # Convert pixels to m²
        ideal_area_m2 = 150   # Ideal size 150 m²
        size_score = 1.0 - abs(area_m2 - ideal_area_m2) / ideal_area_m2
        size_score = max(0, min(1, size_score))
        
        # NDVI score (lower is better for calisthenics parks)
        ndvi_score = 1.0 - max(0, avg_ndvi - 0.1) / 0.3  # Best if NDVI < 0.1
        ndvi_score = max(0, min(1, ndvi_score))
        
        # Shape score (compactness)
        shape_score = compactness
        
        # Weighted combination
        confidence = (0.4 * size_score + 0.4 * ndvi_score + 0.2 * shape_score)
        
        return confidence
    
    def validate_against_known_parks(self, candidates: List[Dict]) -> Dict:
        """Validate detections against known calisthenics park locations."""
        print("✅ Validating against known park locations...")
        
        validation_results = {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'matches': []
        }
        
        # Check each known park
        for known_park in self.known_parks:
            closest_candidate = None
            min_distance = float('inf')
            
            # Find closest detection to known park
            for candidate in candidates:
                lat_diff = candidate['center_latlon'][0] - known_park['lat']
                lon_diff = candidate['center_latlon'][1] - known_park['lon']
                distance = np.sqrt(lat_diff**2 + lon_diff**2) * 111000  # Rough conversion to meters
                
                if distance < min_distance:
                    min_distance = distance
                    closest_candidate = candidate
            
            # Consider it a match if within 500m
            if min_distance < 500:
                validation_results['true_positives'] += 1
                validation_results['matches'].append({
                    'known_park': known_park['name'],
                    'detected_location': closest_candidate['center_latlon'],
                    'distance_m': min_distance,
                    'confidence': closest_candidate['confidence']
                })
            else:
                validation_results['false_negatives'] += 1
        
        # False positives are candidates not matched to known parks
        validation_results['false_positives'] = len(candidates) - validation_results['true_positives']
        
        return validation_results
    
    def create_results_map(self, candidates: List[Dict], validation: Dict) -> folium.Map:
        """Create interactive map showing detected calisthenics parks."""
        print("🗺️ Creating results map...")
        
        # Center map on Düsseldorf
        center_lat = (self.study_area['min_lat'] + self.study_area['max_lat']) / 2
        center_lon = (self.study_area['min_lon'] + self.study_area['max_lon']) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=11)
        
        # Add known parks (ground truth)
        for park in self.known_parks:
            folium.Marker(
                location=[park['lat'], park['lon']],
                popup=f"""
                <b>{park['name']}</b><br>
                Status: {"Verified" if park['verified'] else "To be verified"}<br>
                Description: {park.get('description', 'Known calisthenics park')}<br>
                Type: Ground truth location
                """,
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)
        
        # Add detected candidates
        for i, candidate in enumerate(candidates):
            # Color based on confidence
            if candidate['confidence'] > 0.7:
                color = 'green'
                status = 'High confidence'
            elif candidate['confidence'] > 0.5:
                color = 'orange' 
                status = 'Medium confidence'
            else:
                color = 'red'
                status = 'Low confidence'
            
            folium.CircleMarker(
                location=candidate['center_latlon'],
                radius=8,
                popup=f"""
                <b>Detected Calisthenics Park #{i+1}</b><br>
                Confidence: {candidate['confidence']:.2f}<br>
                Status: {status}<br>
                Area: {candidate['area_m2']:.0f} m²<br>
                Dimensions: {candidate['dimensions'][0]:.0f}m x {candidate['dimensions'][1]:.0f}m<br>
                NDVI: {candidate['avg_ndvi']:.2f}<br>
                Compactness: {candidate['compactness']:.2f}
                """,
                color=color,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)
        
        # Add study area boundary
        boundary = [
            [self.study_area['min_lat'], self.study_area['min_lon']],
            [self.study_area['max_lat'], self.study_area['min_lon']], 
            [self.study_area['max_lat'], self.study_area['max_lon']],
            [self.study_area['min_lat'], self.study_area['max_lon']],
        ]
        
        folium.Polygon(
            locations=boundary,
            popup="Düsseldorf Study Area",
            color='black',
            weight=2,
            fillOpacity=0.1
        ).add_to(m)
        
        return m
    
    def export_results(self, candidates: List[Dict], validation: Dict, output_path: str):
        """Export results to GeoJSON and CSV formats."""
        print(f"💾 Exporting results to {output_path}...")
        
        # Create GeoDataFrame for spatial data
        geometries = []
        properties = []
        
        for i, candidate in enumerate(candidates):
            # Create point geometry
            point = Point(candidate['center_latlon'][1], candidate['center_latlon'][0])
            geometries.append(point)
            
            # Properties
            properties.append({
                'id': i + 1,
                'confidence': candidate['confidence'],
                'area_m2': candidate['area_m2'],
                'dimensions_m': f"{candidate['dimensions'][0]:.0f}x{candidate['dimensions'][1]:.0f}",
                'avg_ndvi': candidate['avg_ndvi'],
                'compactness': candidate['compactness'],
                'detection_method': 'sentinel2_ndvi_analysis'
            })
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(properties, geometry=geometries, crs='EPSG:4326')
        
        # Export to GeoJSON
        gdf.to_file(f"{output_path}_calisthenics_parks.geojson", driver='GeoJSON')
        
        # Export to CSV
        df = pd.DataFrame(properties)
        df['latitude'] = [g.y for g in geometries]
        df['longitude'] = [g.x for g in geometries]
        df.to_csv(f"{output_path}_calisthenics_parks.csv", index=False)
        
        # Export validation report
        with open(f"{output_path}_validation_report.json", 'w') as f:
            json.dump(validation, f, indent=2)
        
        print(f"✅ Exported {len(candidates)} detections and validation report")
    
    def run_full_analysis(self) -> Dict:
        """Run complete calisthenics park detection analysis for Düsseldorf."""
        print("🚀 Starting Düsseldorf Calisthenics Park Detection Analysis")
        print("=" * 60)
        
        # Step 1: Get satellite data
        data = self.get_sentinel2_data_mock()
        
        # Step 2: Calculate indices
        indices = self.calculate_indices(data)
        
        # Step 3: Detect candidates
        candidates = self.detect_calisthenics_candidates(indices)
        
        # Step 4: Validation
        validation = self.validate_against_known_parks(candidates)
        
        # Step 5: Create map
        results_map = self.create_results_map(candidates, validation)
        
        # Step 6: Export results
        self.export_results(candidates, validation, "dusseldorf_calisthenics")
        
        # Step 7: Save map
        results_map.save("dusseldorf_calisthenics_detection_results.html")
        
        # Summary report
        results = {
            'total_candidates': len(candidates),
            'high_confidence': len([c for c in candidates if c['confidence'] > 0.7]),
            'medium_confidence': len([c for c in candidates if 0.5 < c['confidence'] <= 0.7]),
            'low_confidence': len([c for c in candidates if c['confidence'] <= 0.5]),
            'validation': validation,
            'candidates': candidates
        }
        
        print("\n📊 ANALYSIS RESULTS")
        print("=" * 40)
        print(f"Total candidates detected: {results['total_candidates']}")
        print(f"High confidence (>0.7): {results['high_confidence']}")
        print(f"Medium confidence (0.5-0.7): {results['medium_confidence']}")
        print(f"Low confidence (<0.5): {results['low_confidence']}")
        print(f"\nValidation against known parks:")
        print(f"  True positives: {validation['true_positives']}")
        print(f"  False negatives: {validation['false_negatives']}")
        print(f"  False positives: {validation['false_positives']}")
        
        if validation['matches']:
            print(f"\nMatched known parks:")
            for match in validation['matches']:
                print(f"  - {match['known_park']}: {match['distance_m']:.0f}m away, confidence {match['confidence']:.2f}")
        
        print(f"\n💾 Results saved:")
        print(f"  - dusseldorf_calisthenics_detection_results.html")
        print(f"  - dusseldorf_calisthenics_calisthenics_parks.geojson")
        print(f"  - dusseldorf_calisthenics_calisthenics_parks.csv")
        print(f"  - dusseldorf_calisthenics_validation_report.json")
        
        return results


def main():
    """Main function to run calisthenics park detection."""
    print("🏋️ DÜSSELDORF CALISTHENICS PARK DETECTION")
    print("🛰️ Using Sentinel-2 Satellite Data Analysis")
    print("🎯 CASSINI Hackathon Challenge #2 Implementation")
    print()
    
    # Initialize detector
    detector = CalisthenicsDetectorDusseldorf()
    
    # Run analysis
    results = detector.run_full_analysis()
    
    print("\n🎉 Analysis complete!")
    print("📂 Check the generated files for detailed results.")
    print("🗺️ Open 'dusseldorf_calisthenics_detection_results.html' to see the interactive map!")
    
    return results


if __name__ == "__main__":
    results = main()