# API reference

## Main functions

```python
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
    left_config: DrawConfig | None = None,
    right_config: DrawConfig | None = None,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, Axes] | None = None,
) -> CircuitCompareResult

plot_histogram(
    data: object,
    *,
    config: HistogramConfig | None = None,
    ax: Axes | None = None,
) -> HistogramResult
```

These are the public entry points for circuit drawing, side-by-side circuit
comparison, and result histograms.

## `DrawConfig`

`DrawConfig` groups the public options in one stable object:

```python
DrawConfig(
    framework=None,
    backend="matplotlib",
    layout=None,
    view="2d",
    mode=DrawMode.AUTO,
    composite_mode="compact",
    topology="line",
    topology_menu=False,
    direct=True,
    show=True,
    output_path=None,
    figsize=None,
    preset=None,
    style=None,
    hover=False,
    unsupported_policy=UnsupportedPolicy.RAISE,
)
```

### Field order

The fields are ordered by responsibility:

1. framework and backend
2. layout and view
3. mode selection
4. 3D topology options
5. display and saving
6. style and hover

### Important fields

- `view`: `"2d"` or `"3d"`
- `mode`: `DrawMode.AUTO`, `PAGES`, `PAGES_CONTROLS`, `SLIDER`, or `FULL`
- `topology`: only used in 3D
- `topology_menu`: managed interactive 3D topology selector
- `show`: whether the library should show the figure
- `output_path`: optional file path for saving
- `figsize`: managed figure size in inches
- `style`: `DrawStyle`, mapping, or `None`
- `hover`: `bool`, `HoverOptions`, mapping, or `None`

## `DrawMode`

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
  - 2D: discrete horizontal / vertical slider navigation
  - 3D: horizontal slider navigation
- `FULL`
  - full unpaged render

## `DrawResult`

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

Examples:

- simple managed render: one figure and one axes
- `pages` in a notebook: several figures, one per page
- caller-managed `ax=...`: one figure and one axes, wrapped in `DrawResult`

## Extension API

For third-party extensions, the stable v1 public surface is:

- `quantum_circuit_drawer.adapters` for adapter registration
- `quantum_circuit_drawer.typing` for `LayoutEngineLike` and `LayoutEngine3DLike`

The recommended public helpers for adapters are:

- `register_adapter(...)`
- `unregister_adapter(...)`
- `available_frameworks()`
- `detect_framework_name(...)`
- `get_adapter(...)`

See [Extension API](extensions.md) for the supported contract, examples, and the list of public vs internal modules.

## Internal compatibility facades

These packages remain importable for compatibility and compatibility-sensitive tests, but they are not part of the stable public extension contract:

- `quantum_circuit_drawer.drawing`
- `quantum_circuit_drawer.managed`
- `quantum_circuit_drawer.plots`

## `CircuitCompareConfig`

```python
CircuitCompareConfig(
    left_title="Left",
    right_title="Right",
    highlight_differences=True,
    show_summary=True,
    show=True,
    output_path=None,
    figsize=None,
)
```

Notes:

- `compare_circuits(...)` is a 2D-only v1 API
- per-side configs still control framework, preset, style, and hover
- per-side `mode`, `show`, and `output_path` are normalized internally

## `CircuitCompareResult`

`compare_circuits(...)` returns one figure with two subplot axes.

Fields:

- `figure`
- `axes`
- `left_result`
- `right_result`
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

## `HistogramKind`

- `AUTO`
  - infers counts from non-negative integers
  - otherwise treats the data as quasi-probabilities
- `COUNTS`
  - requires non-negative integer values
- `QUASI`
  - accepts positive and negative weights

## `HistogramMode`

- `AUTO`
  - normal script: `interactive`
  - notebook widget backend such as `nbagg`, `ipympl`, or `widget`: `interactive`
  - inline or non-widget notebook backend: `static`
- `STATIC`
  - draws one static histogram with the selected ordering
- `INTERACTIVE`
  - adds a managed slider viewport, per-bin hover, an order button that shows the current mode, a label button for binary or decimal state labels, a `Mode: Counts` / `Mode: Quasi` toggle when the original input is counts, a conditional slider button when hidden bins exist, and a marginal-qubits text box
  - requires a library-managed figure and cannot be combined with `ax=...`

## `HistogramStateLabelMode`

- `BINARY`
  - keeps the normalized state labels exactly as bitstrings
- `DECIMAL`
  - converts each state label to decimal for display
  - if the state contains space-separated registers, each register is converted independently

## `HistogramConfig`

```python
HistogramConfig(
    kind=HistogramKind.AUTO,
    mode=HistogramMode.AUTO,
    sort=HistogramSort.STATE,
    qubits=None,
    result_index=0,
    data_key=None,
    state_label_mode=HistogramStateLabelMode.BINARY,
    show=True,
    output_path=None,
    figsize=None,
    hover=True,
)
```

Important fields:

- `kind`: `AUTO`, `COUNTS`, or `QUASI`
- `mode`: `AUTO`, `STATIC`, or `INTERACTIVE`
- `sort`: `STATE`, `STATE_DESC`, `VALUE_ASC`, or `VALUE_DESC`
- `qubits`: optional tuple for a joint marginal over a subset of qubits
- `result_index`: which entry to read when the input object or tuple/list contains several histogram payloads
- `data_key`: which Qiskit `DataBin` field to use when several bit-array fields exist
- `state_label_mode`: `BINARY` or `DECIMAL` for the visible x-axis labels
- `output_path`: optional file path for saving
- `figsize`: managed figure size in inches
- `hover`: whether histogram bin and control help hover is enabled in interactive mode

