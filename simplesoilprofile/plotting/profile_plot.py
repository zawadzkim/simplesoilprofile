"""Profile views: a single column, several columns side by side, and a fence of profiles in one elevation datum.

Colours and hatches are keyed by the horizon key (or material name), so a site's library gets one consistent encoding across every figure; horizons without an entry fall back to a texture-class colour, then grey.
Depths are metres; ``datum="depth"`` draws depth below the surface (positive down, axis inverted), ``datum="elevation"`` draws metres above the site datum and needs ``profile.elevation``.
Site overlays (screens, pipes, reach of a sounding) are added with :func:`mark_interval` and :func:`mark_depth`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle

from simplesoilprofile.core.discretization import sublayers
from simplesoilprofile.core.horizon import Horizon
from simplesoilprofile.core.nodes import node_depths
from simplesoilprofile.core.profile import SoilProfile

Datum = Literal["depth", "elevation"]

# Default colour mapping for common USDA texture classes
DEFAULT_TEXTURE_COLORS: dict[str, str] = {
    "sand": "#c2b280",
    "loamy sand": "#bcaa7d",
    "sandy loam": "#b5a077",
    "silt loam": "#9c8a70",
    "silt": "#8c7a63",
    "loam": "#7f6a4f",
    "sandy clay loam": "#6b5c42",
    "silty clay loam": "#5c4d35",
    "clay loam": "#4d3f28",
    "sandy clay": "#3e3118",
    "silty clay": "#2f240b",
    "clay": "#1f1600",
}
UNKNOWN_COLOR = "#808080"


def _label(h: Horizon) -> str:
    return h.key or h.material.name


def _color(h: Horizon, colors: Mapping[str, str] | None) -> str:
    label = _label(h)
    if colors and label in colors:
        return colors[label]
    if colors and h.material.name in colors:
        return colors[h.material.name]
    tc = (h.material.texture_class or "").lower()
    return DEFAULT_TEXTURE_COLORS.get(tc, UNKNOWN_COLOR)


def _hatch(h: Horizon, hatches: Mapping[str, str] | None) -> str | None:
    if not hatches:
        return None
    return hatches.get(_label(h), hatches.get(h.material.name))


def _y(profile: SoilProfile, depth: float, datum: Datum) -> float:
    if datum == "depth":
        return depth
    if profile.elevation is None:
        raise ValueError(f"Profile '{profile.name}' has no elevation; datum='elevation' needs one")
    return profile.elevation - depth


def _properties_text(h: Horizon) -> str:
    m = h.material
    props = [f"{_label(h)}", f"texture: {m.texture_class or 'unknown'}"]
    if m.has_texture:
        props.append(f"clay/silt/sand: {m.clay_content:.0f}/{m.silt_content:.0f}/{m.sand_content:.0f} %")
    if m.theta_res is not None and m.theta_sat is not None:
        props.append(f"θr/θs: {m.theta_res:.3f}/{m.theta_sat:.3f}")
    if m.alpha is not None and m.n is not None:
        props.append(f"alpha/n: {m.alpha:.4f}/{m.n:.3f}")
    if m.k_sat is not None:
        props.append(f"Ks: {m.k_sat:.3g} cm/d")
    return "\n".join(props)


def draw_column(
    profile: SoilProfile,
    ax: Axes,
    *,
    x: float = 0.0,
    width: float = 1.0,
    datum: Datum = "depth",
    colors: Mapping[str, str] | None = None,
    hatches: Mapping[str, str] | None = None,
    show_sublayers: bool = False,
    show_nodes: bool = False,
    edgecolor: str = "black",
) -> list[Rectangle]:
    """Draw the present horizons of ``profile`` as stacked rectangles from ``x`` to ``x + width``; returns the patches."""
    patches = []
    for i, h in profile.present:
        top, bottom = profile.bounds[i]
        y0, y1 = _y(profile, top, datum), _y(profile, bottom, datum)
        rect = Rectangle(
            (x, min(y0, y1)), width, abs(y1 - y0),
            facecolor=_color(h, colors), hatch=_hatch(h, hatches), edgecolor=edgecolor, linewidth=0.6,
            label=_label(h),
        )
        ax.add_patch(rect)
        patches.append(rect)
    if show_sublayers:
        for s in sublayers(profile, strict=False):
            if s.top > 0.0:
                y = _y(profile, s.top, datum)
                ax.plot([x, x + width], [y, y], color="orange", linestyle=":", linewidth=0.6, alpha=0.7)
    if show_nodes:
        try:
            z = node_depths(profile)
        except ValueError:
            z = None
        if z is not None:
            ax.plot([x + width / 2] * len(z), [_y(profile, d, datum) for d in z], ".", color="black", markersize=1.5, alpha=0.6)
    return patches


def _finish_axes(ax: Axes, profiles: Sequence[SoilProfile], datum: Datum) -> None:
    if datum == "depth":
        ax.set_ylim(0.0, max(p.depth for p in profiles) * 1.02)
        ax.invert_yaxis()
        ax.set_ylabel("depth below surface (m)")
    else:
        tops = [p.elevation for p in profiles if p.elevation is not None]
        bottoms = [p.elevation - p.depth for p in profiles if p.elevation is not None]
        span = max(tops) - min(bottoms)
        ax.set_ylim(min(bottoms) - 0.02 * span, max(tops) + 0.06 * span)
        ax.set_ylabel("elevation (m)")


def plot_profile(
    profile: SoilProfile,
    ax: Axes | None = None,
    *,
    datum: Datum = "depth",
    colors: Mapping[str, str] | None = None,
    hatches: Mapping[str, str] | None = None,
    show_sublayers: bool = True,
    show_nodes: bool = False,
    annotate: bool = True,
    figsize: tuple[float, float] = (5, 8),
) -> Axes:
    """Plot one profile as a column with its horizon properties written beside it."""
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    draw_column(profile, ax, datum=datum, colors=colors, hatches=hatches, show_sublayers=show_sublayers, show_nodes=show_nodes)
    if annotate:
        for i, h in profile.present:
            top, bottom = profile.bounds[i]
            ax.text(1.08, _y(profile, (top + bottom) / 2, datum), _properties_text(h), va="center", ha="left", fontsize=8)
        ax.set_xlim(-0.05, 2.2)
    else:
        ax.set_xlim(-0.05, 1.05)
    ax.set_xticks([])
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    _finish_axes(ax, [profile], datum)
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)
    title = profile.name
    if profile.elevation is not None:
        title += f" ({profile.elevation:.2f} m)"
    ax.set_title(title, loc="left")
    return ax


def plot_profiles(
    profiles: Sequence[SoilProfile],
    axes: Sequence[Axes] | None = None,
    *,
    datum: Datum = "depth",
    colors: Mapping[str, str] | None = None,
    hatches: Mapping[str, str] | None = None,
    show_sublayers: bool = False,
    legend: bool = True,
    figsize: tuple[float, float] | None = None,
) -> list[Axes]:
    """Plot several profiles side by side, one axes each, sharing the y axis; a legend keyed by horizon key on the last axes."""
    if axes is None:
        _, axes = plt.subplots(1, len(profiles), figsize=figsize or (2.6 * len(profiles), 6), sharey=True)
        axes = list(axes) if len(profiles) > 1 else [axes]
    for ax, p in zip(axes, profiles, strict=True):
        draw_column(p, ax, datum=datum, colors=colors, hatches=hatches, show_sublayers=show_sublayers)
        ax.set_xlim(-0.05, 1.05)
        ax.set_xticks([])
        ax.set_title(p.name + (f" ({p.elevation:.2f} m)" if p.elevation is not None else ""), loc="left", fontsize=10)
    _finish_axes(axes[0], profiles, datum)
    if legend:
        axes[-1].legend(*legend_entries(profiles, colors, hatches), loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False, fontsize=8)
    return list(axes)


def plot_fence(
    profiles: Sequence[SoilProfile],
    ax: Axes | None = None,
    *,
    x: Sequence[float] | None = None,
    labels: Sequence[str] | None = None,
    width: float = 0.62,
    colors: Mapping[str, str] | None = None,
    hatches: Mapping[str, str] | None = None,
    annotate_absent: bool = True,
    legend: bool = True,
    figsize: tuple[float, float] = (10, 5),
) -> Axes:
    """A fence of profiles in one elevation datum: every profile a bar at ``x`` (default: its order), absent horizons annotated.

    Raises:
        ValueError: a profile has no elevation.
    """
    missing = [p.name for p in profiles if p.elevation is None]
    if missing:
        raise ValueError(f"a fence needs elevations; missing on {missing}")
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    xs = list(x) if x is not None else list(range(len(profiles)))
    for xi, p in zip(xs, profiles, strict=True):
        draw_column(p, ax, x=xi - width / 2, width=width, datum="elevation", colors=colors, hatches=hatches, edgecolor="white")
        absent = [_label(h) for h, t in zip(p.horizons, p.thicknesses, strict=True) if t == 0.0]
        if annotate_absent and absent:
            ax.annotate(", ".join(absent) + " absent", (xi, p.elevation), xytext=(0, 4), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7, color="#555555")
    ax.set_xticks(xs, list(labels) if labels is not None else [p.name for p in profiles])
    ax.set_xlim(min(xs) - 0.6 * max(width, 1.0), max(xs) + 0.6 * max(width, 1.0))
    _finish_axes(ax, profiles, "elevation")
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)
    if legend:
        ax.legend(*legend_entries(profiles, colors, hatches), loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=8)
    return ax


def legend_entries(
    profiles: Sequence[SoilProfile],
    colors: Mapping[str, str] | None = None,
    hatches: Mapping[str, str] | None = None,
) -> tuple[list[Rectangle], list[str]]:
    """(handles, labels) for every distinct horizon key across ``profiles``, in order of first appearance."""
    seen: dict[str, Horizon] = {}
    for p in profiles:
        for h in p.horizons:
            seen.setdefault(_label(h), h)
    handles = [Rectangle((0, 0), 1, 1, facecolor=_color(h, colors), hatch=_hatch(h, hatches), edgecolor="black", linewidth=0.5) for h in seen.values()]
    return handles, list(seen)


def mark_interval(
    ax: Axes,
    profile: SoilProfile,
    top: float,
    bottom: float,
    label: str | None = None,
    *,
    x: float = 0.4,
    width: float = 0.2,
    datum: Datum = "depth",
    facecolor: str = "white",
    edgecolor: str = "black",
) -> Rectangle:
    """Mark a depth interval [top, bottom] m (a well screen, a sample layer) as a small box inside the column."""
    y0, y1 = _y(profile, top, datum), _y(profile, bottom, datum)
    rect = Rectangle((x, min(y0, y1)), width, abs(y1 - y0), facecolor=facecolor, edgecolor=edgecolor, linewidth=1.0, zorder=5)
    ax.add_patch(rect)
    if label:
        ax.annotate(label, (x + width, (y0 + y1) / 2), xytext=(3, 0), textcoords="offset points", va="center", fontsize=7.5, zorder=6)
    return rect


def mark_depth(
    ax: Axes,
    profile: SoilProfile,
    depth: float,
    label: str | None = None,
    *,
    x0: float = 0.0,
    x1: float = 1.0,
    datum: Datum = "depth",
    color: str = "black",
    linestyle: str | tuple = (0, (3, 2)),
) -> None:
    """Mark one depth [m] (a pipe, the reach of a sounding) as a dashed line across the column."""
    y = _y(profile, depth, datum)
    ax.plot([x0, x1], [y, y], color=color, linestyle=linestyle, linewidth=0.9, zorder=4)
    if label:
        ax.annotate(label, (x1, y), xytext=(3, 0), textcoords="offset points", va="center", fontsize=7.5, color=color, zorder=6)
