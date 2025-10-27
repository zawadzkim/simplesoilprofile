"""Simple soil profile package for hydrological modeling."""

from .models import SoilLayer, SoilProfile
from .plotting import plot_profile

__version__ = "0.0.1"

__all__ = [
    "SoilLayer",
    "SoilProfile",
    "plot_profile",
]
