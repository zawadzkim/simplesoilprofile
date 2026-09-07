"""Map SWAP's per-node output onto the profile's nodes and average it over depth intervals.

SWAP writes node values (water content ``WC``, pressure head ``H``, temperature ...) against ``DEPTH`` in cm, negative downward, at the compartment centres.
This module converts that to the package's metres below the surface and checks the nodes against the profile's discretization; pandas in, pandas out, no pyswap import.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from simplesoilprofile.core.nodes import interval_weights, node_depths
from simplesoilprofile.core.profile import SoilProfile

CM_PER_M = 100.0
#: Tolerance [m] when matching SWAP's output depths with the profile's node depths.
NODE_TOL = 1e-6


def at_nodes(tz: pd.DataFrame, profile: SoilProfile, var: str = "WC", depth_col: str = "DEPTH") -> pd.DataFrame:
    """Pivot a SWAP per-node output frame to (time x node depth [m]) and check it against ``profile``.

    Args:
        tz: SWAP's node output as a frame with a time index (or a first column of dates), a ``DEPTH`` column in cm (negative down) and the variable column.
        profile: The discretized profile the run used; its node depths become the columns.
        var: Variable column to pivot.
        depth_col: Name of the depth column.

    Raises:
        ValueError: the output nodes do not match the profile's nodes.
    """
    frame = tz.reset_index()
    time_col = frame.columns[0]
    mat = frame.pivot_table(index=time_col, columns=depth_col, values=var, aggfunc="mean")
    mat.index = pd.to_datetime(mat.index)
    depths = -mat.columns.to_numpy(dtype=float) / CM_PER_M
    order = np.argsort(depths)
    mat, depths = mat.iloc[:, order], depths[order]
    expected = node_depths(profile)
    if len(depths) != len(expected) or not np.allclose(depths, expected, atol=NODE_TOL):
        raise ValueError(
            f"SWAP output has {len(depths)} nodes (first {depths[:3]} m); profile '{profile.name}' has "
            f"{len(expected)} (first {expected[:3]} m) — is this the profile the run used?"
        )
    mat.columns = pd.Index(expected, name="depth_m")
    return mat.sort_index()


def interval_mean(values: pd.DataFrame, profile: SoilProfile, top: float, bottom: float) -> pd.Series:
    """Depth-average of a (time x node) frame over [top, bottom] m, weighted by compartment overlap."""
    w = interval_weights(profile, top, bottom)
    if values.shape[1] != len(w):
        raise ValueError(f"frame has {values.shape[1]} node columns, profile '{profile.name}' has {len(w)} nodes")
    return pd.Series(values.to_numpy() @ w, index=values.index, name=f"{top:g}-{bottom:g} m")
