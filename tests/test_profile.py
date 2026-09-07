"""SoilProfile: geometry, absent horizons, datum helpers, functional updates, JSON round trip."""

import pytest
from pydantic import ValidationError

from simplesoilprofile import CountRule, DiscretizationType, Horizon, SoilProfile
from tests.conftest import EVEN, material


def profile(bottoms, **kw) -> SoilProfile:
    return SoilProfile(
        name=kw.pop("name", "p"),
        horizons=[Horizon(material=material(f"L{i + 1}"), bottom=b, rule=EVEN, key=f"L{i + 1}") for i, b in enumerate(bottoms)],
        **kw,
    )


def test_geometry():
    p = profile([0.5, 2.4, 4.0])
    assert p.bounds == [(0.0, 0.5), (0.5, 2.4), (2.4, 4.0)]
    assert p.thicknesses == [0.5, pytest.approx(1.9), pytest.approx(1.6)]
    assert p.depth == 4.0
    assert p.horizon_at(0.25) == (0, p.horizons[0])
    assert p.horizon_at(2.4) == (1, p.horizons[1])  # boundary belongs to the upper horizon
    assert p.horizon_at(9.0) is None


def test_absent_horizon_keeps_index():
    p = profile([0.5, 2.4, 2.4, 4.0])
    assert p.thicknesses[2] == 0.0
    assert [i for i, _ in p.present] == [0, 1, 3]
    assert p.horizon_at(2.4)[0] == 1
    assert list(p.sublayer_boundaries()) == [0, 1, 3]


def test_ordering_and_depth_validation():
    with pytest.raises(ValueError, match="above the previous bottom"):
        profile([1.0, 0.5])
    with pytest.raises(ValueError, match="positive total depth"):
        profile([0.0])
    with pytest.raises(ValidationError):
        SoilProfile(name="empty", horizons=[])


def test_frozen_and_with():
    p = profile([0.5, 2.4])
    with pytest.raises(ValidationError):
        p.name = "q"  # type: ignore[misc]
    assert p.with_(name="q").name == "q"
    with pytest.raises(ValueError, match="unknown fields"):
        p.with_(layers=[])
    r = p.with_rule("L2", None)
    assert r.horizons[1].rule is None and r.horizons[0].rule is not None
    m = p.with_material(1, material("other"))
    assert m.horizons[1].material.name == "other" and m.horizons[1].key == "L2"
    with pytest.raises(ValidationError):
        p.with_horizons([Horizon(material=material(), bottom=0.0)])


def test_index_of():
    p = profile([0.5, 2.4])
    assert p.index_of(-1) == 1
    assert p.index_of("L2") == 1
    assert p.index_of("L1") == 0  # key first, material name as fallback
    with pytest.raises(KeyError):
        p.index_of("nope")
    with pytest.raises(IndexError):
        p.index_of(5)


def test_datum_helpers():
    p = profile([0.5, 2.4], elevation=32.60)
    assert p.depth_of(31.85) == pytest.approx(0.75)
    assert p.elevation_of(p.depth_of(31.85)) == pytest.approx(31.85)
    with pytest.raises(ValueError, match="no elevation"):
        profile([1.0]).depth_of(30.0)


def test_point_is_lazy_and_optional():
    p = profile([1.0], x=247172.56, y=204590.58)
    assert p.point.x == 247172.56
    with pytest.raises(ValueError, match="no x/y"):
        _ = profile([1.0]).point


def test_json_round_trip(tmp_path):
    p = profile([0.5, 2.4, 2.4, 4.0], x=1.0, y=2.0, elevation=33.2, description="d")
    p = p.with_material(0, p.horizons[0].material.with_(source="lab", source_type="measured", k_sat=12.0))
    path = tmp_path / "p.json"
    p.to_json(path)
    back = SoilProfile.from_json(path)
    assert back == p
    assert SoilProfile.from_json(p.to_json()) == p
    assert back.horizons[0].material.metadata["k_sat"].source == "lab"
    assert back.horizons[0].rule == CountRule(type=DiscretizationType.EVEN, num_sublayers=2, num_compartments=5)
