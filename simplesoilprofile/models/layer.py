"""Soil layer model representing a single layer with physical properties."""

from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

from .discretization import LayerDiscretization, compute_sublayer_boundaries


class SoilLayer(BaseModel):
    """A soil layer with uniform properties.
    
    This class represents a soil layer with van Genuchten parameters and other
    properties needed for hydrological modeling, particularly for SWAP model
    integration. The layer can be discretized into sublayers for numerical computation.
    """

    name: str = Field(..., description="Name or identifier of the soil layer")
    discretization: Optional[LayerDiscretization] = Field(
        None, description="Configuration for layer discretization into sublayers"
    )
    description: Optional[str] = Field(None, description="Description of the soil layer")
    
    # Van Genuchten parameters
    theta_res: float = Field(..., description="Residual water content [cm³/cm³]", ge=0.0, le=1.0)
    theta_sat: float = Field(..., description="Saturated water content [cm³/cm³]", ge=0.0, le=1.0)
    alpha: float = Field(..., description="Shape parameter alpha [1/cm]", gt=0.0)
    n: float = Field(..., description="Shape parameter n [-]", gt=1.0)
    k_sat: float = Field(..., description="Saturated hydraulic conductivity [cm/day]", gt=0.0)
    l: float = Field(0.5, description="Tortuosity parameter lambda [-]")

    # Additional physical properties
    texture_class: Optional[str] = Field(None, description="Soil texture class (e.g., 'sand', 'clay', etc.)")
    clay_content: Optional[float] = Field(None, description="Clay content [%]", ge=0.0, le=100.0)
    silt_content: Optional[float] = Field(None, description="Silt content [%]", ge=0.0, le=100.0)
    sand_content: Optional[float] = Field(None, description="Sand content [%]", ge=0.0, le=100.0)
    organic_matter: Optional[float] = Field(None, description="Organic matter content [%]", ge=0.0)
    bulk_density: Optional[float] = Field(None, description="Bulk density [g/cm³]", gt=0.0)

    @model_validator(mode='after')
    def validate_texture_composition(self) -> 'SoilLayer':
        """Ensure clay, silt, and sand contents do not sum to more than 100% when all provided."""
        if all(v is not None for v in (self.clay_content, self.silt_content, self.sand_content)):
            total = self.clay_content + self.silt_content + self.sand_content
            if total > 100.0 + 0.1:  # Allow small rounding tolerance
                raise ValueError("Clay, silt, and sand contents must not exceed 100% in total")
        return self

    @model_validator(mode='after')
    def validate_water_contents(self) -> 'SoilLayer':
        """Validate that residual water content is less than saturated water content."""
        if self.theta_res >= self.theta_sat:
            raise ValueError("Residual water content must be less than saturated water content")
        return self

    def get_sublayer_boundaries(self, top: float, bottom: float) -> List[float]:
        """Get the sublayer boundary depths for this layer.
        
        Args:
            top: Top depth of the layer [cm]
            bottom: Bottom depth of the layer [cm]
            
        Returns:
            List of boundary depths [cm], including top and bottom depths.
            If no discretization is configured, returns [top, bottom].
        """
        if self.discretization is None:
            return [top, bottom]
        
        return compute_sublayer_boundaries(top, bottom, self.discretization)