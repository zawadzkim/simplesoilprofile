"""SoilLibrary: materials defined once, profiles built from them, fitted values written back."""

import pytest

from simplesoilprofile import Horizon, SoilLibrary, SoilMaterial, SoilProfile
from simplesoilprofile.core.library import FRAME_COLUMNS
from tests.conftest import EVEN, material


@pytest.fixture
def lib() -> SoilLibrary:
    return SoilLibrary(
        name="site",
        materials={m.name: m for m in (material("topsoil"), material("sand", k_sat=1440.0), material("leaky", k_sat=8.0))},
        provenance={"ksat": "CPTu S06 harmonic mean"},
    )


SEQ = [("topsoil", 0.5), ("sand", 2.4), ("leaky", 4.0), ("sand", 6.5)]


def test_keys_must_equal_names():
    with pytest.raises(ValueError, match="mismatched: \\['wrong'\\]"):
        SoilLibrary(name="x", materials={"wrong": material("sand")})


def test_access_and_frame(lib):
    assert lib.keys() == ["topsoil", "sand", "leaky"]
    assert "leaky" in lib and len(lib) == 3 and list(lib) == lib.keys()
    assert lib["leaky"].k_sat == 8.0
    with pytest.raises(KeyError, match="available"):
        lib["gravel"]
    frame = lib.to_frame()
    assert frame.columns.tolist() == FRAME_COLUMNS
    assert frame.index.tolist() == lib.keys() and frame.loc["sand", "k_sat"] == 1440.0


def test_from_library_sets_keys_and_absent_horizons(lib):
    p = SoilProfile.from_library(lib, SEQ, name="S05", elevation=32.6, rules={"topsoil": EVEN})
    assert p.keys == ["topsoil", "sand", "leaky", "sand"]
    assert p.horizons[1].material == lib["sand"] and p.horizons[3].material == lib["sand"]
    assert p.horizons[0].rule == EVEN and p.horizons[1].rule is None
    absent = SoilProfile.from_library(lib, [("topsoil", 0.5), ("leaky", 0.5), ("sand", 2.4)], name="S02")
    assert [i for i, _ in absent.present] == [0, 2]
    with pytest.raises(KeyError, match="gravel"):
        SoilProfile.from_library(lib, [("gravel", 1.0)], name="bad")


def test_with_values_then_rebuild(lib):
    p = SoilProfile.from_library(lib, SEQ, name="S05")
    fitted = lib.with_values({("leaky", "k_sat"): 0.17, ("topsoil", "n"): 1.2495}, note="notebook 04 v4")
    assert lib["leaky"].k_sat == 8.0  # the a-priori library is untouched
    assert fitted["leaky"].k_sat == 0.17 and fitted["leaky"].metadata["k_sat"].source_type == "modeled"
    assert fitted["leaky"].metadata["k_sat"].note == "notebook 04 v4"
    assert "n" not in fitted["leaky"].metadata and fitted["sand"] == lib["sand"]
    assert p.horizons[2].material.k_sat == 8.0  # profiles are derived: unchanged until rebuilt
    r = p.rebuild(fitted)
    assert r.horizons[2].material.k_sat == 0.17 and r.horizons[0].material.n == 1.2495
    assert [h.bottom for h in r.horizons] == [h.bottom for h in p.horizons]
    assert r.horizons[1].material == r.horizons[3].material


def test_with_values_validates(lib):
    with pytest.raises(KeyError, match="gravel"):
        lib.with_values({("gravel", "k_sat"): 1.0})
    with pytest.raises(ValueError, match="not a parameter field"):
        lib.with_values({("sand", "name"): "x"})
    with pytest.raises(ValueError):
        lib.with_values({("sand", "n"): 30.0})


def test_rebuild_needs_keys(lib):
    hand = SoilProfile(name="h", horizons=[Horizon(material=material(), bottom=1.0)])
    with pytest.raises(ValueError, match="no library key"):
        hand.rebuild(lib)
    p = SoilProfile.from_library(lib, SEQ, name="S05")
    smaller = SoilLibrary(name="s", materials={"topsoil": lib["topsoil"]})
    with pytest.raises(KeyError, match="sand"):
        p.rebuild(smaller)


def test_with_material_and_json_round_trip(lib, tmp_path):
    lib2 = lib.with_material(SoilMaterial(name="gravel", k_sat=2300.0, bulk_density=1.7))
    assert lib2.keys()[-1] == "gravel" and "gravel" not in lib
    path = tmp_path / "lib.json"
    lib2.to_json(path)
    assert SoilLibrary.from_json(path) == lib2
    assert SoilLibrary.from_json(lib2.to_json()) == lib2
