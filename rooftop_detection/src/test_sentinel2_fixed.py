"""
Fixed Sentinel-2 Search with Correct OData Syntax
=================================================
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List


class FixedSentinel2Search:
    """Fixed version with correct OData query syntax."""
    
    def __init__(self):
        self.api_base = "https://catalogue.dataspace.copernicus.eu"
        self.access_token = None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Copernicus Data Space."""
        try:
            print(f"🔐 Authenticating...")
            
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
                print("✅ Authentication successful!")
                return True
            else:
                print(f"❌ Auth failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Auth error: {e}")
            return False
    
    def search_simple(self, days_back: int = 7) -> List[Dict]:
        """Simplified search without complex geometry."""
        
        print(f"🔍 Searching Sentinel-2 products (last {days_back} days)")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            search_url = f"{self.api_base}/odata/v1/Products"
            
            # Simplified filter - just collection and date
            params = {
                '$filter': (f"Collection/Name eq 'SENTINEL-2' and "
                           f"ContentDate/Start ge {start_date.strftime('%Y-%m-%d')}T00:00:00.000Z"),
                '$orderby': 'ContentDate/Start desc',
                '$top': '10'
            }
            
            response = requests.get(search_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('value', [])
                
                print(f"✅ Found {len(products)} products")
                
                # Filter for Düsseldorf area manually
                dusseldorf_products = []
                
                for product in products:
                    name = product.get('Name', '')
                    
                    # Sentinel-2 naming: S2A_MSIL1C_20231108T103031_N0509_R108_T32ULC_20231108T124649
                    # T32ULC is the tile that covers Düsseldorf
                    if 'T32UL' in name:  # Covers Düsseldorf area
                        cloud_cover = self._extract_cloud_cover(product)
                        
                        dusseldorf_products.append({
                            'id': product['Id'],
                            'name': name,
                            'date': product['ContentDate']['Start'][:10],
                            'cloud_cover': cloud_cover,
                            'tile': self._extract_tile(name),
                            'size_gb': round(product['ContentLength'] / 1024**3, 2)
                        })
                
                print(f"🎯 Düsseldorf area products: {len(dusseldorf_products)}")
                return dusseldorf_products
                
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(response.text[:300])
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def _extract_cloud_cover(self, product: Dict) -> float:
        """Extract cloud cover from product attributes."""
        try:
            for attr in product.get('Attributes', []):
                if attr.get('Name') == 'cloudCover':
                    return round(attr.get('Value', 0), 1)
            return 0.0
        except:
            return 0.0
    
    def _extract_tile(self, name: str) -> str:
        """Extract tile ID from product name."""
        parts = name.split('_')
        for part in parts:
            if part.startswith('T') and len(part) == 6:  # e.g., T32ULC
                return part
        return 'Unknown'
    
    def get_download_link(self, product_id: str) -> str:
        """Get direct download link for a product."""
        if not self.access_token:
            return "❌ Not authenticated"
        
        download_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
        return f"✅ Ready: {download_url}"


def quick_test():
    """Quick test with your credentials."""
    print("🚀 Quick Sentinel-2 Test")
    print("=" * 30)
    
    s2 = FixedSentinel2Search()
    
    # Use your credentials directly (since they worked)
    username = "christopher-george@web.de"
    password = "***REMOVED***"
    
    if s2.authenticate(username, password):
        # Search for recent products
        products = s2.search_simple(days_back=14)
        
        if products:
            print(f"\n📊 Results:")
            for i, product in enumerate(products[:5], 1):
                status = "🟢 Clear" if product['cloud_cover'] < 10 else "🌥️ Cloudy" if product['cloud_cover'] < 30 else "☁️ Very cloudy"
                
                print(f"{i}. {product['tile']} - {product['date']}")
                print(f"   Cloud: {product['cloud_cover']}% | Size: {product['size_gb']}GB")
                print(f"   Status: {status}")
                print(f"   ID: {product['id']}")
                
                if i == 1:  # Show download link for best product
                    download_link = s2.get_download_link(product['id'])
                    print(f"   Download: {download_link}")
                print()
        
        else:
            print("⚠️ No Düsseldorf products found in last 14 days")
            print("💡 Tip: Sentinel-2 revisit time is 5 days, try longer period")
    
    else:
        print("❌ Authentication failed")


if __name__ == "__main__":
    quick_test()