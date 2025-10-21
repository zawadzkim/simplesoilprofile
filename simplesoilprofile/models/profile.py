"""Soil profile model representing a vertical arrangement of soil layers."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, model_validator
from shapely.geometry import Point
from .layer import SoilLayer
from pydantic import BaseModel, Field, model_validator, computed_field


class SoilProfile(BaseModel):
    """A soil profile composed of layers with spatial information."""

    model_config = {
        'arbitrary_types_allowed': True,
    }

    name: str = Field(..., description="Name or identifier of the soil profile")
    description: Optional[str] = Field(None, description="Description of the soil profile")
    
    location: Optional[Point] = Field(None, description="Spatial location of the profile as a Point object (x, y coordinates)")
    elevation: Optional[float] = Field(None, description="Z coordinate (elevation) of the profile surface [m]")
    
    layers: List[SoilLayer] = Field(..., description="List of soil layers in the profile")
    layer_bottoms: List[float] = Field(
        ..., 
        description="List of bottom depths for each layer [cm]. Top of first layer is assumed to be 0."
    )

    @model_validator(mode='after')
    def validate_layer_depths(self) -> 'SoilProfile':
        """Validate that layer depths are consistent and monotonically increasing."""
        if not self.layer_bottoms:
            raise ValueError("Layer depths cannot be empty")
        
        if len(self.layer_bottoms) != len(self.layers):
            raise ValueError("Must provide bottom depths for all layers")
        
        prev_depth = 0
        for i, bottom in enumerate(self.layer_bottoms):
            if bottom <= prev_depth:
                raise ValueError(f"Layer {i}: bottom depth must be greater than previous layer")
            prev_depth = bottom
        
        return self

    @computed_field
    @property
    def layer_bounds(self) -> Dict[int, tuple[float, float]]:
        """Get dictionary of (top, bottom) bounds for each layer."""
        bounds = {}
        prev_depth = 0
        for i, bottom in enumerate(self.layer_bottoms):
            bounds[i] = (prev_depth, bottom)
            prev_depth = bottom
        return bounds
    
    @computed_field
    @property
    def profile_depth(self) -> float:
        """Total depth of the profile in cm (bottom of last layer)."""
        return self.layer_bottoms[-1] if self.layer_bottoms else 0.0
    
    def get_layer_at_depth(self, depth: float) -> Optional[tuple[SoilLayer, int]]:
        """Get the soil layer at a specific depth."""
        prev_depth = 0
        for i, bottom in enumerate(self.layer_bottoms):
            if prev_depth <= depth <= bottom:
                return (self.layers[i], i)
            prev_depth = bottom
        return None
    
    def get_sublayer_boundaries(self) -> Dict[int, List[float]]:
        """Get all sublayer boundaries for each layer in the profile."""
        boundaries = {}
        prev_depth = 0
        for i, bottom in enumerate(self.layer_bottoms):
            boundaries[i] = self.layers[i].get_sublayer_boundaries(prev_depth, bottom)
            prev_depth = bottom
        return boundaries
    
    def get_sublayer_depths(self) -> List[float]:
        """Get a sorted list of all sublayer boundary depths in the profile."""
        all_depths = []
        for depths in self.get_sublayer_boundaries().values():
            all_depths.extend(depths)
        return sorted(list(set(all_depths)))
