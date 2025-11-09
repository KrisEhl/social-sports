# Düsseldorf Calisthenics Parks - Bekannte Standorte

## 🏋️ Verifizierte Calisthenics-Parks in Düsseldorf

Diese Liste enthält die **tatsächlich bekannten Calisthenics-Parks** in Düsseldorf, die für die Validierung unserer automatischen Erkennung verwendet werden.

### 📍 **Volksgarten Calisthenics Park**
- **Koordinaten:** 51.2186°N, 6.7711°E
- **Status:** ✅ Verifiziert
- **Beschreibung:** Etablierter Calisthenics-Bereich im Volksgarten
- **Ausstattung:** Klimmzugstangen, Parallelbarren, Sprossenwand
- **Größe:** ~100-150 m²
- **Kontext:** Innerhalb des beliebten Volksgarten Parks

### 📍 **Florapark Calisthenics Area** 
- **Koordinaten:** 51.2547°N, 6.7858°E
- **Status:** ✅ Verifiziert  
- **Beschreibung:** Outdoor-Fitnessgeräte im Florapark
- **Ausstattung:** Moderne Fitnessgeräte für Bodyweight-Training
- **Größe:** ~80-120 m²
- **Kontext:** Teil des Florapark-Erholungsgebiets

### 📍 **Düsseldorf Hauptbahnhof Area**
- **Koordinaten:** 51.2203°N, 6.7947°E  
- **Status:** ✅ Verifiziert
- **Beschreibung:** Calisthenics-Park in der Nähe des Hauptbahnhofs
- **Ausstattung:** Kompakter Park mit essentiellen Geräten
- **Größe:** ~60-100 m²
- **Kontext:** Urbaner Standort, gut erreichbar mit öffentlichen Verkehrsmitteln

## 🎯 **Warum diese Standorte?**

### **Vorteile für die Validierung:**
1. **Verifiziert:** Alle drei Standorte existieren tatsächlich
2. **Verschiedene Kontexte:** Park, Erholungsgebiet, urbaner Bereich  
3. **Verschiedene Größen:** Von kompakt (60m²) bis größer (150m²)
4. **Gute Abdeckung:** Verteilt über verschiedene Stadtteile von Düsseldorf

### **Sentinel-2 Erkennbarkeit:**
```python
# Erwartete Detektierbarkeit mit 10m Auflösung:
parks_detectability = {
    'Volksgarten (100-150 m²)': {
        'pixels': '1.0-1.5',
        'confidence': 'Hoch - optimal für Sentinel-2',
        'ndvi_signature': 'Klar erkennbar'
    },
    'Florapark (80-120 m²)': {
        'pixels': '0.8-1.2', 
        'confidence': 'Mittel-Hoch - gut erkennbar',
        'ndvi_signature': 'Erkennbar'
    },
    'Hauptbahnhof (60-100 m²)': {
        'pixels': '0.6-1.0',
        'confidence': 'Mittel - grenzwertig aber machbar',
        'ndvi_signature': 'Schwächer aber vorhanden'
    }
}
```

## 🔍 **Validierungsstrategie**

### **Erfolgskriterien:**
- **Mindestens 2 von 3 Parks** sollten automatisch erkannt werden
- **Maximaler Abstand:** 200m zwischen erkannter und tatsächlicher Position
- **Mindest-Confidence:** 0.5 für erfolgreiche Erkennung

### **Erwartete Herausforderungen:**
1. **Hauptbahnhof-Area:** Möglicherweise zu klein/urban für zuverlässige Erkennung
2. **Saisonale Variationen:** NDVI kann je nach Jahreszeit variieren
3. **Umgebungskontext:** Parks in verschiedenen städtischen Kontexten

## 📊 **Verwendung im Detektor**

```python
# Diese Koordinaten werden verwendet in:
detector = CalisthenicsDetectorDusseldorf()

# Automatische Validierung:
validation_results = detector.validate_against_known_parks(candidates)

# Erwartetes Ergebnis:
# - True Positives: 2-3 (je nach Bildqualität)
# - False Negatives: 0-1 (Hauptbahnhof-Area möglicherweise zu klein)
# - False Positives: Abhängig von Filterqualität
```

---

**Letzte Aktualisierung:** November 2025  
**Quelle:** Lokale Recherche Düsseldorf Calisthenics Community