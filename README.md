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

### Fetching Data from DOV API

```python
from simplesoilprofile.api import DOVClient

# Create a client
client = DOVClient()

# Fetch a profile
profile = client.fetch_profile("profile_id")
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

## API Integration

The package includes a flexible API integration framework that can be configured using YAML files. Here's an example configuration for a new data source:

```yaml
base_url: "https://api.example.com"
endpoint: "/soil-data"
method: "GET"
response_type: "json"
layer_path: "$.data.layers"

field_mappings:
  name: "$.id"
  description: "$.description"
  texture_class: "$.texture"
  clay_content: "$.clay_percentage"
  silt_content: "$.silt_percentage"
  sand_content: "$.sand_percentage"
```

## Contributing

First, create a repository on GitHub with the same name as this project, and then run the following commands:

```bash
git init -b main
git add .
git commit -m "init commit"
git remote add origin git@github.com:zawadzkim/simplesoilprofile.git
git push -u origin main
```

Finally, install the environment and the pre-commit hooks with

```bash
make install
```

You are now ready to start development on your project!
The CI/CD pipeline will be triggered when you open a pull request, merge to main, or when you create a new release.

To finalize the set-up for publishing to PyPI or Artifactory, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/publishing/#set-up-for-pypi).
For activating the automatic documentation with MkDocs, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/mkdocs/#enabling-the-documentation-on-github).
To enable the code coverage reports, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/codecov/).

## Releasing a new version

- Create an API Token on [PyPI](https://pypi.org/).
- Add the API Token to your projects secrets with the name `PYPI_TOKEN` by visiting [this page](https://github.com/zawadzkim/simplesoilprofile/settings/secrets/actions/new).
- Create a [new release](https://github.com/zawadzkim/simplesoilprofile/releases/new) on Github.
- Create a new tag in the form `*.*.*`.
- For more details, see [here](https://fpgmaas.github.io/cookiecutter-poetry/features/cicd/#how-to-trigger-a-release).

---

Repository initiated with [fpgmaas/cookiecutter-poetry](https://github.com/fpgmaas/cookiecutter-poetry).
