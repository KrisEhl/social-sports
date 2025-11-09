"""
Real Sentinel-2 Data Access via Copernicus Data Space Ecosystem
===============================================================

This module provides access to real Sentinel-2 satellite data for calisthenics park detection.
Two approaches: 1) Direct API access, 2) Local/cached data integration
"""

import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import os
from pathlib import Path
# import rasterio  # Optional - only for real data downloads
# from rasterio.windows import from_bounds
import warnings
warnings.filterwarnings('ignore')


class Sentinel2DataAccess:
    """
    Access real Sentinel-2 data from Copernicus Data Space Ecosystem.
    
    Two methods:
    1. Direct API access (requires authentication)
    2. Sample data download (for testing)
    """
    
    def __init__(self):
        self.api_base = "https://catalogue.dataspace.copernicus.eu"
        self.download_base = "https://zipper.dataspace.copernicus.eu"
        self.access_token = None
        
        # Cache directory for downloaded data
        self.cache_dir = Path("../data/sentinel2_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with Copernicus Data Space Ecosystem.
        
        Register for free at: https://dataspace.copernicus.eu/
        """
        try:
            auth_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
            
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
                print("✅ Successfully authenticated with Copernicus Data Space!")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def search_sentinel2_products(self, bbox: Tuple[float, float, float, float],
                                start_date: str, end_date: str,
                                max_cloud_cover: float = 20.0) -> List[Dict]:
        """
        Search for Sentinel-2 products covering the area of interest.
        
        Args:
            bbox: (west, south, east, north) in decimal degrees
            start_date: 'YYYY-MM-DD' format
            end_date: 'YYYY-MM-DD' format  
            max_cloud_cover: Maximum cloud cover percentage
            
        Returns:
            List of product metadata dictionaries
        """
        print(f"🔍 Searching Sentinel-2 products for bbox {bbox}")
        
        # Build search parameters
        search_params = {
            'collections': 'SENTINEL-2',
            'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            'datetime': f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            'limit': 10,
            'query': {
                'eo:cloud_cover': {'lt': max_cloud_cover}
            }
        }
        
        try:
            search_url = f"{self.api_base}/odata/v1/Products"
            
            # Convert to OData filter format
            west, south, east, north = bbox
            geometry_filter = f"geography'POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))'"
            
            params = {
                '$filter': f"Collection/Name eq 'SENTINEL-2' and "
                          f"ContentDate/Start ge {start_date}T00:00:00.000Z and "
                          f"ContentDate/Start le {end_date}T23:59:59.000Z and "
                          f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {max_cloud_cover}) and "
                          f"OData.CSC.Intersects(area={geometry_filter})",
                '$orderby': 'ContentDate/Start desc',
                '$top': '10'
            }
            
            response = requests.get(search_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('value', [])
                
                print(f"✅ Found {len(products)} Sentinel-2 products")
                
                # Process product metadata
                processed_products = []
                for product in products:
                    processed_products.append({
                        'id': product['Id'],
                        'name': product['Name'],
                        'date': product['ContentDate']['Start'][:10],
                        'cloud_cover': self._extract_cloud_cover(product),
                        'size_mb': product['ContentLength'] / 1024 / 1024,
                        'download_url': f"{self.download_base}/odata/v1/Products({product['Id']})/$value"
                    })
                
                return processed_products
                
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(response.text)
                return []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def _extract_cloud_cover(self, product: Dict) -> float:
        """Extract cloud cover from product attributes."""
        try:
            for attr in product.get('Attributes', []):
                if attr.get('Name') == 'cloudCover':
                    return attr.get('Value', 0)
            return 0
        except:
            return 0
    
    def download_product_bands(self, product_id: str, bands: List[str] = None,
                             bbox: Tuple[float, float, float, float] = None) -> Dict[str, np.ndarray]:
        """
        Download specific bands from a Sentinel-2 product.
        
        Args:
            product_id: Product ID from search results
            bands: List of band names (e.g., ['B04', 'B08', 'B02', 'B03'])
            bbox: Spatial subset bounds (west, south, east, north)
            
        Returns:
            Dictionary mapping band names to numpy arrays
        """
        if bands is None:
            bands = ['B04', 'B08']  # Red and NIR for NDVI
            
        print(f"📥 Downloading bands {bands} for product {product_id}")
        
        if not self.access_token:
            print("❌ Not authenticated! Call authenticate() first.")
            return {}
        
        downloaded_bands = {}
        
        for band in bands:
            try:
                # Download band data
                band_url = f"{self.download_base}/odata/v1/Products({product_id})/Nodes('{band}.jp2')/$value"
                
                headers = {'Authorization': f'Bearer {self.access_token}'}
                response = requests.get(band_url, headers=headers, stream=True, timeout=60)
                
                if response.status_code == 200:
                    # Save to cache
                    cache_file = self.cache_dir / f"{product_id}_{band}.jp2"
                    
                    with open(cache_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    # Read with rasterio
                    with rasterio.open(cache_file) as src:
                        if bbox:
                            # Read spatial subset
                            window = from_bounds(*bbox, src.transform)
                            data = src.read(1, window=window)
                        else:
                            # Read full image
                            data = src.read(1)
                        
                        # Convert to reflectance (divide by 10000)
                        data = data.astype(np.float32) / 10000.0
                        downloaded_bands[band] = data
                        
                        print(f"✅ Downloaded {band}: {data.shape} pixels")
                        
                else:
                    print(f"❌ Failed to download {band}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error downloading {band}: {e}")
        
        return downloaded_bands
    
    def get_sample_data_dusseldorf(self) -> Dict[str, np.ndarray]:
        """
        Get sample Sentinel-2 data for Düsseldorf area.
        
        This uses pre-downloaded sample data or generates realistic synthetic data
        for testing when real API access is not available.
        """
        print("📋 Loading sample Sentinel-2 data for Düsseldorf...")
        
        # Check if we have cached real data
        sample_files = list(self.cache_dir.glob("*_B*.jp2"))
        
        if sample_files:
            print("✅ Found cached Sentinel-2 data")
            # Load from cache
            bands = {}
            for file in sample_files:
                band_name = file.stem.split('_')[-1]
                with rasterio.open(file) as src:
                    bands[band_name] = src.read(1).astype(np.float32) / 10000.0
            return bands
        
        else:
            print("⚠️ No cached data, generating realistic sample data")
            return self._generate_realistic_sample_data()
    
    def _generate_realistic_sample_data(self) -> Dict[str, np.ndarray]:
        """Generate realistic Sentinel-2 data based on Düsseldorf characteristics."""
        
        # 1km x 1km area at 10m resolution = 100x100 pixels
        size = 100
        
        # Generate realistic spectral signatures
        np.random.seed(42)  # Reproducible
        
        # Base urban/vegetation mix
        vegetation_mask = np.random.random((size, size)) > 0.3  # 70% vegetation
        
        # B04 (Red) - vegetation: 0.03-0.06, urban: 0.12-0.18
        red_band = np.where(vegetation_mask, 
                           np.random.normal(0.04, 0.01, (size, size)),
                           np.random.normal(0.15, 0.03, (size, size)))
        
        # B08 (NIR) - vegetation: 0.4-0.6, urban: 0.2-0.3  
        nir_band = np.where(vegetation_mask,
                           np.random.normal(0.5, 0.05, (size, size)),
                           np.random.normal(0.25, 0.03, (size, size)))
        
        # B02 (Blue) and B03 (Green) for visualization
        blue_band = np.where(vegetation_mask,
                            np.random.normal(0.02, 0.005, (size, size)),
                            np.random.normal(0.12, 0.02, (size, size)))
        
        green_band = np.where(vegetation_mask,
                             np.random.normal(0.03, 0.01, (size, size)),
                             np.random.normal(0.13, 0.02, (size, size)))
        
        # Add some fitness equipment areas (low NDVI signatures)
        equipment_centers = [(20, 30), (45, 70), (75, 85)]
        
        for cx, cy in equipment_centers:
            # Create equipment signature: higher red, lower NIR
            y1, y2 = max(0, cy-5), min(size, cy+5)
            x1, x2 = max(0, cx-5), min(size, cx+5)
            
            red_band[y1:y2, x1:x2] = np.random.normal(0.3, 0.05, (y2-y1, x2-x1))
            nir_band[y1:y2, x1:x2] = np.random.normal(0.2, 0.03, (y2-y1, x2-x1))
        
        # Clip values to valid range
        bands = {
            'B02': np.clip(blue_band, 0, 1),
            'B03': np.clip(green_band, 0, 1),
            'B04': np.clip(red_band, 0, 1),
            'B08': np.clip(nir_band, 0, 1)
        }
        
        print("✅ Generated realistic sample data:")
        for band, data in bands.items():
            print(f"   {band}: {data.shape}, range {data.min():.3f}-{data.max():.3f}")
        
        return bands


def test_sentinel2_access():
    """Test Sentinel-2 data access capabilities."""
    print("🧪 Testing Sentinel-2 Data Access")
    print("=" * 40)
    
    s2_access = Sentinel2DataAccess()
    
    # Düsseldorf bounding box
    dusseldorf_bbox = (6.7, 51.15, 6.9, 51.3)  # west, south, east, north
    
    # Test 1: Search for products (without authentication)
    print("\n1️⃣ Testing product search...")
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    products = s2_access.search_sentinel2_products(
        bbox=dusseldorf_bbox,
        start_date=start_date,
        end_date=end_date,
        max_cloud_cover=30.0
    )
    
    if products:
        print(f"✅ Found {len(products)} products:")
        for i, product in enumerate(products[:3], 1):
            print(f"{i}. {product['name']}")
            print(f"   Date: {product['date']}")
            print(f"   Cloud cover: {product['cloud_cover']:.1f}%")
            print(f"   Size: {product['size_mb']:.0f} MB")
    else:
        print("⚠️ No products found or API unavailable")
    
    # Test 2: Load sample data
    print(f"\n2️⃣ Testing sample data access...")
    sample_bands = s2_access.get_sample_data_dusseldorf()
    
    if sample_bands:
        print(f"✅ Loaded {len(sample_bands)} spectral bands")
        
        # Calculate NDVI
        if 'B04' in sample_bands and 'B08' in sample_bands:
            red = sample_bands['B04']
            nir = sample_bands['B08']
            
            ndvi = (nir - red) / (nir + red + 1e-6)
            
            print(f"\n📊 NDVI Analysis:")
            print(f"   Range: {ndvi.min():.3f} to {ndvi.max():.3f}")
            print(f"   Mean: {ndvi.mean():.3f}")
            
            # Equipment detection
            equipment_areas = (ndvi < 0.3) & (ndvi > -0.2)
            equipment_pixels = np.sum(equipment_areas)
            
            print(f"   Equipment pixels: {equipment_pixels} ({equipment_pixels/ndvi.size*100:.1f}%)")
    
    # Test 3: Show how to authenticate for real data
    print(f"\n3️⃣ Authentication info:")
    print("To access real Sentinel-2 data:")
    print("1. Register at https://dataspace.copernicus.eu/")
    print("2. Call s2_access.authenticate(username, password)")
    print("3. Use s2_access.download_product_bands(product_id)")
    
    return sample_bands


if __name__ == "__main__":
    bands = test_sentinel2_access()