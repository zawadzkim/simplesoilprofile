"""SWAP-facing exports: pyswap-compatible tables and parameter specs (this package never imports pyswap)."""

from simplesoilprofile.swap.params import HYD_COLUMNS, ParamSpec, apply_fit, param, params
from simplesoilprofile.swap.tables import soilhydrfunc_table, soilprofile_table, texture_table

__all__ = [
    "HYD_COLUMNS",
    "ParamSpec",
    "apply_fit",
    "param",
    "params",
    "soilhydrfunc_table",
    "soilprofile_table",
    "texture_table",
]
