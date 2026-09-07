"""SoilMaterial: validation, immutability, provenance, functional updates."""

import pytest
from pydantic import ValidationError

from simplesoilprofile import ProvenanceEntry, SoilMaterial
from tests.conftest import material


def test_frozen():
    m = material()
    with pytest.raises(ValidationError):
        m.n = 30.0  # type: ignore[misc]


def test_with_revalidates():
    m = material()
    assert m.with_(n=1.6).n == 1.6
    with pytest.raises(ValidationError):
        m.with_(n=30.0)  # n is bounded to (1, 9], SWAP's NPAR range
    with pytest.raises(ValueError, match="unknown fields"):
        m.with_(npar=1.5)


def test_residual_below_saturated_even_at_zero():
    with pytest.raises(ValueError, match="Residual water content"):
        SoilMaterial(name="x", theta_res=0.0, theta_sat=0.0)
    with pytest.raises(ValueError, match="Residual water content"):
        material().with_(theta_res=0.5, theta_sat=0.4)


def test_metadata_keys_are_checked():
    with pytest.raises(ValueError, match="unknown: \\['npar'\\]"):
        SoilMaterial(name="x", metadata={"npar": ProvenanceEntry()})
    m = material().with_(source="lab", source_type="measured", k_sat=42.0)
    assert m.k_sat == 42.0
    assert m.metadata["k_sat"].source == "lab"
    assert m.metadata["k_sat"].source_type == "measured"
    assert "n" not in m.metadata


def test_with_metadata():
    m = material().with_metadata(k_sat={"source": "CPTu S06", "source_type": "derived"})
    assert m.metadata["k_sat"].source == "CPTu S06"


def test_texture_helpers():
    m = material()
    assert m.has_texture and m.sum_texture == 100.0
    assert SoilMaterial(name="bare").sum_texture is None
    n = material(sand_content=73.0, silt_content=22.0, clay_content=3.0).normalized_fractions()
    assert n.sum_texture == pytest.approx(100.0)
    assert n.metadata["sand_content"].source_type == "derived"
    m100 = material()
    assert m100.normalized_fractions() is m100


def test_with_texture_class_usda_and_flemish():
    usda = SoilMaterial(name="x").with_texture_class("loamy sand")
    assert (usda.sand_content, usda.silt_content, usda.clay_content) == (82.0, 12.0, 6.0)
    assert usda.texture_class == "loamy sand"
    assert "Levi" in usda.metadata["sand_content"].source
    flemish = SoilMaterial(name="y").with_texture_class("lemig zand", system="flemish")
    assert flemish.sand_content == pytest.approx(75.0)
    with pytest.raises(ValueError, match="Unknown texture system"):
        SoilMaterial(name="z").with_texture_class("sand", system="iso")


# --- Rosetta ----------------------------------------------------------------------


def test_rosetta_linear_units():
    """rosetta-soil >= 0.3 returns linear values; the 0.0.9 10** back-transform gave n ~ 30."""
    m = SoilMaterial(name="topsoil", sand_content=82, silt_content=13, clay_content=5).with_rosetta(version=2)
    assert 1.1 < m.n < 2.5
    assert 0.001 < m.alpha < 0.2
    assert 1.0 < m.k_sat < 1000.0
    assert 0.0 <= m.theta_res < m.theta_sat <= 0.6
    assert m.l_mualem != 0.5  # Rosetta's own L, not the default
    assert m.metadata["n"].source_type == "modeled"
    assert "Rosetta v2" in m.metadata["n"].source


def test_rosetta_keep_ksat():
    m = SoilMaterial(name="t", sand_content=82, silt_content=13, clay_content=5, k_sat=104.0)
    r = m.with_rosetta(version=2, keep_ksat=True)
    assert r.k_sat == 104.0
    assert "k_sat" not in r.metadata
    assert "n" in r.metadata


def test_rosetta_bulk_density_predictor():
    texture = {"sand_content": 60, "silt_content": 25, "clay_content": 15}
    without = SoilMaterial(name="a", **texture).with_rosetta(version=3)
    with_bd = SoilMaterial(name="b", bulk_density=1.6, **texture).with_rosetta(version=3)
    ignored = SoilMaterial(name="c", bulk_density=1.6, **texture).with_rosetta(version=3, use_bulk_density=False)
    assert "input code 2" in without.metadata["n"].source
    assert "input code 3" in with_bd.metadata["n"].source
    assert with_bd.theta_sat != pytest.approx(without.theta_sat)
    assert ignored.theta_sat == pytest.approx(without.theta_sat)


def test_rosetta_requires_texture():
    with pytest.raises(ValueError, match="sand, silt and clay"):
        SoilMaterial(name="bare").with_rosetta()
