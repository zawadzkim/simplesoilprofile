"""Soil material: the hydraulic and textural properties of one kind of soil.

A material carries no depth.
It is placed in a profile through a :class:`~simplesoilprofile.core.horizon.Horizon`, and the same material may be placed in many profiles (see :class:`~simplesoilprofile.core.library.SoilLibrary`).

Units: alpha in 1/cm, k_sat and ksatexm in cm/d, h_enpr in cm, bulk_density in g/cm3, texture fractions in percent.
Materials are immutable; every ``with_*`` method returns a new, re-validated object.
"""

from __future__ import annotations

from datetime import date
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from simplesoilprofile.utils.logging import setup_logger

logger = setup_logger(__name__)

SourceType = Literal["measured", "modeled", "derived", "literature", "estimated", "default", "unknown"]


class ProvenanceEntry(BaseModel):
    """Where the value of one parameter came from."""

    model_config = ConfigDict(frozen=True)

    source: str = Field("User-provided", description="Data source, e.g. 'Rosetta v3', 'Field measurement', 'DOV WMS'")
    source_type: SourceType = Field("unknown", description="Kind of source")
    note: str | None = Field(None, description="Free text: notebook, commit, method")
    url: HttpUrl | None = Field(None, description="URL to the original data source")
    access_date: date | None = Field(None, description="Date the data was retrieved")
    uncertainty: float | None = Field(None, description="Measurement uncertainty or confidence interval")


