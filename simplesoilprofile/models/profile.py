"""Soil profile model representing a vertical arrangement of soil layers."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, model_validator
from shapely.geometry import Point
from .layer import SoilLayer


class SoilProfile(BaseModel):
    """A soil profile composed of layers with spatial information.
    
    This class represents a vertical soil profile with multiple layers and their
    depths, along with spatial coordinates for quasi-3D positioning.
    """

    model_config = {
        'arbitrary_types_allowed': True,
    }

    name: str = Field(..., description="Name or identifier of the soil profile")
    description: Optional[str] = Field(None, description="Description of the soil profile")
    
    # Spatial location
    location: Optional[Point] = Field(None, description="Spatial location of the profile as a Point object (x, y coordinates)")
    elevation: Optional[float] = Field(None, description="Z coordinate (elevation) of the profile surface [m]")
    
    # Layers and their depths
    layers: List[SoilLayer] = Field(..., description="List of soil layers in the profile")
    layer_depths: Dict[int, tuple[float, float]] = Field(
        ..., 
        description="Dictionary mapping layer index to (top, bottom) depth pairs [cm]"
    )

    @model_validator(mode='after')
    def validate_layer_depths(self) -> 'SoilProfile':
        """Validate that layer depths are consistent and continuous."""
        if not self.layer_depths:
            raise ValueError("Layer depths cannot be empty")
        
        # Check that we have depths for all layers
        if set(self.layer_depths.keys()) != set(range(len(self.layers))):
            raise ValueError("Must provide depths for all layers and only existing layers")
        
        # Sort depths by layer index and check continuity
        sorted_depths = sorted(self.layer_depths.items(), key=lambda x: x[0])
        prev_bottom = None
        
        for layer_idx, (top, bottom) in sorted_depths:
            # Check individual layer validity
            if top >= bottom:
                raise ValueError(f"Layer {layer_idx}: top depth must be less than bottom depth")
            
            # Check continuity with previous layer
            if prev_bottom is not None and abs(top - prev_bottom) > 0.001:  # Allow small floating point differences
                raise ValueError(f"Gap detected between layers {layer_idx-1} and {layer_idx}")
            
            prev_bottom = bottom
        
        return self
    
    def get_layer_at_depth(self, depth: float) -> Optional[tuple[SoilLayer, int]]:
        """Get the soil layer at a specific depth.
        
        Args:
            depth: The depth in cm from the surface
            
        Returns:
            A tuple of (SoilLayer, layer_index) if a layer exists at that depth,
            None otherwise.
        """
        for idx, (top, bottom) in self.layer_depths.items():
            if top <= depth <= bottom:
                return (self.layers[idx], idx)
        return None
    
    def get_profile_depth(self) -> float:
        """Get the total depth of the profile in cm."""
        if not self.layer_depths:
            return 0.0
        return max(bottom for _, bottom in self.layer_depths.values())
    
    def get_sublayer_boundaries(self) -> Dict[int, List[float]]:
        """Get all sublayer boundaries for each layer in the profile.
        
        Returns:
            Dictionary mapping layer index to a list of boundary depths [cm].
            Each boundary list includes both the top and bottom of the layer.
        """
        boundaries = {}
        for idx, (top, bottom) in self.layer_depths.items():
            boundaries[idx] = self.layers[idx].get_sublayer_boundaries(top, bottom)
        return boundaries
    
    def get_sublayer_depths(self) -> List[float]:
        """Get a sorted list of all sublayer boundary depths in the profile.
        
        This is useful for plotting or numerical computations that need all
        discretization points across the entire profile.
        
        Returns:
            Sorted list of unique boundary depths [cm] from top to bottom.
        """
        # Get all boundaries and flatten into a single list
        all_depths = []
        for depths in self.get_sublayer_boundaries().values():
            all_depths.extend(depths)
        
        # Remove duplicates and sort
        return sorted(list(set(all_depths)))