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

## Quick Start

### Creating a Soil Profile

```python
from simplesoilprofile import SoilLayer, SoilProfile

# Create soil layers
topsoil = SoilLayer(
    name="Topsoil",
    description="Sandy loam topsoil",
    theta_res=0.02,
    theta_sat=0.4,
    alpha=0.02,
    n=1.5,
    k_sat=10.0,
    texture_class="sandy loam",
    clay_content=10.0,
    silt_content=20.0,
    sand_content=70.0,
)

subsoil = SoilLayer(
    name="Subsoil",
    description="Clay loam subsoil",
    theta_res=0.05,
    theta_sat=0.45,
    alpha=0.01,
    n=1.3,
    k_sat=5.0,
    texture_class="clay loam",
    clay_content=30.0,
    silt_content=35.0,
    sand_content=35.0,
)

# Create a profile
profile = SoilProfile(
    name="Test Profile",
    layers=[topsoil, subsoil],
    layer_depths={
        0: (0, 30),    # Topsoil from 0-30 cm
        1: (30, 100),  # Subsoil from 30-100 cm
    },
    x=100.0,
    y=200.0,
    z=5.0,
)
```

### Generating SWAP Input

```python
from simplesoilprofile.models.swap import write_swap_soil_file

# Write to a SWAP soil file
with open("soil.swp", "w") as f:
    write_swap_soil_file(profile, f)
```

### Visualizing a Profile

```python
import matplotlib.pyplot as plt
from simplesoilprofile.plotting import plot_profile

# Create a new figure
fig, ax = plt.subplots(figsize=(8, 12))

# Plot the profile
plot_profile(profile, ax=ax, show_properties=True)
plt.show()
```
