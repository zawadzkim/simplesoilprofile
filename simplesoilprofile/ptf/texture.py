"""Texture-class tables: class name <-> sand/silt/clay percentages.

Two systems ship as package data: ``usda`` (Levi 2017 centroids) and ``flemish`` (Belgian triangle).
The fraction-limit question for the Flemish table is tracked in issue #1.
"""

from __future__ import annotations

from functools import cache
from importlib import resources
from typing import Any

import yaml

SYSTEMS = {"usda": "usda_texture.yaml", "flemish": "flemish_texture.yaml"}


class SoilTextureConverter:
    """Convert between texture class names and sand/silt/clay percentages for one classification system."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.centroids: dict[str, dict[str, float]] = config["centroids"]
        self.ranges: dict[str, dict[str, Any]] = config.get("ranges", {})
        self.aliases: dict[str, str] = config.get("aliases", {})
        self.metadata: dict[str, Any] = config.get("metadata", {})

    @classmethod
    def from_yaml(cls, path: str) -> SoilTextureConverter:
        with open(path) as f:
            return cls(yaml.safe_load(f))

    def _normalize_class_name(self, texture_class: str) -> str:
        normalized = texture_class.lower().strip().replace(" ", "_").replace("-", "_")
        return self.aliases.get(normalized, normalized)

    def class_to_percentages(
        self, texture_class: str, method: str = "centroid", normalize: bool = True
    ) -> tuple[float, float, float]:
        """(sand, silt, clay) percentages of a class; ``method`` 'centroid' or 'mean' (statistical ranges)."""
        key = self._normalize_class_name(texture_class)
        if method == "centroid":
            table = self.centroids
            if key not in table:
                raise ValueError(f"Unknown texture class '{texture_class}'. Available: {list(table)}")
            sand, silt, clay = table[key]["sand"], table[key]["silt"], table[key]["clay"]
        elif method == "mean":
            if key not in self.ranges:
                raise ValueError(f"Unknown texture class '{texture_class}'. Available: {list(self.ranges)}")
            data = self.ranges[key]
            sand, silt, clay = data["sand"]["mean"], data["silt"]["mean"], data["clay"]["mean"]
        else:
            raise ValueError(f"Unknown method '{method}'. Use 'centroid' or 'mean'")
        if normalize:
            total = sand + silt + clay
            if total > 0:
                sand, silt, clay = (v / total * 100 for v in (sand, silt, clay))
        return sand, silt, clay

    def get_ranges(self, texture_class: str) -> dict[str, Any]:
        key = self._normalize_class_name(texture_class)
        if key not in self.ranges:
            raise ValueError(f"Unknown texture class '{texture_class}'")
        return self.ranges[key]

    def list_available_classes(self) -> list[str]:
        return list(self.centroids)


@cache
def texture_system(system: str = "usda") -> SoilTextureConverter:
    """The converter for a packaged classification system ('usda' or 'flemish'), loaded once."""
    if system not in SYSTEMS:
        raise ValueError(f"Unknown texture system '{system}'. Available: {list(SYSTEMS)}")
    text = (resources.files("simplesoilprofile.ptf") / "data" / SYSTEMS[system]).read_text(encoding="utf-8")
    return SoilTextureConverter(yaml.safe_load(text))
