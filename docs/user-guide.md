# User guide

This guide focuses on how the library behaves in real use, not just on listing parameters.

The best way to think about `quantum-circuit-drawer` is:

- your framework or IR object stays the source of truth
- the config objects let you steer rendering without changing your workflow
- the result objects give you a stable handle back

## Circuit Workflows

### The normal script workflow

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(show=False),
)
```

This is the default recommendation for scripts because it gives you:

- one stable `DrawResult`
- library-managed figures
- room to switch modes later without rewriting the call shape

### Auto mode

`DrawMode.AUTO` resolves by runtime context:

- real notebook: `pages`
- normal `.py` execution: `pages_controls`

That means you can often leave `mode` alone until you have a reason to override it.

### When to choose each draw mode

#### `pages`

Use this when you want explicit pages:

- notebooks
- export workflows
- direct access to every page through `DrawResult.figures`

In managed 2D mode, the library creates one figure per page. In managed 3D mode, it creates one figure per 3D page window.

#### `pages_controls`

Use this when you want a managed page browser:

- 2D: `Page` and `Visible`
- 3D: `Page` and `Visible`, with several visible 3D pages stacked vertically

This is the best default for normal script execution.

#### `slider`

Use this when the circuit is wide and you want a viewport instead of separate pages:

- 2D: horizontal and vertical sliders when needed
- 3D: horizontal slider only

#### `full`

Use this when the whole circuit fits comfortably in one scene and you want the unpaged view directly.

## Caller-Managed Axes

Pass `ax=...` only for static rendering.

```python
import matplotlib.pyplot as plt

from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

figure, axes = plt.subplots(figsize=(8, 3))
result = draw_quantum_circuit(
    circuit,
    ax=axes,
    config=DrawConfig(mode=DrawMode.PAGES, show=False),
)
```

Use this when the circuit is just one subplot in a larger figure. Do not combine `ax=...` with `pages_controls` or `slider`.

## Saving

`output_path` always saves a clean figure:

- `pages`, `pages_controls`, and `slider` save the concatenated paged composition
- `full` saves the full unpaged scene

```python
draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        mode="slider",
        output_path="circuit.png",
        show=False,
    ),
)
```

This lets you use an interactive mode during work and still export a clean image without widget chrome.

## 3D Workflows

3D rendering is useful when topology matters visually or when you want a hardware-layout perspective.

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode="pages_controls",
        topology="grid",
        topology_menu=True,
        direct=False,
        show=False,
    ),
)
```

What changes in 3D:

- `pages` works
- `pages_controls` works
- `slider` is horizontal only
- `full` works
- managed `pages_controls` preserves a shared camera while you navigate

## Presets, Style, And Hover

### Presets

Presets are the quickest way to change the overall feel of the output:

- `paper`
- `notebook`
- `compact`
- `presentation`

They are useful when you want a sensible baseline without tuning many style fields manually.

```python
from quantum_circuit_drawer import DrawConfig, StylePreset, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        preset=StylePreset.PRESENTATION,
        show=False,
    ),
)
```

### Fine style control

You can still override individual fields:

```python
config = DrawConfig(
    preset="paper",
    style={
        "max_page_width": 9.0,
        "wire_line_width": 1.8,
        "classical_wire_line_width": 1.5,
        "connection_line_width": 1.9,
        "measurement_line_width": 1.4,
    },
    hover={"enabled": True, "show_size": True},
)
```

`DrawTheme` covers more than circuit strokes now. It also covers:

- control markers
- control connections
- topology colors
- managed UI colors
- hover colors

### Hover

Hover is optional and public through `DrawConfig.hover`.

Typical example:

```python
config = DrawConfig(
    hover={
        "enabled": True,
        "show_size": True,
        "show_matrix": "auto",
        "matrix_max_qubits": 2,
    },
    show=False,
)
```

Use `show_matrix="never"` when you want the lightest path, especially for frameworks that may be heavier on native Windows.

## Recoverable Unsupported Operations

The default policy is strict:

```python
from quantum_circuit_drawer import DrawConfig, UnsupportedPolicy

config = DrawConfig(
    unsupported_policy=UnsupportedPolicy.RAISE,
    show=False,
)
```

If you prefer a best-effort drawing with placeholders for recoverable unsupported operations:

```python
config = DrawConfig(
    unsupported_policy=UnsupportedPolicy.PLACEHOLDER,
    show=False,
)
```

