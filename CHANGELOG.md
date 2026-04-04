# Changelog

## [0.1.0] - 2026-04-04

### Added

- Public package version export through `quantum_circuit_drawer.__version__`
- `RenderingError` for output and render-write failures
- Logging hooks for debug-level diagnostics without configuring logging globally
- CI workflow for lint, type checking, tests, and package builds
- Initial CUDA-Q adapter support for closed kernels through Quake/MLIR, including visible `MZ` / `MX` / `MY` measurement labels

### Changed

- Narrowed optional dependency import handling so unexpected import errors are no longer swallowed
- Removed the custom pytest `tmp_path` override and switched back to pytest's built-in temporary directory handling
- Refined package typing with a layout protocol, explicit render result typing, and `py.typed`
- Reworked README and example documentation to match the real v0.1.0 surface
- Added a Linux/WSL-first optional `cudaq` extra and a dedicated Linux CI job for real CUDA-Q integration coverage

### Removed

- Unused autodetection helper from `utils`
- Generated artifacts and cache directories from the intended versioned repo surface
