"""
Simple Sentinel-2 Test WITHOUT Rasterio Dependencies
====================================================

Test authentication and product search first, before adding complex dependencies.
"""

import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class SimpleSentinel2Access:
    """Simplified Sentinel-2 access for testing authentication and search."""
    
    def __init__(self):
        self.api_base = "https://catalogue.dataspace.copernicus.eu"
        self.access_token = None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Copernicus Data Space Ecosystem."""
        try:
            print(f"🔐 Authenticating user: {username}")
            
            auth_url = ("https://identity.dataspace.copernicus.eu/auth/realms/"
                       "CDSE/protocol/openid-connect/token")
            
            auth_data = {
                'grant_type': 'password',
                'username': username,
                'password': password,
                'client_id': 'cdse-public'
            }
            
            response = requests.post(auth_url, data=auth_data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                
                # Token info
                expires_in = token_data.get('expires_in', 0)
                print(f"✅ Authentication successful!")
                print(f"🕒 Token expires in: {expires_in} seconds")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def search_products_dusseldorf(self, days_back: int = 30,
                                  max_cloud: float = 20.0) -> List[Dict]:
        """Search for recent Sentinel-2 products over Düsseldorf."""
        
        print(f"🔍 Searching Sentinel-2 products for Düsseldorf")
        print(f"   Last {days_back} days, max {max_cloud}% cloud cover")
        
        # Düsseldorf bounding box (slightly expanded)
        west, south = 6.65, 51.10
        east, north = 6.95, 51.35
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            search_url = f"{self.api_base}/odata/v1/Products"
            
            # Create geometry filter for Düsseldorf
            geometry = (f"geography'POLYGON(({west} {south},"
                       f"{east} {south},{east} {north},"
                       f"{west} {north},{west} {south}))'")
            
            # Build OData filter
            filter_parts = [
                "Collection/Name eq 'SENTINEL-2'",
                f"ContentDate/Start ge {start_date.strftime('%Y-%m-%d')}T00:00:00.000Z",
                f"ContentDate/Start le {end_date.strftime('%Y-%m-%d')}T23:59:59.000Z",
                f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {max_cloud})",
                f"OData.CSC.Intersects(area={geometry})"
            ]
            
            params = {
                '$filter': ' and '.join(filter_parts),
                '$orderby': 'ContentDate/Start desc',
                '$top': '5',
                '$select': 'Id,Name,ContentDate,ContentLength,Attributes'
            }
            
            response = requests.get(search_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('value', [])
                
                print(f"✅ Found {len(products)} suitable products")
                
                # Process results
                processed = []
                for product in products:
                    cloud_cover = self._extract_cloud_cover(product)
                    size_gb = product['ContentLength'] / 1024 / 1024 / 1024
                    
                    processed.append({
                        'id': product['Id'],
                        'name': product['Name'],
                        'date': product['ContentDate']['Start'][:10],
                        'cloud_cover': cloud_cover,
                        'size_gb': round(size_gb, 2),
                        'suitable_for_analysis': cloud_cover <= max_cloud
                    })
                
                return processed
                
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def _extract_cloud_cover(self, product: Dict) -> float:
        """Extract cloud cover percentage from product."""
        try:
            for attr in product.get('Attributes', []):
                if attr.get('Name') == 'cloudCover':
                    return round(attr.get('Value', 0), 1)
            return 0.0
        except:
            return 0.0
    
    def get_product_download_info(self, product_id: str) -> Dict:
        """Get download information for a product."""
        if not self.access_token:
            return {'error': 'Not authenticated'}
        
        try:
            # Get product details
            product_url = f"{self.api_base}/odata/v1/Products({product_id})"
            
            response = requests.get(product_url, timeout=30)
            
            if response.status_code == 200:
                product = response.json()
                
                download_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
                
                return {
                    'product_id': product_id,
                    'name': product['Name'],
                    'size_gb': round(product['ContentLength'] / 1024 / 1024 / 1024, 2),
                    'download_url': download_url,
                    'requires_auth': True,
                    'auth_header': f"Authorization: Bearer {self.access_token[:20]}..."
                }
            else:
                return {'error': f'Product info failed: {response.status_code}'}
                
        except Exception as e:
            return {'error': str(e)}


def test_real_sentinel2_access():
    """Interactive test for real Sentinel-2 access."""
    print("🧪 Testing Real Sentinel-2 Access")
    print("=" * 40)
    
    s2 = SimpleSentinel2Access()
    
    # Get credentials
    print("\n📝 Enter your Copernicus Data Space credentials:")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    if not username or not password:
        print("❌ Username and password required!")
        return
    
    # Test authentication
    print(f"\n🔐 Testing authentication...")
    if s2.authenticate(username, password):
        print("✅ Ready to access Sentinel-2 data!")
        
        # Search for products
        print(f"\n🔍 Searching for recent Düsseldorf imagery...")
        products = s2.search_products_dusseldorf(days_back=14, max_cloud=30)
        
        if products:
            print(f"\n📋 Available products:")
            for i, product in enumerate(products, 1):
                status = "✅ Good" if product['suitable_for_analysis'] else "⚠️ Cloudy"
                print(f"{i}. {product['name'][:50]}...")
                print(f"   Date: {product['date']} | Cloud: {product['cloud_cover']}% | Size: {product['size_gb']}GB")
                print(f"   Status: {status}")
                print()
            
            # Show download info for best product
            best_product = min(products, key=lambda x: x['cloud_cover'])
            print(f"🏆 Best product (lowest cloud cover):")
            print(f"   ID: {best_product['id']}")
            
            download_info = s2.get_product_download_info(best_product['id'])
            if 'error' not in download_info:
                print(f"   Download URL ready: ✅")
                print(f"   Size: {download_info['size_gb']}GB")
                print(f"   Authentication: Required")
            
        else:
            print("⚠️ No suitable products found. Try:")
            print("- Increase days_back parameter")
            print("- Increase max_cloud_cover")
            print("- Check if Düsseldorf area is correct")
    
    else:
        print("❌ Authentication failed. Check:")
        print("- Username/password correct?")
        print("- Account activated?") 
        print("- Network connection?")


if __name__ == "__main__":
    test_real_sentinel2_access()