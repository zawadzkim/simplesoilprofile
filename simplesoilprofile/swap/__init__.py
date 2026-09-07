"""SWAP-facing exports: pyswap-compatible tables (this package never imports pyswap)."""

from simplesoilprofile.swap.tables import soilhydrfunc_table, soilprofile_table, texture_table

__all__ = ["soilhydrfunc_table", "soilprofile_table", "texture_table"]
