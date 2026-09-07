"""Soil layer model representing a single layer with physical properties."""

import os
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator
from rosetta import SoilData, rosetta

from simplesoilprofile.models.metadata import SoilLayerMetadata as M
from simplesoilprofile.models.texture_conversion import SoilTextureConverter
from simplesoilprofile.utils.logging import setup_logger

from .discretization import LayerDiscretization, compute_sublayer_boundaries

logger = setup_logger(__name__)

class SoilLayer(BaseModel):
    """A soil layer with uniform properties.

    This class represents a soil layer with van Genuchten parameters and other
    properties needed for hydrological modeling, particularly for SWAP model
    integration. The layer can be discretized into sublayers for numerical computation.
    """

    name: str = Field(..., description="Name or identifier of the soil layer")
    texture_class: str | None = Field(None, description="Soil texture class (e.g., 'sand', 'clay', etc.)")
    discretization: LayerDiscretization | None = Field(
        None, description="Configuration for layer discretization into sublayers"
    )
    description: str | None = Field(None, description="Description of the soil layer")

    # Van Genuchten parameters
    theta_res: float | None = Field(None, description="Residual water content [cm³/cm³]", ge=0.0, le=1.0)
    theta_sat: float | None = Field(None, description="Saturated water content [cm³/cm³]", ge=0.0, le=1.0)
    alpha: float | None = Field(None, description="Shape parameter alpha [1/cm]", gt=0.0)
    n: float | None = Field(None, description="Shape parameter n [-]", gt=1.0)
    k_sat: float | None = Field(None, description="Saturated hydraulic conductivity [cm/day]", gt=0.0)
    lambda_param: float | None = Field(0.5, description="Tortuosity parameter lambda [-]", alias="l")
    alphaw: float | None = Field(None, description="Alfa parameter of main wetting curve [cm]", ge=0.0, le=100.0)
    h_enpr: float | None = Field(None, description="Air entry pressure head [cm]", ge=-40.0, le=0)
    ksatexm: float | None = Field(None, description="Measured hydraulic conductivity at saturated conditions [cm/day]", ge=0.0, le=1e5)
    bulk_density: float | None = Field(None, description="Bulk density [g/cm³]", gt=0.0)

    #  texture information (used in heat flow section of SWAP)
    clay_content: float | None = Field(None, description="Clay content [%]", ge=0.0, le=100.0)
    silt_content: float | None = Field(None, description="Silt content [%]", ge=0.0, le=100.0)
    sand_content: float | None = Field(None, description="Sand content [%]", ge=0.0, le=100.0)
    organic_matter: float | None = Field(None, description="Organic matter content [%]", ge=0.0)

    metadata: dict[str, M] | None = Field(
        default_factory=dict,
        description="Metadata for each measured parameter, keyed by parameter name"
    )

    @model_validator(mode='after')
    def validate_water_contents(self) -> 'SoilLayer':
        """Validate that residual water content is less than saturated water content."""
        if self.theta_res is None or self.theta_sat is None:
            return self

        if self.theta_res >= self.theta_sat:
            raise ValueError("Residual water content must be less than saturated water content")
        return self

    @computed_field
    @property
    def sum_texture(self) -> float | None:
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

    def get_sublayer_boundaries(self, top: float, bottom: float) -> list[float]:
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

    def predict_van_genuchten(
        self,
        method: Literal["rosetta"] = "rosetta",
        version: Literal[1, 2, 3] = 3,
        use_bulk_density: bool = True,
        keep_ksat: bool = False,
    ) -> dict[str, float]:
        """Predict van Genuchten parameters from soil texture with a pedotransfer function.

        Requires ``rosetta-soil >= 0.3``: ``rosetta()`` returns arithmetic means in linear
        units (theta [cm3/cm3], alpha [1/cm], n [-], Ksat [cm/d]), so no back-transform is applied.
        The predicted values are written to ``theta_res``, ``theta_sat``, ``alpha``, ``n``,
        ``lambda_param`` and (unless ``keep_ksat``) ``k_sat``; each written parameter gets a
        metadata entry naming the model.

        Args:
            method: Pedotransfer function; only ``"rosetta"`` is implemented.
            version: Rosetta version (1, 2 or 3).
            use_bulk_density: Add ``bulk_density`` to the predictors when it is set
                (Rosetta's SSC+BD hierarchy level), otherwise predict from texture alone.
            keep_ksat: Leave ``k_sat`` untouched — for profiles whose saturated conductivity
                comes from a measurement or another source. The Rosetta Ksat is still returned.

        Returns:
            The full prediction: theta_res, theta_sat, alpha, n, k_sat, k0, lambda_param.

        Raises:
            ValueError: unknown method, or texture fractions missing.
        """
        if method != "rosetta":
            raise ValueError(f"Unknown pedotransfer method: '{method}'. Available: 'rosetta'")
        if any(v is None for v in (self.sand_content, self.silt_content, self.clay_content)):
            raise ValueError(f"Layer '{self.name}': sand, silt and clay contents are required for Rosetta")

        predictors = [self.sand_content, self.silt_content, self.clay_content]
        if use_bulk_density and self.bulk_density is not None:
            predictors.append(self.bulk_density)

        mean, _stdev, codes = rosetta(version, SoilData.from_iter([predictors]))
        logger.debug("Raw Rosetta output (mean values): %s", mean)
        theta_res, theta_sat, alpha, n, k_sat, k0, lambda_param = (float(v) for v in mean[0])
        predicted = {
            "theta_res": theta_res,
            "theta_sat": theta_sat,
            "alpha": alpha,
            "n": n,
            "k_sat": k_sat,
            "k0": k0,
            "lambda_param": lambda_param,
        }

        source = M(source=f"Rosetta v{version} (input code {int(codes[0])})", source_type="modeled")
        self.theta_res = theta_res
        self.theta_sat = theta_sat
        self.alpha = alpha
        self.n = n
        self.lambda_param = lambda_param
        written = ["theta_res", "theta_sat", "alpha", "n", "lambda_param"]
        if not keep_ksat:
            self.k_sat = k_sat
            written.append("k_sat")
        if self.metadata is None:
            self.metadata = {}
        for key in written:
            self.metadata[key] = source

        logger.info("Predicted van Genuchten parameters for layer '%s' with Rosetta v%d", self.name, version)
        return predicted

    def infer_fractions_from_texture(
            self,
            texture_class: str
        ) -> None:
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
