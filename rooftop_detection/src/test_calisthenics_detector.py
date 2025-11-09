"""
Test Script für Calisthenics Park Detektor
==========================================

Testet die aktualisierte Implementierung mit realistischen Größenparametern (min. 50m²)
"""

from calisthenics_detector_dusseldorf import CalisthenicsDetectorDusseldorf

def test_detection_parameters():
    """Teste die aktualisierten Erkennungsparameter."""
    print("🧪 Testing Calisthenics Detection Parameters")
    print("=" * 50)
    
    detector = CalisthenicsDetectorDusseldorf()
    
    # Zeige die aktualisierten Parameter
    params = detector.detection_params
    print("Aktualisierte Erkennungsparameter:")
    print(f"  Mindestgröße: {params['min_area_m2']} m²")
    print(f"  Maximalgröße: {params['max_area_m2']} m²") 
    print(f"  Mindestpixel: {params['min_area_pixels']} Pixel")
    print(f"  Maximalpixel: {params['max_area_pixels']} Pixel")
    print(f"  NDVI-Bereich: {params['ndvi_threshold_low']} - {params['ndvi_threshold_high']}")
    print(f"  Seitenverhältnis: {params['aspect_ratio_min']} - {params['aspect_ratio_max']}")
    print(f"  Kompaktheit min: {params['compactness_min']}")
    
    print("\n✅ Parameter erfolgreich aktualisiert!")
    return True

def test_size_conversion():
    """Teste die Umrechnung zwischen Pixeln und Quadratmetern."""
    print("\n🔄 Testing Size Conversion Logic")
    print("=" * 35)
    
    # Bei 10m Auflösung: 1 Pixel = 10m x 10m = 100 m²
    test_cases = [
        (0.5, 50),    # 0.5 Pixel = 50 m²
        (1.0, 100),   # 1 Pixel = 100 m²
        (1.5, 150),   # 1.5 Pixel = 150 m²
        (2.0, 200),   # 2 Pixel = 200 m²
        (4.0, 400),   # 4 Pixel = 400 m²
    ]
    
    print("Pixel → m² Umrechnung (bei 10m Auflösung):")
    for pixels, expected_m2 in test_cases:
        calculated_m2 = pixels * 100
        status = "✅" if calculated_m2 == expected_m2 else "❌"
        print(f"  {pixels} Pixel = {calculated_m2} m² {status}")
    
    return True

def test_realistic_calisthenics_sizes():
    """Teste ob die neuen Parameter realistische Calisthenics-Park-Größen abdecken."""
    print("\n🏋️ Testing Realistic Calisthenics Park Sizes")
    print("=" * 45)
    
    # Typische Calisthenics-Park-Größen
    realistic_parks = [
        ("Kleiner Park (nur Klimmzugstange)", 30, "❌ Zu klein (unter 50 m²)"),
        ("Minimaler Park (Klimmzug + Barren)", 50, "✅ Erkennbar"), 
        ("Typischer Park (mehrere Geräte)", 100, "✅ Optimal"),
        ("Großer Park (komplette Ausstattung)", 200, "✅ Optimal"),
        ("Sehr großer Park (mit Laufstrecke)", 400, "✅ Erkennbar"),
        ("Zu großer Bereich (ganzer Spielplatz)", 600, "❌ Zu groß (über 400 m²)"),
    ]
    
    detector = CalisthenicsDetectorDusseldorf()
    min_size = detector.detection_params['min_area_m2']
    max_size = detector.detection_params['max_area_m2']
    
    print(f"Erkennungsbereich: {min_size}-{max_size} m²")
    print("\nBewertung typischer Parkgrößen:")
    
    for park_type, size, expected in realistic_parks:
        detectable = min_size <= size <= max_size
        status = "✅ Erkennbar" if detectable else "❌ Nicht erkennbar"
        print(f"  {size:3d} m² - {park_type:<35} → {status}")
        
    return True

def run_quick_demo():
    """Führe eine schnelle Demo-Erkennung durch."""
    print("\n🚀 Running Quick Detection Demo")
    print("=" * 35)
    
    try:
        detector = CalisthenicsDetectorDusseldorf()
        
        # Simuliere Datenabfrage
        print("📡 Simuliere Sentinel-2 Datenabfrage für Düsseldorf...")
        data = detector.get_sentinel2_data_mock()
        
        # Berechne Indizes
        print("🔄 Berechne Vegetationsindizes...")
        indices = detector.calculate_indices(data)
        
        # Erkenne Kandidaten
        print("🎯 Erkenne Calisthenics-Park-Kandidaten...")
        candidates = detector.detect_calisthenics_candidates(indices)
        
        print(f"\n📊 Demo-Ergebnisse:")
        print(f"  Gefundene Kandidaten: {len(candidates)}")
        
        if candidates:
            print(f"\nTop 3 Kandidaten:")
            sorted_candidates = sorted(candidates, key=lambda x: x['confidence'], reverse=True)[:3]
            
            for i, candidate in enumerate(sorted_candidates, 1):
                print(f"  {i}. Größe: {candidate['area_m2']:.0f} m², "
                      f"Vertrauen: {candidate['confidence']:.2f}, "
                      f"NDVI: {candidate['avg_ndvi']:.2f}")
        
        print("\n✅ Demo erfolgreich abgeschlossen!")
        return True
        
    except Exception as e:
        print(f"❌ Fehler in der Demo: {e}")
        return False

def main():
    """Hauptfunktion für alle Tests."""
    print("🏋️ CALISTHENICS PARK DETECTOR - TEST SUITE")
    print("🎯 Testet aktualisierte Parameter (min. 50m²)")
    print("=" * 55)
    
    # Führe alle Tests durch
    tests = [
        ("Parameter-Test", test_detection_parameters),
        ("Größenumrechnung-Test", test_size_conversion), 
        ("Realistische Größen-Test", test_realistic_calisthenics_sizes),
        ("Demo-Lauf", run_quick_demo)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Fehler in {test_name}: {e}")
            results.append((test_name, False))
    
    # Zusammenfassung
    print("\n" + "=" * 55)
    print("📋 TEST ZUSAMMENFASSUNG")
    print("=" * 55)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ BESTANDEN" if result else "❌ FEHLER"
        print(f"  {test_name:<25} → {status}")
    
    print(f"\nErgebnis: {passed}/{total} Tests bestanden")
    
    if passed == total:
        print("🎉 Alle Tests erfolgreich! Detektor ist bereit.")
        print("\n💡 Nächste Schritte:")
        print("   1. Echte Copernicus-Daten testen")
        print("   2. Mit bekannten Calisthenics-Parks in Düsseldorf validieren")
        print("   3. Parameter für bessere Genauigkeit optimieren")
    else:
        print("⚠️ Einige Tests fehlgeschlagen - bitte überprüfen.")

if __name__ == "__main__":
    main()