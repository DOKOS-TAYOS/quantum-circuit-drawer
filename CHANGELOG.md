# Changelog

## [Unreleased]

### Changed

- Polished managed 2D exploration controls so `Wires`, `Ancillas`, and block actions only appear when they can actually change the current view, and moved the horizontal slider onto its own row above the lower button strip
- Made compare-mode difference bands subtler and theme-aware, kept hover and zoom-responsive text behavior on compare axes, and applied theme text colors to per-side titles and the shared summary for dark-mode readability
- Tightened 2D exploration emphasis so the selected operation stands out more clearly than related neighbors, added low-alpha grouped highlight boxes around expanded decomposition members, and kept collapsed synthetic blocks compact even with long labels
- Normalized probability-style visible gate labels such as `PROBABILITY`, `PROB`, and `PROBS` to `Prob` while preserving the native result kind in hover details
- Shrunk the managed 3D topology selector panel slightly by reducing its bounds, marker size, and label size together

### Fixed

- Managed 2D hovers now stay visually above the slider row, and the slider row no longer overlaps the lower managed buttons
- Interactive histogram hovers now cover the uniform reference guide line with an explanation of the uniform baseline and how its value is derived

## [0.4.0] - 2026-04-22

### Added

- Added `qiskit-2d-exploration-showcase`, a dedicated Qiskit demo for managed 2D exploration with active-wire filtering, ancilla toggles, folded-wire markers, and contextual block controls
- Added contextual managed-2D circuit exploration for `slider` and `pages_controls`, including click selection, related-operation highlighting, semantic block collapse/expand, `Wires: All/Active`, `Ancillas: Show/Hide`, and folded-wire markers for hidden wire ranges
- Added project-managed `pyright` support in the `dev` extra and CI so static type checking no longer depends on a globally installed tool
- Added Windows-safe Cirq adapter contract tests based on stubbed circuits so optional adapter coverage still runs even when the real dependency is unavailable
- Added Windows-safe PennyLane adapter contract tests for tape wrappers, safe prebuilt `._tape` inputs, conditional operations, and composite expansion coverage
- Added a public semantic IR layer under `quantum_circuit_drawer.ir`, plus an explicit lowerer back into `CircuitIR`, so richer adapters can preserve native grouping and provenance before rendering
- Added `plot_histogram` with public `HistogramConfig`, `HistogramKind`, and `HistogramResult` types for counts, quasi-probabilities, and joint marginals on selected qubits
- Added support for histogram inputs from plain mappings and Qiskit 2.x result objects, including `Counts`, `QuasiDistribution`, `SamplerResult`, `PrimitiveResult`, `SamplerPubResult`, `BitArray`, and `DataBin`
- Added support for histogram inputs from Cirq `Result` / `ResultDict`, PennyLane probability vectors and sample arrays, MyQLM `qat.core.Result.raw_data`, CUDA-Q `SampleResult`-style containers, and direct mapping-like count objects
- Added histogram ordering, top-k filtering, theme-aware styling, alternative bar styles, and a uniform-reference guide line based on the full state space size
- Added interactive histogram mode with managed slider navigation, per-bin hover, cyclic sort controls, slider toggling, and a marginal-qubits text box
- Added the public `HistogramMode` enum and the `HistogramSort.STATE_DESC` ordering mode
- Added a large 7-bit histogram demo that visibly exercises the interactive controls on dense state spaces
- Added the public `HistogramStateLabelMode` enum so histograms can display binary or decimal state labels, including decimal conversion per space-separated register
- Added a multi-register histogram demo that shows decimal labels for several classical-register groups
- Added framework-specific histogram demos for Qiskit, Cirq, PennyLane, myQLM, and CUDA-Q result payloads

### Changed

