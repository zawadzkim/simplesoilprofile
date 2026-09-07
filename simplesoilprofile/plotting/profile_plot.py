"""Plotting utilities for visualizing soil profiles (single-column view; the multi-profile views come with 0.1.0's plotting stage)."""

from __future__ import annotations

import matplotlib.pyplot as plt

from simplesoilprofile.core.horizon import Horizon
from simplesoilprofile.core.profile import SoilProfile

# Default color mapping for common soil textures
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


def _properties_text(h: Horizon) -> str:
    m = h.material
    props = [f"Horizon: {m.name}", f"Texture: {m.texture_class or 'Unknown'}"]
    if m.has_texture:
        props.append(f"Clay/Silt/Sand: {m.clay_content:.0f}/{m.silt_content:.0f}/{m.sand_content:.0f}%")
    if m.theta_res is not None and m.theta_sat is not None:
        props.append(f"θr/θs: {m.theta_res:.3f}/{m.theta_sat:.3f}")
    if m.k_sat is not None:
        props.append(f"Ks: {m.k_sat:.2f} cm/d")
    return "\n".join(props)


def plot_profile(
    profile: SoilProfile,
    ax: plt.Axes | None = None,
    figsize: tuple[float, float] = (8, 12),
    texture_colors: dict[str, str] | None = None,
    show_depths: bool = True,
    show_layer_properties: bool = True,
    show_sublayers: bool = True,
) -> plt.Axes:
    """Plot a profile: one rectangle per present horizon, depth in metres downward.

    Args:
        profile: The profile to plot
        ax: Optional matplotlib axes to plot on
        figsize: Figure size (width, height) if creating new figure
        texture_colors: Optional mapping of texture classes to colors
        show_depths: Whether to draw depth grid lines
        show_layer_properties: Whether to annotate each horizon with its properties
        show_sublayers: Whether to draw sublayer boundaries of discretized horizons

    Returns:
        The matplotlib axes object containing the plot
    """
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    colors = DEFAULT_TEXTURE_COLORS if texture_colors is None else texture_colors

    for i, h in profile.present:
        top, bottom = profile.bounds[i]
        color = colors.get(h.material.texture_class.lower() if h.material.texture_class else "unknown", UNKNOWN_COLOR)
        ax.add_patch(plt.Rectangle((0, -bottom), 1, bottom - top, facecolor=color, edgecolor="black", linewidth=0.5))
        if show_sublayers and h.rule is not None:
            for depth in h.rule.boundaries(top, bottom)[1:-1]:
                ax.axhline(y=-depth, xmin=0, xmax=1, color="orange", linestyle=":", linewidth=0.5, alpha=0.5)
        if show_layer_properties:
            ax.text(1.1, -(top + bottom) / 2, _properties_text(h), va="center", ha="left", fontsize=8)

    ax.set_xlim(-0.1, 2.0)
    ax.set_ylim(-profile.depth * 1.1, 0)
    ax.xaxis.set_visible(False)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    if show_depths:
        ax.yaxis.set_major_locator(plt.MultipleLocator(0.2))
        ax.yaxis.set_minor_locator(plt.MultipleLocator(0.05))
        ax.grid(True, axis="y", which="major", linestyle="--", alpha=0.3)

    title = f"Soil Profile: {profile.name}"
    coords = []
    if profile.x is not None and profile.y is not None:
        coords.append(f"x={profile.x:.1f}, y={profile.y:.1f}")
    if profile.elevation is not None:
        coords.append(f"z={profile.elevation:.1f} m")
    if coords:
        title += f"\n({', '.join(coords)})"
    ax.set_title(title)
    ax.set_ylabel("Depth [m]")
    return ax
