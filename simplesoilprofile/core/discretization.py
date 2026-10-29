"""Discretization of horizons into SWAP sublayers and compartments.

Three kinds of rule, each attached to a :class:`~simplesoilprofile.core.horizon.Horizon`:

- :class:`CompartmentRule` — a target compartment height in metres, optionally with a finer cap at the top of the horizon (``top_cap=(thickness, hcomp)``). Every sublayer thickness must be a multiple of its compartment height.
- :class:`CountRule` — the count-based schemes (even or logarithmic spacing of a number of sublayers, each with a number of compartments).
- :class:`SublayerRule` — an explicit list of sublayers, (thickness, compartments) each, as a SWAP soil database gives them.

:func:`sublayers` resolves a whole profile into :class:`Sublayer` rows and enforces SWAP's limits (``MACP`` = 5000 compartments in SWAP 4.2.0).
All lengths in metres.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

if TYPE_CHECKING:
    from simplesoilprofile.core.profile import SoilProfile

#: Maximum number of compartments in SWAP 4.2.0 (``MACP`` in ``arrays.fi``).
MACP = 5000
#: Tolerance [m] on "sublayer thickness is a multiple of the compartment height".
LENGTH_TOL = 1e-9


class DiscretizationType(str, Enum):
    """Types of layer discretization methods."""

    EVEN = "even"
    LOG_TOP = "logarithmic_top"
    LOG_BOTTOM = "logarithmic_bottom"
    LOG_BOTH = "logarithmic_both"

class CountRule(BaseModel):
    """Discretization by counts: a number of sublayers, each with a number of compartments."""

    model_config = ConfigDict(frozen=True)

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
    def validate_discretization(self) -> CountRule:
        """Validate discretization parameters."""
        if self.type != DiscretizationType.EVEN and self.log_density <= 0:
            raise ValueError("log_density must be positive for logarithmic discretization")
        return self

    def boundaries(self, top: float, bottom: float) -> list[float]:
        """Sublayer boundary depths between ``top`` and ``bottom`` (same unit in, same unit out)."""
        return compute_sublayer_boundaries(top, bottom, self)

    @computed_field
    @property
    def compartment_heights(self) -> list[float]:
        """Get the ordered list of compartment heights for this discretization.

        The heights are calculated based on the discretization type and parameters.
        The order is from top to bottom of the layer.

        Returns:
            List of compartment height fractions of the layer thickness, in order from top to bottom.
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
    discretization: CountRule
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


class CompartmentRule(BaseModel):
    """Discretization by compartment height [m], with an optional finer cap at the horizon top."""

    model_config = ConfigDict(frozen=True)

    hcomp: float = Field(..., description="Compartment height [m]", gt=0.0)
    top_cap: tuple[float, float] | None = Field(
        None, description="(thickness [m], compartment height [m]) of a finer sublayer at the top of the horizon"
    )

    @model_validator(mode="after")
    def _cap_is_positive(self) -> CompartmentRule:
        if self.top_cap is not None and (self.top_cap[0] <= 0.0 or self.top_cap[1] <= 0.0):
            raise ValueError("top_cap thickness and compartment height must be positive")
        return self


class SublayerRule(BaseModel):
    """An explicit list of sublayers, top down: (thickness [m], compartments) each, as a SWAP soil database gives them.

    The thicknesses add up to the horizon's.
    """

    model_config = ConfigDict(frozen=True)

    sublayers: tuple[tuple[float, int], ...] = Field(
        ..., min_length=1, description="(thickness [m], compartments) of each sublayer, top down"
    )

    @model_validator(mode="after")
    def _sublayers_are_positive(self) -> SublayerRule:
        for t, n in self.sublayers:
            if t <= 0.0 or n < 1:
                raise ValueError(f"sublayer ({t}, {n}): the thickness must be positive and the compartments at least 1")
        return self


Rule = CompartmentRule | CountRule | SublayerRule


@dataclass(frozen=True)
class Sublayer:
    """One SWAP sublayer: a run of equal compartments inside a horizon (lengths in metres)."""

    isoillay: int
    """1-based index among the *present* horizons — the SWAP soil layer number."""
    horizon: int
    """0-based index of the horizon in the profile."""
    top: float
    bottom: float
    hcomp: float
    ncomp: int

    @property
    def thickness(self) -> float:
        return self.bottom - self.top


def _ncomp(thickness: float, hcomp: float, where: str) -> int:
    n = thickness / hcomp
    ncomp = round(n)
    if ncomp < 1 or abs(n - ncomp) * hcomp > LENGTH_TOL:
        remainder = thickness - int(n) * hcomp
        raise ValueError(
            f"{where}: sublayer thickness {thickness:.6g} m is not a multiple of the compartment height {hcomp:.6g} m "
            f"(remainder {remainder:.6g} m)"
        )
    return ncomp


def _resolve(rule: Rule, top: float, bottom: float, where: str) -> list[tuple[float, float, float, int]]:
    """(top, bottom, hcomp, ncomp) of every sublayer of one horizon."""
    thickness = bottom - top
    if isinstance(rule, SublayerRule):
        total = sum(t for t, _ in rule.sublayers)
        if abs(total - thickness) > LENGTH_TOL:
            raise ValueError(f"{where}: its sublayers add up to {total:.6g} m, the horizon is {thickness:.6g} m")
        out, start = [], top
        for t, n in rule.sublayers:
            out.append((start, start + t, t / n, n))
            start += t
        return out
    if isinstance(rule, CountRule):
        bounds = rule.boundaries(top, bottom)
        return [
            (t, b, (b - t) / rule.num_compartments, rule.num_compartments)
            for t, b in pairwise(bounds)
        ]
    out = []
    start = top
    if rule.top_cap is not None:
        cap_thickness, cap_hcomp = rule.top_cap
        if cap_thickness >= thickness - LENGTH_TOL:
            raise ValueError(f"{where}: top cap {cap_thickness:.6g} m is not thinner than the horizon ({thickness:.6g} m)")
        out.append((start, start + cap_thickness, cap_hcomp, _ncomp(cap_thickness, cap_hcomp, where + " (top cap)")))
        start += cap_thickness
    out.append((start, bottom, rule.hcomp, _ncomp(bottom - start, rule.hcomp, where)))
    return out


def sublayers(profile: SoilProfile, strict: bool = True) -> list[Sublayer]:
    """Resolve the present horizons of ``profile`` into SWAP sublayers, top down.

    Args:
        profile: The profile; every present horizon needs a rule.
        strict: Raise on a present horizon without a rule (the SWAP export needs a complete column); with ``strict=False`` such horizons are skipped (plotting).

    Raises:
        ValueError: missing rule, a sublayer thickness that is not a multiple of its compartment height, a top cap thicker than its horizon, or more than ``MACP`` compartments in total.
    """
    out: list[Sublayer] = []
    for isoillay, (i, h) in enumerate(profile.present, start=1):
        where = f"Horizon {i} '{h.material.name}'"
        if h.rule is None:
            if strict:
                raise ValueError(f"{where} has no discretization rule; set `rule` before exporting")
            continue
        top, bottom = profile.bounds[i]
        for t, b, hcomp, ncomp in _resolve(h.rule, top, bottom, where):
            out.append(Sublayer(isoillay, i, t, b, hcomp, ncomp))
    total = sum(s.ncomp for s in out)
    if total > MACP:
        raise ValueError(f"Profile '{profile.name}': {total} compartments exceed SWAP's limit of {MACP}")
    return out
