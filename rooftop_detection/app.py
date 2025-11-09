"""Streamlit app for rooftop detection

Interactive web interface for detecting suitable rooftops for soccer fields.
"""
import streamlit as st
import sys
from pathlib import Path
import json
import folium
from streamlit_folium import folium_static
import pandas as pd
import os

# Get app directory (works when cloned)
APP_DIR = Path(__file__).parent.resolve()
RESULTS_DIR = APP_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Add rooftop_detection to path
sys.path.insert(0, str(APP_DIR / "rooftop_detection"))

from rooftop_detector import RooftopDetector, CITY_BBOX, process_city_tiled

st.set_page_config(
    page_title="Rooftop Soccer Field Detector",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Rooftop Soccer Field Detector")
st.markdown("""
Identify suitable rooftops for soccer field installation using satellite imagery and terrain analysis.
""")

# Sidebar for city selection
st.sidebar.header("Configuration")

# Group cities by region
city_groups = {
    'Berlin': [k for k in CITY_BBOX.keys() if k.startswith('berlin')],
    'Düsseldorf': [k for k in CITY_BBOX.keys() if k.startswith('duesseldorf')],
}

# Create a more user-friendly city selector
st.sidebar.subheader("Select Region")
region = st.sidebar.selectbox(
    "City",
    options=list(city_groups.keys()),
)

st.sidebar.subheader("Select Area")
area_options = city_groups[region]

# Format display names
def format_area_name(key):
    if '_' not in key:
        return key.title()
    parts = key.split('_')
    if len(parts) == 1:
        return parts[0].title()
    city = parts[0].title()
    district = parts[1].replace('_', ' ').title()
    return f"📍 {district}" if parts[1] != parts[0] else f"🌆 Full {city}"

display_options = {format_area_name(k): k for k in area_options}

# Full city option first, then districts
full_city_key = [k for k in area_options if '_' not in k or k.split('_')[1] == k.split('_')[0]][0]
full_city_display = format_area_name(full_city_key)

# Sort districts
district_displays = sorted([format_area_name(k) for k in area_options if k != full_city_key])

ordered_displays = [full_city_display] + district_displays
ordered_options = {d: display_options[d] for d in ordered_displays}

selected_display = st.sidebar.radio(
    "Choose coverage",
    options=list(ordered_options.keys()),
    index=0
)

city = ordered_options[selected_display]

# Display city info
bbox = CITY_BBOX[city]
area_km2 = ((bbox[2] - bbox[0]) * 111 * (bbox[3] - bbox[1]) * 111)  # Rough calculation
st.sidebar.info(f"""
**Selected Area:** {selected_display}

**Coverage:**
- Area: ~{area_km2:.1f} km²
- Bounds: {bbox[1]:.3f}°N to {bbox[3]:.3f}°N

**Processing Time:**
- Small district: ~2-5 min
- Full city: ~5-15 min
""")

# Check if results already exist
geojson_path = RESULTS_DIR / f"{city}_rooftops.geojson"
results_exist = geojson_path.exists()

if results_exist:
    st.sidebar.success("✅ Results available for this area")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("� Show Results", type="primary", use_container_width=True):
            st.session_state['show_results'] = True
            st.session_state['current_city'] = city
    with col2:
        if st.button("🔄 Re-run", help="Process again (overwrites existing results)", use_container_width=True):
            st.session_state['force_rerun'] = True
            st.session_state['show_results'] = False
else:
    st.sidebar.warning("⚠️ No results yet for this area")

# Detection button
run_detection = False
if not results_exist:
    run_detection = st.sidebar.button("🔍 Start Detection", type="primary")
elif st.session_state.get('force_rerun', False):
    run_detection = True
    st.session_state['force_rerun'] = False

if run_detection:
    with st.spinner("Detecting rooftops... This may take several minutes."):
        # Initialize detector
        detector = RooftopDetector()
        
        # Authenticate
        progress_text = st.empty()
        progress_text.text("Authenticating with Copernicus...")
        detector.authenticate()
        
        # Process city
        progress_text.text(f"Processing {city}...")
        features = process_city_tiled(city, detector)
        
        # Save results
        progress_text.text("Saving results...")
        geojson_path = RESULTS_DIR / f"{city}_rooftops.geojson"
        feature_collection = {"type": "FeatureCollection", "features": features}
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(feature_collection, f, ensure_ascii=False, indent=2)
        
        progress_text.empty()
        st.success(f"✅ Detection complete! Found {len(features)} rooftops")
        st.session_state['show_results'] = True
        st.session_state['current_city'] = city
        st.rerun()

# Check if we should display results
# Only show if: results exist AND (show_results button was pressed OR detection just completed)
should_show_results = (
    geojson_path.exists() and 
    st.session_state.get('show_results', False) and
    st.session_state.get('current_city') == city
)

# Display results if available and button was pressed
if should_show_results:
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    features = data['features']
    
    # Metrics (always show full dataset stats)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Rooftops", len(features))
    
    with col2:
        avg_area = sum(f['properties']['area_m2'] for f in features) / len(features)
        st.metric("Avg Area", f"{avg_area:.0f} m²")
    
    with col3:
        avg_score = sum(f['properties']['suitability_score'] for f in features) / len(features)
        st.metric("Avg Suitability", f"{avg_score:.2f}")
    
    with col4:
        avg_slope = sum(f['properties']['slope_deg'] for f in features) / len(features)
        st.metric("Avg Slope", f"{avg_slope:.1f}°")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["🗺️ Map", "📊 Data Table", "📈 Statistics"])
    
    with tab1:
        st.subheader("Interactive Map")
        
        # Filter toggle - moved to map tab, show all by default
        show_top_10 = st.checkbox("🏆 Show only Top 10 candidates", value=False, key="map_filter")
        
        # Prepare features for display
        features_sorted = sorted(features, key=lambda x: x['properties']['suitability_score'], reverse=True)
        
        if show_top_10:
            features_display = features_sorted[:10]
            st.info(f"🎯 Showing top 10 candidates (from {len(features)} total)")
        else:
            features_display = features_sorted
        
        # Navigation controls
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        
        # Sort features by suitability for navigation
        features_sorted = sorted(features_display, key=lambda x: x['properties']['suitability_score'], reverse=True)
        
        # Initialize navigation state
        if 'current_rooftop_index' not in st.session_state:
            st.session_state.current_rooftop_index = 0
        
        with col_nav1:
            if st.button("⬅️ Previous", use_container_width=True):
                st.session_state.current_rooftop_index = (st.session_state.current_rooftop_index - 1) % len(features_sorted)
        
        with col_nav2:
            current_rooftop = features_sorted[st.session_state.current_rooftop_index]
            st.markdown(f"**Rooftop {st.session_state.current_rooftop_index + 1}/{len(features_sorted)}** - "
                       f"Suitability: {current_rooftop['properties']['suitability_score']:.3f}")
        
        with col_nav3:
            if st.button("Next ➡️", use_container_width=True):
                st.session_state.current_rooftop_index = (st.session_state.current_rooftop_index + 1) % len(features_sorted)
        
        # Get center coordinates for current rooftop
        current_coords = current_rooftop['geometry']['coordinates'][0]
        center_lats = [c[1] for c in current_coords]
        center_lons = [c[0] for c in current_coords]
        center_lat = sum(center_lats) / len(center_lats)
        center_lon = sum(center_lons) / len(center_lons)
        
        # Calculate region center for initial view
        bbox = CITY_BBOX[city]
        region_center_lat = (bbox[1] + bbox[3]) / 2
        region_center_lon = (bbox[0] + bbox[2]) / 2
        
        # Calculate appropriate zoom level for region
        lat_diff = bbox[3] - bbox[1]
        lon_diff = bbox[2] - bbox[0]
        max_diff = max(lat_diff, lon_diff)
        
        # Determine zoom: smaller area = higher zoom
        if max_diff > 0.5:
            region_zoom = 10
        elif max_diff > 0.2:
            region_zoom = 11
        elif max_diff > 0.1:
            region_zoom = 12
        else:
            region_zoom = 13
        
        # Create map centered on region first
        m = folium.Map(
            location=[region_center_lat, region_center_lon],
            zoom_start=region_zoom,
            tiles='OpenStreetMap',
            zoom_control=True,
            scrollWheelZoom=True
        )
        
        # Add region boundary highlight
        bbox = CITY_BBOX[city]
        region_boundary = [
            [bbox[1], bbox[0]],  # Southwest corner (min_lat, min_lon)
            [bbox[1], bbox[2]],  # Southeast corner (min_lat, max_lon)
            [bbox[3], bbox[2]],  # Northeast corner (max_lat, max_lon)
            [bbox[3], bbox[0]],  # Northwest corner (max_lat, min_lon)
            [bbox[1], bbox[0]]   # Close the polygon
        ]
        
        folium.Polygon(
            locations=region_boundary,
            color='purple',
            weight=3,
            fill=False,
            opacity=0.8,
            popup=f"<b>Detection Area:</b><br>{selected_display}",
            tooltip=f"📍 {selected_display}"
        ).add_to(m)
        
        # Add legend
        legend_html = f'''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 220px; height: auto; 
                    background-color: white; z-index:9999; font-size:14px;
                    border:2px solid grey; border-radius: 5px; padding: 10px">
        <h4 style="margin-top:0;">Rooftop Suitability</h4>
        <p><i class="fa fa-square" style="color:darkgreen"></i> Excellent (0.9-1.0)</p>
        <p><i class="fa fa-square" style="color:green"></i> Very Good (0.8-0.9)</p>
        <p><i class="fa fa-square" style="color:blue"></i> Good (0.7-0.8)</p>
        <p><i class="fa fa-square" style="color:orange"></i> Moderate (0.6-0.7)</p>
        <p><i class="fa fa-square" style="color:red"></i> Low (&lt;0.6)</p>
        <hr style="margin: 10px 0;">
        <p style="margin:0;"><strong>Current:</strong> #{st.session_state.current_rooftop_index + 1}</p>
        <hr style="margin: 10px 0;">
        <p style="margin:0; color:purple;"><strong>━━━</strong> Detection Area</p>
        <p style="margin:0; font-size:12px;">{selected_display}</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Function to determine color based on suitability
        def get_color(score):
            if score >= 0.9:
                return 'darkgreen'
            elif score >= 0.8:
                return 'green'
            elif score >= 0.7:
                return 'blue'
            elif score >= 0.6:
                return 'orange'
            else:
                return 'red'
        
        # Add all rooftops with color coding
        for i, feature in enumerate(features_sorted):
            score = feature['properties']['suitability_score']
            is_current = (i == st.session_state.current_rooftop_index)
            
            folium.GeoJson(
                {"type": "FeatureCollection", "features": [feature]},
                style_function=lambda x, score=score, is_current=is_current: {
                    'fillColor': get_color(score),
                    'color': 'black' if is_current else get_color(score),
                    'weight': 4 if is_current else 2,
                    'fillOpacity': 0.7 if is_current else 0.4,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['id', 'area_m2', 'suitability_score', 'mean_height_m', 'slope_deg', 'ndvi_mean'],
                    aliases=['ID:', 'Area (m²):', 'Score:', 'Height (m):', 'Slope (°):', 'NDVI:'],
                    localize=True
                )
            ).add_to(m)
        
        # Add marker for current rooftop
        folium.Marker(
            [center_lat, center_lon],
            popup=f"Rank #{st.session_state.current_rooftop_index + 1}<br>Score: {current_rooftop['properties']['suitability_score']:.3f}",
            icon=folium.Icon(color='red', icon='star')
        ).add_to(m)
        
        # Add smooth zoom animation using Leaflet's flyTo
        zoom_animation = f"""
        <script>
        // Wait for map to be fully loaded
        function animateToRooftop() {{
            var mapElement = document.querySelector('.folium-map');
            if (!mapElement) {{
                setTimeout(animateToRooftop, 100);
                return;
            }}
            
            // Try to get the Leaflet map instance
            var mapId = mapElement.getAttribute('id');
            if (window[mapId]) {{
                var map = window[mapId];
                // Wait 800ms to show region, then fly to rooftop
                setTimeout(function() {{
                    map.flyTo([{center_lat}, {center_lon}], 17, {{
                        duration: 2.5,
                        easeLinearity: 0.25
                    }});
                }}, 800);
            }} else {{
                setTimeout(animateToRooftop, 100);
            }}
        }}
        
        // Start animation after page loads
        if (document.readyState === 'complete') {{
            animateToRooftop();
        }} else {{
            window.addEventListener('load', animateToRooftop);
        }}
        </script>
        """
        m.get_root().html.add_child(folium.Element(zoom_animation))
        
        # Display map
        folium_static(m, width=1400, height=600)
    
    with tab2:
        st.subheader("Detected Rooftops")
        
        # Show all features in table (not filtered)
        # Convert to DataFrame
        df_data = []
        for f in features_sorted:
            props = f['properties']
            coords = f['geometry']['coordinates'][0][0]
            df_data.append({
                'ID': props['id'],
                'Area (m²)': round(props['area_m2'], 1),
                'Height (m)': round(props['mean_height_m'], 1),
                'Slope (°)': round(props['slope_deg'], 1),
                'NDVI': round(props['ndvi_mean'], 3),
                'Suitability': round(props['suitability_score'], 3),
                'Longitude': round(coords[0], 5),
                'Latitude': round(coords[1], 5)
            })
        
        df = pd.DataFrame(df_data)
        # Already sorted by suitability from features_sorted
        
        st.dataframe(df, use_container_width=True, height=400)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"{city}_rooftops.csv",
            mime="text/csv"
        )
    
    with tab3:
        st.subheader("Statistics")
        
        # Show all features in statistics (not filtered)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Area Distribution**")
            area_bins = [400, 1000, 2000, 5000, 10000]
            area_labels = ['400-1k', '1k-2k', '2k-5k', '5k-10k']
            areas = [f['properties']['area_m2'] for f in features]
            area_counts = pd.cut(areas, bins=area_bins, labels=area_labels).value_counts().sort_index()
            st.bar_chart(area_counts)
        
        with col2:
            st.markdown("**Suitability Score Distribution**")
            scores = [f['properties']['suitability_score'] for f in features]
            score_bins = [0, 0.6, 0.7, 0.8, 0.9, 1.0]
            score_labels = ['0.0-0.6', '0.6-0.7', '0.7-0.8', '0.8-0.9', '0.9-1.0']
            score_counts = pd.cut(scores, bins=score_bins, labels=score_labels).value_counts().sort_index()
            st.bar_chart(score_counts)
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("**Slope Distribution**")
            slopes = [f['properties']['slope_deg'] for f in features]
            slope_df = pd.DataFrame({'Slope (°)': slopes})
            st.line_chart(slope_df, height=200)
        
        with col4:
            st.markdown("**Height Distribution**")
            heights = [f['properties']['mean_height_m'] for f in features]
            height_df = pd.DataFrame({'Height (m)': heights})
            st.line_chart(height_df, height=200)

else:
    # No results to show - display information
    st.info("👆 Select a city and click 'Start Detection' to begin, or 'Show Results' if data is already available.")
    
    # Show what we're looking for
    st.markdown("---")
    st.subheader("What We're Looking For")
    
    st.markdown("""
    We identify **large, flat rooftops on tall buildings** that could be converted into soccer fields. 
    Ideal candidates are:
    
    - 🏢 **Commercial or industrial buildings** with expansive flat roofs
    - 📐 **Large enough** for a mini soccer field (at least 400 m²)
    - 📏 **Flat surfaces** (less than 10° slope) for safe sports activities  
    - 🏗️ **Structurally sound** buildings (over 10m tall) that can handle additional load
    - 🌿 **Non-vegetated roofs** (concrete, metal, or similar) ready for installation
    
    Think warehouses, shopping centers, office buildings, parking garages - not residential apartment buildings.
    """)
    
    # Show technical criteria
    st.markdown("---")
    st.subheader("Technical Detection Criteria")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Size Requirements:**
        - Minimum: 400 m²
        - Maximum: 10,000 m²
        
        **Structure:**
        - Height > 10m
        - Slope < 10°
        """)
    
    with col2:
        st.markdown("""
        **Surface:**
        - NDVI < 0.3 (non-vegetated)
        - High reflectance
        
        **Shape:**
        - Aspect ratio < 4.0
        - Clear boundaries
        """)
