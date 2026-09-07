"""Publication tables from libraries and profiles.

Generated LaTeX is *data, not presentation*: :func:`latex_rows` writes only the table's data rows, preceded by a provenance comment (package version, date, and whatever the caller passes — notebook, commit).
Captions, labels, column headers and macros belong to the hand-written wrapper in the paper, which ``\\input``s the row file; the same frame renders to Markdown for a synthesis document.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from simplesoilprofile.core.discretization import sublayers
from simplesoilprofile.core.library import SoilLibrary
from simplesoilprofile.core.profile import SoilProfile

Format = str | Callable[[float], str]


def sig(digits: int = 3) -> Callable[[float], str]:
    """A formatter with ``digits`` significant figures and no exponent (1440.49 -> '1440', 0.1703 -> '0.170', 37.3 -> '37.3')."""

    def _format(value: float) -> str:
        if value == 0:
            return "0"
        decimals = max(digits - 1 - math.floor(math.log10(abs(value))), 0)
        return f"{value:.{decimals}f}"

    return _format


@dataclass(frozen=True)
class Column:
    """One publication column: the material attribute, its symbol/unit for the reader, and a format (``str.format`` pattern or callable)."""

    attribute: str
    label: str
    unit: str
    fmt: Format = "{:.3f}"


#: Default publication columns of a library table, in order.
LIBRARY_COLUMNS: tuple[Column, ...] = (
    Column("sand_content", "sand", "%", "{:.0f}"),
    Column("silt_content", "silt", "%", "{:.0f}"),
    Column("clay_content", "clay", "%", "{:.0f}"),
    Column("bulk_density", "rho_b", "g cm-3", "{:.2f}"),
    Column("theta_res", "theta_r", "cm3 cm-3", "{:.3f}"),
    Column("theta_sat", "theta_s", "cm3 cm-3", "{:.3f}"),
    Column("alpha", "alpha", "cm-1", "{:.4f}"),
    Column("n", "n", "-", "{:.3f}"),
    Column("l_mualem", "L", "-", "{:.2f}"),
    Column("k_sat", "K_s", "cm d-1", sig(3)),
)

#: Formats of :func:`horizon_frame`.
HORIZON_FORMATS = {"top_m": "{:.2f}", "bottom_m": "{:.2f}", "thickness_m": "{:.2f}", "hcomp_m": "{:.2f}", "ncomp": "{:d}"}


def library_frame(library: SoilLibrary, columns: Sequence[Column] = LIBRARY_COLUMNS) -> pd.DataFrame:
    """The library as a numeric publication frame: one row per material, ``columns`` in order, index named ``material``.

    The frame's ``attrs`` carry ``formats`` (column -> format string) and ``units`` for :func:`latex_rows` and :func:`markdown_table`.
    """
    frame = pd.DataFrame(
        [{c.label: getattr(m, c.attribute) for c in columns} for m in library.materials.values()],
        index=pd.Index(library.keys(), name="material"),
    )
    frame.attrs["formats"] = {c.label: c.fmt for c in columns}
    frame.attrs["units"] = {c.label: c.unit for c in columns}
    return frame


def horizon_frame(profile: SoilProfile, include_absent: bool = False) -> pd.DataFrame:
    """The horizons of a profile: material, top, bottom, thickness [m], compartment height(s) and count.

    Absent horizons are left out unless ``include_absent``; horizons without a rule show no compartments.
    """
    per_horizon: dict[int, list] = {}
    for s in sublayers(profile, strict=False):
        per_horizon.setdefault(s.horizon, []).append(s)
    rows = []
    for i, h in enumerate(profile.horizons):
        top, bottom = profile.bounds[i]
        if bottom <= top and not include_absent:
            continue
        subs = per_horizon.get(i, [])
        hcomps = sorted({s.hcomp for s in subs})
        rows.append({
            "horizon": i + 1,
            "material": h.key or h.material.name,
            "top_m": top,
            "bottom_m": bottom,
            "thickness_m": bottom - top,
            "hcomp_m": hcomps[0] if len(hcomps) == 1 else (None if not hcomps else "/".join(f"{v:g}" for v in hcomps)),
            "ncomp": sum(s.ncomp for s in subs) if subs else None,
        })
    frame = pd.DataFrame(rows).set_index("horizon")
    frame.attrs["formats"] = dict(HORIZON_FORMATS)
    frame.attrs["units"] = {"top_m": "m", "bottom_m": "m", "thickness_m": "m", "hcomp_m": "m", "ncomp": "-"}
    return frame


def _fmt(value, fmt: Format | None, na: str) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return na
    if fmt is None or isinstance(value, str):
        return str(value)
    if callable(fmt):
        return fmt(value)
    if fmt.endswith("d}"):
        return fmt.format(int(value))
    return fmt.format(value)


def _tex_escape(text: str) -> str:
    return text.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def latex_rows(
    frame: pd.DataFrame,
    path: str | Path | None = None,
    *,
    formats: Mapping[str, Format] | None = None,
    provenance: Iterable[str] | str | None = None,
    index: bool = True,
    na: str = "--",
    escape_index: bool = True,
) -> str:
    """Render ``frame`` as LaTeX data rows only (``a & b & c \\\\``) with a provenance comment header.

    No ``tabular`` environment, no header row, no caption: those live in the paper's wrapper.
    ``formats`` defaults to ``frame.attrs["formats"]``; ``provenance`` lines (notebook, commit, ...) go into the header after the package version and date.
    Writes to ``path`` when given; returns the text.
    """
    from simplesoilprofile import __version__

    fmts = dict(frame.attrs.get("formats", {}))
    fmts.update(formats or {})
    header = [f"% generated by simplesoilprofile {__version__} on {date.today().isoformat()} - data rows only; the wrapper owns caption, header and label"]
    if provenance:
        header += [f"% {line}" for line in ([provenance] if isinstance(provenance, str) else provenance)]
    lines = list(header)
    for idx, row in frame.iterrows():
        cells = [_tex_escape(str(idx)) if escape_index else str(idx)] if index else []
        cells += [_fmt(v, fmts.get(col), na) for col, v in row.items()]
        lines.append(" & ".join(cells) + r" \\")
    text = "\n".join(lines) + "\n"
    if path is not None:
        Path(path).write_text(text)
    return text


def markdown_table(
    frame: pd.DataFrame,
    *,
    formats: Mapping[str, Format] | None = None,
    units: bool = True,
    index: bool = True,
    na: str = "--",
) -> str:
    """Render ``frame`` as a GitHub-flavoured Markdown table (header with units from ``frame.attrs``), for synthesis documents."""
    fmts = dict(frame.attrs.get("formats", {}))
    fmts.update(formats or {})
    unit_of = frame.attrs.get("units", {}) if units else {}
    head = ([frame.index.name or ""] if index else []) + [f"{c} ({unit_of[c]})" if c in unit_of and unit_of[c] not in ("", "-") else str(c) for c in frame.columns]
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    for idx, row in frame.iterrows():
        cells = ([str(idx)] if index else []) + [_fmt(v, fmts.get(col), na) for col, v in row.items()]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
