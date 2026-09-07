"""Soil library: named materials defined once and placed in many profiles.

The library is a per-project object — the package ships the container, not its contents.
It is the single source of truth of a site's materials: profiles are built from it (:meth:`SoilProfile.from_library`), a calibration writes fitted values back into a new library (:meth:`SoilLibrary.with_values`), and the profiles are rebuilt from that (:meth:`SoilProfile.rebuild`).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from simplesoilprofile.core.material import SoilMaterial, SourceType

#: Column order of :meth:`SoilLibrary.to_frame`.
FRAME_COLUMNS = [
    "theta_res", "theta_sat", "alpha", "n", "l_mualem", "k_sat", "h_enpr", "ksatexm", "bulk_density", "alphaw",
    "sand_content", "silt_content", "clay_content", "organic_matter", "texture_class",
]


class SoilLibrary(BaseModel):
    """An ordered collection of named materials with project-level provenance."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Name of the library (site, project)")
    description: str | None = Field(None, description="Free description")
    materials: dict[str, SoilMaterial] = Field(..., description="Materials keyed by name, in order", min_length=1)
    provenance: dict[str, str] = Field(
        default_factory=dict, description="Library-level notes, e.g. {'ksat': 'CPTu S06 harmonic mean', 'notebook': '03-...'}"
    )

    @model_validator(mode="after")
    def _keys_match_names(self) -> SoilLibrary:
        bad = [k for k, m in self.materials.items() if k != m.name]
        if bad:
            raise ValueError(f"library keys must equal the material names; mismatched: {bad}")
        return self

    # --- access ------------------------------------------------------------------------

    def __getitem__(self, key: str) -> SoilMaterial:
        try:
            return self.materials[key]
        except KeyError:
            raise KeyError(f"'{key}' is not in library '{self.name}'; available: {self.keys()}") from None

    def __contains__(self, key: object) -> bool:
        return key in self.materials

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        return iter(self.materials)

    def __len__(self) -> int:
        return len(self.materials)

    def keys(self) -> list[str]:
        return list(self.materials)

    def to_frame(self) -> pd.DataFrame:
        """The materials as a table, one row per key, columns in :data:`FRAME_COLUMNS` order."""
        return pd.DataFrame(
            [{col: getattr(m, col) for col in FRAME_COLUMNS} for m in self.materials.values()],
            index=pd.Index(self.keys(), name="material"),
        )

    # --- functional updates -----------------------------------------------------------

    def with_(self, **values: Any) -> SoilLibrary:
        """Return a copy with ``values`` replaced, re-validated."""
        unknown = sorted(set(values) - set(type(self).model_fields))
        if unknown:
            raise ValueError(f"unknown fields: {unknown}")
        data = self.model_dump()
        data.update(values)
        return type(self).model_validate(data)

    def with_material(self, material: SoilMaterial) -> SoilLibrary:
        """Return a copy with ``material`` added or replaced under its name."""
        materials = {**self.materials, material.name: material}
        return self.with_(materials={k: m.model_dump() for k, m in materials.items()})

    def with_values(
        self,
        values: Mapping[tuple[str, str], float],
        *,
        source: str | None = None,
        source_type: SourceType = "modeled",
        note: str | None = None,
    ) -> SoilLibrary:
        """Return a copy with parameter values replaced: ``{(key, attribute): value}``.

        Each replaced parameter gets a provenance entry (``source_type`` 'modeled' by default — a fitted value), so a fitted library carries its own history.

        Raises:
            KeyError: unknown material key.
            ValueError: unknown attribute, or a value outside the field's bounds.
        """
        per_key: dict[str, dict[str, float]] = {}
        for (key, attr), value in values.items():
            if key not in self.materials:
                raise KeyError(f"'{key}' is not in library '{self.name}'; available: {self.keys()}")
            if attr not in SoilMaterial.PARAMETER_FIELDS:
                raise ValueError(f"'{attr}' is not a parameter field of SoilMaterial")
            per_key.setdefault(key, {})[attr] = value
        materials = dict(self.materials)
        for key, updates in per_key.items():
            materials[key] = materials[key].with_(
                source=source or "fitted", source_type=source_type, note=note, **updates
            )
        return self.with_(materials={k: m.model_dump() for k, m in materials.items()})

    # --- persistence -------------------------------------------------------------------

    def to_json(self, path: str | Path | None = None, indent: int = 2) -> str:
        """Serialize to JSON; write to ``path`` when given. Returns the JSON text."""
        text = self.model_dump_json(indent=indent)
        if path is not None:
            Path(path).write_text(text)
        return text

    @classmethod
    def from_json(cls, source: str | Path) -> SoilLibrary:
        """Load from a JSON file path or JSON text."""
        text = source if isinstance(source, str) and source.lstrip().startswith("{") else Path(source).read_text()
        return cls.model_validate(json.loads(text))
