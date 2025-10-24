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
    texture_class: Optional[str] = Field(None, description="Soil texture class (e.g., 'sand', 'clay', etc.)")
    discretization: Optional[LayerDiscretization] = Field(
        None, description="Configuration for layer discretization into sublayers"
    )
    description: Optional[str] = Field(None, description="Description of the soil layer")
    
    # Van Genuchten parameters
    theta_res: Optional[float] = Field(None, description="Residual water content [cm³/cm³]", ge=0.0, le=1.0)
    theta_sat: Optional[float] = Field(None, description="Saturated water content [cm³/cm³]", ge=0.0, le=1.0)
    alpha: Optional[float] = Field(None, description="Shape parameter alpha [1/cm]", gt=0.0)
    n: Optional[float] = Field(None, description="Shape parameter n [-]", gt=1.0)
    k_sat: Optional[float] = Field(None, description="Saturated hydraulic conductivity [cm/day]", gt=0.0)
    l: Optional[float] = Field(0.5, description="Tortuosity parameter lambda [-]")
    alphaw: Optional[float] = Field(None, description="Alfa parameter of main wetting curve [cm]", ge=0.0, le=100.0)
    h_enpr: Optional[float] = Field(None, description="Air entry pressure head [cm]", ge=-40.0, le=0)
    ksatexm: Optional[float] = Field(None, description="Measured hydraulic conductivity at saturated conditions [cm/day]", ge=0.0, le=1e5)
    bulk_density: Optional[float] = Field(None, description="Bulk density [g/cm³]", gt=0.0)
    
    #  texture information (used in heat flow section of SWAP)
    clay_content: Optional[float] = Field(None, description="Clay content [%]", ge=0.0, le=100.0)
    silt_content: Optional[float] = Field(None, description="Silt content [%]", ge=0.0, le=100.0)
    sand_content: Optional[float] = Field(None, description="Sand content [%]", ge=0.0, le=100.0)
    organic_matter: Optional[float] = Field(None, description="Organic matter content [%]", ge=0.0)


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
    
    @computed_field
    @property
    def sum_texture(self) -> Optional[float]:
        """Compute the sum of clay, silt, and sand contents if all are provided."""
        if all(v is not None for v in (self.clay_content, self.silt_content, self.sand_content)):
            return self.clay_content + self.silt_content + self.sand_content
        return None
    
    def normalize_soil_fractions(
        self,
        tolerance: float = 2.0
    ) -> tuple[float, float, float]:
        """
        Normalize soil texture fractions to sum to 100%.
        
        Parameters
        ----------
        sand, silt, clay : float
            Soil fraction percentages
        tolerance : float
            Maximum acceptable deviation from 100% before normalization (default: 2%)
            
        Returns
        -------
        tuple[float, float, float]
            Normalized (sand, silt, clay) percentages
            
        Examples
        --------
        >>> normalize_soil_fractions(72.97, 22.44, 3.61)
        (73.76, 22.68, 3.65)  # Sum was 99.02, now 100.0
        """
        total = self.sand_content + self.silt_content + self.clay_content
        
        # Check if normalization is needed
        if abs(total - 100.0) < 0.01:  # Already at 100%
            return None

        # Warn if deviation is large (potential data quality issue)
        if abs(total - 100.0) > tolerance:
            logger.warning(
                "Sum of soil fractions %.2f%% exceeds tolerance of %.1f%% for layer '%s'",
                total, tolerance, self.name
            )
        
        # Proportional normalization
        if total > 0:
            logger.warning(
                "Normalizing soil fractions for layer '%s': %.2f%% -> 100.0%%",
                self.name, total
            )
            self.sand_content = (self.sand_content / total) * 100.0
            self.silt_content = (self.silt_content / total) * 100.0
            self.clay_content = (self.clay_content / total) * 100.0

            return None
        else:
            raise ValueError("Sum of fractions is zero or negative")


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
    
    def predict_van_genuchten(self, method: Literal["rosetta",]):
        """Predict van Genuchten parameters from soil texture."""
        if method == "rosetta":
            input = [
                [self.sand_content, self.silt_content, self.clay_content]
            ]
            soildata = SoilData.from_array(input)

            mean, stdev, codes = rosetta(2, soildata)
            logger.debug("Raw Rosetta output (mean values): %s", mean)
            
            # Convert from log10 values for alpha, n, and k_sat
            self.theta_res = mean[0][0]  # Residual water content
            self.theta_sat = mean[0][1]  # Saturated water content
            self.alpha = 10 ** mean[0][2]  # Convert from log10(1/cm)
            self.n = 10 ** mean[0][3]      # Convert from log10(-)
            self.k_sat = 10 ** mean[0][4]  # Convert from log10(cm/day)

            logger.info("Predicted van Genuchten parameters for layer '%s'")


    def enrich_soil_layer_from_texture_class(
            self,
            texture_class: str
        ) -> 'SoilLayer':
        """
        Add sand/silt/clay percentages to a SoilLayer based on texture class.
        
        Parameters
        ----------
        layer : SoilLayer
            Soil layer to enrich
        texture_class : str
            Texture class name from field observations
            
        Returns
        -------
        SoilLayer
            Updated layer with estimated percentages
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        data_path = os.path.join(project_root, 'simplesoilprofile', 'models', 'data', 'usda_texture.yaml')
        texture_converter = SoilTextureConverter(data_path)

        # Get percentages from texture class
        sand, silt, clay = texture_converter.class_to_percentages(texture_class)
        
        # Update layer
        self.sand_content = sand
        self.silt_content = silt
        self.clay_content = clay
        self.texture_class = texture_class
        
        # Add metadata about the conversion
        self.description = (
            f"{self.description or ''} "
            f"[Texture fractions estimated from class '{texture_class}' "
            f"using {texture_converter.metadata['reference']}]"
        )
        
        return None