class SoilMaterial(BaseModel):
    """A soil with uniform properties: van Genuchten-Mualem parameters, texture, provenance."""

    model_config = ConfigDict(frozen=True)

    #: Fields that describe a parameter value and may carry a provenance entry.
    PARAMETER_FIELDS: ClassVar[frozenset[str]] = frozenset({
        "theta_res", "theta_sat", "alpha", "n", "k_sat", "l_mualem", "h_enpr", "ksatexm", "alphaw", "bulk_density",
        "clay_content", "silt_content", "sand_content", "organic_matter",
    })

    name: str = Field(..., description="Name of the material; the key when it sits in a library")
    description: str | None = Field(None, description="Free description")
    texture_class: str | None = Field(None, description="Texture class name, e.g. 'sandy loam'")

    # van Genuchten-Mualem parameters
    theta_res: float | None = Field(None, description="Residual water content [cm3/cm3]", ge=0.0, le=1.0)
    theta_sat: float | None = Field(None, description="Saturated water content [cm3/cm3]", ge=0.0, le=1.0)
    alpha: float | None = Field(None, description="Shape parameter alpha [1/cm]", gt=0.0, le=100.0)
    n: float | None = Field(None, description="Shape parameter n [-]", gt=1.0, le=9.0)
    k_sat: float | None = Field(None, description="Saturated hydraulic conductivity [cm/d]", gt=0.0)
    l_mualem: float = Field(0.5, description="Mualem tortuosity exponent L [-]", ge=-25.0, le=25.0)
    h_enpr: float | None = Field(None, description="Air entry pressure head [cm]", ge=-40.0, le=0.0)
    ksatexm: float | None = Field(None, description="Measured saturated conductivity [cm/d]", ge=0.0, le=1e5)
    alphaw: float | None = Field(None, description="Alpha of the main wetting curve [1/cm] (hysteresis)", ge=0.0, le=100.0)
    bulk_density: float | None = Field(None, description="Dry bulk density [g/cm3]", gt=0.0)

    # texture
    clay_content: float | None = Field(None, description="Clay content [%]", ge=0.0, le=100.0)
    silt_content: float | None = Field(None, description="Silt content [%]", ge=0.0, le=100.0)
    sand_content: float | None = Field(None, description="Sand content [%]", ge=0.0, le=100.0)
    organic_matter: float | None = Field(None, description="Organic matter content [%]", ge=0.0)

    metadata: dict[str, ProvenanceEntry] = Field(
        default_factory=dict, description="Provenance per parameter, keyed by field name"
    )

    @field_validator("metadata")
    @classmethod
    def _metadata_keys_are_parameters(cls, value: dict[str, ProvenanceEntry]) -> dict[str, ProvenanceEntry]:
        unknown = sorted(set(value) - cls.PARAMETER_FIELDS)
        if unknown:
            raise ValueError(f"metadata keys must be parameter fields; unknown: {unknown}")
        return value

    @model_validator(mode="after")
    def _residual_below_saturated(self) -> SoilMaterial:
        if self.theta_res is not None and self.theta_sat is not None and self.theta_res >= self.theta_sat:
            raise ValueError("Residual water content must be less than saturated water content")
        return self

    # --- derived -----------------------------------------------------------------------

    @property
    def has_texture(self) -> bool:
        """True when sand, silt and clay are all set."""
        return all(v is not None for v in (self.sand_content, self.silt_content, self.clay_content))

    @property
    def sum_texture(self) -> float | None:
        """Sum of sand, silt and clay [%], or None when a fraction is missing."""
        if not self.has_texture:
            return None
        return self.sand_content + self.silt_content + self.clay_content  # type: ignore[operator]

    # --- functional updates -----------------------------------------------------------

    def with_(
        self,
        *,
        source: str | None = None,
        source_type: SourceType | None = None,
        note: str | None = None,
        **values: Any,
    ) -> SoilMaterial:
        """Return a copy with ``values`` replaced, re-validated.

        When ``source``, ``source_type`` or ``note`` is given, every parameter field in ``values`` receives a provenance entry built from them.
        """
        unknown = sorted(set(values) - set(type(self).model_fields))
        if unknown:
            raise ValueError(f"unknown fields: {unknown}")
        data = self.model_dump()
        data.update(values)
        if source is not None or source_type is not None or note is not None:
            entry = ProvenanceEntry(
                source=source or "User-provided", source_type=source_type or "unknown", note=note
            )
            metadata = dict(data["metadata"])
            for key in values:
                if key in self.PARAMETER_FIELDS:
                    metadata[key] = entry
            data["metadata"] = metadata
        return type(self).model_validate(data)

    def with_metadata(self, **entries: ProvenanceEntry | dict[str, Any]) -> SoilMaterial:
        """Return a copy with provenance entries added or replaced."""
        metadata = {**self.metadata, **entries}
        return self.with_(metadata=metadata)

    def with_rosetta(
        self,
        version: Literal[1, 2, 3] = 3,
        use_bulk_density: bool = True,
        keep_ksat: bool = False,
    ) -> SoilMaterial:
        """Return a copy with van Genuchten-Mualem parameters predicted by Rosetta.

        Sets theta_res, theta_sat, alpha, n, l_mualem and (unless ``keep_ksat``) k_sat, each with a provenance entry naming the model.
        Uses the bulk density as a predictor when it is set and ``use_bulk_density`` is true.

        Raises:
            ValueError: texture fractions missing.
        """
        from simplesoilprofile.ptf.rosetta import predict

        if not self.has_texture:
            raise ValueError(f"Material '{self.name}': sand, silt and clay contents are required for Rosetta")
        pred = predict(
            self.sand_content,  # type: ignore[arg-type]
            self.silt_content,  # type: ignore[arg-type]
            self.clay_content,  # type: ignore[arg-type]
            bulk_density=self.bulk_density if use_bulk_density else None,
            version=version,
        )
        values: dict[str, float] = {
            "theta_res": pred.theta_res,
            "theta_sat": pred.theta_sat,
            "alpha": pred.alpha,
            "n": pred.n,
            "l_mualem": pred.l_mualem,
        }
        if not keep_ksat:
            values["k_sat"] = pred.k_sat
        logger.info("Rosetta v%d parameters for material '%s' (input code %d)", version, self.name, pred.code)
        return self.with_(source=f"Rosetta v{version} (input code {pred.code})", source_type="modeled", **values)

    def with_texture_class(self, texture_class: str, system: str = "usda") -> SoilMaterial:
        """Return a copy with sand/silt/clay set to the centroid of ``texture_class`` in ``system``."""
        from simplesoilprofile.ptf.texture import texture_system

        converter = texture_system(system)
        sand, silt, clay = converter.class_to_percentages(texture_class)
        return self.with_(
            source=f"{converter.metadata['reference']}: centroid of class '{texture_class}'",
            source_type="estimated",
            sand_content=sand,
            silt_content=silt,
            clay_content=clay,
            texture_class=texture_class,
        )

    def normalized_fractions(self, tolerance: float = 2.0) -> SoilMaterial:
        """Return a copy whose sand, silt and clay sum to 100 %.

        Returns ``self`` when they already do.
        Warns when the deviation exceeds ``tolerance`` (a data-quality signal), and raises when the fractions are missing or sum to zero.
        """
        if not self.has_texture:
            raise ValueError(f"Material '{self.name}': sand, silt and clay contents are required")
        total = self.sum_texture or 0.0
        if abs(total - 100.0) < 0.01:
            return self
        if total <= 0:
            raise ValueError("Sum of fractions is zero or negative")
        if abs(total - 100.0) > tolerance:
            logger.warning("Sum of soil fractions %.2f%% exceeds tolerance of %.1f%% for '%s'", total, tolerance, self.name)
        return self.with_(
            source=f"normalized from a {total:.2f} % sum",
            source_type="derived",
            sand_content=self.sand_content / total * 100.0,  # type: ignore[operator]
            silt_content=self.silt_content / total * 100.0,  # type: ignore[operator]
            clay_content=self.clay_content / total * 100.0,  # type: ignore[operator]
        )
