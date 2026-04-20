# Changelog

## [Unreleased]

### Added

- Added `plot_histogram` with public `HistogramConfig`, `HistogramKind`, and `HistogramResult` types for counts, quasi-probabilities, and joint marginals on selected qubits
- Added support for histogram inputs from plain mappings and Qiskit 2.x result objects, including `Counts`, `QuasiDistribution`, `SamplerResult`, `PrimitiveResult`, `SamplerPubResult`, `BitArray`, and `DataBin`
- Added histogram ordering, top-k filtering, theme-aware styling, alternative bar styles, and a uniform-reference guide line based on the full state space size

### Changed

- Updated the README, API reference, and recipes with examples for counts histograms, quasi-probability plots, and joint marginals
- Expanded the histogram demos so they cover larger state spaces and visibly exercise sorting, top-k filtering, draw styles, and uniform-reference guides
- Reduced 2D interactive redraw overhead by caching runtime notebook detection, reusing Matplotlib page projections across repeated renders, and keeping text-fit caches alive through page-window and slider redraws
- Improved the synthetic `16 wires / 120 layers / 2 repeats` benchmark in this Windows environment from about `full_draw_seconds=0.2673` to `0.1328`, with `layout_seconds` dropping from about `0.0287` to `0.0127`
- Reorganized the internal package into domain-focused subpackages: `drawing` for orchestration, `managed` for interactive Matplotlib state, `plots` for histogram implementation, and `export` for shared figure saving, while keeping the public imports stable
- Split the heaviest managed and 3D internals into smaller helpers, including dedicated modules for shared managed controls, 2D slider windowing, 3D slider orchestration, 3D page-range balancing, and focused 3D layout and renderer support code
- Split the remaining 2D hot spots into focused helpers, including dedicated modules for 2D Matplotlib primitives, 2D slider orchestration, 2D page-window controls/rendering/windowing, and smaller domain-aligned managed-rendering and renderer test files
- Moved internal matrix helpers under `quantum_circuit_drawer.utils.matrix_support` and updated internal code and tests to target the new structure directly

### Fixed

- Tightened public config validation so boolean values are no longer accepted where positive numeric `figsize`, `top_k`, `result_index`, qubit-index, or hover matrix limits are required
- `HoverOptions` now validates direct construction the same way as mapping-based hover input, preventing invalid booleans and unsupported `show_matrix` values from slipping through
- Unified circuit and histogram output saving behind one shared export helper so directory creation, Matplotlib save handling, and wrapped `RenderingError` behavior stay consistent

## [0.3.0] - 2026-04-20

### Changed

- Reworked the public drawing API around `DrawConfig`, `DrawMode`, and `DrawResult`, replacing the old flag-heavy call shape with a single ordered configuration object and a stable normalized return object
- Added the public draw modes `auto`, `pages`, `pages_controls`, `slider`, and `full`, with context-sensitive `auto` defaults for notebooks and scripts
- Added managed 3D support for `pages`, `pages_controls`, and `full`, including vertically stacked visible pages and shared-view preservation in the 3D page viewer
- Clean paged saving now follows the selected public mode and keeps widget chrome out of saved output
- Expanded public style and theme coverage so color and stroke customization now includes managed UI colors, hover colors, controls, control connections, topology colors, and explicit stroke families
- Updated the README, API reference, user guide, recipes, and examples to use the new `DrawConfig` / `DrawMode` API
- Removed dynamic 2D layout recomposition on window resize; 2D figures now choose their base layout when rendered and keep it fixed until an explicit navigation action or rerender
- Simplified managed 2D rendering by dropping the old resize-driven auto-paging state and callbacks, which reduces post-render work while keeping zoom-based text fitting
- Visible circuit labels now use Matplotlib MathText by default through `DrawStyle(use_mathtext=True)`, giving paper-friendly gate names and parameters while keeping hover text plain
- Refreshed the default dark theme and managed interactive controls with a softer IDE-like night palette, elevated control surfaces, clearer button states, and a more consistent 3D topology selector
- Refined managed paging controls with reversed vertical scrolling, compact increment/decrement steppers on numeric inputs, cleaner horizontal slider labeling, and more polished page-navigation buttons
- Managed 3D slider navigation now preserves the current camera view and stable object sizing across steps, hides residual axes chrome, and prioritizes gate hover over qubit and bit lines
- Internal managed 3D redraw state now uses a typed shared camera container, which removes stale `dict`-based plumbing and keeps the view-restoration path explicit for static type checking
- Removed the remaining `Rows` chrome from the vertical managed slider and halved 3D temporal column spacing so layouts read much more compactly
- Removed an unused stacked gate-text layout helper from the Matplotlib primitives module

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

[Unreleased]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/releases/tag/v0.1.0
