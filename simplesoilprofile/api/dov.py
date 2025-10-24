"""Client for the Belgian DOV (Databank Ondergrond Vlaanderen) API."""

from typing import Dict, Any
from shapely.geometry import Point

from .base import WMSClient
from .geopunt import GeopuntClient
from ..models import SoilLayer, SoilProfile
from ..models.metadata import SoilLayerMetadata as M


class DOVClient(WMSClient):
    """Client for fetching soil data from the Belgian DOV API."""
    
    def __init__(self):
        """Initialize the DOV client.
        
        Connects to the DOV Geoserver WMS service for accessing soil data
        and related geological information.
        """
        super().__init__(base_url="https://www.dov.vlaanderen.be/geoserver")
    
    def list_wms_layers(self, only_soil: bool = True) -> Dict[str, str]:
        """List available WMS layers from the DOV service.
        
        Args:
            only_soil: If True, only return layers related to soil data
            
        Returns:
            Dictionary of layer names and titles
        """
        def soil_filter(name: str, title: str) -> bool:
            return not only_soil or 'bodem' in name.lower()
            
        return super().list_wms_layers(filter_func=soil_filter)
        
    def parse_feature_info(self, content: str, **kwargs) -> Any:
        """Parse GetFeatureInfo response from DOV WMS.
        
        The parsing method depends on the content type and query type:
        - For soil texture: Parses JSON response with layer properties
        - For other queries: Returns raw content for specific handling
        
        Args:
            content: Raw response content
            **kwargs: Additional parameters:
                - content_type: Expected content type
                - query_type: Type of query (e.g., 'texture', 'properties')
                
        Returns:
            Parsed content in appropriate format
        """
        content_type = kwargs.get('content_type', 'application/json')
        query_type = kwargs.get('query_type', 'properties')
        
        if content_type == 'application/json' and query_type == 'texture':
            return self._parse_texture_response(content)
            
        return content        

    def _parse_texture_response(self, data: Any) -> Dict[str, float]:
        """Parse the WMS GetFeatureInfo response to extract texture fractions.
        
        Args:
            response: WMS GetFeatureInfo response
            
        Returns:
            Dictionary with clay, silt, and sand fractions
        """
        import json
        json_data = json.loads(data)
        features = json_data.get('features', [])

        if not features:
            return {}
        
        properties = [feature.get("properties") for feature in features]

        # create Layer objects for each of the profiles
        depth_keys = [k for k in properties[0].keys() if not k.endswith('_betrouwbaarheid')]

        # Map Dutch depth notation to layer info
        depth_mapping = {
            '_0_-_10_cm': (0, 10, 'Layer_0-10cm'),
            '_10_-_30_cm': (10, 30, 'Layer_10-30cm'),
            '_30_-_60_cm': (30, 60, 'Layer_30-60cm'),
            '_60_-_100_cm': (60, 100, 'Layer_60-100cm'),
            '_100_-_150_cm': (100, 150, 'Layer_100-150cm'),
        }

        soil_layers = []
        base_mtd = M(
            source_type="modeled",
            url="https://www.dov.vlaanderen.be/geoserver/wms"
        )
        for depth_key in depth_keys:

            ci_key = f"{depth_key}_betrouwbaarheid"

            # Extract texture percentages and confidence intervals
            clay_pct = properties[0][depth_key]
            clay_mtd = base_mtd.model_copy(update={
                "source": "DOV WMS, bdbstat:fractie_klei_basisdata_bodemkartering",
                "uncertainty": properties[0][ci_key]
            })
            silt_pct = properties[1][depth_key]
            silt_mtd = base_mtd.model_copy(update={
                "source": "DOV WMS, bdbstat:fractie_leem_basisdata_bodemkartering",
                "uncertainty": properties[1][ci_key]
            })
            sand_pct = properties[2][depth_key]
            sand_mtd = base_mtd.model_copy(update={
                "source": "DOV WMS, bdbstat:fractie_zand_basisdata_bodemkartering",
                "uncertainty": properties[2][ci_key]
            })

            # Get depth info
            top_depth, bottom_depth, layer_name = depth_mapping[depth_key]

            # Create SoilLayer object
            layer = SoilLayer(
                name=layer_name,
                description=f"Soil layer from {top_depth} to {bottom_depth} cm depth",
                sand_content=sand_pct,
                silt_content=silt_pct,
                clay_content=clay_pct,
                metadata={
                    "clay_content": clay_mtd,
                    "silt_content": silt_mtd,
                    "sand_content": sand_mtd,
                }
            )
            layer.normalize_soil_fractions()
            soil_layers.append(layer)
        
        return soil_layers
    
    def fetch_profile(self, profile_name: str, location: Point, elevation: float | None = None, crs: str = "EPSG:31370") -> SoilProfile | None:
        """Fetch soil texture information from the DOV WMS at a specific location.
        
        This method queries the DOV WMS service for clay, silt, and sand content
        at different depths at the specified location. The data is used to create
        a SoilProfile object with appropriate layers.
        
        Args:
            profile_name: Name for the created soil profile
            location: Point object with x, y coordinates
            elevation: Optional elevation in meters. If None, will be fetched from Geopunt
            crs: Coordinate reference system
            
        Returns:
            SoilProfile object with texture data or None if data not found
            
        Note:
            The texture data can also be visualized using WMS GetMap requests, e.g.:
            >>> img = self.wms.getmap(
            >>>     layers=['bdbstat:fractie_zand_basisdata_bodemkartering'],
            >>>     styles=[''],
            >>>     srs='EPSG:31370',
            >>>     bbox=bbox,
            >>>     size=(800, 800),
            >>>     format='image/png',
            >>>     transparent=True
            >>> )
        """
        # Define texture layers
        layers = [
            "bdbstat:fractie_klei_basisdata_bodemkartering",  # clay
            "bdbstat:fractie_leem_basisdata_bodemkartering",  # silt
            "bdbstat:fractie_zand_basisdata_bodemkartering",  # sand
        ]
        
        # Verify layers exist
        for layer in layers:
            if not self.check_layer_exists(layer):
                print(f"Layer {layer} not found")
                return None
        
        # Define query area
        buffer = 0.0001
        bbox = (
            location.x - buffer, location.y - buffer,
            location.x + buffer, location.y + buffer
        )
        
        try:
            # Query texture data
            response = self.wms.getfeatureinfo(
                layers=layers,
                query_layers=layers,
                srs=crs,
                bbox=bbox,
                size=(100, 100),
                info_format='application/json',
                xy=(50, 50)  # center pixel
            )
            
            # Parse response using the base class method
            layers = self.parse_feature_info(
                response.read(), 
                content_type='application/json',
                query_type='texture'
            )
            
            # Fetch elevation if not provided
            if elevation is None:
                client = GeopuntClient()
                elevation = client.fetch_elevation(location, crs)
            
            # Create profile
            profile = SoilProfile(
                name=profile_name,
                location=location,
                elevation=elevation,
                layers=layers,
                layer_bottoms=[10, 30, 60, 100, 150],
            )
            
            return profile
            
        except Exception as e:
            print(f"Error fetching texture data: {str(e)}")
            return None


