# API reference

This page documents the current public API surface.

For task-oriented guidance, prefer [Getting started](getting-started.md), [User guide](user-guide.md), [Recipes](recipes.md), and [Examples](../examples/README.md). This page stays reference-oriented on purpose.

The public entry points stay intentionally small:

- `analyze_quantum_circuit(...)`
- `draw_quantum_circuit(...)`
- `compare_circuits(...)`
- `plot_histogram(...)`
- `compare_histograms(...)`

## Main functions

```python
analyze_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
) -> CircuitAnalysisResult

draw_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult

compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, Axes] | None = None,
) -> CircuitCompareResult

plot_histogram(
    data: object,
    *,
    config: HistogramConfig | None = None,
    ax: Axes | None = None,
) -> HistogramResult

compare_histograms(
    left_data: object,
    right_data: object,
    *,
    config: HistogramCompareConfig | None = None,
    ax: Axes | None = None,
) -> HistogramCompareResult
```

## Circuit analysis

`analyze_quantum_circuit(...)` prepares the same normalized circuit pipeline as drawing, but it does not render figures, call `show()`, or save `OutputOptions.output_path`.

`CircuitAnalysisResult` includes framework, mode, view, page count, wire counts, operation counts, diagnostics, `warnings`, and `to_dict()`.

## Circuit drawing

`draw_quantum_circuit(...)` accepts supported framework objects, public `CircuitIR` objects, OpenQASM 2/3 text, `.qasm` files, and `.qasm3` files. OpenQASM paths use Qiskit for parsing: OpenQASM 2 requires `quantum-circuit-drawer[qiskit]`, and OpenQASM 3 requires `quantum-circuit-drawer[qasm3]`.

### `DrawConfig`

`DrawConfig` groups circuit options into one side block plus one output block:

```python
DrawConfig(
    side=DrawSideConfig(
        render=CircuitRenderOptions(
            framework=None,
            backend="matplotlib",
            layout=None,
            view="2d",
            mode=DrawMode.AUTO,
            composite_mode="compact",
            topology="line",
            topology_qubits="used",
            topology_resize="error",
            topology_menu=False,
            direct=True,
            unsupported_policy=UnsupportedPolicy.RAISE,
            adapter_options={},
        ),
        appearance=CircuitAppearanceOptions(
            preset=None,
            style=None,
            hover=False,
        ),
    ),
    output=OutputOptions(
        show=True,
        output_path=None,
        figsize=None,
    ),
)
```

Important fields:

- `side.render.framework`: optional explicit framework name such as `"qiskit"` or `"ir"`
- `side.render.backend`: currently `"matplotlib"`
- `side.render.layout`: optional custom 2D or 3D layout engine
- `side.render.view`: `"2d"` or `"3d"`
- `side.render.mode`: `DrawMode.AUTO`, `PAGES`, `PAGES_CONTROLS`, `SLIDER`, or `FULL`
- `side.render.composite_mode`: `"compact"` or `"expand"`
- `side.render.topology`: only used in 3D
- `side.render.topology_qubits`: `"used"` renders only allocated topology nodes; `"all"` renders the full topology footprint
- `side.render.topology_resize`: `"error"` rejects undersized topologies; `"fit"` rebuilds functional or periodic topologies for the circuit size
- `side.render.topology_menu`: managed interactive 3D topology selector
- `side.render.direct`: 3D layout flag for topology routing behavior
- `side.render.unsupported_policy`: `UnsupportedPolicy.RAISE` or `UnsupportedPolicy.PLACEHOLDER`
- `side.render.adapter_options`: optional adapter-specific mapping, such as `{"cudaq_args": (...)}`
- `side.appearance.preset`: shared style preset baseline
- `side.appearance.style`: `DrawStyle`, mapping, or `None`
- `side.appearance.hover`: `bool`, `HoverOptions`, mapping, or `None`
- `output.show`: whether the library should call `pyplot.show()` when appropriate
- `output.output_path`: optional file path for saving
- `output.figsize`: managed figure size in inches

OpenQASM details:

