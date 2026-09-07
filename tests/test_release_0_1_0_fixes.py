"""Regression tests for the bugs fixed on release/v0.1.0.

Each test pins one behaviour that was wrong in 0.0.9: the Rosetta bridge against
rosetta-soil >= 0.3, the SWAP exporters (required columns, undiscretized layers),
absent layers, and the package version.
"""

import pandas as pd
import pytest

import simplesoilprofile
from simplesoilprofile.models import SoilLayer, SoilProfile
from simplesoilprofile.models.discretization import DiscretizationType, LayerDiscretization
from simplesoilprofile.models.swap import (
    profile_to_soilhydfunc_table,
    profile_to_sublayer_table,
    profile_to_texture_table,
)

EVEN = LayerDiscretization(type=DiscretizationType.EVEN, num_sublayers=2, num_compartments=5)


def full_layer(name: str = "sand", **overrides) -> SoilLayer:
    values = {
        "theta_res": 0.04,
        "theta_sat": 0.38,
        "alpha": 0.05,
        "n": 1.48,
        "k_sat": 100.0,
        "bulk_density": 1.5,
        "discretization": EVEN,
    }
    values.update(overrides)
    return SoilLayer(name=name, **values)


# --- Rosetta bridge -----------------------------------------------------------------


def test_rosetta_returns_linear_units():
    """rosetta-soil >= 0.3 returns linear values; the old 10** back-transform gave n ~ 30."""
    layer = SoilLayer(name="topsoil", sand_content=82, silt_content=13, clay_content=5)
    predicted = layer.predict_van_genuchten(version=2)
    assert 1.1 < layer.n < 2.5
    assert 0.001 < layer.alpha < 0.2
    assert 1.0 < layer.k_sat < 1000.0
    assert 0.0 <= layer.theta_res < layer.theta_sat <= 0.6
    assert layer.lambda_param == pytest.approx(predicted["lambda_param"])
    assert layer.metadata["n"].source_type == "modeled"
    assert "Rosetta v2" in layer.metadata["n"].source


def test_rosetta_keep_ksat_preserves_measured_conductivity():
    layer = SoilLayer(name="topsoil", sand_content=82, silt_content=13, clay_content=5, k_sat=104.0)
    predicted = layer.predict_van_genuchten(version=2, keep_ksat=True)
    assert layer.k_sat == 104.0
    assert predicted["k_sat"] != 104.0
    assert "k_sat" not in layer.metadata


def test_rosetta_uses_bulk_density_when_present():
    texture = {"sand_content": 60, "silt_content": 25, "clay_content": 15}
    without = SoilLayer(name="a", **texture)
    with_bd = SoilLayer(name="b", bulk_density=1.6, **texture)
    without.predict_van_genuchten(version=3)
    with_bd.predict_van_genuchten(version=3)
    assert "input code 2" in without.metadata["n"].source
    assert "input code 3" in with_bd.metadata["n"].source
    assert with_bd.theta_sat != pytest.approx(without.theta_sat)


def test_rosetta_requires_texture():
    with pytest.raises(ValueError, match="sand, silt and clay"):
        SoilLayer(name="bare").predict_van_genuchten()


def test_theta_res_zero_is_still_validated():
    with pytest.raises(ValueError, match="Residual water content"):
        SoilLayer(name="x", theta_res=0.0, theta_sat=0.0)


# --- SWAP exporters -----------------------------------------------------------------


def test_soilhydfunc_fills_swap_defaults():
    profile = SoilProfile(name="p", layers=[full_layer()], layer_bottoms=[50])
    table = profile_to_soilhydfunc_table(profile)
    assert table.columns.tolist() == ["ORES", "OSAT", "ALFA", "NPAR", "LEXP", "KSATFIT", "H_ENPR", "KSATEXM", "BDENS"]
    assert table.loc[0, "H_ENPR"] == 0.0
    assert table.loc[0, "KSATEXM"] == table.loc[0, "KSATFIT"]
    assert table.loc[0, "LEXP"] == 0.5
    assert table.loc[0, "BDENS"] == 1500.0  # g/cm3 on the layer, mg/cm3 in SWAP


def test_soilhydfunc_keeps_explicit_h_enpr_and_ksatexm():
    profile = SoilProfile(name="p", layers=[full_layer(h_enpr=-2.0, ksatexm=80.0)], layer_bottoms=[50])
    table = profile_to_soilhydfunc_table(profile)
    assert table.loc[0, "H_ENPR"] == -2.0
    assert table.loc[0, "KSATEXM"] == 80.0


def test_soilhydfunc_names_missing_parameters():
    layer = SoilLayer(name="vg-only", theta_res=0.02, theta_sat=0.4, alpha=0.02, n=1.5, k_sat=10.0)
    profile = SoilProfile(name="p", layers=[layer], layer_bottoms=[50])
    with pytest.raises(ValueError, match="Layer 0 'vg-only': SWAP requires BDENS"):
        profile_to_soilhydfunc_table(profile)


