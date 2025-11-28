"""Tests for the plotting utilities."""

import matplotlib.pyplot as plt
import pytest

from simplesoilprofile.models import SoilLayer, SoilProfile
from simplesoilprofile.plotting.profile_plot import plot_profile


@pytest.fixture
def sample_profile():
    """Create a sample soil profile for testing."""
    layer1 = SoilLayer(
        name="Topsoil",
        theta_res=0.02,
        theta_sat=0.4,
        alpha=0.02,
        n=1.5,
        k_sat=10.0,
        texture_class="sandy loam",
        clay_content=10.0,
        silt_content=20.0,
        sand_content=70.0,
    )

    layer2 = SoilLayer(
        name="Subsoil",
        theta_res=0.05,
        theta_sat=0.45,
        alpha=0.01,
        n=1.3,
        k_sat=5.0,
        texture_class="clay loam",
        clay_content=30.0,
        silt_content=35.0,
        sand_content=35.0,
    )

    return SoilProfile(
        name="Test Profile",
        layers=[layer1, layer2],
        layer_bottoms=[30, 100],  # Bottom depths of each layer
    )


def test_plot_creation(sample_profile):
    """Test creating a soil profile plot."""
    fig, ax = plt.subplots()
    ax = plot_profile(sample_profile, ax=ax)

    # Check basic plot properties
    assert ax.get_title().startswith("Soil Profile: Test Profile")
    assert ax.get_ylabel() == "Depth [cm]"
    assert not ax.xaxis.get_visible()  # X-axis should be hidden

    # Check depth range
    ymin, ymax = ax.get_ylim()
    assert ymax == 0  # Surface at 0
    assert ymin < -100  # Bottom should extend past deepest layer

    plt.close(fig)


def test_plot_annotations(sample_profile):
    """Test plot annotations and text elements."""
    fig, ax = plt.subplots()
    ax = plot_profile(sample_profile, ax=ax, show_layer_properties=True)

    # Check that we have text annotations
    texts = ax.texts
    assert len(texts) > 0

    # Basic title check (coordinates won't be present since profile has no location)
    assert sample_profile.name in ax.get_title()

    plt.close(fig)
