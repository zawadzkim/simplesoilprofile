"""Discretization rules and the sublayer resolver."""

import re

import pytest
from pydantic import ValidationError

from simplesoilprofile import CompartmentRule, Horizon, SoilLibrary, SoilProfile, SublayerRule, sublayers
from simplesoilprofile.core import MACP
from simplesoilprofile.swap import soilprofile_table
from tests.conftest import EVEN, material

# The Kinrooi rule of notebook 03: top 0.10 m at 0.01, rest of layer 1 at 0.02, layers 2-6 at 0.05, gravel at 0.10.
KINROOI = {
    "L1": CompartmentRule(hcomp=0.02, top_cap=(0.10, 0.01)),
    **{f"L{i}": CompartmentRule(hcomp=0.05) for i in range(2, 7)},
    "L7": CompartmentRule(hcomp=0.10),
}
LIB = SoilLibrary(name="s06", materials={f"L{i}": material(f"L{i}") for i in range(1, 8)})
S06 = SoilProfile.from_library(
    LIB, [("L1", 0.5), ("L2", 2.4), ("L3", 4.0), ("L4", 6.5), ("L5", 8.2), ("L6", 8.9), ("L7", 12.5)], name="S06", rules=KINROOI
)
# notebook 03's `subs` list for these bounds: (layer, HSUBLAY cm, HCOMP cm)
NOTEBOOK_SUBS = [(1, 10, 1), (1, 40, 2), (2, 190, 5), (3, 160, 5), (4, 250, 5), (5, 170, 5), (6, 70, 5), (7, 360, 10)]