- Refreshed the README, examples catalog, and core user docs so the nested public config API, showcase recommendations, and managed-2D exploration workflow are described consistently
- Reworked the public configuration surface into nested typed blocks ordered by responsibility: `DrawConfig(side, output)`, `CircuitCompareConfig(shared, compare, output, per-side overrides)`, `HistogramConfig(data, view, appearance, output)`, and `HistogramCompareConfig(data, compare, output)`
- Removed the old flat public config constructor style from docs, examples, and tests, and made `compare_circuits(...)` use one shared `config=` object without `left_config` / `right_config`
- Unified public output handling around shared `OutputOptions(show, output_path, figsize)` across circuit drawing, circuit comparison, histogram plotting, and histogram comparison
- Tightened internal typing around shared example helpers, benchmark request normalization, and 2D/3D benchmark execution so `pyright` can validate the intended render flow
- Clarified the production support matrix across the README and core docs, keeping IR and Qiskit as the strong paths, Cirq and PennyLane as best-effort on native Windows, MyQLM as scoped adapter support, and CUDA-Q as Linux/WSL2-only
- Migrated the Qiskit adapter onto the shared semantic path as well, keeping simple `if_test(...)` expansion while rendering `if_else` with `else`, `switch_case`, `for_loop`, and `while_loop` as compact native boxes with preserved hover details instead of flattening or simulating their control flow
- Extended public-parity coverage for Cirq and PennyLane with Windows-safe mixed-framework compare tests and broader contract coverage for compact/expanded composite behavior
- Reworked the Cirq and PennyLane adapter internals around a native-first semantic path, so comparison, hover, annotations, and diagnostics can preserve framework-specific meaning instead of flattening everything directly into the legacy render IR
- Consolidated the shared adapter pipeline so richer semantic adapters and legacy `to_ir(...)` adapters coexist cleanly, then migrated MyQLM and CUDA-Q onto that same native semantic route without changing the public draw API
- Managed 2D draw preparation now keeps a separate expanded semantic source and stable per-operation scene identifiers internally, so exploration controls can restyle or rebuild the visible viewport without changing the public drawing API
- MyQLM now preserves gate provenance, composite provenance, decomposition origin, resets, and supported classical-control expressions before lowering back to the shared render IR
- CUDA-Q now preserves Quake provenance, measurement basis, value-form wire flow, and supported `reset` operations before lowering back to the shared render IR, while still rejecting constructs without a clean shared equivalent
- PennyLane terminal results now render as compact output boxes with preserved result kind, observable summaries, and wire-scope hover details instead of being flattened into fake per-wire projective measurements
- Controlled-gate rendering now preserves explicit binary control states through semantic IR and render IR, so Qiskit, Cirq, and PennyLane can draw open controls faithfully in both 2D and 3D instead of treating every control as closed-on-`1`
- Marked `quantum_circuit_drawer.drawing`, `managed`, and `plots` as compatibility facades that remain importable but are outside the stable public extension contract
- Updated the README, API reference, and recipes with examples for counts histograms, quasi-probability plots, joint marginals, and interactive histogram exploration
- Extended the framework guide and histogram docs so they spell out which result payloads can be passed directly from each supported framework, plus when to use `result_index`
- Refreshed the example catalog and public docs around a more user-facing showcase flow, adding new framework demos for Qiskit control flow, Cirq native controls, PennyLane terminal outputs, MyQLM structure, and the supported CUDA-Q kernel subset
- Applied a transversal compatibility polish pass so MyQLM qubit-targeted resets keep drawing even with extra classical metadata, PennyLane obscure observables prefer deterministic fallback labels over a vague generic box name, and the docs/showcase descriptions track the real supported subset more closely
- Expanded the histogram demos so they cover larger state spaces and visibly exercise sorting, draw styles, uniform-reference guides, and the new interactive controls
- Histogram plots now default to `HistogramMode.AUTO`, so large histograms open with managed controls in normal scripts and widget notebooks while inline notebook backends keep the static fallback
- Histogram bin hover is now enabled by default in interactive mode and can be disabled explicitly with `hover=False`
- Histogram interactive controls now include a label-mode button for switching between binary and decimal labels without changing the normalized result data
- Histogram interactive controls now include a counts/quasi toggle for count-based inputs, while quasi-only inputs keep the simpler control set
- Reduced 2D interactive redraw overhead by caching runtime notebook detection, reusing Matplotlib page projections across repeated renders, and keeping text-fit caches alive through page-window and slider redraws
- Improved the synthetic `16 wires / 120 layers / 2 repeats` benchmark in this Windows environment from about `full_draw_seconds=0.2673` to `0.1328`, with `layout_seconds` dropping from about `0.0287` to `0.0127`
- Reorganized the internal package into domain-focused subpackages: `drawing` for orchestration, `managed` for interactive Matplotlib state, `plots` for histogram implementation, and `export` for shared figure saving, while keeping the public imports stable
- Split the heaviest managed and 3D internals into smaller helpers, including dedicated modules for shared managed controls, 2D slider windowing, 3D slider orchestration, 3D page-range balancing, and focused 3D layout and renderer support code
- Split the remaining 2D hot spots into focused helpers, including dedicated modules for 2D Matplotlib primitives, 2D slider orchestration, 2D page-window controls/rendering/windowing, and smaller domain-aligned managed-rendering and renderer test files
- Moved internal matrix helpers under `quantum_circuit_drawer.utils.matrix_support` and updated internal code and tests to target the new structure directly
- Replaced the remaining reflective compatibility-facade exports with explicit `__all__` surfaces and direct reexports, keeping the observable import contract while making internal ownership clearer for tooling and maintenance

