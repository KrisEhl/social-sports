"""
Sentinel Hub Catalog API - The RIGHT Way to Access Sentinel-2 Data
==================================================================

Using modern STAC-compatible Sentinel Hub API instead of legacy OData API.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List


class SentinelHubCatalog:
    """
    Modern Sentinel Hub Catalog API for Sentinel-2 data access.
    
    This is the RECOMMENDED way to access Copernicus data!
    """
    
    def __init__(self):
        self.catalog_url = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"
        self.auth_url = ("https://identity.dataspace.copernicus.eu/auth/realms/"
                        "CDSE/protocol/openid-connect/token")
        self.access_token = None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Copernicus Data Space."""
        try:
            print("🔐 Authenticating with Sentinel Hub...")
            
            auth_data = {
                'grant_type': 'password', 
                'username': username,
                'password': password,
                'client_id': 'cdse-public'
            }
            
            response = requests.post(self.auth_url, data=auth_data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                print("✅ Sentinel Hub authentication successful!")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def search_sentinel2_dusseldorf(self, days_back: int = 14,
                                   max_cloud_cover: float = 30.0) -> List[Dict]:
        """
        Search Sentinel-2 data for Düsseldorf using modern Catalog API.
        
        This uses the STAC-compatible Sentinel Hub Catalog API.
        """
        print(f"🔍 Searching Sentinel-2 for Düsseldorf (last {days_back} days)")
        
        # Düsseldorf bounding box [west, south, east, north]
        dusseldorf_bbox = [6.65, 51.10, 6.95, 51.35]
        
        # Date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Modern STAC search request
        search_data = {
            "bbox": dusseldorf_bbox,
            "datetime": f"{start_date.strftime('%Y-%m-%d')}T00:00:00Z/{end_date.strftime('%Y-%m-%d')}T23:59:59Z",
            "collections": ["sentinel-2-l2a"],  # Level-2A (atmospherically corrected)
            "limit": 10,
            "filter": f"eo:cloud_cover <= {max_cloud_cover}",
            "fields": {
                "include": [
                    "id", "properties.datetime", "properties.eo:cloud_cover",
                    "assets", "bbox", "properties.s2:mgrs_tile"
                ]
            }
        }
        
        try:
            # Make search request
            headers = {}
            if self.access_token:
                headers['Authorization'] = f'Bearer {self.access_token}'
            
            response = requests.post(self.catalog_url, json=search_data,
                                   headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                
                print(f"✅ Found {len(features)} Sentinel-2 products")
                
                # Process results
                products = []
                for feature in features:
                    props = feature.get('properties', {})
                    assets = feature.get('assets', {})
                    
                    # Count available bands
                    band_count = sum(1 for key in assets.keys() if key.startswith('B'))
                    
                    products.append({
                        'id': feature['id'],
                        'date': props.get('datetime', '')[:10],
                        'cloud_cover': props.get('eo:cloud_cover', 0),
                        'tile': props.get('s2:mgrs_tile', 'Unknown'),
                        'bbox': feature.get('bbox', []),
                        'bands_available': band_count,
                        'assets': list(assets.keys())[:5],  # First 5 asset names
                        'download_links': self._extract_download_links(assets)
                    })
                
                # Sort by cloud cover (best first)
                products.sort(key=lambda x: x['cloud_cover'])
                
                return products
                
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(response.text[:300])
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def _extract_download_links(self, assets: Dict) -> Dict:
        """Extract download links for key bands."""
        key_bands = ['B04', 'B08', 'B02', 'B03']  # Red, NIR, Blue, Green
        
        links = {}
        for band in key_bands:
            if band in assets:
                asset = assets[band]
                if 'href' in asset:
                    links[band] = asset['href']
        
        return links
    
    def get_band_data_info(self, product: Dict) -> Dict:
        """Get information about downloading specific bands."""
        if not self.access_token:
            return {'error': 'Authentication required'}
        
        download_info = {
            'product_id': product['id'],
            'date': product['date'],
            'cloud_cover': product['cloud_cover'],
            'tile': product['tile'],
            'bands_for_ndvi': []
        }
        
        # Check if NDVI bands are available
        required_bands = ['B04', 'B08']  # Red and NIR for NDVI
        available_bands = []
        
        for band in required_bands:
            if band in product['download_links']:
                available_bands.append({
                    'band': band,
                    'name': 'Red' if band == 'B04' else 'NIR',
                    'download_url': product['download_links'][band],
                    'auth_required': True
                })
        
        download_info['bands_for_ndvi'] = available_bands
        download_info['ndvi_ready'] = len(available_bands) == 2
        
        return download_info


def test_sentinel_hub_api():
    """Test the modern Sentinel Hub Catalog API."""
    print("🚀 Testing Sentinel Hub Catalog API")
    print("=" * 40)
    
    catalog = SentinelHubCatalog()
    
    # Use your credentials
    username = "christopher-george@web.de"
    password = "***REMOVED***"  # Note: In production, use env vars!
    
    if catalog.authenticate(username, password):
        print("\n🔍 Searching for Düsseldorf Sentinel-2 data...")
        
        products = catalog.search_sentinel2_dusseldorf(
            days_back=30,  # Extended search
            max_cloud_cover=50.0  # More lenient cloud cover
        )
        
        if products:
            print(f"\n📊 Results (best cloud cover first):")
            
            for i, product in enumerate(products[:5], 1):
                status = "🟢 Excellent" if product['cloud_cover'] < 5 else \
                        "🟡 Good" if product['cloud_cover'] < 20 else \
                        "🟠 Usable" if product['cloud_cover'] < 40 else "🔴 Cloudy"
                
                print(f"\n{i}. {product['tile']} - {product['date']}")
                print(f"   Cloud Cover: {product['cloud_cover']:.1f}% {status}")
                print(f"   Bands Available: {product['bands_available']}")
                print(f"   Sample Assets: {', '.join(product['assets'])}")
                
                # Show NDVI readiness for best product
                if i == 1:
                    ndvi_info = catalog.get_band_data_info(product)
                    if ndvi_info['ndvi_ready']:
                        print(f"   🎯 NDVI Ready: ✅ (Red + NIR bands available)")
                        print(f"   📥 Download authentication: Required")
                    else:
                        print(f"   🎯 NDVI Ready: ❌ (Missing bands)")
        
        else:
            print("⚠️ No products found. This could mean:")
            print("- No recent clear imagery")
            print("- Try increasing days_back or max_cloud_cover")
            print("- Check Düsseldorf coordinates")
    
    else:
        print("❌ Authentication failed")


if __name__ == "__main__":
    test_sentinel_hub_api()