def test_kinrooi_rule_reproduces_notebook_03():
    table = soilprofile_table(S06)
    assert table["ISUBLAY"].tolist() == list(range(1, 9))
    assert list(zip(table["ISOILLAY"], table["HSUBLAY"], table["HCOMP"], strict=True)) == [
        (lay, float(hs), float(hc)) for lay, hs, hc in NOTEBOOK_SUBS
    ]
    assert table["NCOMP"].tolist() == [hs // hc for _, hs, hc in NOTEBOOK_SUBS]
    assert table["HSUBLAY"].sum() == 1250.0


def test_sublayers_rows():
    rows = sublayers(S06)
    assert [s.horizon for s in rows] == [0, 0, 1, 2, 3, 4, 5, 6]
    assert rows[0].top == 0.0 and rows[0].bottom == pytest.approx(0.10) and rows[0].ncomp == 10
    assert rows[1].top == pytest.approx(0.10) and rows[1].bottom == 0.5 and rows[1].ncomp == 20
    assert rows[-1].thickness == pytest.approx(3.6) and rows[-1].ncomp == 36


def test_absent_horizon_renumbers_isoillay():
    p = SoilProfile.from_library(
        LIB, [("L1", 0.5), ("L2", 2.4), ("L3", 2.4), ("L4", 6.5)], name="S02", rules=KINROOI
    )
    rows = sublayers(p)
    assert [(s.horizon, s.isoillay) for s in rows] == [(0, 1), (0, 1), (1, 2), (3, 3)]


def test_not_a_multiple_raises():
    p = SoilProfile(name="p", horizons=[Horizon(material=material(), bottom=0.07, rule=CompartmentRule(hcomp=0.02))])
    with pytest.raises(ValueError, match=re.escape("0.07 m is not a multiple of the compartment height 0.02 m (remainder 0.01 m)")):
        sublayers(p)


def test_float_multiples_are_accepted():
    """0.07 / 0.01 is 7.000000000000001 in binary; 2.4 - 0.5 = 1.9000000000000001."""
    p = SoilProfile(name="p", horizons=[
        Horizon(material=material(), bottom=0.07, rule=CompartmentRule(hcomp=0.01)),
        Horizon(material=material(), bottom=2.4, rule=CompartmentRule(hcomp=0.05, top_cap=(0.03, 0.01))),
    ])
    rows = sublayers(p)
    assert [s.ncomp for s in rows] == [7, 3, 46]
    assert soilprofile_table(p)["HSUBLAY"].tolist() == [7.0, 3.0, 230.0]


def test_top_cap_validation():
    with pytest.raises(ValidationError):
        CompartmentRule(hcomp=0.02, top_cap=(0.0, 0.01))
    p = SoilProfile(name="p", horizons=[Horizon(material=material(), bottom=0.1, rule=CompartmentRule(hcomp=0.02, top_cap=(0.1, 0.01)))])
    with pytest.raises(ValueError, match=re.escape("top cap 0.1 m is not thinner than the horizon")):
        sublayers(p)


def test_missing_rule_strict_and_lenient():
    p = S06.with_rule("L3", None)
    with pytest.raises(ValueError, match="Horizon 2 'L3' has no discretization rule"):
        sublayers(p)
    assert [s.horizon for s in sublayers(p, strict=False)] == [0, 0, 1, 3, 4, 5, 6]
    assert 2 not in p.sublayer_boundaries() and p.sublayer_boundaries()[0] == pytest.approx([0.0, 0.10, 0.5])


def test_macp_limit():
    p = SoilProfile(name="deep", horizons=[Horizon(material=material(), bottom=50.01, rule=CompartmentRule(hcomp=0.01))])
    with pytest.raises(ValueError, match=re.escape(f"5001 compartments exceed SWAP's limit of {MACP}")):
        sublayers(p)


def test_count_rule_unchanged():
    p = SoilProfile(name="p", horizons=[Horizon(material=material(), bottom=0.5, rule=EVEN), Horizon(material=material(), bottom=2.4, rule=EVEN)])
    table = soilprofile_table(p)
    assert table["HSUBLAY"].tolist() == [25.0, 25.0, 95.0, 95.0]
    assert table["HCOMP"].tolist() == [5.0, 5.0, 19.0, 19.0] and table["NCOMP"].tolist() == [5] * 4


def test_rules_round_trip_json(tmp_path):
    path = tmp_path / "s06.json"
    S06.to_json(path)
    back = SoilProfile.from_json(path)
    assert back == S06 and isinstance(back.horizons[0].rule, CompartmentRule) and back.horizons[0].rule.top_cap == (0.10, 0.01)


def db_profile(*rules) -> SoilProfile:
    bottoms, depth = [], 0.0
    for r in rules:
        depth += sum(t for t, _ in r.sublayers)
        bottoms.append(depth)
    return SoilProfile(
        name="db",
        horizons=[
            Horizon(material=material(f"m{i}"), bottom=b, rule=r)
            for i, (b, r) in enumerate(zip(bottoms, rules, strict=True))
        ],
    )


def test_sublayer_rule_gives_its_sublayers():
    p = db_profile(SublayerRule(sublayers=((0.01, 1), (0.04, 2), (0.05, 1))), SublayerRule(sublayers=((0.20, 4),)))
    table = soilprofile_table(p)
    assert list(zip(table["ISOILLAY"], table["HSUBLAY"], table["HCOMP"], table["NCOMP"], strict=True)) == [
        (1, 1.0, 1.0, 1),
        (1, 4.0, 2.0, 2),
        (1, 5.0, 5.0, 1),
        (2, 20.0, 5.0, 4),
    ]


def test_sublayer_rule_must_fill_its_horizon():
    p = SoilProfile(
        name="db", horizons=[Horizon(material=material(), bottom=0.10, rule=SublayerRule(sublayers=((0.05, 1),)))]
    )
    with pytest.raises(ValueError, match=r"add up to 0\.05 m, the horizon is 0\.1 m"):
        sublayers(p)


@pytest.mark.parametrize("bad", [((0.0, 1),), ((0.1, 0),), ()])
def test_sublayer_rule_refuses_a_degenerate_sublayer(bad):
    with pytest.raises(ValidationError):
        SublayerRule(sublayers=bad)


def test_sublayer_rule_survives_json():
    p = db_profile(SublayerRule(sublayers=((0.01, 1), (0.04, 2))))
    q = SoilProfile.from_json(p.to_json())
    assert q.horizons[0].rule == p.horizons[0].rule