- pass a string that starts with `OPENQASM` for direct OpenQASM 2 or OpenQASM 3 text input
- pass `Path("circuit.qasm")`, `"circuit.qasm"`, `Path("circuit.qasm3")`, or `"circuit.qasm3"` for UTF-8 file input
- use `CircuitRenderOptions(framework="qasm")` when you want to opt into the QASM parser explicitly
- non-`.qasm` / `.qasm3` path objects are rejected before framework autodetection
- OpenQASM 2 parsing is delegated to `qiskit.QuantumCircuit.from_qasm_str(...)`
- OpenQASM 3 parsing is delegated to `qiskit.qasm3.loads(...)`

CUDA-Q runtime arguments:

- CUDA-Q remains Linux/WSL2-only because upstream CUDA-Q is not available for native Windows
- closed kernels do not need extra options
- scalar runtime arguments use `CircuitRenderOptions(adapter_options={"cudaq_args": (...)})`
- the first supported runtime values are `int`, `float`, and `bool`

OpenQASM example:

```python
from pathlib import Path

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    Path("bell.qasm"),
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(framework="qasm")),
        output=OutputOptions(show=False),
    ),
)
```

### `DrawMode`

For a guided managed-2D walkthrough, see `qiskit-2d-exploration-showcase` in [Examples](../examples/README.md).

- `AUTO`
  - notebook: `pages`
  - normal script: `pages_controls`
- `PAGES`
  - 2D: one managed figure per page
  - 3D: one managed figure per page window
- `PAGES_CONTROLS`
  - 2D: managed `Page` / `Visible` controls
  - 3D: managed `Page` / `Visible` controls with vertically stacked 3D pages
- `SLIDER`
  - 2D: discrete horizontal and vertical slider navigation
  - 3D: horizontal slider navigation
- `FULL`
  - full unpaged render

### `UnsupportedPolicy`

- `RAISE`
  - fail on recoverable unsupported operations
- `PLACEHOLDER`
  - keep the render alive with placeholders when the unsupported case is recoverable

### 3D topology inputs

`side.render.topology` accepts the built-in names `"line"`, `"grid"`, `"star"`, `"star_tree"`, and `"honeycomb"`, or a typed topology object.

Public topology helpers:

- `HardwareTopology`
  - static topology with explicit node ids, edges, optional coordinates, and a name
- `FunctionalTopology`
  - wraps a `Callable[[int], HardwareTopology]`
- `PeriodicTopology1D`
  - composes initial, repeating, and final cells with bridge edges between neighboring cells
- `PeriodicTopology2D`
  - composes corner, edge, and center cells with horizontal and vertical bridge edges
- `line_topology(qubit_count)`
- `grid_topology(qubit_count)`
- `star_topology(qubit_count)`
- `star_tree_topology(qubit_count)`
- `honeycomb_topology(qubit_count)`

The built-in names are backed by the public functional builders and support any positive qubit count. The `"honeycomb"` builder creates an IBM-inspired compact hexagonal footprint. For circuits that use fewer qubits than a topology contains, `topology_qubits="used"` keeps the view focused on the first allocated nodes, while `topology_qubits="all"` also shows inactive physical nodes using their topology ids as labels. If a circuit needs more nodes than the topology currently has, `topology_resize="fit"` can resize functional and periodic topologies; static `HardwareTopology` instances stay fixed.

### `StylePreset`

- `PAPER`
- `NOTEBOOK`
- `COMPACT`
- `PRESENTATION`
- `ACCESSIBLE`

Presets are shared by circuit drawing and histogram plotting. `ACCESSIBLE` uses a high-contrast, colorblind-friendlier palette and stronger circuit strokes.

### `DrawResult`

`draw_quantum_circuit(...)` always returns `DrawResult`.

Fields:

- `primary_figure`
- `primary_axes`
- `figures`
- `axes`
- `mode`
- `page_count`
- `diagnostics`
- `detected_framework`
- `interactive_enabled`
- `hover_enabled`
- `saved_path`

Convenience properties:

- `resolved_mode`
- `warnings`

Export helpers:

- `save(path)`
- `save_all_pages(output_dir, filename_prefix="page", extension=".png")`
- `to_dict()`

Example: `result.save(path)`, `result.save_all_pages(output_dir)`, and `result.to_dict()`.

## Comparison APIs

Circuit comparison and histogram comparison are the two public comparison APIs.

## Circuit comparison

### `CircuitCompareConfig`

`CircuitCompareConfig` keeps one shared side baseline, optional per-side block overrides, one compare block, and one output block:

```python
CircuitCompareConfig(
    shared=DrawSideConfig(),
    left_render=None,
    right_render=None,
    left_appearance=None,
    right_appearance=None,
    compare=CircuitCompareOptions(
        left_title="Left",
        right_title="Right",
        highlight_differences=True,
        show_summary=True,
    ),
    output=OutputOptions(
        show=True,
        output_path=None,
        figsize=None,
    ),
)
```

Notes:

- `compare_circuits(...)` is a 2D-only public API
- `shared` provides the baseline `DrawSideConfig` used on both sides
- `left_render` / `right_render` override only the render block on one side
- `left_appearance` / `right_appearance` override only the appearance block on one side
- the default `auto` mode renders the two circuits as normal managed `pages_controls` figures and uses `result.figure` for the compact comparison summary
- explicit circuit modes `pages`, `pages_controls`, and `slider` also render the two circuits as normal managed circuit figures
- explicit `mode="full"` or caller-owned `axes` use the static side-by-side comparison path

### `CircuitCompareResult`

`compare_circuits(...)` returns two normal per-side circuit figures plus one compact summary figure by default. When `mode="full"` is requested, or when caller-owned axes are provided, it returns one static side-by-side figure.

Fields:

- `figure`: the compact summary figure in managed comparison, or the side-by-side figure in static comparison
- `axes`: the primary left and right circuit axes
- `left_result`: nested `DrawResult` for the left circuit
- `right_result`: nested `DrawResult` for the right circuit
- `metrics`
- `diagnostics`
- `saved_path`

`metrics` includes:

- layer counts and `layer_delta`
- total operation counts and `operation_delta`
- multi-qubit counts and `multi_qubit_delta`
- measurement counts and `measurement_delta`
- swap counts and `swap_delta`
- `differing_layer_count`
- `left_only_layer_count`
- `right_only_layer_count`

Export helpers:

- `save(path)`
- `to_dict()`

## Histogram APIs

Single and comparison histogram APIs share the same normalization path for counts, quasi-probabilities, selected marginals, and framework-native result payloads.

## Histograms

### `HistogramKind`

- `AUTO`
  - infers counts from non-negative integers
  - otherwise treats the data as quasi-probabilities
- `COUNTS`
  - requires non-negative integer values
- `QUASI`
  - accepts positive and negative weights

### `HistogramMode`

- `AUTO`
  - normal script: `interactive`
  - notebook widget backend such as `nbagg`, `ipympl`, or `widget`: `interactive`
  - inline or non-widget notebook backend: `static`
- `STATIC`
  - draws one static histogram with the selected ordering
- `INTERACTIVE`
  - adds a managed slider viewport, per-bin hover, an order button that shows the current mode, a label button for binary or decimal state labels, a `Mode: Counts` / `Mode: Quasi` toggle when the original input is counts, a conditional slider button when hidden bins exist, and a marginal-qubits text box
  - requires a library-managed figure and cannot be combined with `ax=...`

### `HistogramStateLabelMode`

- `BINARY`
  - keeps normalized state labels as bitstrings
- `DECIMAL`
  - converts each state label to decimal for display
  - if the state contains space-separated registers, each register is converted independently

### `HistogramSort`

- `STATE`
- `STATE_DESC`
- `VALUE_DESC`
- `VALUE_ASC`

### `HistogramDrawStyle`

- `SOLID`
- `OUTLINE`
- `SOFT`

### `HistogramConfig`

`HistogramConfig` separates data selection, view, appearance, and output:

```python
HistogramConfig(
    data=HistogramDataOptions(
        kind=HistogramKind.AUTO,
        top_k=None,
        qubits=None,
        result_index=0,
        data_key=None,
    ),
    view=HistogramViewOptions(
        mode=HistogramMode.AUTO,
        sort=HistogramSort.STATE,
        state_label_mode=HistogramStateLabelMode.BINARY,
    ),
    appearance=HistogramAppearanceOptions(
        preset=None,
        theme=None,
        draw_style=HistogramDrawStyle.SOLID,
        hover=True,
        show_uniform_reference=False,
    ),
    output=OutputOptions(
        show=True,
        output_path=None,
        figsize=None,
    ),
)
```

Important fields:

- `data.kind`: `AUTO`, `COUNTS`, or `QUASI`
- `view.mode`: `AUTO`, `STATIC`, or `INTERACTIVE`
- `view.sort`: `STATE`, `STATE_DESC`, `VALUE_DESC`, or `VALUE_ASC`
- `data.top_k`: keep only the highest-ranked bins after sorting
- `data.qubits`: joint marginal over a subset of qubits
- `data.result_index`: which entry to read when the input object or tuple/list contains several histogram payloads
- `data.data_key`: which Qiskit `DataBin` field to use when several bit-array fields exist
- `appearance.preset`: shared preset baseline
- `appearance.theme`: explicit theme override
- `appearance.draw_style`: `SOLID`, `OUTLINE`, or `SOFT`
- `view.state_label_mode`: `BINARY` or `DECIMAL`
- `appearance.hover`: whether histogram bin and control-help hover is enabled in interactive mode
- `appearance.show_uniform_reference`: draw a uniform reference line for easier visual comparison
- `output.output_path`: optional file path for saving
- `output.figsize`: managed figure size in inches

Interactive notes:

- the order button cycles through binary ascending, binary descending, value ascending, and value descending
- the order button label shows the current ordering mode directly
- the label button switches the visible state labels between binary and decimal without changing `HistogramResult.state_labels`
- the kind-toggle button only appears when interactive menus are active and the original histogram input is counts
- the slider button only appears when the current histogram distribution has more bins than the visible window can show at once
- the marginal text box accepts comma-separated qubit indices such as `0,2,5`
- hovering the marginal text box shows a short multi-line usage hint
- saved interactive histograms omit widget chrome and keep the current visible data window

### `HistogramCompareConfig`

`HistogramCompareConfig` keeps data selection in `data`, comparison presentation in `compare`, and shared output in `output`:

```python
HistogramCompareConfig(
    data=HistogramDataOptions(
        kind=HistogramKind.AUTO,
        top_k=None,
        qubits=None,
        result_index=0,
        data_key=None,
    ),
    compare=HistogramCompareOptions(
        sort=HistogramCompareSort.STATE,
        left_label="Left",
        right_label="Right",
        hover=True,
        preset=None,
        theme=None,
    ),
    output=OutputOptions(
        show=True,
        output_path=None,
        figsize=None,
    ),
)
```

Important fields:

- `data.kind`: `AUTO`, `COUNTS`, or `QUASI`
- `compare.sort`: `STATE`, `STATE_DESC`, or `DELTA_DESC`
- `data.top_k`: keep only the largest states after sorting
- `data.qubits`: optional joint marginal over selected qubits
- `data.result_index`: choose one entry when the input is a tuple or list of results
- `data.data_key`: choose one Qiskit `DataBin` field when several exist
- `compare.preset`: shared preset baseline
- `compare.theme`: histogram theme override
- `compare.left_label` and `compare.right_label`: legend labels

### `HistogramResult`

`plot_histogram(...)` always returns `HistogramResult`.

Fields:

- `figure`
- `axes`
- `kind`
- `state_labels`
- `values`
- `qubits`
- `diagnostics`
- `saved_path`

Notes:

- direct mappings can use `str` or `int` state keys
- Qiskit inputs include `Counts`, `QuasiDistribution`, `SamplerResult`, `PrimitiveResult`, `SamplerPubResult`, `BitArray`, and `DataBin`
- Cirq result inputs can use the `measurements` mapping from `Result` / `ResultDict`
- PennyLane execution outputs can be passed directly as `qml.counts()` dictionaries, `qml.probs()` vectors, or `qml.sample()` arrays
- MyQLM result inputs can use `qat.core.Result.raw_data`
- CUDA-Q sample inputs can use `SampleResult`-style objects that expose count pairs through `items()`
- tuple or list results from frameworks can be passed directly and narrowed with `HistogramDataOptions(result_index=...)`
- when `qubits` is provided, the function returns one joint marginal and preserves the exact qubit order you passed
- in interactive mode, `state_labels` and `values` still describe the full ordered histogram distribution, not just the visible slider window

Export helpers:

- `save(path)`
- `to_dict()`
- `to_csv(path)`

### `HistogramCompareResult`

Fields:

- `figure`
- `axes`
- `kind`
- `state_labels`
- `left_values`
- `right_values`
- `delta_values`
- `metrics`
- `qubits`
- `diagnostics`
- `saved_path`

`metrics` includes:

- `total_variation_distance`
- `max_absolute_delta`

Export helpers:

- `save(path)`
- `to_dict()`
- `to_csv(path)`

## Builder and IR APIs

### `CircuitBuilder`

`CircuitBuilder` is the simplest framework-free way to construct a `CircuitIR`.

Typical pattern:

```python
from quantum_circuit_drawer import CircuitBuilder

circuit = (
    CircuitBuilder(2, 1, name="demo")
    .h(0)
    .cx(0, 1)
    .measure(1, 0)
    .build()
)
```

Useful builder methods include:

- single-qubit gates such as `.h()`, `.x()`, `.rz()`, `.u()`
- controlled gates such as `.cx()`, `.cz()`, `.crx()`, `.cu()`
- `.swap()`
- `.barrier()`
- `.reset()`
- `.measure()`
- `.measure_all()`

### Public IR modules

The public IR surface lives under `quantum_circuit_drawer.ir`.

Import it when you want:

- complete control over wires, layers, and operations
- a framework-free intermediate representation
- a base for your own preprocessing or adapter work

## `ax` and `axes`

### `ax` for `draw_quantum_circuit(...)` and `plot_histogram(...)`

`ax` is reserved for caller-managed static rendering paths.

For circuit drawing:

- allowed with `pages` and `full`
- not allowed with `pages_controls` or `slider`
- 3D requires a Matplotlib axes created with `projection="3d"`

For histograms:

- allowed only for static histogram rendering
- interactive histogram mode requires a library-managed figure

### `axes` for `compare_circuits(...)`

`compare_circuits(...)` accepts `axes=(left_axes, right_axes)` when you want to embed the comparison in your own Matplotlib figure.
Caller-owned axes are only valid for the static comparison path. With axes, `mode="auto"` is treated like `mode="full"`. Managed compare modes such as `pages`, `pages_controls`, and `slider` create their own figures, just like `draw_quantum_circuit(...)`.

## Style and theme

`DrawStyle` controls geometry, spacing, and line widths. The main stroke families are:

- `wire_line_width`
- `classical_wire_line_width`
- `gate_edge_line_width`
- `barrier_line_width`
- `measurement_line_width`
- `connection_line_width`
- `topology_edge_line_width`

`DrawTheme` controls colors for:

- figure and axes backgrounds
- text
- quantum and classical wires
- gates and measurements
- controls and control connections
- topology edges and topology planes
- hover labels
- managed UI widgets

Built-in theme names are `light`, `paper`, `dark`, and `accessible`.

## Hover

`HoverOptions` stays public and is nested under `DrawConfig.side.appearance.hover`.

```python
DrawConfig(
    side=DrawSideConfig(
        appearance=CircuitAppearanceOptions(
            hover={
                "enabled": True,
                "show_size": True,
                "show_matrix": "auto",
                "matrix_max_qubits": 2,
            }
        )
    )
)
```

## Extension API

For third-party extensions, the stable public surface is:

- `quantum_circuit_drawer.adapters` for adapter registration
- `quantum_circuit_drawer.ir` for `CircuitIR`, semantic IR types, and `lower_semantic_circuit(...)`
- `quantum_circuit_drawer.typing` for `LayoutEngineLike` and `LayoutEngine3DLike`
- `quantum_circuit_drawer.layout` and scene modules for layout outputs

The recommended public helpers for adapters are:

- `register_adapter(...)`
- `unregister_adapter(...)`
- `available_frameworks()`
- `detect_framework_name(...)`
- `get_adapter(...)`

Adapter authors can stay on the legacy `to_ir(...)` path or add the richer optional `to_semantic_ir(...)` path when they need native grouping, provenance, or annotations to survive comparison and diagnostics longer.

See [Extension API](extensions.md) for the supported contract, examples, and the list of public vs internal modules.

## Internal compatibility facades

These packages remain importable for compatibility and compatibility-sensitive tests, but they are not part of the stable public extension contract:

- `quantum_circuit_drawer.drawing`
- `quantum_circuit_drawer.managed`
- `quantum_circuit_drawer.plots`

Treat them as compatibility facades, not as long-term public modules to build against.