def get_profile_from_dov(
    x: float,
    y: float,
    profile_name: str | None = None,
    crs: str = "EPSG:31370",
    elevation: bool = True,
    predict_vg: bool = True
) -> SoilProfile | None:
    """Convenience function to fetch a soil profile from DOV at given coordinates.
    
    This function handles all the necessary client setup and coordinate conversion
    to get a soil profile from the DOV service. It's a simpler alternative to
    creating and managing DOV and Geopunt clients manually.
    
    Args:
        x: X-coordinate in the specified CRS (default Lambert72)
        y: Y-coordinate in the specified CRS (default Lambert72)
        profile_name: Optional name for the profile. If None, will use coordinates
        crs: Coordinate reference system of the input coordinates
        elevation: elevation data
        
    Returns:
        SoilProfile object with texture and optional elevation data,
        or None if the data couldn't be fetched
        
    Example:
        >>> profile = get_profile_from_dov(247172.56, 204590.58)
        >>> print(f"Elevation: {profile.elevation:.2f}m")
        >>> print(f"Number of layers: {len(profile.layers)}")
    """
    try:
        # Create location point
        location = Point(x, y)
        
        # Use coordinates for profile name if none provided
        if profile_name is None:
            profile_name = f"Profile_{x:.0f}_{y:.0f}"
            
        # Create DOV client
        client = DOVClient()
        
        # Fetch profile (elevation will be automatically fetched if include_elevation is True)
        profile = client.fetch_profile(
            profile_name=profile_name,
            location=location,
            elevation=elevation or 0.0,
            crs=crs
        )

        if predict_vg:
            [layer.predict_van_genuchten("rosetta") for layer in profile.layers]
        
        return profile
        
    except Exception as e:
        print(f"Error fetching profile from DOV: {str(e)}")
        return None

        