"""SWAP input tables from a profile, as pandas frames with pyswap's column names.

Every exporter enumerates the *present* horizons in order, so the row order of SOILHYDRFUNC and SOILTEXTURE and the ISOILLAY numbering of SOILPROFILE agree.
Unit conversions of the package happen here: depths m -> cm, bulk density g/cm3 -> mg/cm3.
"""

from __future__ import annotations

import pandas as pd

from simplesoilprofile.core.profile import SoilProfile

#: SoilMaterial attribute -> SOILHYDRFUNC column, for the parameters SWAP requires.
REQUIRED_HYD = {
    "theta_res": "ORES",
    "theta_sat": "OSAT",
    "alpha": "ALFA",
    "n": "NPAR",
    "l_mualem": "LEXP",
    "k_sat": "KSATFIT",
    "bulk_density": "BDENS",
}
#: Default air-entry head: the classical Mualem-van Genuchten form (no Ippisch modification).
DEFAULT_H_ENPR = 0.0
#: SoilMaterial.bulk_density is g/cm3 (the Rosetta convention); SWAP's BDENS is mg/cm3.
BDENS_PER_G_CM3 = 1000.0
CM_PER_M = 100.0


def soilhydrfunc_table(profile: SoilProfile) -> pd.DataFrame:
    """SOILHYDRFUNC: one row per present horizon.

    ``H_ENPR`` defaults to 0 and ``KSATEXM`` to ``KSATFIT`` when the material does not set them; the other parameters must be present.
    ``ALFAW`` (hysteresis only) is emitted when every present horizon sets it and omitted when none does.

    Raises:
        ValueError: a required parameter is missing, or ALFAW is set on some horizons but not all.
    """
    rows = []
    for i, h in profile.present:
        m = h.material
        missing = [col for attr, col in REQUIRED_HYD.items() if getattr(m, attr) is None]
        if missing:
            raise ValueError(f"Horizon {i} '{m.name}': SWAP requires {', '.join(missing)} — set the parameter(s) on the material")
        rows.append({
            "ORES": m.theta_res,
            "OSAT": m.theta_sat,
            "ALFA": m.alpha,
            "NPAR": m.n,
            "LEXP": m.l_mualem,
            "KSATFIT": m.k_sat,
            "H_ENPR": DEFAULT_H_ENPR if m.h_enpr is None else m.h_enpr,
            "KSATEXM": m.k_sat if m.ksatexm is None else m.ksatexm,
            "BDENS": m.bulk_density * BDENS_PER_G_CM3,  # type: ignore[operator]
            "ALFAW": m.alphaw,
        })
    df = pd.DataFrame(rows)
    if df["ALFAW"].isna().all():
        df = df.drop(columns="ALFAW")
    elif df["ALFAW"].isna().any():
        raise ValueError("ALFAW is set on some horizons but not all; SWAP needs it for every layer or none")
    return df


def soilprofile_table(profile: SoilProfile) -> pd.DataFrame:
    """SOILPROFILE: sublayers and compartments (ISUBLAY, ISOILLAY, HSUBLAY, HCOMP, NCOMP), heights in cm.

    Every present horizon must carry a rule; a horizon without one cannot be silently dropped, because SWAP would then see a profile with a hole in it.
    """
    rows = []
    isublay = 1
    for isoillay, (i, h) in enumerate(profile.present, start=1):
        if h.rule is None:
            raise ValueError(f"Horizon {i} '{h.material.name}' has no discretization rule; set `rule` before exporting")
        top, bottom = profile.bounds[i]
        thickness_cm = (bottom - top) * CM_PER_M
        for fraction in h.rule.compartment_heights:
            hsublay = fraction * thickness_cm
            rows.append({
                "ISUBLAY": isublay,
                "ISOILLAY": isoillay,
                "HSUBLAY": hsublay,
                "HCOMP": hsublay / h.rule.num_compartments,
                "NCOMP": h.rule.num_compartments,
            })
            isublay += 1
    return pd.DataFrame(rows)


def texture_table(profile: SoilProfile) -> pd.DataFrame:
    """SOILTEXTURE (heat flow): PCLAY, PSILT, PSAND, ORGMAT per present horizon."""
    rows = [
        {
            "PCLAY": h.material.clay_content,
            "PSILT": h.material.silt_content,
            "PSAND": h.material.sand_content,
            "ORGMAT": h.material.organic_matter,
        }
        for _i, h in profile.present
    ]
    return pd.DataFrame(rows)
