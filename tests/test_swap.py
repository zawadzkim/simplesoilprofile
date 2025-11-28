"""Tests for the SWAP integration module."""

import io

from simplesoilprofile.models import SoilLayer, SoilProfile
from simplesoilprofile.models.swap import write_swap_soil_file


def test_swap_file_generation():
    """Test generating SWAP soil input file."""
    # Create a test profile
    layer1 = SoilLayer(
        name="TopSoil",
        theta_res=0.02,
        theta_sat=0.4,
        alpha=0.02,
        n=1.5,
        k_sat=10.0,
        l=0.5,
    )

    layer2 = SoilLayer(
        name="Subsoil",
        theta_res=0.05,
        theta_sat=0.45,
        alpha=0.01,
        n=1.3,
        k_sat=5.0,
        l=0.5,
    )

    profile = SoilProfile(
        name="Test Profile",
        layers=[layer1, layer2],
        layer_depths={
            0: (0, 30),
            1: (30, 100),
        },
    )

    # Write to a string buffer
    output = io.StringIO()
    write_swap_soil_file(profile, output)
    content = output.getvalue()

    # Check basic content
    assert "Test Profile" in content
    assert "2    ! ISOILLAY = number of soil layers" in content
    assert "TopSoil" in content
    assert "Subsoil" in content

    # Check layer thicknesses
    assert "30.0 70.0    ! HSUBLAY = thickness of soil layers [cm]" in content

    # Check van Genuchten parameters are included
    for param in ["ORES", "OSAT", "ALFA", "NPAR", "KSAT", "LEXP"]:
        assert param in content
