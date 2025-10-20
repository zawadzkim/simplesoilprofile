"""Plotting utilities for visualizing soil profiles."""

import matplotlib.pyplot as plt
import numpy as np
from typing import Optional, Dict, Tuple
from ..models import SoilProfile


# Default color mapping for common soil textures
DEFAULT_TEXTURE_COLORS: Dict[str, str] = {
    'sand': '#c2b280',       # Sand color
    'loamy sand': '#bcaa7d', # Slightly darker sand
    'sandy loam': '#b5a077', # Light brown
    'silt loam': '#9c8a70',  # Medium brown
    'silt': '#8c7a63',       # Dark brown
    'loam': '#7f6a4f',       # Brown
    'sandy clay loam': '#6b5c42', # Dark brown
    'silty clay loam': '#5c4d35', # Very dark brown
    'clay loam': '#4d3f28',  # Dark brown
    'sandy clay': '#3e3118', # Very dark brown
    'silty clay': '#2f240b', # Almost black
    'clay': '#1f1600',       # Black
}


def plot_profile(
    profile: SoilProfile,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[float, float] = (8, 12),
    texture_colors: Optional[Dict[str, str]] = None,
    show_depths: bool = True,
    show_properties: bool = True,
    show_sublayers: bool = True,
) -> plt.Axes:
    """Plot a soil profile showing layers and their properties.
    
    Args:
        profile: The soil profile to plot
        ax: Optional matplotlib axes to plot on
        figsize: Figure size (width, height) if creating new figure
        texture_colors: Optional mapping of texture classes to colors
        show_depths: Whether to show depth labels
        show_properties: Whether to show soil properties in annotations
        show_sublayers: Whether to show sublayer boundaries for discretized layers
        
    Returns:
        The matplotlib axes object containing the plot
    """
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    
    if texture_colors is None:
        texture_colors = DEFAULT_TEXTURE_COLORS
    
    # Sort layers by depth
    sorted_depths = sorted(profile.layer_depths.items(), key=lambda x: x[0])
    total_depth = profile.get_profile_depth()
    
    # Plot each layer
    for layer_idx, (top, bottom) in sorted_depths:
        layer = profile.layers[layer_idx]
        
        # Get color based on texture class or use default
        color = texture_colors.get(
            layer.texture_class.lower() if layer.texture_class else 'unknown',
            '#808080'  # Default gray for unknown textures
        )
        
        # Plot the layer as a rectangle
        rect = plt.Rectangle(
            (0, -bottom),           # (x, y) of bottom-left corner
            1,                      # width (normalized to 1)
            bottom - top,           # height
            facecolor=color,
            edgecolor='black',
            linewidth=0.5,
        )
        ax.add_patch(rect)
        
        # Add sublayer lines if enabled and layer has discretization
        if show_sublayers and layer.discretization is not None:
            sublayer_depths = layer.get_sublayer_boundaries(top, bottom)
            for depth in sublayer_depths[1:-1]:  # Skip top and bottom depths
                ax.axhline(
                    y=-depth,
                    xmin=0,
                    xmax=1,
                    color='orange',
                    linestyle=':',
                    linewidth=0.5,
                    alpha=0.5
                )
        
        # Add layer information if requested
        if show_properties:
            # Prepare property text
            props = [
                f"Layer: {layer.name}",
                f"Texture: {layer.texture_class or 'Unknown'}"
            ]
            
            if all(x is not None for x in [layer.clay_content, layer.silt_content, layer.sand_content]):
                props.append(f"Clay/Silt/Sand: {layer.clay_content:.0f}/{layer.silt_content:.0f}/{layer.sand_content:.0f}%")
            
            props.append(f"θr/θs: {layer.theta_res:.3f}/{layer.theta_sat:.3f}")
            props.append(f"Ks: {layer.k_sat:.2f} cm/d")
            
            # Add text annotation
            mid_depth = (top + bottom) / 2
            ax.text(
                1.1, -mid_depth,
                '\n'.join(props),
                verticalalignment='center',
                horizontalalignment='left',
                fontsize=8,
            )
    
    # Set axis limits and labels
    ax.set_xlim(-0.1, 2.0)  # Leave space for annotations
    ax.set_ylim(-total_depth * 1.1, 0)  # Add 10% padding at bottom
    
    # Remove x-axis and right spine
    ax.xaxis.set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    
    # Add depth ticks if requested
    if show_depths:
        ax.yaxis.set_major_locator(plt.MultipleLocator(20))
        ax.yaxis.set_minor_locator(plt.MultipleLocator(5))
        ax.grid(True, axis='y', which='major', linestyle='--', alpha=0.3)
        ax.set_ylabel('Depth [cm]')
    
    # Add title with profile information
    title = f"Soil Profile: {profile.name}"
    if any(coord is not None for coord in [profile.location.x, profile.location.y, profile.elevation]):
        coords = []
        if profile.location.x is not None and profile.location.y is not None:
            coords.append(f"x={profile.location.x:.1f}, y={profile.location.y:.1f}")
        if profile.elevation is not None:
            coords.append(f"z={profile.elevation:.1f}")
        if coords:
            title += f"\n({', '.join(coords)})"
    ax.set_title(title)
    
    return ax