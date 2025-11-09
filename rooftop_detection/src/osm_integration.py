"""
Real OpenStreetMap Integration for Calisthenics Park Detection
============================================================

This module provides actual OSM data integration using Overpass API.
"""

import requests
from typing import List, Dict


class OSMIntegration:
    """Handle OpenStreetMap data retrieval and processing."""
    
    def __init__(self):
        self.overpass_url = "http://overpass-api.de/api/interpreter"
        
    def get_fitness_stations_dusseldorf(self) -> List[Dict]:
        """
        Get actual fitness stations from OpenStreetMap for Düsseldorf.
        
        Returns:
            List of fitness stations with coordinates and tags
        """
        print("🗺️ Querying OpenStreetMap for fitness stations in Düsseldorf...")
        
        # Overpass QL query for Düsseldorf fitness stations
        query = """
        [out:json][timeout:25];
        (
          area["name"="Düsseldorf"]["admin_level"="6"];
        )->.searchArea;
        (
          node["leisure"="fitness_station"](area.searchArea);
          node["amenity"="fitness_station"](area.searchArea);
          node["sport"="fitness"](area.searchArea);
          node["fitness"](area.searchArea);
          way["leisure"="fitness_station"](area.searchArea);
          way["sport"="fitness"](area.searchArea);
          relation["leisure"="fitness_station"](area.searchArea);
        );
        out center meta;
        """
        
        try:
            response = requests.post(
                self.overpass_url, 
                data=query, 
                timeout=30,
                headers={'User-Agent': 'CalisthenicsDetector/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                fitness_stations = self._process_osm_response(data)
                print(f"✅ Found {len(fitness_stations)} fitness stations in OSM")
                return fitness_stations
            else:
                print(f"❌ OSM API Error: {response.status_code}")
                return self._get_fallback_data()
                
        except Exception as e:
            print(f"❌ OSM Query failed: {e}")
            return self._get_fallback_data()
    
    def _process_osm_response(self, data: Dict) -> List[Dict]:
        """Process raw OSM response into structured fitness station data."""
        fitness_stations = []
        
        for element in data.get('elements', []):
            # Get coordinates
            if element['type'] == 'node':
                lat, lon = element['lat'], element['lon']
            elif element['type'] == 'way' and 'center' in element:
                lat, lon = element['center']['lat'], element['center']['lon']
            elif element['type'] == 'relation' and 'center' in element:
                lat, lon = element['center']['lat'], element['center']['lon']
            else:
                continue
                
            # Process tags
            tags = element.get('tags', {})
            
            station = {
                'osm_id': element['id'],
                'osm_type': element['type'],
                'lat': lat,
                'lon': lon,
                'name': tags.get('name', f"Fitness Station {element['id']}"),
                'leisure': tags.get('leisure'),
                'sport': tags.get('sport'),
                'fitness': tags.get('fitness'),
                'amenity': tags.get('amenity'),
                'all_tags': tags,
                'source': 'openstreetmap',
                'confidence': self._calculate_osm_confidence(tags)
            }
            
            fitness_stations.append(station)
            
        return fitness_stations
    
    def _calculate_osm_confidence(self, tags: Dict) -> float:
        """Calculate confidence that this OSM element is actually a calisthenics park."""
        confidence = 0.0
        
        # Base confidence from primary tags
        if tags.get('leisure') == 'fitness_station':
            confidence += 0.8
        elif tags.get('amenity') == 'fitness_station':
            confidence += 0.7
        elif tags.get('sport') == 'fitness':
            confidence += 0.6
        
        # Bonus for specific fitness equipment tags
        fitness_equipment = tags.get('fitness', '').lower()
        calisthenics_keywords = ['pull_up', 'parallel_bars', 'bar', 'calisthenics', 'street_workout']
        
        for keyword in calisthenics_keywords:
            if keyword in fitness_equipment:
                confidence += 0.1
        
        # Bonus for having a name
        if tags.get('name'):
            confidence += 0.1
            
        # Check for calisthenics-specific names
        name = tags.get('name', '').lower()
        if any(word in name for word in ['calisthenics', 'street workout', 'klimmzug', 'barren']):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _get_fallback_data(self) -> List[Dict]:
        """Fallback data if OSM API fails."""
        print("⚠️ Using fallback data (OSM API unavailable)")
        
        return [
            {
                'osm_id': 'fallback_1',
                'osm_type': 'node',
                'lat': 51.2186,
                'lon': 6.7711,
                'name': 'Volksgarten Fitness (Fallback)',
                'leisure': 'fitness_station',
                'source': 'fallback',
                'confidence': 0.5
            },
            {
                'osm_id': 'fallback_2', 
                'osm_type': 'node',
                'lat': 51.2547,
                'lon': 6.7858,
                'name': 'Florapark Fitness (Fallback)',
                'leisure': 'fitness_station',
                'source': 'fallback',
                'confidence': 0.5
            }
        ]
    
    def get_parks_context(self) -> List[Dict]:
        """Get parks in Düsseldorf for context analysis."""
        print("🌳 Getting parks context from OSM...")
        
        query = """
        [out:json][timeout:25];
        (
          area["name"="Düsseldorf"]["admin_level"="6"];
        )->.searchArea;
        (
          way["leisure"="park"](area.searchArea);
          relation["leisure"="park"](area.searchArea);
        );
        out center;
        """
        
        try:
            response = requests.post(self.overpass_url, data=query, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                parks = []
                
                for element in data.get('elements', []):
                    if 'center' in element:
                        tags = element.get('tags', {})
                        parks.append({
                            'osm_id': element['id'],
                            'lat': element['center']['lat'],
                            'lon': element['center']['lon'],
                            'name': tags.get('name', 'Unnamed Park'),
                            'area': tags.get('area')
                        })
                
                print(f"✅ Found {len(parks)} parks for context")
                return parks
            else:
                print("⚠️ Parks context unavailable")
                return []
                
        except Exception as e:
            print(f"❌ Parks query failed: {e}")
            return []
    
    def validate_coordinates_against_osm(self, lat: float, lon: float, 
                                       max_distance: float = 200) -> Dict:
        """
        Check if given coordinates are near any OSM fitness station.
        
        Args:
            lat: Latitude
            lon: Longitude  
            max_distance: Maximum distance in meters to consider a match
            
        Returns:
            Dictionary with match information
        """
        fitness_stations = self.get_fitness_stations_dusseldorf()
        
        closest_match = None
        min_distance = float('inf')
        
        for station in fitness_stations:
            # Calculate distance (rough)
            lat_diff = lat - station['lat'] 
            lon_diff = lon - station['lon']
            distance = ((lat_diff**2 + lon_diff**2) ** 0.5) * 111000  # Rough km to meters
            
            if distance < min_distance:
                min_distance = distance
                closest_match = station
        
        if min_distance <= max_distance:
            return {
                'is_match': True,
                'distance_m': min_distance,
                'matched_station': closest_match,
                'confidence': closest_match['confidence']
            }
        else:
            return {
                'is_match': False,
                'distance_m': min_distance,
                'matched_station': None,
                'confidence': 0.0
            }


def test_osm_integration():
    """Test the OSM integration."""
    print("🧪 Testing OSM Integration")
    print("=" * 40)
    
    osm = OSMIntegration()
    
    # Test 1: Get fitness stations
    fitness_stations = osm.get_fitness_stations_dusseldorf()
    
    print(f"\n📊 Results:")
    print(f"Found {len(fitness_stations)} fitness stations")
    
    if fitness_stations:
        print(f"\nTop 5 stations:")
        for i, station in enumerate(fitness_stations[:5], 1):
            print(f"{i}. {station['name']}")
            print(f"   Coords: {station['lat']:.4f}, {station['lon']:.4f}")
            print(f"   Tags: leisure={station['leisure']}, sport={station['sport']}")
            print(f"   Confidence: {station['confidence']:.2f}")
            print(f"   OSM ID: {station['osm_type']}/{station['osm_id']}")
            print()
    
    # Test 2: Validate known coordinates
    print("🔍 Testing coordinate validation:")
    test_coords = [
        (51.2186, 6.7711, "Volksgarten Area"),
        (51.2547, 6.7858, "Florapark Area"), 
        (51.2203, 6.7947, "Hauptbahnhof Area")
    ]
    
    for lat, lon, name in test_coords:
        result = osm.validate_coordinates_against_osm(lat, lon)
        status = "✅ MATCH" if result['is_match'] else "❌ NO MATCH"
        print(f"{name}: {status} (Distance: {result['distance_m']:.0f}m)")
    
    return fitness_stations


if __name__ == "__main__":
    # Direct test
    stations = test_osm_integration()