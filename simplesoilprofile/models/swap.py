"""Utilities for generating SWAP model input files from soil profiles."""

import pandas as pd

from ..models import SoilProfile


def profile_to_soilhydfunc_table(
    profile: SoilProfile,
) -> pd.DataFrame:
    """Convert a SoilProfile to a SWAP-compatible SOILHYDRFUNC table.

    Args:
        profile: The soil profile to convert

    Returns:
        DataFrame containing the SOILHYDRFUNC table with any column that contains
        None/NaN values removed.
    """
    rows = []
    for layer in profile.layers:
        rows.append({
            "ORES": layer.theta_res,
            "OSAT": layer.theta_sat,
            "ALFA": layer.alpha,
            "NPAR": layer.n,
            "LEXP": layer.lambda_param,
            "KSATFIT": layer.k_sat,
            "H_ENPR": layer.h_enpr,
            "KSATEXM": layer.ksatexm,
            "BDENS": layer.bulk_density,
            "ALFAW": layer.alphaw,
        })

    df = pd.DataFrame(rows)
    df = df.dropna(axis=1, how="any")
    return df

def profile_to_sublayer_table(profile: SoilProfile) -> pd.DataFrame:
    """Convert a SoilProfile to a DataFrame representing sublayers and compartments."""
    rows = []
    sublay_counter = 1
    for isoillay, layer in enumerate(profile.layers, start=1):
        if layer.discretization:
            # scale normalized compartment heights by the actual layer thickness
            top, bottom = profile.layer_bounds[isoillay - 1]
            thickness = bottom - top
            for height_ratio in layer.discretization.compartment_heights:
                height = height_ratio * thickness
                rows.append({
                    'ISUBLAY': sublay_counter,
                    'ISOILLAY': isoillay,
                    'HSUBLAY': height,
                    'NCOMP': layer.discretization.num_compartments,
                    'HCOMP': height / layer.discretization.num_compartments
                })
                sublay_counter += 1

    return pd.DataFrame(rows)

def profile_to_texture_table(
    profile: SoilProfile,
) -> pd.DataFrame:
    """Convert a SoilProfile to a SWAP-compatible SOILTEXTURE table.

    Args:
        profile: The soil profile to convert

    Returns:
        DataFrame containing the SOILTEXTURE table.
    """
    rows = []
    for layer in profile.layers:
        rows.append({
            "PCLAY": layer.clay_content,
            "PSILT": layer.silt_content,
            "PSAND": layer.sand_content,
            "ORGMAT": layer.organic_matter,
        })
    return pd.DataFrame(rows)
