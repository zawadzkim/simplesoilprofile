"""Profiles from the Flemish soil database (DOV) through ``dovwms`` (optional extra ``dov``)."""

from __future__ import annotations

from simplesoilprofile.core.horizon import Horizon
from simplesoilprofile.core.material import ProvenanceEntry, SoilMaterial
from simplesoilprofile.core.profile import SoilProfile

CM_PER_M = 100.0


def profile_from_dov(
    x: float,
    y: float,
    crs: str = "EPSG:31370",
    fetch_elevation: bool = False,
    name: str | None = None,
) -> SoilProfile | None:
    """Build a profile from the DOV WMS texture layers at (x, y).

    dovwms returns four texture layers (0-30, 30-60, 60-100, 100-150 cm) with sand/silt/clay percentages and a provenance entry per fraction; the horizons carry texture only — run :meth:`SoilMaterial.with_rosetta` on them for hydraulic parameters.

    Returns None when DOV has no data at the location.

    Raises:
        ImportError: the ``dov`` extra is not installed.
    """
    try:
        from dovwms import get_profile_from_dov
    except ImportError as e:
        raise ImportError("DOV access needs the optional dependencies: pip install 'simplesoilprofile[dov]'") from e

    data = get_profile_from_dov(x, y, fetch_elevation=fetch_elevation, crs=crs)
    if data is None:
        return None

    horizons = []
    for layer in data["layers"]:
        metadata = {
            key: ProvenanceEntry(source=entry.get("source", "DOV WMS"), source_type="derived",
                                 uncertainty=entry.get("uncertainty"))
            for key, entry in layer.get("metadata", {}).items()
        }
        material = SoilMaterial(
            name=layer["name"],
            sand_content=layer["sand_content"],
            silt_content=layer["silt_content"],
            clay_content=layer["clay_content"],
            metadata=metadata,
        )
        horizons.append(Horizon(material=material, bottom=layer["layer_bottom"] / CM_PER_M))

    elevation = data.get("elevation", {}).get("elevation") if fetch_elevation else None
    return SoilProfile(
        name=name or f"DOV profile at {x:.0f}, {y:.0f}",
        x=x, y=y, crs=crs, elevation=elevation, horizons=horizons,
    )
