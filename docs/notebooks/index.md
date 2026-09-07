# Tutorials

Welcome to the simplesoilprofile tutorials! These Jupyter notebooks demonstrate practical usage of the package for various soil profile modeling tasks.

## Available Tutorials

### [Complete Example](000-complete-example.ipynb)
A comprehensive walkthrough showing how to:
- Define materials, predict their hydraulic parameters with Rosetta, and keep the provenance of every value
- Build a profile from horizons with compartment-height discretization rules
- Export the SWAP tables (pyswap column names, no pyswap dependency)
- Define a site's materials once in a library, build several profiles, write fitted values back
- Address calibration parameters by material instead of table row
- Read SWAP output back onto the nodes and average it over sample layers
- Visualize profiles and fences
- Fetch texture profiles from DOV

This tutorial covers all the main functionality of the package and serves as a practical introduction to hydrological soil modeling with simplesoilprofile.