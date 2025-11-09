"""
Quick Test Runner for Calisthenics Park Detection
================================================

This script runs the calisthenics park detection for Düsseldorf
and shows immediate results.

Usage: python run_calisthenics_detection.py
"""

import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("🏋️ DÜSSELDORF CALISTHENICS PARK DETECTION - QUICK TEST")
    print("=" * 60)
    
    try:
        # Import our detector
        from calisthenics_detector_dusseldorf import CalisthenicsDetectorDusseldorf
        
        print("✅ Successfully imported detector")
        
        # Initialize and run
        detector = CalisthenicsDetectorDusseldorf()
        print("✅ Detector initialized for Düsseldorf")
        
        # Run the analysis
        results = detector.run_full_analysis()
        
        print("\n🎉 SUCCESS! Calisthenics park detection completed!")
        print(f"Found {results['total_candidates']} potential calisthenics parks")
        print(f"High confidence detections: {results['high_confidence']}")
        
        print("\n📁 Generated files:")
        print("  - dusseldorf_calisthenics_detection_results.html (open in browser)")
        print("  - dusseldorf_calisthenics_calisthenics_parks.geojson") 
        print("  - dusseldorf_calisthenics_calisthenics_parks.csv")
        print("  - dusseldorf_calisthenics_validation_report.json")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure all required libraries are installed:")
        print("pip install numpy folium geopandas opencv-python scikit-learn matplotlib pandas rasterio shapely")
        return False
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🚀 NEXT STEPS FOR HACKATHON:")
        print("1. Replace mock data with real Copernicus Sentinel-2 API calls")
        print("2. Fine-tune detection parameters based on validation results") 
        print("3. Add web interface for interactive exploration")
        print("4. Integrate with OpenStreetMap for additional validation")
        print("5. Extend to other German cities")
    else:
        print("\n🔧 Fix the issues above and try again!")