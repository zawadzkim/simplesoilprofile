"""Horizon: a material placed in a profile, from the previous horizon's bottom to its own."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from simplesoilprofile.core.discretization import CompartmentRule, CountRule
from simplesoilprofile.core.material import SoilMaterial


class Horizon(BaseModel):
    """One placement of a material.

    Depths are metres below the profile surface.
    A horizon whose bottom equals the bottom of the horizon above has zero thickness: it is *absent* at this location but keeps its position in the sequence.
    """

    model_config = ConfigDict(frozen=True)

    material: SoilMaterial
    bottom: float = Field(..., description="Bottom depth [m below surface]", ge=0.0)
    rule: CompartmentRule | CountRule | None = Field(None, description="Discretization rule for this horizon")
    key: str | None = Field(None, description="Library key the material was taken from, if any")
