# User guide

This guide explains the main behavior of `quantum-circuit-drawer` from a user point of view.

## The core idea

The library is built around one public function:

```python
draw_quantum_circuit(
    circuit,
    framework=None,
    *,
    style=None,
    layout=None,
    backend="matplotlib",
    ax=None,
    output=None,
    show=True,
    page_slider=False,
    composite_mode="compact",
    **options,
)
```

Most users only need `circuit`, and sometimes `style`, `output`, `show`, `ax`, or `composite_mode`.

## What you can pass as `circuit`

You can pass:

- a supported framework object such as a Qiskit, Cirq, PennyLane, or CUDA-Q circuit representation
- a `CircuitIR` object from `quantum_circuit_drawer.ir`

By default, the library tries to detect the right adapter automatically.

If you already know the framework and want to be explicit, pass `framework="qiskit"` or another supported framework name.

If the explicit framework does not match the object you pass, the call raises `UnsupportedFrameworkError`.

## What the function returns

The return value depends on how you render:

- If `ax is None`, the library creates a managed Matplotlib figure and returns `(figure, axes)`.
- If `ax` is provided, the library draws on that axes and returns the same axes object.

This small difference is worth remembering when you write reusable code.

## Showing and saving

### `show`

- `show=True` means the managed figure is shown when the current Matplotlib backend is interactive.
- `show=False` means no window is opened.

Use `show=False` for scripts, tests, automated exports, or notebook flows where you want full control.

### `output`

Pass a path to save the rendered result:

```python
draw_quantum_circuit(circuit, output="circuit.png", show=False)
```

The path can be a string or another path-like object.

### `ax`

Use `ax` when you want to place the circuit inside your own Matplotlib layout:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 3))
draw_quantum_circuit(circuit, ax=ax)
```

This is useful when the circuit is only one panel in a larger figure.

## Styling

You can configure styling in two ways:

- pass a mapping such as `style={"theme": "paper", "show_params": False}`
- pass a `DrawStyle` instance

The built-in themes are:

- `dark` for a high-contrast dark background
- `light` for a clean bright background
- `paper` for a softer publication-style look

### Quick styling example

```python
draw_quantum_circuit(
    circuit,
    style={
        "theme": "paper",
        "show_params": False,
        "max_page_width": 6.0,
    },
)
```

### Style options

These are the user-facing style fields accepted by the current public API.

| Option | Default | Meaning |
| --- | --- | --- |
| `font_size` | `12.0` | Base text size used in the drawing |
| `wire_spacing` | `1.2` | Vertical distance between wires |
| `layer_spacing` | `0.45` | Horizontal distance between layers |
| `gate_width` | `0.72` | Gate box width |
| `gate_height` | `0.72` | Gate box height |
| `line_width` | `1.6` | Main line thickness |
| `control_radius` | `0.08` | Controlled-gate dot radius |
| `show_params` | `True` | Whether gate parameters are shown |
| `show_wire_labels` | `True` | Whether wire labels are shown |
| `theme` | `dark` | Built-in theme or a `DrawTheme` |
| `margin_left` | `0.85` | Left outer margin |
| `margin_right` | `0.35` | Right outer margin |
| `margin_top` | `0.8` | Top outer margin |
| `margin_bottom` | `0.8` | Bottom outer margin |
| `label_margin` | `0.18` | Space between wires and labels |
| `classical_wire_gap` | `0.75` | Separation inside classical-wire rendering |
| `swap_marker_size` | `0.14` | Size of swap markers |
| `max_page_width` | `20.0` | Page width before wrapping to another page |
| `page_vertical_gap` | `1.8` | Vertical gap between wrapped pages |

If you pass an unknown style key or an invalid value, the library raises `StyleValidationError`.

## Wide circuits and `page_slider`

For wide circuits, there are two main modes:

- normal wrapped rendering, controlled mainly by `max_page_width`
- interactive horizontal scrolling, enabled with `page_slider=True`

Example:

```python
draw_quantum_circuit(
    circuit,
    style={"max_page_width": 4.0},
    page_slider=True,
)
```

Important behavior:

- `page_slider=True` only works when the library manages the figure for you
- if you pass `ax=...` together with `page_slider=True`, the call raises `ValueError`
- if you also pass `output=...`, the saved file contains the paged circuit without the slider UI

This makes `page_slider` useful for interactive exploration while keeping exported images clean.

## Composite operations and `composite_mode`

Some frameworks can hand the drawer a subcircuit, composite instruction, or operation with a decomposition.

- `composite_mode="compact"` keeps that operation as one labeled box when the adapter can represent it that way.
- `composite_mode="expand"` asks the adapter to use the available decomposition instead.

Example:

```python
draw_quantum_circuit(
    circuit,
    composite_mode="expand",
)
```

This is especially useful for Qiskit instructions built from subcircuits, Cirq `CircuitOperation`, and PennyLane operations such as `QFT`.

## Classical conditions

For supported frameworks, classical conditions are rendered as a classical double-line connection plus a short label such as `if c[0]=1` or `if c=3`.

The current goal is to show when an operation is conditioned on classical data, not to render full control-flow branches.

## Choosing the framework explicitly

Framework detection is convenient, but explicit selection can make scripts clearer:

```python
draw_quantum_circuit(circuit, framework="cirq")
```

Use this when:

- you want to make your code more self-explanatory
- you work with wrapper objects and want to be explicit about the intended adapter

## Advanced use: custom layout engines

Most users can ignore the `layout` parameter.

It exists for advanced integrations where you want to provide your own layout engine object. That object must provide a `compute(circuit, style)` method compatible with the library's layout protocol.

If you are only drawing circuits, stay with the default layout engine.

## Exceptions you are likely to see

| Exception | Typical meaning |
| --- | --- |
| `UnsupportedFrameworkError` | The object could not be matched to a supported framework, or your explicit `framework` argument does not match the object |
| `UnsupportedBackendError` | You asked for a backend other than the currently supported `matplotlib` backend |
| `StyleValidationError` | One or more style values are invalid |
| `RenderingError` | The figure could not be written to the requested output path |
| `UnsupportedOperationError` | The adapter found an operation that cannot be represented meaningfully |
| `LayoutError` | Layout computation failed |

## Practical guidance

- Start with autodetection and only set `framework` when you need to be explicit.
- Use `show=False` in scripts and tests.
- Use `ax=...` when the circuit is part of a larger Matplotlib figure.
- Use `page_slider=True` for interactive exploration of very wide circuits.
- Use `theme="paper"` when you want a documentation or article-friendly look.

## Next step

- Read [Frameworks](frameworks.md) for source-specific notes.
- Use [Recipes](recipes.md) for copy-paste examples.
