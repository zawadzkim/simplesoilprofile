"""Tests for the SWAP integration module."""

import pandas as pd

from simplesoilprofile.models import SoilLayer, SoilProfile
from simplesoilprofile.models.swap import (
    profile_to_soilhydfunc_table,
    profile_to_texture_table,
)


def test_profile_to_soilhydfunc_table():
    """Test converting profile to SOILHYDRFUNC table."""
    # Create a test profile
    layer1 = SoilLayer(
        name="TopSoil",
        theta_res=0.02,
        theta_sat=0.4,
        alpha=0.02,
        n=1.5,
        k_sat=10.0,
        lambda_param=0.5,
    )

    layer2 = SoilLayer(
        name="Subsoil",
        theta_res=0.05,
        theta_sat=0.45,
        alpha=0.01,
        n=1.3,
        k_sat=5.0,
        lambda_param=0.5,
    )

    profile = SoilProfile(
        name="Test Profile",
        layers=[layer1, layer2],
        layer_bottoms=[30, 100],
    )

    # Convert to table
    table = profile_to_soilhydfunc_table(profile)

    # Check basic structure
    assert isinstance(table, pd.DataFrame)
    assert len(table) == 2  # Two layers

    # Check expected columns exist (only non-null ones should remain)
    expected_cols = ["ORES", "OSAT", "ALFA", "NPAR", "LEXP", "KSATFIT"]
    for col in expected_cols:
        assert col in table.columns

    # Check values
    assert table.iloc[0]["ORES"] == 0.02
    assert table.iloc[0]["OSAT"] == 0.4
    assert table.iloc[1]["ORES"] == 0.05
    assert table.iloc[1]["OSAT"] == 0.45


def test_profile_to_texture_table():
    """Test converting profile to SOILTEXTURE table."""
    # Create a test profile with texture data
    layer1 = SoilLayer(
        name="TopSoil",
        clay_content=25.0,
        silt_content=35.0,
        sand_content=40.0,
        organic_matter=2.5,
    )

    profile = SoilProfile(
        name="Test Profile",
        layers=[layer1],
        layer_bottoms=[30],
    )

    # Convert to table
    table = profile_to_texture_table(profile)

    # Check basic structure
    assert isinstance(table, pd.DataFrame)
    assert len(table) == 1

    # Check columns
    expected_cols = ["PCLAY", "PSILT", "PSAND", "ORGMAT"]
    for col in expected_cols:
        assert col in table.columns

    # Check values
    assert table.iloc[0]["PCLAY"] == 25.0
    assert table.iloc[0]["PSILT"] == 35.0
    assert table.iloc[0]["PSAND"] == 40.0
    assert table.iloc[0]["ORGMAT"] == 2.5
