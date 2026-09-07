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
from simplesoilprofile import CompartmentRule, CountRule, DiscretizationType, Horizon, SoilMaterial, SoilProfile

topsoil = SoilMaterial(name="Topsoil", texture_class="sandy loam", sand_content=65, silt_content=25, clay_content=10,
                       bulk_density=1.45)
subsoil = SoilMaterial(name="Subsoil", texture_class="clay loam", sand_content=35, silt_content=35, clay_content=30,
                       bulk_density=1.55)

# Hydraulic parameters from Rosetta (rosetta-soil >= 0.3); with_rosetta returns a new material
topsoil = topsoil.with_rosetta(version=3)            # texture + bulk density as predictors
subsoil = subsoil.with_rosetta(version=2)            # texture only
measured = topsoil.with_(source="lab", source_type="measured", k_sat=42.0)   # provenance travels with the value

rule = CompartmentRule(hcomp=0.05, top_cap=(0.10, 0.01))   # 5 cm compartments, the top 10 cm at 1 cm
# or by counts: CountRule(type=DiscretizationType.EVEN, num_sublayers=2, num_compartments=5)
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

### A library: define materials once, place them in many profiles

```python
from simplesoilprofile import SoilLibrary

library = SoilLibrary(name="site", materials={m.name: m for m in (topsoil, subsoil)},
                      provenance={"retention": "Rosetta on nominal textures"})
s05 = SoilProfile.from_library(library, [("Topsoil", 0.5), ("Subsoil", 2.4), ("Subsoil", 4.0)],
                               name="S05", elevation=32.6, rules={"Topsoil": rule, "Subsoil": rule})

fitted = library.with_values({("Subsoil", "k_sat"): 0.17}, note="calibration v4")   # a new library; provenance says 'modeled'
s05_fitted = s05.rebuild(fitted)                                                     # same geometry, fitted materials
fitted.to_json("soil_library_fitted.json")
```

One profile, one site: skip the library and build the horizons by hand.

### SWAP tables

```python
from simplesoilprofile.swap import soilhydrfunc_table, soilprofile_table

soilhydrfunc = soilhydrfunc_table(profile)   # one row per present horizon; BDENS in mg/cm³
soilprofile = soilprofile_table(profile)     # ISUBLAY / ISOILLAY / HSUBLAY / HCOMP / NCOMP in cm
```

The frames carry pyswap's column names, so `pyswap.components.soilwater.SOILHYDRFUNC.create(soilhydrfunc.to_dict("list"))` consumes them directly; this package does not import pyswap.

### Calibration parameters by material, not by row number

```python
from simplesoilprofile.swap import apply_fit, param

k_sub = param(s05, "Subsoil", "k_sat", bounds=(0.1, 50), transform="log10", name="k_sub")
# k_sub.path == "soilprofile.soilhydrfunc.KSATFIT[1]", k_sub.also ties KSATEXM[1] and every other row of "Subsoil"
# pyswap side:  Param(**k_sub.as_dict())
fitted = apply_fit(library, {"k_sub": 0.17}, [k_sub], note="calibration v4")   # back into a new library
```

The row is resolved from the horizons present in *that* profile, so a lens that is absent at one sounding raises instead of silently shifting the row.

### Reading SWAP output back onto the profile

```python
from simplesoilprofile.swap import at_nodes, interval_mean

theta = at_nodes(result.csv_tz, s05, var="WC")        # time x node depth [m]; raises if the nodes do not match
theta_0_30 = interval_mean(theta, s05, 0.0, 0.3)      # the 0-30 cm sample layer, weighted by compartment overlap
```

### Profiles from DOV

```python
from simplesoilprofile import profile_from_dov      # needs: pip install "simplesoilprofile[dov]"

profile = profile_from_dov(247172.56, 204590.58, fetch_elevation=True)
profile = profile.with_material(0, profile.horizons[0].material.with_rosetta(version=2))
```

### Visualizing profiles

```python
import matplotlib.pyplot as plt
from simplesoilprofile.plotting import mark_interval, plot_fence, plot_profile, plot_profiles

colors = {"Topsoil": "#748a33", "Subsoil": "#e09600"}        # keyed by horizon key / material name
ax = plot_profile(s05, colors=colors, show_sublayers=True)   # one column, properties beside it
mark_interval(ax, s05, 3.5, 4.0, "PB15A")                    # a well screen
plot_profiles([s05, s06], colors=colors, datum="elevation")  # side by side in one datum
plot_fence([s02, s05, s06], colors=colors)                   # a fence; absent horizons are annotated
plt.show()
```
