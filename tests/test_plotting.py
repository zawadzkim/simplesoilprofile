"""Plotting on the Agg backend: patch counts, datums, fence with absent horizons, overlays."""

import matplotlib.pyplot as plt
import pytest

from simplesoilprofile import CompartmentRule, SoilLibrary, SoilProfile
from simplesoilprofile.plotting import (
    legend_entries,
    mark_depth,
    mark_interval,
    plot_fence,
    plot_profile,
    plot_profiles,
)
from tests.conftest import material

LIB = SoilLibrary(name="s", materials={m.name: m for m in (material("L1"), material("L2"), material("L3"))})
RULES = {k: CompartmentRule(hcomp=0.05) for k in LIB}
S06 = SoilProfile.from_library(LIB, [("L1", 0.5), ("L2", 2.4), ("L3", 4.0)], name="S06", elevation=33.22, rules=RULES)
S02 = SoilProfile.from_library(LIB, [("L1", 0.4), ("L2", 0.4), ("L3", 3.0)], name="S02", elevation=32.1, rules=RULES)
COLORS = {"L1": "#748a33", "L2": "#2a78d6", "L3": "#e09600"}
HATCH = {"L3": "///"}


def test_plot_profile_depth_datum():
    ax = plot_profile(S06, colors=COLORS, hatches=HATCH, show_nodes=True)
    assert len(ax.patches) == 3
    lo, hi = ax.get_ylim()
    assert lo > hi  # inverted: depth increases downward
    assert ax.patches[2].get_hatch() == "///" and ax.patches[0].get_facecolor()[:3] == pytest.approx((0x74 / 255, 0x8a / 255, 0x33 / 255))
    assert ax.get_title(loc="left") == "S06 (33.22 m)"
    plt.close(ax.figure)


def test_plot_profile_elevation_datum_and_absent():
    ax = plot_profile(S02, datum="elevation", annotate=False)
    assert len(ax.patches) == 2  # L2 absent
    assert ax.get_ylim()[1] > 32.1 > ax.get_ylim()[0]
    plt.close(ax.figure)
    with pytest.raises(ValueError, match="no elevation"):
        plot_profile(S06.with_(elevation=None), datum="elevation")


def test_plot_profiles_and_legend():
    axes = plot_profiles([S06, S02], colors=COLORS)
    assert len(axes) == 2 and len(axes[0].patches) == 3 and len(axes[1].patches) == 2
    handles, labels = legend_entries([S06, S02], COLORS)
    assert labels == ["L1", "L2", "L3"] and len(handles) == 3
    plt.close(axes[0].figure)


def test_fence_handles_absent_and_needs_elevation():
    ax = plot_fence([S06, S02], colors=COLORS, hatches=HATCH, labels=["east", "west"])
    assert len(ax.patches) == 5
    assert any("L2 absent" in t.get_text() for t in ax.texts)
    assert [t.get_text() for t in ax.get_xticklabels()] == ["east", "west"]
    plt.close(ax.figure)
    with pytest.raises(ValueError, match="missing on \\['S06'\\]"):
        plot_fence([S06.with_(elevation=None)])


def test_overlays():
    ax = plot_profile(S06, annotate=False)
    n = len(ax.patches)
    mark_interval(ax, S06, 3.5, 4.0, "PB16A")
    mark_depth(ax, S06, 1.0, "pipes")
    assert len(ax.patches) == n + 1 and any(t.get_text() == "PB16A" for t in ax.texts) and any(t.get_text() == "pipes" for t in ax.texts)
    plt.close(ax.figure)
