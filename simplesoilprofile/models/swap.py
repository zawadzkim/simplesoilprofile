"""Utilities for generating SWAP model input tables from soil profiles.

Every exporter enumerates the *present* layers of the profile (positive thickness) in
order, so that the row order of the SOILHYDRFUNC and SOILTEXTURE tables and the
ISOILLAY numbering of the SOILPROFILE table agree with each other.
"""

import pandas as pd

from ..models import SoilProfile

#: SoilLayer attribute -> SOILHYDRFUNC column, for the parameters SWAP requires.
_REQUIRED_HYD = {
    "theta_res": "ORES",
    "theta_sat": "OSAT",
    "alpha": "ALFA",
    "n": "NPAR",
    "lambda_param": "LEXP",
    "k_sat": "KSATFIT",
    "bulk_density": "BDENS",
}
#: Default air-entry head: the classical Mualem-van Genuchten form (no Ippisch modification).
DEFAULT_H_ENPR = 0.0
#: SoilLayer.bulk_density is in g/cm3 (the Rosetta convention); SWAP's BDENS is in mg/cm3.
BDENS_PER_G_CM3 = 1000.0


def profile_to_soilhydfunc_table(
    profile: SoilProfile,
) -> pd.DataFrame:
    """Convert a SoilProfile to a SWAP-compatible SOILHYDRFUNC table.

    SWAP requires every column of the table for every layer. ``H_ENPR`` defaults to
    ``0`` and ``KSATEXM`` to ``KSATFIT`` when the layer does not set them; the other
    parameters must be present on every layer. ``BDENS`` is converted from the layer's
    g/cm3 to SWAP's mg/cm3. ``ALFAW`` (hysteresis only) is emitted
    when every present layer sets it and omitted when none does.

    Args:
        profile: The soil profile to convert

    Returns:
        DataFrame with one row per present layer.

    Raises:
        ValueError: a required parameter is missing on a layer, or ALFAW is set on
            some layers but not all.
    """
    rows = []
    for i, layer, _top, _bottom in profile.present_layers():
        missing = [col for attr, col in _REQUIRED_HYD.items() if getattr(layer, attr) is None]
        if missing:
            raise ValueError(
                f"Layer {i} '{layer.name}': SWAP requires {', '.join(missing)} — set the parameter(s) on the layer"
            )
        rows.append({
            "ORES": layer.theta_res,
            "OSAT": layer.theta_sat,
            "ALFA": layer.alpha,
            "NPAR": layer.n,
            "LEXP": layer.lambda_param,
            "KSATFIT": layer.k_sat,
            "H_ENPR": DEFAULT_H_ENPR if layer.h_enpr is None else layer.h_enpr,
            "KSATEXM": layer.k_sat if layer.ksatexm is None else layer.ksatexm,
            "BDENS": layer.bulk_density * BDENS_PER_G_CM3,
            "ALFAW": layer.alphaw,
        })

    df = pd.DataFrame(rows)
    if df["ALFAW"].isna().all():
        df = df.drop(columns="ALFAW")
    elif df["ALFAW"].isna().any():
        raise ValueError("ALFAW is set on some layers but not all; SWAP needs it for every layer or none")
    return df


def profile_to_sublayer_table(profile: SoilProfile) -> pd.DataFrame:
    """Convert a SoilProfile to a SWAP SOILPROFILE table (sublayers and compartments).

    Every present layer must carry a ``discretization``; a layer without one cannot be
    silently dropped, because SWAP would then see a profile with a hole in it.

    Raises:
        ValueError: a present layer has no discretization.
    """
    rows = []
    sublay_counter = 1
    for isoillay, (i, layer, top, bottom) in enumerate(profile.present_layers(), start=1):
        if layer.discretization is None:
            raise ValueError(
                f"Layer {i} '{layer.name}' has no discretization; set `layer.discretization` before exporting"
            )
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
        DataFrame containing the SOILTEXTURE table, one row per present layer.
    """
    rows = []
    for _i, layer, _top, _bottom in profile.present_layers():
        rows.append({
            "PCLAY": layer.clay_content,
            "PSILT": layer.silt_content,
            "PSAND": layer.sand_content,
            "ORGMAT": layer.organic_matter,
        })
    return pd.DataFrame(rows)
