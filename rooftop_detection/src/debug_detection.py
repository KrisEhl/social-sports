"""
Debug: Why are the known Düsseldorf calisthenics parks not detected?
==================================================================

Let's analyze what went wrong with our detection method.
"""

import requests
import numpy as np

def debug_known_parks():
    """Debug why known calisthenics parks were not detected."""
    
    print("🔍 DEBUGGING: Known Calisthenics Parks Detection")
    print("=" * 55)
    
    # Known calisthenics park locations in Düsseldorf
    known_parks = [
        {
            'name': 'Volksgarten Calisthenics Park',
            'lat': 51.2070, 
            'lon': 6.7995,
            'description': 'Outdoor fitness equipment in Volksgarten'
        },
        {
            'name': 'Florapark Calisthenics Area', 
            'lat': 51.2098,
            'lon': 6.7725,
            'description': 'Fitness equipment in Florapark'
        },
        {
            'name': 'Hauptbahnhof Area Fitness',
            'lat': 51.2203,
            'lon': 6.7947, 
            'description': 'Near central station fitness area'
        }
    ]
    
    print("🎯 KNOWN CALISTHENICS PARKS (Ground Truth):")
    for i, park in enumerate(known_parks, 1):
        print(f"{i}. {park['name']}")
        print(f"   📍 {park['lat']:.4f}, {park['lon']:.4f}")
        print(f"   📝 {park['description']}")
        print()
    
    # Check what our bounding box was
    detection_bbox = [6.65, 51.10, 6.95, 51.35]  # From our detector
    west, south, east, north = detection_bbox
    
    print("🗺️ OUR DETECTION BOUNDING BOX:")
    print(f"   West: {west}, East: {east}")
    print(f"   South: {south}, North: {north}")
    print()
    
    # Check if known parks are within our detection area
    print("📍 COVERAGE ANALYSIS:")
    for park in known_parks:
        lat, lon = park['lat'], park['lon']
        
        within_bounds = (west <= lon <= east) and (south <= lat <= north)
        
        if within_bounds:
            print(f"✅ {park['name']}: WITHIN detection area")
        else:
            print(f"❌ {park['name']}: OUTSIDE detection area!")
            if lon < west or lon > east:
                print(f"   🚨 Longitude {lon} not in range [{west}, {east}]")
            if lat < south or lat > north:
                print(f"   🚨 Latitude {lat} not in range [{south}, {north}]")
        print()
    
    # Check OSM data for these specific locations
    print("🗺️ OSM DATA CHECK:")
    check_osm_at_known_locations(known_parks)


def check_osm_at_known_locations(known_parks):
    """Check what OSM says about our known calisthenics locations."""
    
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    for park in known_parks:
        lat, lon = park['lat'], park['lon']
        
        print(f"🔍 Checking OSM near {park['name']}:")
        
        # Query for anything near this location (500m radius)
        query = f"""
        [out:json][timeout:15];
        (
          node(around:500,{lat},{lon})["leisure"];
          way(around:500,{lat},{lon})["leisure"];
          node(around:500,{lat},{lon})["sport"];
          way(around:500,{lat},{lon})["sport"];
          node(around:500,{lat},{lon})["fitness"];
          way(around:500,{lat},{lon})["fitness"];
        );
        out center meta;
        """
        
        try:
            response = requests.post(overpass_url, data=query, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                elements = data.get('elements', [])
                
                if elements:
                    print(f"   ✅ Found {len(elements)} relevant OSM objects:")
                    
                    for element in elements[:3]:  # Show first 3
                        tags = element.get('tags', {})
                        
                        if element['type'] == 'node':
                            elem_lat, elem_lon = element['lat'], element['lon']
                        elif 'center' in element:
                            elem_lat, elem_lon = element['center']['lat'], element['center']['lon']
                        else:
                            elem_lat, elem_lon = 'N/A', 'N/A'
                        
                        # Calculate distance
                        if elem_lat != 'N/A':
                            lat_diff = lat - elem_lat
                            lon_diff = lon - elem_lon
                            distance = ((lat_diff**2 + lon_diff**2) ** 0.5) * 111000
                        else:
                            distance = 'N/A'
                        
                        print(f"     • {tags.get('name', 'Unnamed')}")
                        print(f"       Tags: {dict(list(tags.items())[:3])}")
                        print(f"       Distance: {distance:.0f}m" if distance != 'N/A' else "       Distance: N/A")
                else:
                    print(f"   ❌ No OSM objects found within 500m")
                    print(f"   💡 This might explain why detection failed!")
                    
            else:
                print(f"   ❌ OSM query failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ OSM error: {e}")
        
        print()


def analyze_detection_problem():
    """Analyze why our detection method failed."""
    
    print("🚨 DETECTION PROBLEM ANALYSIS:")
    print("=" * 35)
    
    problems = {
        'coordinate_mismatch': {
            'description': 'Known parks coordinates might be inaccurate',
            'likelihood': 'HIGH',
            'solution': 'Verify exact coordinates with satellite imagery'
        },
        'osm_data_gaps': {
            'description': 'Calisthenics parks not properly tagged in OSM',
            'likelihood': 'VERY HIGH', 
            'solution': 'Use different OSM query or manual coordinate validation'
        },
        'bbox_too_large': {
            'description': 'Detection area too big, signatures get diluted',
            'likelihood': 'MEDIUM',
            'solution': 'Focus on smaller areas around known parks'
        },
        'ndvi_assumptions_wrong': {
            'description': 'NDVI signature assumptions incorrect for calisthenics equipment',
            'likelihood': 'HIGH',
            'solution': 'Analyze real satellite data at known locations'
        },
        'simulation_unrealistic': {
            'description': 'Synthetic data doesn\'t match real conditions',
            'likelihood': 'VERY HIGH',
            'solution': 'Use actual Sentinel-2 pixel values at known locations'
        }
    }
    
    for problem, details in problems.items():
        likelihood_emoji = "🔴" if details['likelihood'] == 'VERY HIGH' else \
                          "🟠" if details['likelihood'] == 'HIGH' else "🟡"
        
        print(f"{likelihood_emoji} {problem.upper().replace('_', ' ')}")
        print(f"   Problem: {details['description']}")
        print(f"   Likelihood: {details['likelihood']}")
        print(f"   💡 Solution: {details['solution']}")
        print()
    
    print("🎯 RECOMMENDED NEXT STEPS:")
    print("1. Get EXACT coordinates of known calisthenics parks")
    print("2. Download real Sentinel-2 pixels at those locations") 
    print("3. Analyze actual NDVI values at equipment areas")
    print("4. Tune detection parameters based on ground truth")
    print("5. Test detection on smaller, focused areas")


if __name__ == "__main__":
    debug_known_parks()
    print()
    analyze_detection_problem()