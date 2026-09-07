"""Plotting on the Agg backend."""

import matplotlib.pyplot as plt

from simplesoilprofile import Horizon, plot_profile
from tests.conftest import EVEN, material


def test_plot_profile(two_horizon_profile):
    fig, ax = plt.subplots()
    out = plot_profile(two_horizon_profile, ax=ax)
    assert out is ax
    assert len(ax.patches) == 2
    assert "Soil Profile: p" in ax.get_title() and "z=33.2 m" in ax.get_title()
    plt.close(fig)


def test_plot_skips_absent_horizon(two_horizon_profile):
    p = two_horizon_profile.with_horizons([*two_horizon_profile.horizons, Horizon(material=material("absent"), bottom=2.4, rule=EVEN)])
    ax = plot_profile(p, show_layer_properties=False)
    assert len(ax.patches) == 2
    plt.close(ax.figure)
