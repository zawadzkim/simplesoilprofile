"""Node geometry of a discretized profile: compartment centres, their horizons, and depth-interval weights.

All lengths in metres below the surface; nodes follow :func:`~simplesoilprofile.core.discretization.sublayers`.
"""

from __future__ import annotations

import numpy as np

from simplesoilprofile.core.discretization import sublayers
from simplesoilprofile.core.profile import SoilProfile


def node_bounds(profile: SoilProfile) -> np.ndarray:
    """(top, bottom) of every compartment, shape (n, 2), top down."""
    rows = []
    for s in sublayers(profile):
        tops = s.top + np.arange(s.ncomp) * s.hcomp
        rows.append(np.column_stack([tops, tops + s.hcomp]))
    return np.vstack(rows)


def node_depths(profile: SoilProfile) -> np.ndarray:
    """Depth of every compartment centre [m]."""
    b = node_bounds(profile)
    return b.mean(axis=1)


def node_horizons(profile: SoilProfile) -> np.ndarray:
    """Profile horizon index of every compartment."""
    return np.concatenate([np.full(s.ncomp, s.horizon) for s in sublayers(profile)])


def interval_weights(profile: SoilProfile, top: float, bottom: float) -> np.ndarray:
    """Weight of every compartment in the depth-average over [top, bottom]: overlap length / interval length.

    The weights sum to one; the interval must lie inside the profile.

    Raises:
        ValueError: ``bottom <= top``, or the interval reaches outside the profile.
    """
    if bottom <= top:
        raise ValueError(f"interval bottom {bottom} m must be below its top {top} m")
    if top < 0.0 or bottom > profile.depth + 1e-9:
        raise ValueError(f"interval [{top}, {bottom}] m reaches outside profile '{profile.name}' (0 to {profile.depth} m)")
    b = node_bounds(profile)
    overlap = np.clip(np.minimum(b[:, 1], bottom) - np.maximum(b[:, 0], top), 0.0, None)
    return overlap / (bottom - top)
