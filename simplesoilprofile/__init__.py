"""Simple soil profile package for hydrological modeling."""

from importlib.metadata import PackageNotFoundError, version

from simplesoilprofile.core import (
    CompartmentRule,
    CountRule,
    DiscretizationType,
    Horizon,
    ProvenanceEntry,
    SoilLibrary,
    SoilMaterial,
    SoilProfile,
    sublayers,
)
from simplesoilprofile.plotting import plot_profile
from simplesoilprofile.sources import profile_from_dov

try:
    __version__ = version("simplesoilprofile")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0"

__all__ = [
    "CompartmentRule",
    "CountRule",
    "DiscretizationType",
    "Horizon",
    "ProvenanceEntry",
    "SoilLibrary",
    "SoilMaterial",
    "SoilProfile",
    "plot_profile",
    "profile_from_dov",
    "sublayers",
]
