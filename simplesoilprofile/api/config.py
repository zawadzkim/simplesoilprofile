"""Base configuration model for API integrations."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class APIMapping(BaseModel):
    """Mapping configuration for converting API response to SoilProfile attributes."""
    
    # API endpoint configuration
    base_url: str = Field(..., description="Base URL for the API")
    endpoint: str = Field(..., description="Specific endpoint for soil data")
    method: str = Field("GET", description="HTTP method to use")
    
    # Parameters and headers
    params: Dict[str, str] = Field(default_factory=dict, description="Query parameters")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    
    # Response mapping
    response_type: str = Field(..., description="Response format (json, xml, etc.)")
    layer_path: str = Field(..., description="JSON path to array of soil layers")
    
    # Field mappings for SoilLayer attributes
    field_mappings: Dict[str, str] = Field(
        ...,
        description="Mapping of API response fields to SoilLayer attributes"
    )
    
    # Optional transformations
    transformations: Dict[str, str] = Field(
        default_factory=dict,
        description="Python expressions for transforming values"
    )
    
    # Coordinates mapping
    coordinates: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping for x, y, z coordinates in the response"
    )