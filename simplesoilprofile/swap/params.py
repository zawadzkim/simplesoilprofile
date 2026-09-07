"""Calibration parameter specs that address SOILHYDRFUNC cells by material key, not by row number.

A :class:`ParamSpec` carries exactly the fields of pyswap's ``Param`` dataclass (``name, path, bounds, transform, also``) plus the ``key`` and ``attribute`` it was built from, so a fitted value can be written back into the library (:func:`apply_fit`).
This module does not import pyswap; on the pyswap side the spec is consumed with ``Param(**spec.as_dict())``.

The row index of a material in the SOILHYDRFUNC table depends on which horizons are *present* in the profile at hand — the same material sits in a different row at a sounding where a lens above it is absent — so specs are resolved per profile.
A material placed more than once in a profile drives every one of its rows with the same value (pyswap's ``also``), as does the KSATFIT/KSATEXM pair of a conductivity.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from simplesoilprofile.core.library import SoilLibrary
from simplesoilprofile.core.profile import SoilProfile
from simplesoilprofile.swap.tables import BDENS_PER_G_CM3

#: SoilMaterial attribute -> SOILHYDRFUNC column.
HYD_COLUMNS = {
    "theta_res": "ORES",
    "theta_sat": "OSAT",
    "alpha": "ALFA",
    "n": "NPAR",
    "l_mualem": "LEXP",
    "k_sat": "KSATFIT",
    "h_enpr": "H_ENPR",
    "ksatexm": "KSATEXM",
    "bulk_density": "BDENS",
    "alphaw": "ALFAW",
}
#: The fields of pyswap's ``Param`` dataclass, in its order.
PYSWAP_PARAM_FIELDS = ("name", "path", "bounds", "transform", "also")
DEFAULT_TABLE_PATH = "soilprofile.soilhydrfunc"


@dataclass(frozen=True)
class ParamSpec:
    """One bounded parameter addressing SOILHYDRFUNC cells, with the material it came from."""

    name: str
    path: str
    bounds: tuple[float, float]
    transform: Literal["log10"] | None
    also: tuple[str, ...]
    key: str
    attribute: str

    def as_dict(self) -> dict[str, Any]:
        """The pyswap ``Param`` keyword arguments (``Param(**spec.as_dict())``)."""
        return {f: getattr(self, f) for f in PYSWAP_PARAM_FIELDS}

    @property
    def paths(self) -> tuple[str, ...]:
        return (self.path, *self.also)


def _rows(profile: SoilProfile, key: str) -> list[int]:
    present_keys = [h.key for _i, h in profile.present]
    rows = [r for r, k in enumerate(present_keys) if k == key]
    if rows:
        return rows
    if key in profile.keys:
        raise ValueError(f"'{key}' is absent (zero thickness) in profile '{profile.name}'; it has no SOILHYDRFUNC row there")
    raise KeyError(f"'{key}' is not a horizon key of profile '{profile.name}'; keys: {profile.keys}")


def param(
    profile: SoilProfile,
    key: str,
    attribute: str,
    bounds: tuple[float, float],
    *,
    transform: Literal["log10"] | None = None,
    name: str | None = None,
    tie_ksat: bool = True,
    table_path: str = DEFAULT_TABLE_PATH,
) -> ParamSpec:
    """Build the spec for ``attribute`` of the material ``key`` in ``profile``.

    Args:
        profile: The profile whose SOILHYDRFUNC table the spec addresses (rows follow its present horizons).
        key: Horizon/library key of the material.
        attribute: SoilMaterial attribute (see :data:`HYD_COLUMNS`).
        bounds: Physical bounds in the material's units (bulk density in g/cm3; converted to SWAP's mg/cm3).
        transform: Sampling-space transform passed through to pyswap.
        name: Parameter name; default ``"<attribute>_<key>"`` with spaces replaced by underscores.
        tie_ksat: For ``k_sat``, drive KSATEXM together with KSATFIT.
        table_path: Dotted path of the table in the pyswap model.

    Raises:
        KeyError: ``key`` is not in the profile.
        ValueError: unknown attribute, or ``key`` is absent (zero thickness) in this profile.
    """
    if attribute not in HYD_COLUMNS:
        raise ValueError(f"'{attribute}' is not a SOILHYDRFUNC parameter; one of {list(HYD_COLUMNS)}")
    rows = _rows(profile, key)
    paths = [f"{table_path}.{HYD_COLUMNS[attribute]}[{r}]" for r in rows]
    if attribute == "k_sat" and tie_ksat:
        paths += [f"{table_path}.KSATEXM[{r}]" for r in rows]
    if attribute == "bulk_density":
        bounds = (bounds[0] * BDENS_PER_G_CM3, bounds[1] * BDENS_PER_G_CM3)
    return ParamSpec(
        name=name or f"{attribute}_{key}".replace(" ", "_"),
        path=paths[0],
        bounds=(float(bounds[0]), float(bounds[1])),
        transform=transform,
        also=tuple(paths[1:]),
        key=key,
        attribute=attribute,
    )


def params(profile: SoilProfile, specs: Iterable[Mapping[str, Any]]) -> list[ParamSpec]:
    """Build several specs: each mapping holds the keyword arguments of :func:`param`."""
    return [param(profile, **spec) for spec in specs]


def apply_fit(
    library: SoilLibrary,
    values: Mapping[str, float],
    specs: Iterable[ParamSpec],
    *,
    source: str | None = None,
    note: str | None = None,
) -> SoilLibrary:
    """Write fitted values (by parameter name, in SWAP table units) back into a new library.

    Bulk density comes back divided by 1000 (mg/cm3 -> g/cm3).

    Raises:
        KeyError: a spec has no value in ``values``.
    """
    updates: dict[tuple[str, str], float] = {}
    for spec in specs:
        if spec.name not in values:
            raise KeyError(f"no fitted value for parameter '{spec.name}'")
        value = float(values[spec.name])
        if spec.attribute == "bulk_density":
            value /= BDENS_PER_G_CM3
        updates[(spec.key, spec.attribute)] = value
    return library.with_values(updates, source=source or "fitted", source_type="modeled", note=note)
