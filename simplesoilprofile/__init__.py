"""Simple soil profile package for hydrological modeling."""

from importlib.metadata import PackageNotFoundError, version

from .models import SoilLayer, SoilProfile, get_profile_from_dov
from .plotting import plot_profile

try:
    __version__ = version("simplesoilprofile")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0"

__all__ = [
    "SoilLayer",
    "SoilProfile",
    "get_profile_from_dov",
    "plot_profile",
]
