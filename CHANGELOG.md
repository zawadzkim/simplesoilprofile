# Changelog

## 0.1.0 (unreleased) — the horizons refactor

A clean break from 0.0.9: the object model was redesigned around an immutable material/horizon/profile split.
Nothing from the 0.0.9 API is kept under its old name.

### Renamed and moved

| 0.0.9 | 0.1.0 |
|---|---|
| `SoilLayer` | `SoilMaterial` (`simplesoilprofile.core.material`) — carries no depth or discretization |
| `SoilProfile(layers=[...], layer_bottoms=[...])` | `SoilProfile(horizons=[Horizon(material=..., bottom=..., rule=...)])` |
| `SoilLayerMetadata` | `ProvenanceEntry`; keys of `SoilMaterial.metadata` are validated against the parameter fields |
| `LayerDiscretization` | `CountRule` (`simplesoilprofile.core.discretization`), attached to the `Horizon`, not the material |
| `layer.lambda_param` / alias `l` | `material.l_mualem` |
| `layer.predict_van_genuchten(...)` (mutating) | `material.with_rosetta(version=3, use_bulk_density=True, keep_ksat=False)` (returns a new material) |
| `layer.infer_fractions_from_texture(cls)` | `material.with_texture_class(cls, system="usda" \| "flemish")` |
| `layer.normalize_soil_fractions()` | `material.normalized_fractions()` |
| `profile.location: shapely.Point` | `profile.x`, `profile.y`, `profile.crs`; `profile.point` builds the Point on demand (`geo` extra) |
| `profile.layer_bounds` / `profile_depth` / `get_layer_at_depth` | `profile.bounds` / `depth` / `horizon_at` |
| `get_profile_from_dov(Point, ...)` | `profile_from_dov(x, y, crs, fetch_elevation, name)` (`simplesoilprofile.sources.dov`, `dov` extra) |
| `models.swap.profile_to_soilhydfunc_table` etc. | `swap.soilhydrfunc_table`, `swap.soilprofile_table`, `swap.texture_table` |
| `models.texture_conversion.SoilTextureConverter(path)` | `ptf.texture.texture_system("usda" \| "flemish")` (package data, cached) |

### Added

- `SoilLibrary` (`simplesoilprofile.core.library`): named materials defined once, with library-level provenance; `to_frame()`, `with_values({(key, attribute): value}, note=...)` for fitted values (provenance entries marked 'modeled'), `with_material()`, JSON round trip.
- `SoilProfile.from_library(library, [(key, bottom_m), ...], rules={key: rule})` and `SoilProfile.rebuild(library)`: profiles are derived from a library and re-derived after a fit; every horizon records its library `key`.

### Changed

- **All lengths are metres**: horizon bottoms, depths, elevation. The SWAP exporters convert to cm; bulk density (g/cm³) is converted to SWAP's mg/cm³ there as well.
- Models are frozen; every `with_*` method returns a new, re-validated object (`material.n = 30` raises; `material.with_(n=30)` raises).
- A horizon whose bottom equals the previous bottom is absent (zero thickness) and keeps its index; exporters, lookups and plots use `profile.present`.
- `SoilProfile.to_json` / `from_json` round-trip the whole profile, provenance included.
- `depth_of(z)` / `elevation_of(depth)` convert between the site datum and depth below the surface.
- `n` is bounded to (1, 9] and `alpha` to (0, 100], SWAP's ranges.

### Fixed (also released on the `release/v0.1.0` branch as bug fixes to 0.0.9)

- Rosetta bridge for rosetta-soil ≥ 0.3 (linear output; Rosetta's own L).
- SOILHYDRFUNC exporter: required columns enforced, `H_ENPR` and `KSATEXM` defaults, BDENS in mg/cm³.
- SOILPROFILE exporter raises on an undiscretized horizon instead of dropping it.
- Package version read from metadata; pydov/dovwms moved to the `dov` extra; log records emitted once.
