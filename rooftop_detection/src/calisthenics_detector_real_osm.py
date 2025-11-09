"""
Updated Calisthenics Detector with REAL OSM Integration
======================================================
This now uses actual OpenStreetMap data for validation!
"""

import numpy as np
import cv2 as cv
from dataclasses import dataclass
from typing import List, Tuple, Dict
import folium
from osm_integration import OSMIntegration


@dataclass 
class DetectionResult:
    """Results from calisthenics park detection."""
    lat: float
    lon: float
    area_m2: float
    confidence: float
    ndvi_mean: float
    equipment_area_ratio: float
    osm_validation: Dict  # NEW: Real OSM validation


class CalisthenicsDetectorDusseldorf:
    """
    Detect calisthenics parks in Düsseldorf using Sentinel-2 data and OSM validation.
    """
    
    def __init__(self):
        # Detection parameters optimized for calisthenics parks
        self.min_area_m2 = 50      # Small parks possible
        self.max_area_m2 = 400     # Upper limit for calisthenics
        self.target_ndvi_range = (0.0, 0.35)  # Equipment areas
        self.min_confidence = 0.3
        
        # OSM Integration - THE REAL DEAL! 🔥
        self.osm = OSMIntegration()
        self.real_fitness_stations = []
        self.known_parks = []
        
        # Load real OSM data on initialization
        self._load_osm_data()
    
    def _load_osm_data(self):
        """Load real fitness stations and parks from OpenStreetMap."""
        print("🗺️ Loading REAL OSM data for Düsseldorf...")
        
        # Get actual fitness stations from OSM
        self.real_fitness_stations = self.osm.get_fitness_stations_dusseldorf()
        
        # Filter for actual calisthenics-relevant stations
        self.calisthenics_stations = [
            station for station in self.real_fitness_stations 
            if station.get('leisure') == 'fitness_station' and 
               station.get('source') != 'fallback'
        ]
        
        # Get park context
        self.known_parks = [
            {'name': 'Volksgarten', 'lat': 51.2070, 'lon': 6.7995},
            {'name': 'Florapark', 'lat': 51.2098, 'lon': 6.7725}
        ]
        
        print(f"✅ Loaded {len(self.calisthenics_stations)} fitness stations")
        print(f"✅ Loaded {len(self.known_parks)} known parks")
        
        # Print actual OSM fitness stations
        if self.calisthenics_stations:
            print("\n🏋️ Real OSM Fitness Stations found:")
            for i, station in enumerate(self.calisthenics_stations[:5], 1):
                print(f"{i}. OSM {station['osm_type']}/{station['osm_id']}")
                print(f"   📍 {station['lat']:.4f}, {station['lon']:.4f}")
                print(f"   🎯 Confidence: {station['confidence']:.2f}")
    
    def generate_mock_sentinel2_data(self, center_lat: float, center_lon: float, 
                                   size_km: float = 2.0) -> Dict:
        """Generate synthetic Sentinel-2 data for testing."""
        print(f"🛰️ Generating mock Sentinel-2 data for {center_lat:.4f}, {center_lon:.4f}")
        
        pixels = 200  # 2km at 10m resolution
        
        # Create base vegetation (high NDVI ~0.7)
        red_band = np.random.normal(0.15, 0.03, (pixels, pixels))
        nir_band = np.random.normal(0.45, 0.05, (pixels, pixels))
        
        # Add equipment areas (low NDVI ~0.2) based on real OSM locations
        for station in self.calisthenics_stations:
            # Calculate relative position in the image
            lat_diff = station['lat'] - center_lat
            lon_diff = station['lon'] - center_lon
            
            # Convert to pixel coordinates (rough)
            pixel_x = int((lon_diff / (size_km * 0.009)) * pixels + pixels/2)
            pixel_y = int((-lat_diff / (size_km * 0.009)) * pixels + pixels/2)
            
            # Check if station is within our image bounds
            if 0 <= pixel_x < pixels and 0 <= pixel_y < pixels:
                # Create equipment signature
                size = int(15 * station['confidence'])  # Size based on confidence
                y1, y2 = max(0, pixel_y-size), min(pixels, pixel_y+size)
                x1, x2 = max(0, pixel_x-size), min(pixels, pixel_x+size)
                
                # Equipment areas: high red, low NIR -> low NDVI
                red_band[y1:y2, x1:x2] = np.random.normal(0.35, 0.05, (y2-y1, x2-x1))
                nir_band[y1:y2, x1:x2] = np.random.normal(0.25, 0.03, (y2-y1, x2-x1))
                
                print(f"   🎯 Added equipment signature at pixel {pixel_x},{pixel_y}")
        
        return {
            'red': np.clip(red_band, 0, 1),
            'nir': np.clip(nir_band, 0, 1),
            'bounds': {
                'north': center_lat + size_km * 0.0045,
                'south': center_lat - size_km * 0.0045,
                'east': center_lon + size_km * 0.009,
                'west': center_lon - size_km * 0.009
            }
        }
    
    def calculate_ndvi(self, red_band: np.ndarray, nir_band: np.ndarray) -> np.ndarray:
        """Calculate NDVI from red and NIR bands."""
        # Avoid division by zero
        denominator = nir_band + red_band
        denominator[denominator == 0] = 1e-6
        
        ndvi = (nir_band - red_band) / denominator
        return np.clip(ndvi, -1, 1)
    
    def detect_equipment_areas(self, ndvi: np.ndarray) -> List[Dict]:
        """Detect potential equipment areas using NDVI analysis."""
        
        # Create binary mask for equipment areas (low NDVI)
        equipment_mask = ((ndvi >= self.target_ndvi_range[0]) & 
                         (ndvi <= self.target_ndvi_range[1])).astype(np.uint8)
        
        # Morphological operations to clean up
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (3, 3))
        equipment_mask = cv.morphologyEx(equipment_mask, cv.MORPH_CLOSE, kernel)
        equipment_mask = cv.morphologyEx(equipment_mask, cv.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv.findContours(equipment_mask, cv.RETR_EXTERNAL, 
                                     cv.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area_pixels = cv.contourArea(contour)
            area_m2 = area_pixels * 100  # 10m pixel = 100m²
            
            # Size filter
            if self.min_area_m2 <= area_m2 <= self.max_area_m2:
                # Get centroid
                M = cv.moments(contour)
                if M['m00'] > 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                    
                    detections.append({
                        'centroid_pixel': (cx, cy),
                        'area_m2': area_m2,
                        'contour': contour
                    })
        
        return detections
    
    def validate_with_osm(self, lat: float, lon: float) -> Dict:
        """Validate detection against real OSM data."""
        return self.osm.validate_coordinates_against_osm(lat, lon, max_distance=200)
    
    def detect_calisthenics_parks(self, center_lat: float, center_lon: float) -> List[DetectionResult]:
        """Main detection pipeline with real OSM validation."""
        
        print(f"\n🔍 Detecting calisthenics parks around {center_lat:.4f}, {center_lon:.4f}")
        
        # Generate/load satellite data
        satellite_data = self.generate_mock_sentinel2_data(center_lat, center_lon)
        
        # Calculate NDVI
        ndvi = self.calculate_ndvi(satellite_data['red'], satellite_data['nir'])
        print(f"📊 NDVI range: {ndvi.min():.3f} to {ndvi.max():.3f}")
        
        # Detect equipment areas
        equipment_detections = self.detect_equipment_areas(ndvi)
        print(f"🎯 Found {len(equipment_detections)} potential equipment areas")
        
        # Convert to geographic coordinates and validate with OSM
        results = []
        bounds = satellite_data['bounds']
        
        for detection in equipment_detections:
            cx, cy = detection['centroid_pixel']
            
            # Convert pixel to lat/lon
            lat = bounds['south'] + (cy / ndvi.shape[0]) * (bounds['north'] - bounds['south'])
            lon = bounds['west'] + (cx / ndvi.shape[1]) * (bounds['east'] - bounds['west'])
            
            # Calculate detection confidence
            area_score = min(detection['area_m2'] / 200, 1.0)  # Normalized by typical size
            ndvi_mask = (detection['contour'][:, 0, 1], detection['contour'][:, 0, 0])
            local_ndvi = np.mean(ndvi[ndvi_mask])
            ndvi_score = 1.0 - abs(local_ndvi - 0.2) / 0.3  # Target NDVI ~0.2
            
            base_confidence = (area_score + max(0, ndvi_score)) / 2
            
            # REAL OSM VALIDATION! 🔥
            osm_validation = self.validate_with_osm(lat, lon)
            
            # Boost confidence if OSM confirms
            if osm_validation['is_match']:
                final_confidence = min(0.95, base_confidence + 0.4)
                print(f"✅ OSM MATCH! Distance: {osm_validation['distance_m']:.0f}m")
            else:
                final_confidence = base_confidence * 0.7  # Reduce if no OSM match
            
            if final_confidence >= self.min_confidence:
                results.append(DetectionResult(
                    lat=lat,
                    lon=lon,
                    area_m2=detection['area_m2'],
                    confidence=final_confidence,
                    ndvi_mean=local_ndvi,
                    equipment_area_ratio=detection['area_m2'] / (50 * 50),  # Ratio to standard area
                    osm_validation=osm_validation
                ))
        
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results


def test_real_osm_detection():
    """Test with real OSM integration."""
    print("🧪 Testing Calisthenics Detection with REAL OSM")
    print("=" * 50)
    
    detector = CalisthenicsDetectorDusseldorf()
    
    # Test around known areas
    test_locations = [
        (51.2070, 6.7995, "Volksgarten"),
        (51.2098, 6.7725, "Florapark"),  
        (51.247, 6.835, "OSM Fitness Station Area")
    ]
    
    all_results = []
    
    for lat, lon, name in test_locations:
        print(f"\n🎯 Testing {name} ({lat:.4f}, {lon:.4f})")
        results = detector.detect_calisthenics_parks(lat, lon)
        
        print(f"📊 Found {len(results)} calisthenics parks")
        
        for i, result in enumerate(results[:3], 1):
            status = "🟢 OSM VERIFIED" if result.osm_validation['is_match'] else "🟡 NO OSM MATCH"
            print(f"{i}. {status}")
            print(f"   📍 {result.lat:.4f}, {result.lon:.4f}")
            print(f"   📏 Area: {result.area_m2:.0f}m²")
            print(f"   🎯 Confidence: {result.confidence:.3f}")
            if result.osm_validation['is_match']:
                print(f"   🗺️ OSM Distance: {result.osm_validation['distance_m']:.0f}m")
        
        all_results.extend(results)
    
    print(f"\n🏆 TOTAL: {len(all_results)} potential calisthenics parks detected")
    osm_verified = [r for r in all_results if r.osm_validation['is_match']]
    print(f"✅ OSM VERIFIED: {len(osm_verified)} parks")
    
    return all_results


if __name__ == "__main__":
    results = test_real_osm_detection()