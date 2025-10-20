"""Client for the Belgian DOV (Databank Ondergrond Vlaanderen) API."""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
import jsonpath_ng
from ..models import SoilLayer, SoilProfile
from .config import APIMapping


class DOVClient:
    """Client for fetching soil data from the Belgian DOV API."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the DOV client.
        
        Args:
            config_path: Path to the YAML configuration file. If None, uses default config.
        """
        if config_path is None:
            config_path = Path(__file__).parent / "configs" / "dov.yaml"
        
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
        
        self.config = APIMapping(**config_dict)
    
    def _extract_value(self, data: Dict[str, Any], jsonpath: str) -> Any:
        """Extract a value from the response data using a JSONPath expression.
        
        Args:
            data: Response data dictionary
            jsonpath: JSONPath expression for the value
            
        Returns:
            Extracted value or None if not found
        """
        jsonpath_expr = jsonpath_ng.parse(jsonpath)
        matches = jsonpath_expr.find(data)
        return matches[0].value if matches else None
    
    def _transform_value(self, field: str, data: Dict[str, Any]) -> Any:
        """Transform a value using the configured transformation expression.
        
        Args:
            field: Field name to transform
            data: Response data dictionary
            
        Returns:
            Transformed value
        """
        if field not in self.config.transformations:
            return None
            
        expr = self.config.transformations[field]
        try:
            return eval(expr, {"data": data, "exp": __import__("math").exp})
        except Exception as e:
            raise ValueError(f"Error transforming field {field}: {str(e)}")
    
    def _create_soil_layer(self, layer_data: Dict[str, Any]) -> SoilLayer:
        """Create a SoilLayer instance from API response data.
        
        Args:
            layer_data: Layer data from the API response
            
        Returns:
            SoilLayer instance
        """
        layer_dict = {}
        
        # Extract mapped fields
        for field, jsonpath in self.config.field_mappings.items():
            value = self._extract_value(layer_data, jsonpath)
            if value is not None:
                layer_dict[field] = value
        
        # Apply transformations
        for field in ["theta_res", "theta_sat", "alpha", "n", "k_sat", "l"]:
            value = self._transform_value(field, layer_data)
            if value is not None:
                layer_dict[field] = value
        
        return SoilLayer(**layer_dict)
    
    def fetch_profile(self, profile_id: str) -> SoilProfile:
        """Fetch a soil profile from the DOV API.
        
        Args:
            profile_id: ID of the profile to fetch
            
        Returns:
            SoilProfile instance
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the response data is invalid
        """
        # Prepare request
        url = f"{self.config.base_url}{self.config.endpoint}/{profile_id}"
        response = requests.get(
            url,
            params=self.config.params,
            headers=self.config.headers
        )
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Extract layers
        layers_expr = jsonpath_ng.parse(self.config.layer_path)
        layers_data = [match.value for match in layers_expr.find(data)]
        
        if not layers_data:
            raise ValueError(f"No layers found in profile {profile_id}")
        
        # Create profile
        profile_dict = {
            "name": str(profile_id),
            "layers": [self._create_soil_layer(layer) for layer in layers_data],
            "layer_depths": {}  # Will be filled from depth data
        }
        
        # Extract coordinates if available
        for coord in ["x", "y", "z"]:
            if coord in self.config.coordinates:
                value = self._extract_value(data, self.config.coordinates[coord])
                if value is not None:
                    profile_dict[coord] = float(value)
        
        # Extract layer depths (assuming they're in the layer data)
        for i, layer_data in enumerate(layers_data):
            top = float(self._extract_value(layer_data, "$.depth_from") or 0)
            bottom = float(self._extract_value(layer_data, "$.depth_to") or 0)
            profile_dict["layer_depths"][i] = (top, bottom)
        
        return SoilProfile(**profile_dict)