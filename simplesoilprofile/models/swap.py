"""Utilities for generating SWAP model input files from soil profiles."""

from typing import List, TextIO
from ..models import SoilProfile, SoilLayer


def format_van_genuchten_table(layer: SoilLayer) -> str:
    """Format van Genuchten parameters for SWAP soil hydraulic function table.
    
    Args:
        layer: The soil layer containing van Genuchten parameters
        
    Returns:
        Formatted string for SWAP soil hydraulic function table
    """
    return (
        f"* {layer.name}\n"
        f"* ISOILLAY{layer.name.upper():5} ! soil hydraulic functions\n"
        f"  1         ! ORES = {layer.theta_res:.6f}\n"
        f"  2         ! OSAT = {layer.theta_sat:.6f}\n"
        f"  3         ! ALFA = {layer.alpha:.6f}\n"
        f"  4         ! NPAR = {layer.n:.6f}\n"
        f"  5         ! KSAT = {layer.k_sat:.6f}\n"
        f"  6         ! LEXP = {layer.l:.6f}\n"
    )


def write_swap_soil_file(profile: SoilProfile, output_file: TextIO) -> None:
    """Write soil profile data to SWAP format file.
    
    Args:
        profile: The soil profile to convert
        output_file: File object to write to (must be opened in write mode)
    """
    # Write header
    output_file.write(f"* Soil profile: {profile.name}\n")
    if profile.description:
        output_file.write(f"* Description: {profile.description}\n")
    output_file.write("*\n")
    
    # Write number of soil layers
    output_file.write(f"  {len(profile.layers)}    ! ISOILLAY = number of soil layers\n")
    output_file.write("*\n")
    
    # Write thickness of soil layers
    output_file.write("* thickness of soil layers [cm]:\n")
    sorted_depths = sorted(profile.layer_depths.items(), key=lambda x: x[0])
    thicknesses = []
    prev_depth = 0.0
    
    for _, (top, bottom) in sorted_depths:
        thickness = bottom - top
        thicknesses.append(thickness)
        prev_depth = bottom
    
    thickness_str = " ".join(f"{t:.1f}" for t in thicknesses)
    output_file.write(f"  {thickness_str}    ! HSUBLAY = thickness of soil layers [cm]\n")
    output_file.write("*\n")
    
    # Write van Genuchten parameters for each layer
    output_file.write("* soil hydraulic functions:\n")
    for layer in profile.layers:
        output_file.write("\n")
        output_file.write(format_van_genuchten_table(layer))


def get_swap_table_headers() -> List[str]:
    """Get the standard headers for SWAP soil hydraulic function tables.
    
    Returns:
        List of column headers used in SWAP tables
    """
    return [
        "h",         # pressure head [cm]
        "theta",     # water content [cm3/cm3]
        "K",         # hydraulic conductivity [cm/d]
        "C",         # differential moisture capacity [1/cm]
        "Se",        # relative saturation [-]
    ]