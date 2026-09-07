# simplesoilprofile

[![Release](https://img.shields.io/github/v/release/zawadzkim/simplesoilprofile)](https://img.shields.io/github/v/release/zawadzkim/simplesoilprofile)
[![Build status](https://img.shields.io/github/actions/workflow/status/zawadzkim/simplesoilprofile/main.yml?branch=main)](https://github.com/zawadzkim/simplesoilprofile/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/zawadzkim/simplesoilprofile/branch/main/graph/badge.svg)](https://codecov.io/gh/zawadzkim/simplesoilprofile)
[![Commit activity](https://img.shields.io/github/commit-activity/m/zawadzkim/simplesoilprofile)](https://img.shields.io/github/commit-activity/m/zawadzkim/simplesoilprofile)
[![License](https://img.shields.io/github/license/zawadzkim/simplesoilprofile)](https://img.shields.io/github/license/zawadzkim/simplesoilprofile)

A Python package for working with soil profile data in hydrological modeling applications, particularly focused on SWAP model integration.

- **Github repository**: <https://github.com/zawadzkim/simplesoilprofile/>
- **Documentation** <https://zawadzkim.github.io/simplesoilprofile/>

## Features

- Object-oriented representation of soil layers and profiles with Pydantic validation
- Support for van Genuchten parameters and physical soil properties
- Integration with the SWAP model input format
- API integration framework with example implementation for Belgian DOV
- Visualization tools for soil profile display

## Units and conventions

All lengths are metres: horizon bottoms, depths, elevation.
Hydraulic parameters use the Rosetta/SWAP units: α in 1/cm, k_sat in cm/d, bulk density in g/cm³.
The SWAP exporters convert (depths to cm, bulk density to mg/cm³); nothing else does.
Objects are immutable: every `with_*` method returns a new, validated object.

## Quick Start

### Materials and a profile

```python
from simplesoilprofile import CountRule, DiscretizationType, Horizon, SoilMaterial, SoilProfile

topsoil = SoilMaterial(name="Topsoil", texture_class="sandy loam", sand_content=65, silt_content=25, clay_content=10,
                       bulk_density=1.45)
subsoil = SoilMaterial(name="Subsoil", texture_class="clay loam", sand_content=35, silt_content=35, clay_content=30,
                       bulk_density=1.55)

# Hydraulic parameters from Rosetta (rosetta-soil >= 0.3); with_rosetta returns a new material
topsoil = topsoil.with_rosetta(version=3)            # texture + bulk density as predictors
subsoil = subsoil.with_rosetta(version=2)            # texture only
measured = topsoil.with_(source="lab", source_type="measured", k_sat=42.0)   # provenance travels with the value

rule = CountRule(type=DiscretizationType.EVEN, num_sublayers=2, num_compartments=5)
profile = SoilProfile(
    name="Test Profile",
    x=247172.56, y=204590.58, crs="EPSG:31370", elevation=33.2,   # elevation in m above the site datum
    horizons=[
        Horizon(material=topsoil, bottom=0.3, rule=rule),          # bottoms in metres below the surface
        Horizon(material=subsoil, bottom=1.0, rule=rule),
    ],
)
```

A horizon whose bottom equals the previous bottom has zero thickness: it is absent at that location but keeps its index, so one horizon sequence can describe every profile of a site.

### SWAP tables

```python
from simplesoilprofile.swap import soilhydrfunc_table, soilprofile_table

soilhydrfunc = soilhydrfunc_table(profile)   # one row per present horizon; BDENS in mg/cm³
soilprofile = soilprofile_table(profile)     # ISUBLAY / ISOILLAY / HSUBLAY / HCOMP / NCOMP in cm
```

The frames carry pyswap's column names, so `pyswap.components.soilwater.SOILHYDRFUNC.create(soilhydrfunc.to_dict("list"))` consumes them directly; this package does not import pyswap.

### Profiles from DOV

```python
from simplesoilprofile import profile_from_dov      # needs: pip install "simplesoilprofile[dov]"

profile = profile_from_dov(247172.56, 204590.58, fetch_elevation=True)
profile = profile.with_material(0, profile.horizons[0].material.with_rosetta(version=2))
```

### Visualizing a Profile

```python
import matplotlib.pyplot as plt
from simplesoilprofile import plot_profile

fig, ax = plt.subplots(figsize=(8, 12))
plot_profile(profile, ax=ax, show_layer_properties=True)
plt.show()
```
