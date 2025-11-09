"""
Expanded OSM query to find actual calisthenics parks in Düsseldorf.
"""

import requests

def expanded_calisthenics_search():
    """Search for calisthenics parks with broader query."""
    
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Much broader query including playgrounds and sports areas
    query = """
    [out:json][timeout:25];
    (
      area["name"="Düsseldorf"]["admin_level"="6"];
    )->.searchArea;
    (
      // Fitness stations
      node["leisure"="fitness_station"](area.searchArea);
      way["leisure"="fitness_station"](area.searchArea);
      
      // Sports centres with fitness
      node["leisure"="sports_centre"]["sport"~"fitness|calisthenics"](area.searchArea);
      way["leisure"="sports_centre"]["sport"~"fitness|calisthenics"](area.searchArea);
      
      // Playgrounds with fitness equipment
      node["leisure"="playground"]["fitness"](area.searchArea);
      way["leisure"="playground"]["fitness"](area.searchArea);
      
      // Generic fitness amenities
      node["amenity"="fitness"](area.searchArea);
      way["amenity"="fitness"](area.searchArea);
      
      // Anything tagged with calisthenics
      node["sport"="calisthenics"](area.searchArea);
      way["sport"="calisthenics"](area.searchArea);
      
      // Street workout areas
      node["fitness"~"pull.*up|bar|calisthenics"](area.searchArea);
      way["fitness"~"pull.*up|bar|calisthenics"](area.searchArea);
    );
    out center meta;
    """
    
    try:
        print("🔍 Erweiterte OSM-Suche für Calisthenics...")
        response = requests.post(overpass_url, data=query, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Gefunden: {len(data['elements'])} Objekte")
            
            # Analyze results
            for i, element in enumerate(data['elements'][:10], 1):
                tags = element.get('tags', {})
                
                # Get coordinates
                if element['type'] == 'node':
                    lat, lon = element['lat'], element['lon']
                elif 'center' in element:
                    lat, lon = element['center']['lat'], element['center']['lon']
                else:
                    lat, lon = 'N/A', 'N/A'
                
                print(f"\n{i}. OSM {element['type']}/{element['id']}")
                print(f"   📍 Koordinaten: {lat}, {lon}")
                print(f"   🏷️ Name: {tags.get('name', 'Unbekannt')}")
                print(f"   🏋️ Leisure: {tags.get('leisure')}")
                print(f"   ⚽ Sport: {tags.get('sport')}")
                print(f"   💪 Fitness: {tags.get('fitness')}")
                
                # Check for calisthenics keywords
                relevant_tags = []
                for key, value in tags.items():
                    if any(word in str(value).lower() for word in ['pull', 'bar', 'fitness', 'calisthenics', 'workout']):
                        relevant_tags.append(f"{key}={value}")
                
                if relevant_tags:
                    print(f"   🎯 Relevante Tags: {', '.join(relevant_tags[:3])}")
                    
        else:
            print(f"❌ OSM Fehler: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Abfrage fehlgeschlagen: {e}")

def search_parks_with_fitness():
    """Search for parks that might contain fitness equipment."""
    
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    query = """
    [out:json][timeout:25];
    (
      area["name"="Düsseldorf"]["admin_level"="6"];
    )->.searchArea;
    (
      // All parks in Düsseldorf
      way["leisure"="park"]["name"~"Volksgarten|Flora|Bahnhof"](area.searchArea);
      relation["leisure"="park"]["name"~"Volksgarten|Flora|Bahnhof"](area.searchArea);
    );
    out center;
    """
    
    try:
        print("\n🌳 Suche nach bekannten Parks...")
        response = requests.post(overpass_url, data=query, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Parks gefunden: {len(data['elements'])}")
            
            for element in data['elements']:
                tags = element.get('tags', {})
                if 'center' in element:
                    lat, lon = element['center']['lat'], element['center']['lon']
                    print(f"   🌲 {tags.get('name')}: {lat:.4f}, {lon:.4f}")
                    
        else:
            print(f"❌ Parks-Suche Fehler: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Parks-Abfrage fehlgeschlagen: {e}")

if __name__ == "__main__":
    expanded_calisthenics_search()
    search_parks_with_fitness()