"""Rosetta pedotransfer bridge (rosetta-soil >= 0.3).

``rosetta()`` returns arithmetic means in linear units — theta [cm3/cm3], alpha [1/cm], n [-], Ksat and K0 [cm/d], L [-] — so no back-transform is applied here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from rosetta import SoilData, rosetta


@dataclass(frozen=True)
class RosettaPrediction:
    """One Rosetta prediction in linear units."""

    theta_res: float
    theta_sat: float
    alpha: float
    n: float
    k_sat: float
    k0: float
    l_mualem: float
    version: int
    code: int
    """Rosetta input code: 2 = sand/silt/clay, 3 = + bulk density (higher codes need retention points)."""


def predict(
    sand: float,
    silt: float,
    clay: float,
    bulk_density: float | None = None,
    version: Literal[1, 2, 3] = 3,
) -> RosettaPrediction:
    """Predict van Genuchten-Mualem parameters from texture (percent) and optional bulk density (g/cm3)."""
    predictors = [sand, silt, clay] if bulk_density is None else [sand, silt, clay, bulk_density]
    mean, _stdev, codes = rosetta(version, SoilData.from_iter([predictors]))
    theta_res, theta_sat, alpha, n, k_sat, k0, l_mualem = (float(v) for v in mean[0])
    return RosettaPrediction(theta_res, theta_sat, alpha, n, k_sat, k0, l_mualem, int(version), int(codes[0]))
