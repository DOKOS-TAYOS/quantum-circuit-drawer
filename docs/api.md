# API reference

## Main functions

```python
draw_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult

plot_histogram(
    data: object,
    *,
    config: HistogramConfig | None = None,
    ax: Axes | None = None,
) -> HistogramResult
```

These are the public entry points for circuit drawing and result histograms.

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
    style=None,
    hover=False,
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

Examples:

- simple managed render: one figure and one axes
- `pages` in a notebook: several figures, one per page
- caller-managed `ax=...`: one figure and one axes, wrapped in `DrawResult`

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
  - adds a managed slider viewport, per-bin hover, an order button that shows the current mode, a label button for binary or decimal state labels, a conditional slider button when hidden bins exist, and a marginal-qubits text box
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
- `result_index`: which Qiskit result entry to read when the object contains several results
- `data_key`: which Qiskit `DataBin` field to use when several bit-array fields exist
- `state_label_mode`: `BINARY` or `DECIMAL` for the visible x-axis labels
- `output_path`: optional file path for saving
- `figsize`: managed figure size in inches
- `hover`: whether histogram bin and control help hover is enabled in interactive mode

Interactive notes:

- the order button cycles through binary ascending, binary descending, value ascending, and value descending
- the order button label shows the current ordering mode directly
- the label button switches the visible state labels between binary and decimal without changing `HistogramResult.state_labels`
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
