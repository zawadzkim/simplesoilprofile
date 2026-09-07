"""SWAP-facing exports: pyswap-compatible tables and parameter specs (this package never imports pyswap)."""

from simplesoilprofile.swap.params import HYD_COLUMNS, ParamSpec, apply_fit, param, params
from simplesoilprofile.swap.results import at_nodes, interval_mean
from simplesoilprofile.swap.tables import soilhydrfunc_table, soilprofile_table, texture_table

__all__ = [
    "HYD_COLUMNS",
    "ParamSpec",
    "apply_fit",
    "at_nodes",
    "interval_mean",
    "param",
    "params",
    "soilhydrfunc_table",
    "soilprofile_table",
    "texture_table",
]
