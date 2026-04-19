# Changelog

## [Unreleased]

### Changed

- Visible circuit labels now use Matplotlib MathText by default through `DrawStyle(use_mathtext=True)`, giving paper-friendly gate names and parameters while keeping hover text plain
- Refreshed the default dark theme and managed interactive controls with a softer IDE-like night palette, elevated control surfaces, clearer button states, and a more consistent 3D topology selector
- Refined managed paging controls with reversed vertical scrolling, compact increment/decrement steppers on numeric inputs, cleaner horizontal slider labeling, and more polished page-navigation buttons
- Managed 3D slider navigation now preserves the current camera view and stable object sizing across steps, hides residual axes chrome, and prioritizes gate hover over qubit and bit lines

## [0.2.1] - 2026-04-18

### Changed

- Improved library performance
- Improved compatibility across environments and optional framework adapters

### Fixed

- Several visualization issues in circuit rendering and layout

## [0.2.0] - 2026-04-17

### Added

- Native MyQLM adapter support for `qat.core.Circuit` inputs, including common gates, measurements, reset, simple single-bit classical control, and composite gate expansion through `gateDic`
- Optional `myqlm` package extra and three runnable MyQLM demos in the shared example catalog
- Public `HoverOptions` support for interactive 2D inspection, including gate name, matrix dimensions, qubits, optional visual size, and configurable matrix display rules
- Matrix-enrichment helpers for hover tooltips, with framework extraction where available (`qiskit`, `cirq`, `pennylane`) plus canonical fallbacks for supported small gates
- Richer 2D hover coverage for gate boxes, controls, `X` targets, swaps, and other shared gate artists so the same operation can be inspected from the full drawing

### Changed

- Improved circuit visualization and homogenized gate appearance across the drawer
- Improved slider behavior
- Adjusted font sizes and color palette for clearer typography and contrast
- Reduced rendering and layout computation time
- Managed Matplotlib rendering now keeps hover alive for notebook-interactive backends when `show=False`, avoiding duplicate notebook output while preserving interactivity on the returned figure
- The default 2D hover content now prioritizes matrix dimensions and qubit labels, while the full matrix appears automatically only when it is small enough or explicitly requested
- Shared example scripts and `examples/run_demo.py` now expose hover controls and use the newer hover defaults so the demos match the current library behavior
- Updated README and user docs to cover MyQLM installation, usage, and current support limits
- Updated API, user-guide, recipes, troubleshooting, and examples documentation to cover hover configuration, notebook behavior, and the new example flags

### Fixed

- Restored reliable 2D hover tooltips on interactive figures, including controlled-gate markers and other non-box artists that previously stopped triggering hover details
- Fixed managed-figure hover cleanup during automatic redraws so resizing a window with hover enabled no longer raises `NotImplementedError: cannot remove artist`

## [0.1.1] - 2026-04-05

### Added

- Project URLs in package metadata for the public GitHub repository, issue tracker, and changelog
- Import-laziness regression tests for the package root and `quantum_circuit_drawer.api`
- Deterministic performance guard tests for renderer page transforms and layout metric reuse
- Wheel smoke-test step in CI after building distribution artifacts

### Changed

- Switched package version metadata to a single internal source in `quantum_circuit_drawer._version`
- Deferred the public `draw_quantum_circuit` import path so importing the package no longer eagerly loads Matplotlib
- Expanded `mypy` coverage to the full `src/quantum_circuit_drawer` package and aligned pytest coverage enforcement between local runs and CI
- Refactored `LayoutEngine` into smaller helpers with cached per-operation metrics to avoid repeated width computation
- Refactored `MatplotlibRenderer` to precompute per-page scene elements instead of re-transforming gates and measurements multiple times
- Split the CUDA-Q Quake/MLIR parser into a dedicated private module to keep `CudaqAdapter` focused
- Extended optional-adapter CI coverage to Windows in addition to Linux
- Refreshed the README development guidance to match the stricter verification baseline

### Fixed

- CUDA-Q Quake parser compatibility with IR from current CUDA-Q builds (`alloca !quake.veq` without a colon, kernel tail `dealloc`, `null_wire`, `discriminate`)
- CI reliability: `mypy` overrides for optional framework imports, coverage scope for dev-only installs, `--no-cov` on adapter-only pytest jobs, and Matplotlib `add_axes` typing

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

[Unreleased]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/releases/tag/v0.1.0
