"""Tests for the core models module."""

import pytest
from simplesoilprofile.models import SoilLayer, SoilProfile


def test_soil_layer_creation():
    """Test creating a valid soil layer."""
    layer = SoilLayer(
        name="Test Layer",
        description="A test layer",
        theta_res=0.02,
        theta_sat=0.4,
        alpha=0.02,
        n=1.5,
        k_sat=10.0,
        l=0.5,
        texture_class="sandy loam",
        clay_content=10.0,
        silt_content=20.0,
        sand_content=70.0,
    )
    
    assert layer.name == "Test Layer"
    assert layer.theta_res == 0.02
    assert layer.texture_class == "sandy loam"


def test_soil_layer_validation():
    """Test soil layer validation rules."""
    # Test invalid water content relationship
    with pytest.raises(ValueError, match="Residual water content must be less than"):
        SoilLayer(
            name="Invalid Layer",
            theta_res=0.5,
            theta_sat=0.4,
            alpha=0.02,
            n=1.5,
            k_sat=10.0,
        )
    
    # Test invalid texture composition
    with pytest.raises(ValueError, match="Clay, silt, and sand contents must sum to 100"):
        SoilLayer(
            name="Invalid Layer",
            theta_res=0.02,
            theta_sat=0.4,
            alpha=0.02,
            n=1.5,
            k_sat=10.0,
            clay_content=20.0,
            silt_content=30.0,
            sand_content=20.0,  # Sum = 70% != 100%
        )


def test_soil_profile_creation():
    """Test creating a valid soil profile."""
    layer1 = SoilLayer(
        name="Top Layer",
        theta_res=0.02,
        theta_sat=0.4,
        alpha=0.02,
        n=1.5,
        k_sat=10.0,
    )
    
    layer2 = SoilLayer(
        name="Bottom Layer",
        theta_res=0.05,
        theta_sat=0.45,
        alpha=0.01,
        n=1.3,
        k_sat=5.0,
    )
    
    profile = SoilProfile(
        name="Test Profile",
        layers=[layer1, layer2],
        layer_depths={
            0: (0, 50),
            1: (50, 100),
        },
        x=100.0,
        y=200.0,
        z=5.0,
    )
    
    assert len(profile.layers) == 2
    assert profile.get_profile_depth() == 100.0
    assert profile.get_layer_at_depth(25)[0] == layer1
    assert profile.get_layer_at_depth(75)[0] == layer2


def test_profile_layer_continuity():
    """Test profile validation for layer continuity."""
    layer = SoilLayer(
        name="Test Layer",
        theta_res=0.02,
        theta_sat=0.4,
        alpha=0.02,
        n=1.5,
        k_sat=10.0,
    )
    
    # Test for gap between layers
    with pytest.raises(ValueError, match="Gap detected between layers"):
        SoilProfile(
            name="Invalid Profile",
            layers=[layer, layer],
            layer_depths={
                0: (0, 50),
                1: (60, 100),  # Gap between 50-60cm
            },
        )
    
    # Test for overlapping layers
    with pytest.raises(ValueError, match="Layer .* top depth must be less than bottom"):
        SoilProfile(
            name="Invalid Profile",
            layers=[layer, layer],
            layer_depths={
                0: (0, 60),
                1: (50, 100),  # Overlap between 50-60cm
            },
        )