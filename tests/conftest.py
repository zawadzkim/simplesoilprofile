"""Shared fixtures; a headless matplotlib backend so the plotting tests run without a display."""

import matplotlib
import pytest

from simplesoilprofile import CountRule, DiscretizationType, Horizon, SoilMaterial, SoilProfile

matplotlib.use("Agg")

EVEN = CountRule(type=DiscretizationType.EVEN, num_sublayers=2, num_compartments=5)


def material(name: str = "sand", **overrides) -> SoilMaterial:
    values = {
        "theta_res": 0.04,
        "theta_sat": 0.38,
        "alpha": 0.05,
        "n": 1.48,
        "k_sat": 100.0,
        "bulk_density": 1.5,
        "texture_class": "sand",
        "sand_content": 92.0,
        "silt_content": 5.0,
        "clay_content": 3.0,
    }
    values.update(overrides)
    return SoilMaterial(name=name, **values)


@pytest.fixture
def full_material():
    return material


@pytest.fixture
def two_horizon_profile() -> SoilProfile:
    return SoilProfile(
        name="p",
        x=247172.56,
        y=204590.58,
        elevation=33.2,
        horizons=[
            Horizon(material=material("top", texture_class="sandy loam"), bottom=0.5, rule=EVEN),
            Horizon(material=material("sub", texture_class="clay loam", k_sat=5.0), bottom=2.4, rule=EVEN),
        ],
    )