### Fixed

- Restored `mypy` cleanliness for the public config wrappers, histogram config properties, managed 2D visual-state helpers, Matplotlib gate grouping helpers, and best-effort figure cleanup for `SubFigure` inputs
- Managed 2D exploration no longer duplicates collapsed composite blocks after expand/collapse or wire-visibility toggles, and the `pages_controls` row now gives `Page` / `Visible` inputs less dead space while keeping longer block-action buttons readable
- Hardened custom topology validation and draw-style replacement typing so invalid graph-like inputs and optional style overrides fail more predictably under static and runtime checks
- Explicit `framework="cudaq"` requests now fail with a platform-aware message that points native Windows users to Linux or WSL2 instead of a generic framework-mismatch error
- PennyLane wrapper detection now prefers already-materialized `._tape` inputs and avoids touching lazy `.qtape` / `.tape` properties or calling `construct()` implicitly
- `compare_circuits(...)` no longer treats visually similar but semantically different native adapter paths as identical once semantic provenance is available
- Hover matrix inference for simple controlled single-qubit gates now respects open-control states, so control-on-`0` no longer shows the wrong compact matrix in tooltips
- Example and benchmark helpers now validate builder callability earlier and clean up rendered Matplotlib figures more defensively after demo execution
- Histogram and compare example helpers now share the same figure-title and cleanup support as the main example runner, so they close rendered Matplotlib figures reliably and only ignore benign destroyed-window title errors
- Tightened public config validation so boolean values are no longer accepted where positive numeric `figsize`, `top_k`, `result_index`, qubit-index, or hover matrix limits are required
- `HoverOptions` now validates direct construction the same way as mapping-based hover input, preventing invalid booleans and unsupported `show_matrix` values from slipping through
- Unified circuit and histogram output saving behind one shared export helper so directory creation, Matplotlib save handling, and wrapped `RenderingError` behavior stay consistent
- Refined histogram managed-control layout so the slider no longer overlaps the ordering controls or state labels, and hiding the slider no longer drops the plot into the control row
- Removed the redundant histogram status banner, moved the active ordering label into the order button itself, and added hover help to the marginal-qubits text box
- Histogram status messages such as marginal-input validation errors are now centered horizontally above the figure controls for easier reading
- Narrowed 2D hover hit areas for connected multi-artist gates such as `CNOT`, `CZ`, and `SWAP`, including connection-line hitboxes, so hovering no longer claims the full rectangle between separated markers or nearby empty columns
- Rebalanced managed 3D page-window ranges for visually dense circuits so example demos like `qiskit-random` stop packing so many routed columns into one page
- Example scripts now close rendered Matplotlib figures and trigger prompt cleanup after the window closes, which reduces the lingering shutdown lag seen most often with Cirq and PennyLane demos
- Restored core coverage after the internal package split by exercising the root compatibility facades and lazy package exports in the modularization test suite
- Managed 2D paged saves now log best-effort figure-cleanup failures instead of silently swallowing them, so odd shutdown issues remain diagnosable without breaking successful renders

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

[Unreleased]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/releases/tag/v0.1.0
