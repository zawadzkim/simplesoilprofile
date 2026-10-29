"""Core object model: materials, horizons, profiles and discretization rules."""

from simplesoilprofile.core.discretization import (
    MACP,
    CompartmentRule,
    CountRule,
    DiscretizationType,
    Rule,
    Sublayer,
    SublayerRule,
    sublayers,
)
from simplesoilprofile.core.horizon import Horizon
from simplesoilprofile.core.library import SoilLibrary
from simplesoilprofile.core.material import ProvenanceEntry, SoilMaterial, SourceType
from simplesoilprofile.core.nodes import interval_weights, node_bounds, node_depths, node_horizons
from simplesoilprofile.core.profile import SoilProfile

__all__ = [
    "MACP",
    "CompartmentRule",
    "CountRule",
    "DiscretizationType",
    "Horizon",
    "ProvenanceEntry",
    "Rule",
    "SoilLibrary",
    "SoilMaterial",
    "SoilProfile",
    "SourceType",
    "Sublayer",
    "SublayerRule",
    "interval_weights",
    "node_bounds",
    "node_depths",
    "node_horizons",
    "sublayers",
]