This can be useful when you are inspecting larger circuits and want to keep visual continuity even if some operations are not yet fully representable.

## Comparison Workflows

### Compare two circuits

`compare_circuits(...)` is the quickest way to inspect structural change.

```python
from quantum_circuit_drawer import CircuitCompareConfig, compare_circuits

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

What you get back:

- one figure with two subplot axes
- one nested `DrawResult` per side
- metrics such as layers, total operations, multi-qubit operations, swaps, and measurements
- optional highlighted background bands on layers that changed

Use this for:

- transpilation inspection
- compact vs expanded composite comparison
- version-to-version circuit regressions

### Compare two histograms

Use `compare_histograms(...)` when you want two aligned distributions on the same state space.

```python
from quantum_circuit_drawer import HistogramCompareConfig, compare_histograms

result = compare_histograms(
    left_data,
    right_data,
    config=HistogramCompareConfig(
        left_label="Ideal",
        right_label="Sampled",
        sort="delta_desc",
        show=False,
    ),
)
```

This is especially useful for:

- ideal vs sampled comparisons
- baseline vs new execution comparisons
- comparing two result objects with the same logical meaning but different noise levels

## Histogram Workflows

### Single histogram

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

result = plot_histogram(
    data,
    config=HistogramConfig(show=False),
)
```

### Counts vs quasi-probabilities

`HistogramKind.AUTO` infers counts when the values are non-negative integers and otherwise treats the data as quasi-probabilities.

You can still force the meaning:

```python
from quantum_circuit_drawer import HistogramConfig, HistogramKind

config = HistogramConfig(
    kind=HistogramKind.QUASI,
    show=False,
)
```

### Sorting, top-k, and labels

Useful controls:

- `sort="state"`
- `sort="state_desc"`
- `sort="value_desc"`
- `sort="value_asc"`
- `top_k=<n>`
- `state_label_mode="binary" | "decimal"`

### Marginals

Use `qubits=(...)` when you want a joint marginal over selected qubits:

```python
result = plot_histogram(
    {"101": 2, "001": 1, "111": 3},
    config=HistogramConfig(qubits=(0, 2), show=False),
)
```

The qubit order is preserved exactly as passed.

### Interactive histogram mode

`HistogramMode.AUTO` resolves by runtime context:

- normal script: `interactive`
- notebook widget backend such as `nbagg`, `ipympl`, or `widget`: `interactive`
- inline or non-widget notebook backend: `static`

In interactive mode, the managed figure can add:

- a slider viewport
- per-bin hover
- an order button that shows the current mode
- a label button for binary or decimal labels
- a `Mode: Counts` / `Mode: Quasi` toggle when the original input is counts
- a slider button when hidden bins exist
- a marginal-qubits text box

Set `hover=False` if you want the interactive controls without hover labels.

## Framework-Native Result Inputs

`plot_histogram(...)` is not limited to raw `dict` data.

It also accepts:

- plain mappings such as `dict` or `Counter`
- Qiskit counts, quasi-distributions, and sampler result containers
- Cirq `Result` / `ResultDict` measurement mappings
- PennyLane `qml.counts()` dictionaries, `qml.probs()` vectors, and `qml.sample()` arrays
- MyQLM `qat.core.Result` objects through `raw_data`
- CUDA-Q `SampleResult`-style objects through `items()`

If a framework returns several payloads at once, pass the tuple or list directly and choose one entry with `HistogramConfig(result_index=...)`.

## Working With The Result Objects

### `DrawResult`

The most used fields are:

- `primary_figure`
- `primary_axes`
- `figures`
- `axes`
- `page_count`
- `detected_framework`
- `interactive_enabled`
- `hover_enabled`
- `saved_path`
- `warnings`

### `HistogramResult`

The most used fields are:

- `figure`
- `axes`
- `kind`
- `state_labels`
- `values`
- `qubits`
- `diagnostics`

### Comparison results

For comparisons, keep an eye on:

- `CircuitCompareResult.metrics`
- `HistogramCompareResult.metrics`

Those metrics are often enough to summarize structural or distribution change programmatically.

## Framework-Free Workflows

If you want a framework-free path, choose one of these:

- `CircuitBuilder` for small or generated circuits
- public `CircuitIR` types for full control

That path is especially useful for:

- custom preprocessors
- research tooling
- tests
- pipelines where the circuit source is not one of the built-in adapters
