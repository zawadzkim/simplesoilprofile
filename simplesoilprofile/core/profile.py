"""Soil profile: an ordered sequence of horizons at a location.

Depths are metres below the surface; ``elevation`` is the surface in metres above the datum of the site (e.g. m TAW).
Profiles are immutable; every ``with_*`` method returns a new, re-validated object.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from simplesoilprofile.core.discretization import Rule, sublayers
from simplesoilprofile.core.horizon import Horizon
from simplesoilprofile.core.material import SoilMaterial

if TYPE_CHECKING:
    from shapely.geometry import Point

    from simplesoilprofile.core.library import SoilLibrary


class SoilProfile(BaseModel):
    """A vertical sequence of horizons with a location and a surface elevation.

    A horizon whose bottom equals the previous bottom is *absent* here (zero thickness).
    Absent horizons keep their index, so one horizon sequence can describe every profile of a site; :attr:`present` lists the ones with thickness.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Name or identifier of the profile")
    description: str | None = Field(None, description="Free description")
    x: float | None = Field(None, description="Easting in ``crs``")
    y: float | None = Field(None, description="Northing in ``crs``")
    crs: str = Field("EPSG:31370", description="Coordinate reference system of x and y")
    elevation: float | None = Field(None, description="Surface elevation [m above the site datum]")
    horizons: list[Horizon] = Field(..., description="Horizons from the surface down", min_length=1)

    @model_validator(mode="after")
    def _bottoms_are_ordered(self) -> SoilProfile:
        prev = 0.0
        for i, h in enumerate(self.horizons):
            if h.bottom < prev:
                raise ValueError(f"Horizon {i} '{h.material.name}': bottom {h.bottom} m is above the previous bottom {prev} m")
            prev = h.bottom
        if prev <= 0.0:
            raise ValueError("The profile must have a positive total depth")
        return self

    # --- geometry ----------------------------------------------------------------------

    @property
    def point(self) -> Point:
        """The location as a shapely Point (shapely is imported on demand)."""
        if self.x is None or self.y is None:
            raise ValueError(f"Profile '{self.name}' has no x/y location")
        from shapely.geometry import Point

        return Point(self.x, self.y)

    @property
    def bounds(self) -> list[tuple[float, float]]:
        """(top, bottom) of every horizon [m]."""
        out, prev = [], 0.0
        for h in self.horizons:
            out.append((prev, h.bottom))
            prev = h.bottom
        return out

    @property
    def thicknesses(self) -> list[float]:
        """Thickness of every horizon [m]; zero when absent."""
        return [b - t for t, b in self.bounds]

    @property
    def depth(self) -> float:
        """Total depth [m] (bottom of the last horizon)."""
        return self.horizons[-1].bottom

    @property
    def present(self) -> list[tuple[int, Horizon]]:
        """(index, horizon) of every horizon with positive thickness, top down."""
        return [(i, h) for i, (h, (t, b)) in enumerate(zip(self.horizons, self.bounds, strict=True)) if b > t]

    @property
    def keys(self) -> list[str | None]:
        """Library key of every horizon (None for hand-built horizons)."""
        return [h.key for h in self.horizons]

    def index_of(self, ref: int | str) -> int:
        """Resolve a horizon reference: an index, a library key, or a material name."""
        if isinstance(ref, int):
            if not -len(self.horizons) <= ref < len(self.horizons):
                raise IndexError(f"horizon index {ref} out of range for {len(self.horizons)} horizons")
            return ref % len(self.horizons)
        hits = [i for i, h in enumerate(self.horizons) if h.key == ref]
        if not hits:
            hits = [i for i, h in enumerate(self.horizons) if h.material.name == ref]
        if len(hits) != 1:
            raise KeyError(f"'{ref}' matches {len(hits)} horizons of profile '{self.name}'")
        return hits[0]

    def horizon_at(self, depth: float) -> tuple[int, Horizon] | None:
        """The present horizon containing ``depth`` [m], inclusive of both bounds; None outside the profile."""
        for i, h in self.present:
            top, bottom = self.bounds[i]
            if top <= depth <= bottom:
                return i, h
        return None

    def depth_of(self, z: float) -> float:
        """Depth [m below surface] of an elevation ``z`` [m above the site datum]."""
        if self.elevation is None:
            raise ValueError(f"Profile '{self.name}' has no elevation")
        return self.elevation - z

    def elevation_of(self, depth: float) -> float:
        """Elevation [m above the site datum] of a depth [m below surface]."""
        if self.elevation is None:
            raise ValueError(f"Profile '{self.name}' has no elevation")
        return self.elevation - depth

    def sublayer_boundaries(self) -> dict[int, list[float]]:
        """Sublayer boundary depths [m] per present horizon that carries a rule."""
        out: dict[int, list[float]] = {}
        for s in sublayers(self, strict=False):
            bounds = out.setdefault(s.horizon, [s.top])
            bounds.append(s.bottom)
        return out

    # --- functional updates -----------------------------------------------------------

    def with_(self, **values: Any) -> SoilProfile:
        """Return a copy with ``values`` replaced, re-validated."""
        unknown = sorted(set(values) - set(type(self).model_fields))
        if unknown:
            raise ValueError(f"unknown fields: {unknown}")
        data = self.model_dump()
        data.update(values)
        return type(self).model_validate(data)

    def with_horizons(self, horizons: list[Horizon]) -> SoilProfile:
        """Return a copy with a new horizon sequence."""
        return self.with_(horizons=[h.model_dump() for h in horizons])

    def with_rule(self, ref: int | str, rule: Rule | None) -> SoilProfile:
        """Return a copy with the discretization rule of one horizon replaced."""
        i = self.index_of(ref)
        horizons = list(self.horizons)
        horizons[i] = horizons[i].model_copy(update={"rule": rule})
        return self.with_horizons(horizons)

    def with_material(self, ref: int | str, material: SoilMaterial) -> SoilProfile:
        """Return a copy with the material of one horizon replaced."""
        i = self.index_of(ref)
        horizons = list(self.horizons)
        horizons[i] = horizons[i].model_copy(update={"material": material})
        return self.with_horizons(horizons)

    # --- library -----------------------------------------------------------------------

    @classmethod
    def from_library(
        cls,
        library: SoilLibrary,
        sequence: Sequence[tuple[str, float]],
        *,
        name: str,
        description: str | None = None,
        x: float | None = None,
        y: float | None = None,
        crs: str = "EPSG:31370",
        elevation: float | None = None,
        rules: Mapping[str, Rule | None] | None = None,
    ) -> SoilProfile:
        """Build a profile from library materials: ``sequence`` is ``[(key, bottom_m), ...]`` from the surface down.

        A key may repeat; a bottom equal to the previous one marks an absent horizon.
        Every horizon records its ``key`` so the profile can be :meth:`rebuild` after the library changes.
        ``rules`` assigns a discretization rule per key.
        """
        rules = rules or {}
        horizons = [
            Horizon(material=library[key], bottom=bottom, rule=rules.get(key), key=key)
            for key, bottom in sequence
        ]
        return cls(name=name, description=description, x=x, y=y, crs=crs, elevation=elevation, horizons=horizons)

    def rebuild(self, library: SoilLibrary) -> SoilProfile:
        """Return a copy whose materials are taken afresh from ``library`` by key; bottoms and rules are kept.

        Raises:
            ValueError: a horizon has no key (hand-built profile).
            KeyError: a key is missing from the library.
        """
        missing = [i for i, h in enumerate(self.horizons) if h.key is None]
        if missing:
            raise ValueError(f"Profile '{self.name}': horizons {missing} carry no library key; rebuild needs from_library profiles")
        horizons = [h.model_copy(update={"material": library[h.key]}) for h in self.horizons]  # type: ignore[index]
        return self.with_horizons(horizons)

    # --- persistence -------------------------------------------------------------------

    def to_json(self, path: str | Path | None = None, indent: int = 2) -> str:
        """Serialize to JSON; write to ``path`` when given. Returns the JSON text."""
        text = self.model_dump_json(indent=indent)
        if path is not None:
            Path(path).write_text(text)
        return text

    @classmethod
    def from_json(cls, source: str | Path) -> SoilProfile:
        """Load from a JSON file path or JSON text."""
        text = source if isinstance(source, str) and source.lstrip().startswith("{") else Path(source).read_text()
        return cls.model_validate(json.loads(text))
