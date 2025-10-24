from typing import Optional
from shapely.geometry import Point

from .base import WMSClient


class GeopuntClient(WMSClient):
    """Client for fetching data from the Geopunt API."""
    
    def __init__(self):
        super().__init__(base_url='https://geo.api.vlaanderen.be/DHMV')

    def parse_feature_info(self, content: str, **kwargs) -> Optional[float]:
        """Parse GetFeatureInfo response from Geopunt WMS.
        
        The parsing method depends on the content type and query type:
        - For elevation: Parses semicolon-separated response for elevation value
        - For other queries: Returns raw content for specific handling
        
        Args:
            content: Raw response content
            **kwargs: Additional parameters:
                - content_type: Expected content type
                - query_type: Type of query (e.g., 'elevation')
                
        Returns:
            Parsed content in appropriate format
        """
        query_type = kwargs.get('query_type', 'elevation')
        
        if query_type == 'elevation':
            return self._parse_elevation_response(content)
            
        return content

    def _parse_elevation_response(self, content: str) -> Optional[float]:
        """Parse elevation data from GetFeatureInfo response.
        
        Args:
            content: Raw response content from WMS GetFeatureInfo
            
        Returns:
            Elevation in meters or None if parsing fails
            
        Note:
            Response format example:
            "@DHMVII_DTM_1m Stretched value;Pixel Value; 32.360001;32.360001;"
        """
        try:
            values = content.strip().split(';')
            if len(values) >= 3:
                return float(values[2].strip())
        except (ValueError, IndexError) as e:
            print(f"Error parsing elevation data: {str(e)}")
        return None

    def fetch_elevation(self, location: Point, crs: str = "EPSG:31370", layer_name: str = "DHMVII_DTM_1m") -> float | None:
        """Fetch elevation data from the Geopunt WMS at a specific location.
        
        Args:
            location: Point object with x, y coordinates
            crs: Coordinate reference system
        Returns:
            Elevation in meters or None if not found
        """
        # Layer name for Digital Terrain Model (1m resolution)
        
        if not self.check_layer_exists(layer_name):
            print(f"Layer {layer_name} not found. Available layers: {list(self.wms.contents.keys())}")
            return None
        
        buffer = 0.0001
        bbox = (location.x - buffer, location.y - buffer, location.x + buffer, location.y + buffer)
        
        # Image size and center pixel
        img_width = img_height = 256
        pixel_x = pixel_y = img_width // 2
        
        try:
            # Make GetFeatureInfo request
            response = self.wms.getfeatureinfo(
                layers=[layer_name],
                query_layers=[layer_name],
                info_format='text/plain',
                srs=crs,
                bbox=bbox,
                size=(img_width, img_height),
                xy=(pixel_x, pixel_y)
            )
            
            # Parse response using the base class method
            content = response.read().decode('utf-8')
            elevation = self.parse_feature_info(
                content,
                content_type='text/plain',
                query_type='elevation'
            )
            
            if elevation is not None:
                print("Fetched elevation from Geopunt API")
            
            return elevation
            
        except Exception as e:
            print(f"Error fetching elevation: {str(e)}")
            return None
