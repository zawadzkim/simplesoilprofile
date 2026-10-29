"""Profiles from a SWAP soil database (the tables multiSWAP reads), on synthetic tables."""

import shutil
from pathlib import Path

import pytest

from simplesoilprofile import SublayerRule, profile_from_swap_database
from simplesoilprofile.swap import soilprofile_table

DB = Path(__file__).parent / "data" / "swap_database"


def test_a_profile_from_the_database():
    p = profile_from_swap_database(DB, 1)
    assert p.name == "soil_id 1"
    assert [h.key for h in p.horizons] == ["2", "20"]
    assert [h.bottom for h in p.horizons] == pytest.approx([0.10, 0.30])
    m = p.horizons[0].material
    assert (m.name, m.theta_res, m.theta_sat, m.alpha, m.n) == ("sfu 2", 0.02, 0.40, 0.020, 1.50)
    assert (m.k_sat, m.ksatexm, m.l_mualem, m.h_enpr) == (30.0, 25.0, 0.50, 0.0)
    assert m.bulk_density == pytest.approx(1.3)
    assert (m.clay_content, m.silt_content, m.sand_content, m.organic_matter) == pytest.approx((10.0, 20.0, 70.0, 3.0))


def test_its_sublayers_are_the_databases_in_order():
    t = soilprofile_table(profile_from_swap_database(DB, 1))
    assert list(zip(t["ISOILLAY"], t["HSUBLAY"], t["NCOMP"], strict=True)) == [
        (1, 1.0, 1),
        (1, 4.0, 2),
        (1, 5.0, 1),
        (2, 20.0, 4),
    ]
    assert isinstance(profile_from_swap_database(DB, 1).horizons[0].rule, SublayerRule)


def test_a_bofek_unit_takes_its_representative_profile():
    assert profile_from_swap_database(DB, bofek_unit=1018).name == "soil_id 1"


def test_a_unit_without_one_representative_is_refused():
    with pytest.raises(ValueError, match="BOFEK2020 unit 2000 has 0 representative profiles"):
        profile_from_swap_database(DB, bofek_unit=2000)


def test_the_sss_variant():
    p = profile_from_swap_database(DB, 1, variant="_sss")
    assert len(p.horizons) == 1 and p.horizons[0].bottom == pytest.approx(0.5)
    assert p.horizons[0].rule.sublayers == ((0.5, 10),)


@pytest.mark.parametrize("args", [{}, {"soil_id": 1, "bofek_unit": 1018}])
def test_soil_id_or_bofek_unit(args):
    with pytest.raises(ValueError, match="soil_id or bofek_unit"):
        profile_from_swap_database(DB, **args)


def test_an_unknown_soil_id_is_refused():
    with pytest.raises(ValueError, match=r"no soil_id 7 in soil_profiles_layout\.csv"):
        profile_from_swap_database(DB, 7)


def test_a_unit_missing_from_the_staring_series_is_refused():
    with pytest.raises(ValueError, match=r"sfu 99 is not in staring_series\.csv"):
        profile_from_swap_database(DB, 3)


def test_a_layer_without_texture_has_none(tmp_path):
    db = tmp_path / "db"
    shutil.copytree(DB, db)
    rows = (db / "soil_texture.csv").read_text().splitlines()
    (db / "soil_texture.csv").write_text("\n".join(r for r in rows if not r.startswith("2,")) + "\n")
    m = profile_from_swap_database(db, 2).horizons[0].material
    assert m.bulk_density is None and m.sand_content is None and m.theta_sat == 0.45


def test_a_missing_table_is_named(tmp_path):
    with pytest.raises(FileNotFoundError, match=r"soil_profiles_layout\.csv"):
        profile_from_swap_database(tmp_path, 1)
