"""Node geometry, interval weights and the SWAP output mapping."""

import numpy as np
import pandas as pd
import pytest

from simplesoilprofile import CompartmentRule, Horizon, SoilProfile
from simplesoilprofile.core import interval_weights, node_bounds, node_depths, node_horizons
from simplesoilprofile.swap import at_nodes, interval_mean
from tests.conftest import material

P = SoilProfile(name="p", horizons=[
    Horizon(material=material("L1"), bottom=0.5, rule=CompartmentRule(hcomp=0.02, top_cap=(0.10, 0.01))),
    Horizon(material=material("L2"), bottom=2.4, rule=CompartmentRule(hcomp=0.05)),
    Horizon(material=material("L3"), bottom=2.4, rule=CompartmentRule(hcomp=0.05)),
    Horizon(material=material("L4"), bottom=4.0, rule=CompartmentRule(hcomp=0.10)),
])
N = 10 + 20 + 38 + 16


def test_node_geometry():
    b = node_bounds(P)
    z = node_depths(P)
    assert b.shape == (N, 2) and len(z) == N
    assert z[0] == pytest.approx(0.005) and z[10] == pytest.approx(0.11) and z[-1] == pytest.approx(3.95)
    assert np.allclose(b[1:, 0], b[:-1, 1])  # compartments tile the profile
    assert b[-1, 1] == pytest.approx(4.0)
    assert node_horizons(P).tolist() == [0] * 30 + [1] * 38 + [3] * 16  # the absent horizon 2 has no nodes
    assert all(P.horizon_at(d)[0] == h for d, h in zip(z, node_horizons(P), strict=True))


def test_interval_weights():
    w = interval_weights(P, 0.0, 0.3)
    assert w.sum() == pytest.approx(1.0)
    assert w[:10] == pytest.approx(0.01 / 0.3) and w[10:20] == pytest.approx(0.02 / 0.3) and w[20:].sum() == 0.0
    w2 = interval_weights(P, 0.3, 0.6)   # straddles the L1/L2 boundary and cuts a 5 cm compartment
    assert w2.sum() == pytest.approx(1.0)
    assert w2[30] == pytest.approx(0.05 / 0.3) and w2[31] == pytest.approx(0.05 / 0.3) and w2[32] == 0.0
    with pytest.raises(ValueError, match="must be below"):
        interval_weights(P, 0.3, 0.3)
    with pytest.raises(ValueError, match="outside profile"):
        interval_weights(P, 3.0, 5.0)


def swap_tz(profile: SoilProfile, days: int = 3) -> pd.DataFrame:
    """A csv_tz-shaped frame: date x DEPTH (cm, negative), WC = depth in m + day."""
    z = node_depths(profile)
    rows = []
    for d in range(days):
        for depth in z:
            rows.append({"DATETIME": pd.Timestamp("2022-01-01") + pd.Timedelta(d, unit="D"), "DEPTH": -round(depth * 100, 4), "WC": depth + d})
    return pd.DataFrame(rows).set_index("DATETIME")


def test_at_nodes_and_interval_mean():
    theta = at_nodes(swap_tz(P), P)
    assert theta.shape == (3, N) and theta.columns.name == "depth_m"
    assert np.allclose(theta.columns.to_numpy(), node_depths(P))
    assert theta.iloc[1, 0] == pytest.approx(0.005 + 1)
    m = interval_mean(theta, P, 0.0, 0.3)
    assert m.name == "0-0.3 m" and m.iloc[0] == pytest.approx(0.15) and m.iloc[2] == pytest.approx(2.15)


def test_at_nodes_rejects_other_discretization():
    other = P.with_rule("L4", CompartmentRule(hcomp=0.05))
    with pytest.raises(ValueError, match="is this the profile the run used"):
        at_nodes(swap_tz(other), P)
    with pytest.raises(ValueError, match="node columns"):
        interval_mean(at_nodes(swap_tz(other), other), P, 0.0, 0.3)
