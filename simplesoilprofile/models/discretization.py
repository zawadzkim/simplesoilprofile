"""Layer discretization models and utilities."""

from enum import Enum

import numpy as np
from pydantic import BaseModel, Field, computed_field, model_validator


class DiscretizationType(str, Enum):
    """Types of layer discretization methods."""

    EVEN = "even"
    LOG_TOP = "logarithmic_top"
    LOG_BOTTOM = "logarithmic_bottom"
    LOG_BOTH = "logarithmic_both"

class LayerDiscretization(BaseModel):
    """Configuration for layer discretization."""

    type: DiscretizationType = Field(
        ...,
        description="Type of discretization to apply"
    )
    num_sublayers: int = Field(
        ...,
        description="Number of sublayers to create",
        gt=0
    )
    num_compartments: int = Field(
        ...,
        description="Number of compartments to create",
        gt=0
    )
    log_density: float = Field(
        1.0,
        description="Density parameter for logarithmic spacing (higher = more dense)",
        gt=0
    )

    @model_validator(mode='after')
    def validate_discretization(self) -> 'LayerDiscretization':
        """Validate discretization parameters."""
        if self.type != DiscretizationType.EVEN and self.log_density <= 0:
            raise ValueError("log_density must be positive for logarithmic discretization")
        return self

    @computed_field
    @property
    def compartment_heights(self) -> list[float]:
        """Get the ordered list of compartment heights for this discretization.
        
        The heights are calculated based on the discretization type and parameters.
        The order is from top to bottom of the layer.
        
        Returns:
            List of compartment heights [cm] in order from top to bottom.
            For EVEN discretization, all heights are equal.
            For logarithmic discretizations, heights vary according to the spacing function.
        """
        # Get sublayer boundaries for a unit thickness (1cm) layer
        # (we'll use the ratios, actual heights will be scaled by layer thickness)
        boundaries = compute_sublayer_boundaries(0, 1, self)
        heights = list(np.diff(boundaries))
        return heights

def compute_sublayer_boundaries(
    top: float,
    bottom: float,
    discretization: LayerDiscretization
) -> list[float]:
    """Compute sublayer boundaries based on discretization configuration.
    
    Args:
        top: Top depth of the layer [cm]
        bottom: Bottom depth of the layer [cm]
        discretization: Discretization configuration
        
    Returns:
        List of boundary depths [cm], including top and bottom
    """
    thickness = bottom - top
    n = discretization.num_sublayers

    if discretization.type == DiscretizationType.EVEN:
        # Simple linear spacing
        return list(np.linspace(top, bottom, n + 1))

    elif discretization.type == DiscretizationType.LOG_TOP:
        # Logarithmic spacing with finer discretization at the top
        # Use exponential function to create non-uniform spacing
        positions = np.exp(np.linspace(0, discretization.log_density, n + 1)) - 1
        positions = positions / positions[-1]  # normalize to [0, 1]
        return list(top + positions * thickness)

    elif discretization.type == DiscretizationType.LOG_BOTTOM:
        # Logarithmic spacing with finer discretization at the bottom
        # Use reversed exponential function
        positions = np.exp(np.linspace(0, discretization.log_density, n + 1)) - 1
        positions = positions / positions[-1]  # normalize to [0, 1]
        positions = 1 - positions[::-1]  # reverse and invert
        return list(top + positions * thickness)

    else:  # LOG_BOTH
        # Symmetric logarithmic spacing with finer discretization at both ends
        if n % 2 == 0:
            n += 1  # ensure odd number for middle point

        # Split the layer into two parts
        middle = (top + bottom) / 2
        n_half = (n + 1) // 2

        # Create top half (fine → coarse)
        top_positions = np.exp(np.linspace(0, discretization.log_density, n_half)) - 1
        top_positions = top_positions / top_positions[-1]
        top_boundaries = top + top_positions * (middle - top)

        # Create bottom half (coarse → fine)
        bottom_positions = 1 - top_positions[::-1]
        bottom_boundaries = middle + bottom_positions * (bottom - middle)

        # Combine boundaries, avoiding duplicate middle point
        return list(np.concatenate([top_boundaries[:-1], bottom_boundaries]))
