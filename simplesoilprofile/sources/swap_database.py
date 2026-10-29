"""Profiles from a SWAP soil database: the tables multiSWAP reads (``soil_profiles_layout``, ``soil_discretization``,
``soil_texture`` and ``staring_series``), as the SWAP-MODFLOW 6 cases carry them, and ``soil_profiles_info`` for a
BOFEK2020 unit's representative profile.

Each soil layer of a profile becomes a horizon: its Staring unit's Mualem-van Genuchten parameters, its texture and
bulk density, and its sublayers as a :class:`~simplesoilprofile.core.discretization.SublayerRule`. The tables' cm,
mg/cm3 and fractions become the package's m, g/cm3 and percent. The layout's COFANI (the drainage anisotropy) is
not read.
"""

from __future__ import annotations

import csv
from pathlib import Path

from simplesoilprofile.core.discretization import SublayerRule
from simplesoilprofile.core.horizon import Horizon
from simplesoilprofile.core.material import SoilMaterial
from simplesoilprofile.core.profile import SoilProfile

CM_PER_M = 100.0
MG_PER_G = 1000.0
PERCENT = 100.0


def _rows(path: Path) -> list[dict[str, str]]:
    """A table's rows, its header's names stripped and lower-cased (the files differ in case and spacing); blank lines
    and comment lines (``!`` first, as multiSWAP's reader skips them) are no rows."""
    if not path.exists():
        raise FileNotFoundError(f"{path}: no such table of the SWAP soil database")
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = [h.strip().lower() for h in next(reader)]
        rows = [[c.strip() for c in row] for row in reader]
        return [dict(zip(header, row, strict=True)) for row in rows if any(row) and not row[0].startswith("!")]


def _num(text: str) -> float:
    """A number of the tables, Fortran's exponent ``d`` included (``1.0d-6``)."""
    return float(text.replace("d", "e").replace("D", "e"))


def profile_from_swap_database(
    folder: str | Path, soil_id: int | None = None, *, bofek_unit: int | None = None, variant: str = ""
) -> SoilProfile:
    """The profile ``soil_id`` of the SWAP soil database in ``folder``, or the representative profile of the
    BOFEK2020 unit ``bofek_unit`` (``soil_profiles_info.csv``'s ``BOFEK_2020``).

    ``variant`` is the suffix of the layout, discretization and texture tables (``"_sss"`` for the SWAP-SSS set);
    ``staring_series.csv`` and ``soil_profiles_info.csv`` have none.

    Raises:
        ValueError: neither or both of ``soil_id`` and ``bofek_unit``; a unit with no or several representative
            profiles; a soil_id absent from the layout; layers not numbered 1..n; a Staring unit absent from
            ``staring_series.csv``; a layer without sublayers.
        FileNotFoundError: a table missing.
    """
    folder = Path(folder)
    if (soil_id is None) == (bofek_unit is None):
        raise ValueError("give soil_id or bofek_unit, one of them")
    if bofek_unit is not None:
        info = _rows(folder / "soil_profiles_info.csv")
        hits = [int(r["soil_id"]) for r in info if int(r["bofek_2020"]) == bofek_unit]
        if len(hits) != 1:
            raise ValueError(f"{folder}: BOFEK2020 unit {bofek_unit} has {len(hits)} representative profiles, not one")
        soil_id = hits[0]
    layout_name = f"soil_profiles_layout{variant}.csv"
    layout = sorted(
        (r for r in _rows(folder / layout_name) if int(r["soil_id"]) == soil_id), key=lambda r: int(r["isoillay"])
    )
    if not layout:
        raise ValueError(f"{folder}: no soil_id {soil_id} in {layout_name}")
    if [int(r["isoillay"]) for r in layout] != list(range(1, len(layout) + 1)):
        raise ValueError(f"{folder}: soil_id {soil_id}'s layers in {layout_name} are not numbered 1..{len(layout)}")
    units = {int(r["sfu"]): r for r in _rows(folder / "staring_series.csv")}
    subs: dict[int, list[dict[str, str]]] = {}
    for r in _rows(folder / f"soil_discretization{variant}.csv"):
        if int(r["soil_id"]) == soil_id:
            subs.setdefault(int(r["isoillay"]), []).append(r)
    texture = {
        int(r["isoillay"]): r for r in _rows(folder / f"soil_texture{variant}.csv") if int(r["soil_id"]) == soil_id
    }

    horizons, bottom = [], 0.0
    for r in layout:
        k, sfu = int(r["isoillay"]), int(r["sfu"])
        if sfu not in units:
            raise ValueError(f"{folder}: soil_id {soil_id} layer {k}: sfu {sfu} is not in staring_series.csv")
        if k not in subs:
            raise ValueError(f"{folder}: soil_id {soil_id} layer {k}: no sublayers in soil_discretization{variant}.csv")
        u, tex = units[sfu], texture.get(k)
        rule = SublayerRule(
            sublayers=tuple(
                (_num(s["hsublay"]) / CM_PER_M, int(s["ncomp"]))
                for s in sorted(subs[k], key=lambda s: int(s["isublay"]))
            )
        )
        bottom += sum(t for t, _ in rule.sublayers)
        material = SoilMaterial(
            name=f"sfu {sfu}",
            description=f"Staring unit {sfu} of the SWAP soil database {folder.name}{variant}",
            theta_res=_num(u["ores"]),
            theta_sat=_num(u["osat"]),
            alpha=_num(u["alfa"]),
            n=_num(u["npar"]),
            k_sat=_num(u["ksatfit"]),
            ksatexm=_num(u["xksatexm"]),
            l_mualem=_num(u["lexp"]),
            h_enpr=_num(u["h_enpr"]),
            bulk_density=_num(tex["bdens"]) / MG_PER_G if tex else None,
            clay_content=_num(tex["pclay"]) * PERCENT if tex else None,
            silt_content=_num(tex["psilt"]) * PERCENT if tex else None,
            sand_content=_num(tex["psand"]) * PERCENT if tex else None,
            organic_matter=_num(tex["orgmat"]) * PERCENT if tex else None,
        )
        horizons.append(Horizon(material=material, bottom=bottom, rule=rule, key=str(sfu)))
    return SoilProfile(name=f"soil_id {soil_id}", description=f"SWAP soil database {folder}", horizons=horizons)