def test_soilhydfunc_alfaw_all_or_none():
    both = SoilProfile(name="p", layers=[full_layer(alphaw=0.1), full_layer(alphaw=0.2)], layer_bottoms=[50, 100])
    assert "ALFAW" in profile_to_soilhydfunc_table(both).columns
    mixed = SoilProfile(name="p", layers=[full_layer(alphaw=0.1), full_layer()], layer_bottoms=[50, 100])
    with pytest.raises(ValueError, match="ALFAW"):
        profile_to_soilhydfunc_table(mixed)


def test_sublayer_table_refuses_undiscretized_layer():
    profile = SoilProfile(name="p", layers=[full_layer(discretization=None), full_layer()], layer_bottoms=[50, 240])
    with pytest.raises(ValueError, match="Layer 0 'sand' has no discretization"):
        profile_to_sublayer_table(profile)


def test_sublayer_table_covers_the_whole_profile():
    profile = SoilProfile(name="p", layers=[full_layer("top"), full_layer("sub")], layer_bottoms=[50, 240])
    table = profile_to_sublayer_table(profile)
    assert table["HSUBLAY"].sum() == pytest.approx(240.0)
    assert table["ISOILLAY"].tolist() == [1, 1, 2, 2]
    assert (table["NCOMP"] * table["HCOMP"] == table["HSUBLAY"]).all()


# --- absent (zero-thickness) layers -------------------------------------------------


def test_absent_layer_keeps_its_index():
    layers = [full_layer("L1"), full_layer("L2"), full_layer("L3")]
    profile = SoilProfile(name="S02", layers=layers, layer_bottoms=[50, 240, 240])
    assert profile.layer_thicknesses == [50, 190, 0]
    assert [i for i, *_ in profile.present_layers()] == [0, 1]
    assert profile.get_layer_at_depth(240) == (layers[1], 1)


def test_absent_layer_is_skipped_consistently_by_exporters():
    layers = [full_layer("L1"), full_layer("L2", organic_matter=0.5), full_layer("L3"), full_layer("L4")]
    profile = SoilProfile(name="S02", layers=layers, layer_bottoms=[50, 240, 240, 400])
    hyd = profile_to_soilhydfunc_table(profile)
    sub = profile_to_sublayer_table(profile)
    tex = profile_to_texture_table(profile)
    assert len(hyd) == len(tex) == 3
    assert sub["ISOILLAY"].max() == 3  # ISOILLAY indexes rows of the hydfunc table, not profile layers
    assert sub["HSUBLAY"].sum() == pytest.approx(400.0)
    assert tex.loc[1, "ORGMAT"] == 0.5


def test_decreasing_bottoms_still_rejected():
    with pytest.raises(ValueError, match="must not be less"):
        SoilProfile(name="bad", layers=[full_layer(), full_layer()], layer_bottoms=[100, 50])


def test_profile_needs_positive_depth():
    with pytest.raises(ValueError, match="positive total depth"):
        SoilProfile(name="flat", layers=[full_layer()], layer_bottoms=[0])


# --- packaging ------------------------------------------------------------------------


def test_version_comes_from_package_metadata():
    assert simplesoilprofile.__version__ != "0.0.1"
    assert isinstance(pd.__version__, str)  # pandas is a declared runtime dependency


# --- DOV -> Rosetta chain -------------------------------------------------------------


def test_dov_profile_feeds_rosetta(monkeypatch):
    """The DOV texture layers (dovwms dict shape) build a profile whose layers Rosetta can parameterize."""
    import sys
    import types

    from shapely.geometry import Point

    from simplesoilprofile.models.profile import get_profile_from_dov

    def fake_dov(x, y, fetch_elevation=False, crs="EPSG:31370"):
        layers = []
        for name, top, bottom, sand, silt, clay in [
            ("Layer_0-30cm", 0, 30, 72.0, 22.0, 6.0),
            ("Layer_30-60cm", 30, 60, 70.0, 23.0, 7.0),
            ("Layer_60-100cm", 60, 100, 75.0, 19.0, 6.0),
            ("Layer_100-150cm", 100, 150, 80.0, 15.0, 5.0),
        ]:
            layers.append({
                "name": name, "layer_top": top, "layer_bottom": bottom,
                "sand_content": sand, "silt_content": silt, "clay_content": clay,
                "metadata": {k: {"source": "DOV WMS", "uncertainty": 5.0}
                             for k in ("sand_content", "silt_content", "clay_content")},
            })
        out = {"layers": layers}
        if fetch_elevation:
            out["elevation"] = {"elevation": 33.2}
        return out

    monkeypatch.setitem(sys.modules, "dovwms", types.SimpleNamespace(get_profile_from_dov=fake_dov))

    profile = get_profile_from_dov(Point(247172.56, 204590.58), fetch_elevation=True)
    assert profile.elevation == 33.2
    assert profile.layer_bottoms == [30, 60, 100, 150]
    assert profile.layers[0].metadata["sand_content"].source == "DOV WMS"

    for layer in profile.layers:
        layer.predict_van_genuchten(version=2)
    assert all(1.1 < layer.n < 2.5 for layer in profile.layers)
    assert profile.layers[0].metadata["n"].source_type == "modeled"