Interactive notes:

- the order button cycles through binary ascending, binary descending, value ascending, and value descending
- the order button label shows the current ordering mode directly
- the label button switches the visible state labels between binary and decimal without changing `HistogramResult.state_labels`
- the kind-toggle button only appears when interactive menus are active and the original histogram input is counts, letting you switch between raw counts and normalized quasi-probabilities
- the slider button only appears when the current histogram distribution has more bins than the visible window can show at once
- the marginal text box accepts comma-separated qubit indices such as `0,2,5`
- hovering the marginal text box shows a short multi-line usage hint
- saved interactive histograms omit widget chrome and keep the current visible data window

## `HistogramResult`

`plot_histogram(...)` always returns `HistogramResult`.

Fields:

- `figure`
- `axes`
- `kind`
- `state_labels`
- `values`
- `qubits`

Notes:

- direct mappings can use `str` or `int` state keys
- Qiskit 2.x inputs include `Counts`, `QuasiDistribution`, `SamplerResult`, `PrimitiveResult`, `SamplerPubResult`, and `BitArray`
- Cirq result inputs can use the `measurements` mapping from `Result` / `ResultDict`; if there are several measurement keys, the plotted state labels keep one space-separated register per key
- PennyLane execution outputs can be passed directly as `qml.counts()` dictionaries, `qml.probs()` vectors, or `qml.sample()` arrays
- MyQLM result inputs can use `qat.core.Result.raw_data`
- CUDA-Q sample inputs can use `SampleResult`-style objects that expose count pairs through `items()`
- tuple or list results from frameworks can be passed directly and narrowed with `result_index`
- when `qubits` is provided, the function returns one joint marginal and preserves the exact qubit order you passed
- in interactive mode, `state_labels` and `values` still describe the full ordered histogram distribution, not just the visible slider window

## `ax`

`ax` is reserved for static rendering paths:

- allowed with `pages` and `full`
- not allowed with `pages_controls` or `slider`

When `ax` is provided:

- 2D `pages` draws the static paged composition in that axes
- 3D requires a 3D Matplotlib axes

## Style and theme

`DrawStyle` controls geometry and line widths. The main stroke families are:

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

## Hover

`HoverOptions` stays public and is always nested under `DrawConfig.hover`.

```python
DrawConfig(
    hover={
        "enabled": True,
        "show_size": True,
        "show_matrix": "auto",
        "matrix_max_qubits": 2,
    }
)
```

## Examples

### Minimal managed draw

```python
result = draw_quantum_circuit(circuit, config=DrawConfig(show=False))
```

### 2D managed page viewer

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.PAGES_CONTROLS),
)
```

### 3D slider

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode=DrawMode.SLIDER,
        topology="grid",
        show=False,
    ),
)
```

### Full unpaged render

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.FULL, show=False),
)
```

### Side-by-side circuit comparison

```python
result = compare_circuits(
    left_circuit,
    right_circuit,
    config=CircuitCompareConfig(
        left_title="Before",
        right_title="After",
        show=False,
    ),
)
```

### Counts histogram

```python
result = plot_histogram(
    {"00": 51, "11": 49},
    config=HistogramConfig(show=False),
)
```

### Quasi-probability histogram

```python
result = plot_histogram(
    {0: 0.52, 3: -0.08},
    config=HistogramConfig(kind=HistogramKind.QUASI, show=False),
)
```

### Joint marginal on selected qubits

```python
result = plot_histogram(
    {"101": 2, "001": 1, "111": 3},
    config=HistogramConfig(qubits=(0, 2), show=False),
)
```

### Interactive histogram

```python
result = plot_histogram(
    {format(index, "07b"): ((index * 17) % 41) + ((index * 5) % 13) + 3 for index in range(2**7)},
    config=HistogramConfig(
        show_uniform_reference=True,
        show=False,
    ),
)
```

`HistogramMode.AUTO` is the default, so this becomes interactive in a normal script or widget notebook and stays static on inline notebook backends. Set `hover=False` if you want the interactive controls without hover labels.

### Framework-style result payloads

```python
probabilities = [0.125, 0.375, 0.25, 0.25]  # e.g. PennyLane qml.probs(...)
samples = [[0, 1], [1, 1], [1, 1], [0, 1]]  # e.g. PennyLane qml.sample(...)

probability_result = plot_histogram(
    probabilities,
    config=HistogramConfig(show=False),
)

sample_result = plot_histogram(
    samples,
    config=HistogramConfig(show=False),
)
```

The same entrypoint also accepts Cirq `Result` / `ResultDict`, MyQLM `qat.core.Result`, CUDA-Q `SampleResult`-style objects, and direct tuples or lists of several framework outputs when you select one with `result_index`.

### Multi-register decimal labels

```python
result = plot_histogram(
    {"10 011": 7, "01 101": 3},
    config=HistogramConfig(
        state_label_mode=HistogramStateLabelMode.DECIMAL,
        show=False,
    ),
)
```
