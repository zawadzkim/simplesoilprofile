"""Parameter specs resolved per profile, and the fitted values written back."""

import importlib.util

import pytest

from simplesoilprofile import SoilLibrary, SoilProfile
from simplesoilprofile.swap import ParamSpec, apply_fit, param, params, soilhydrfunc_table
from simplesoilprofile.swap.params import PYSWAP_PARAM_FIELDS
from tests.conftest import material

LIB = SoilLibrary(name="s", materials={m.name: m for m in (material("topsoil"), material("sand"), material("leaky", k_sat=8.0))})
FULL = SoilProfile.from_library(LIB, [("topsoil", 0.5), ("sand", 2.4), ("leaky", 4.0), ("sand", 6.5)], name="S05")
NO_LENS = SoilProfile.from_library(LIB, [("topsoil", 0.5), ("sand", 2.4), ("leaky", 2.4), ("sand", 6.5)], name="S02")


def test_row_follows_present_horizons():
    assert param(FULL, "leaky", "k_sat", (0.1, 50)).path == "soilprofile.soilhydrfunc.KSATFIT[2]"
    assert param(FULL, "topsoil", "n", (1.1, 1.8)).path == "soilprofile.soilhydrfunc.NPAR[0]"
    with pytest.raises(ValueError, match=r"'leaky' is absent .* in profile 'S02'"):
        param(NO_LENS, "leaky", "k_sat", (0.1, 50))
    with pytest.raises(KeyError, match="not a horizon key"):
        param(FULL, "gravel", "k_sat", (0.1, 50))
    with pytest.raises(ValueError, match="not a SOILHYDRFUNC parameter"):
        param(FULL, "sand", "porosity", (0.1, 0.5))


def test_ksat_ties_ksatexm_and_repeated_material_drives_all_rows():
    spec = param(FULL, "sand", "k_sat", (10, 3000), transform="log10")
    assert spec.path == "soilprofile.soilhydrfunc.KSATFIT[1]"
    assert spec.also == (
        "soilprofile.soilhydrfunc.KSATFIT[3]",
        "soilprofile.soilhydrfunc.KSATEXM[1]",
        "soilprofile.soilhydrfunc.KSATEXM[3]",
    )
    assert spec.name == "k_sat_sand" and spec.transform == "log10"
    untied = param(FULL, "leaky", "k_sat", (0.1, 50), tie_ksat=False)
    assert untied.also == ()


def test_bulk_density_bounds_cross_the_unit_boundary():
    spec = param(FULL, "topsoil", "bulk_density", (1.3, 1.7))
    assert spec.bounds == (1300.0, 1700.0) and spec.path.endswith("BDENS[0]")
    fitted = apply_fit(LIB, {spec.name: 1550.0}, [spec])
    assert fitted["topsoil"].bulk_density == pytest.approx(1.55)


def test_as_dict_matches_pyswap_param_fields():
    spec = param(FULL, "leaky", "k_sat", (0.1, 50), name="k_L3")
    assert list(spec.as_dict()) == list(PYSWAP_PARAM_FIELDS)
    assert spec.as_dict()["name"] == "k_L3"
    assert spec.paths == (spec.path, *spec.also)


@pytest.mark.skipif(importlib.util.find_spec("pyswap") is None, reason="pyswap not installed")
def test_pyswap_param_accepts_the_spec():
    import dataclasses

    from pyswap.parameters import Param

    assert tuple(f.name for f in dataclasses.fields(Param)) == PYSWAP_PARAM_FIELDS
    spec = param(FULL, "leaky", "k_sat", (0.1, 50), transform="log10")
    p = Param(**spec.as_dict())
    assert p.paths == spec.paths


def test_apply_fit_round_trip():
    specs = params(FULL, [
        {"key": "leaky", "attribute": "k_sat", "bounds": (0.1, 50), "transform": "log10", "name": "k_L3"},
        {"key": "topsoil", "attribute": "n", "bounds": (1.1, 1.8), "name": "n_L1"},
    ])
    fitted = apply_fit(LIB, {"k_L3": 0.17, "n_L1": 1.2495}, specs, note="notebook 04 v4")
    rebuilt = FULL.rebuild(fitted)
    table = soilhydrfunc_table(rebuilt)
    assert table.loc[2, "KSATFIT"] == 0.17 and table.loc[2, "KSATEXM"] == 0.17
    assert table.loc[0, "NPAR"] == 1.2495
    assert fitted["leaky"].metadata["k_sat"].note == "notebook 04 v4"
    assert LIB["leaky"].k_sat == 8.0
    with pytest.raises(KeyError, match="no fitted value for parameter 'n_L1'"):
        apply_fit(LIB, {"k_L3": 0.17}, specs)


def test_paramspec_is_frozen():
    spec = param(FULL, "leaky", "k_sat", (0.1, 50))
    with pytest.raises(AttributeError):
        spec.name = "x"  # type: ignore[misc]
    assert isinstance(spec, ParamSpec)
