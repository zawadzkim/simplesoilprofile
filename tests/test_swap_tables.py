"""SWAP tables: required columns, defaults, unit conversions, absent horizons."""

import pytest

from simplesoilprofile import Horizon, SoilMaterial, SoilProfile
from simplesoilprofile.swap import soilhydrfunc_table, soilprofile_table, texture_table
from tests.conftest import EVEN, material


def prof(*horizons: Horizon) -> SoilProfile:
    return SoilProfile(name="p", horizons=list(horizons))


def test_soilhydrfunc_defaults_and_units():
    table = soilhydrfunc_table(prof(Horizon(material=material(), bottom=0.5)))
    assert table.columns.tolist() == ["ORES", "OSAT", "ALFA", "NPAR", "LEXP", "KSATFIT", "H_ENPR", "KSATEXM", "BDENS"]
    assert table.loc[0, "H_ENPR"] == 0.0
    assert table.loc[0, "KSATEXM"] == table.loc[0, "KSATFIT"]
    assert table.loc[0, "LEXP"] == 0.5
    assert table.loc[0, "BDENS"] == 1500.0  # g/cm3 on the material, mg/cm3 in SWAP


def test_soilhydrfunc_explicit_values_and_missing():
    table = soilhydrfunc_table(prof(Horizon(material=material(h_enpr=-2.0, ksatexm=80.0), bottom=0.5)))
    assert table.loc[0, "H_ENPR"] == -2.0 and table.loc[0, "KSATEXM"] == 80.0
    vg_only = SoilMaterial(name="vg-only", theta_res=0.02, theta_sat=0.4, alpha=0.02, n=1.5, k_sat=10.0)
    with pytest.raises(ValueError, match="Horizon 0 'vg-only': SWAP requires BDENS"):
        soilhydrfunc_table(prof(Horizon(material=vg_only, bottom=0.5)))


def test_alfaw_all_or_none():
    both = prof(Horizon(material=material(alphaw=0.1), bottom=0.5), Horizon(material=material(alphaw=0.2), bottom=1.0))
    assert "ALFAW" in soilhydrfunc_table(both).columns
    mixed = prof(Horizon(material=material(alphaw=0.1), bottom=0.5), Horizon(material=material(), bottom=1.0))
    with pytest.raises(ValueError, match="ALFAW"):
        soilhydrfunc_table(mixed)


def test_soilprofile_table_in_cm_and_complete():
    p = prof(Horizon(material=material("top"), bottom=0.5, rule=EVEN), Horizon(material=material("sub"), bottom=2.4, rule=EVEN))
    table = soilprofile_table(p)
    assert table["HSUBLAY"].sum() == pytest.approx(240.0)
    assert table["ISOILLAY"].tolist() == [1, 1, 2, 2]
    assert (table["NCOMP"] * table["HCOMP"]).to_numpy() == pytest.approx(table["HSUBLAY"].to_numpy())
    with pytest.raises(ValueError, match="Horizon 0 'top' has no discretization rule"):
        soilprofile_table(p.with_rule(0, None))


def test_absent_horizon_skipped_consistently():
    p = prof(
        Horizon(material=material("L1"), bottom=0.5, rule=EVEN),
        Horizon(material=material("L2", organic_matter=0.5), bottom=2.4, rule=EVEN),
        Horizon(material=material("L3"), bottom=2.4, rule=EVEN),
        Horizon(material=material("L4"), bottom=4.0, rule=EVEN),
    )
    hyd, sub, tex = soilhydrfunc_table(p), soilprofile_table(p), texture_table(p)
    assert len(hyd) == len(tex) == 3
    assert sub["ISOILLAY"].max() == 3  # ISOILLAY indexes rows of the hydfunc table, not profile horizons
    assert sub["HSUBLAY"].sum() == pytest.approx(400.0)
    assert tex.loc[1, "ORGMAT"] == 0.5
