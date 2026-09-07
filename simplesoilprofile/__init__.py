"""Simple soil profile package for hydrological modeling."""

from importlib.metadata import PackageNotFoundError, version

from simplesoilprofile.core import CountRule, DiscretizationType, Horizon, ProvenanceEntry, SoilMaterial, SoilProfile
from simplesoilprofile.plotting import plot_profile
from simplesoilprofile.sources import profile_from_dov

try:
    __version__ = version("simplesoilprofile")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0"

__all__ = [
    "CountRule",
    "DiscretizationType",
    "Horizon",
    "ProvenanceEntry",
    "SoilMaterial",
    "SoilProfile",
    "plot_profile",
    "profile_from_dov",
]
