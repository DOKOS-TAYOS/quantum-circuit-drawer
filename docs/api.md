# API reference

This page describes the public API that most users are expected to call.

Most code only needs `draw_quantum_circuit(...)`. Advanced users may also use `DrawStyle`, `DrawTheme`, and the internal IR types from `quantum_circuit_drawer.ir`.

## Contents

- [Main entry point](#main-entry-point)
- [Parameters](#parameters)
- [Hover options](#hover-options)
- [Return values](#return-values)
- [Common combinations](#common-combinations)
- [Styles and themes](#styles-and-themes)
- [Exceptions](#exceptions)
- [Advanced layout hook](#advanced-layout-hook)
- [Public exports](#public-exports)

## Main entry point

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
    view="2d",
    topology="line",
    direct=True,
    hover=False,
    **options,
)
```

Import it from the package root:

```python
from quantum_circuit_drawer import HoverOptions, draw_quantum_circuit
```

## Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `circuit` | required | A supported framework object or a `CircuitIR` object |
| `framework` | `None` | Optional explicit framework name such as `"qiskit"`, `"cirq"`, `"pennylane"`, `"myqlm"`, `"cudaq"`, or `"ir"` |
| `style` | `None` | A style mapping or `DrawStyle` instance |
| `layout` | `None` | Advanced custom layout engine; most users should leave this unset |
| `backend` | `"matplotlib"` | Rendering backend; currently only `"matplotlib"` is supported |
| `ax` | `None` | Existing Matplotlib axes to draw into |
| `output` | `None` | File path where the rendered figure should be saved |
| `show` | `True` | Whether to show a managed Matplotlib figure when the backend is interactive |
| `page_slider` | `False` | Enable a horizontal slider for wide managed 2D figures |
| `composite_mode` | `"compact"` | Use `"compact"` for one box, or `"expand"` for supported decompositions |
| `view` | `"2d"` | Use `"2d"` or `"3d"` |
| `topology` | `"line"` | 3D topology: `"line"`, `"grid"`, `"star"`, `"star_tree"`, or `"honeycomb"` |
| `direct` | `True` | In 3D, draw direct control connections when `True`; route through topology paths when `False` |
| `hover` | `False` | `False`, `True`, a `HoverOptions` object, or a mapping with hover fields; enables interactive gate hover where supported |
| `**options` | none | Reserved for forward-compatible options used by the draw pipeline |

## Hover options

`hover=True` is a shorthand for the default `HoverOptions()`:

```python
from quantum_circuit_drawer import HoverOptions, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    hover=HoverOptions(
        show_name=True,
        show_matrix_dimensions=True,
        show_qubits=True,
        show_matrix="auto",
        matrix_max_qubits=2,
    ),
)
```

You can also pass a plain mapping with the same keys:

```python
draw_quantum_circuit(
    circuit,
    hover={"show_matrix": "always", "matrix_max_qubits": 1},
)
```

Hover behavior in this release:

- In interactive 2D figures, hover can show the gate name, matrix dimensions, affected qubits, and an optional matrix.
- When a framework provides an exact matrix, hover uses it. Otherwise, supported canonical 1- and 2-qubit gates fall back to an internal matrix resolver.
- In interactive 3D figures, `hover` still enables the existing compact tooltip behavior.
- Saved figures and non-interactive backends keep static labels and do not create tooltips.
- Managed figures created with `show=False` keep hover active on interactive backends, including notebook backends such as `nbagg`, `ipympl`, and `widget`.
- Gate text in 2D rescales on zoom, but wire labels and other annotations keep their base size.

`HoverOptions` fields:

| Field | Default | Meaning |
| --- | --- | --- |
| `enabled` | `True` | Turn hover on or off after the object is created |
| `show_name` | `True` | Show the gate name |
| `show_size` | `False` | Show the visible gate body size in screen pixels |
| `show_matrix_dimensions` | `True` | Show the matrix dimensions such as `2 x 2` or `4 x 4` |
| `show_qubits` | `True` | Show the affected quantum wires in stable order |
| `show_matrix` | `"auto"` | Use `"never"`, `"auto"`, or `"always"` |
| `matrix_max_qubits` | `2` | Do not show matrices larger than this many qubits |

When `show_matrix="auto"`, the matrix is shown only when the visible gate body is small on screen. This is useful for dense circuits where the label would otherwise be hard to read.

## Return values

The return value depends on who owns the Matplotlib axes.

If `ax` is not provided, the library creates the figure and returns `(figure, axes)`:

```python
figure, axes = draw_quantum_circuit(circuit, show=False)
```

If `ax` is provided, the library draws into that axes and returns the same axes object:

```python
import matplotlib.pyplot as plt

figure, axes = plt.subplots(figsize=(8, 3))
returned_axes = draw_quantum_circuit(circuit, ax=axes)
```

The same rule applies in 3D. Managed 3D rendering returns `(figure, axes)`, while caller-managed 3D rendering returns the 3D axes you passed in.

When the active backend is interactive, `show=False` only skips the automatic `pyplot.show()` call. The returned managed figure still keeps interactive hover available.

## Common combinations

Save without opening a window:

```python
draw_quantum_circuit(circuit, output="circuit.png", show=False)
```

Draw into your own Matplotlib layout:

```python
import matplotlib.pyplot as plt

figure, axes = plt.subplots(figsize=(8, 3))
draw_quantum_circuit(circuit, ax=axes)
```

Use a paper-friendly theme:

```python
draw_quantum_circuit(circuit, style={"theme": "paper"})
```

Use a slider for a wide 2D circuit:

```python
draw_quantum_circuit(
    circuit,
    style={"max_page_width": 4.0},
    page_slider=True,
)
```

Use richer hover details in 2D:

```python
draw_quantum_circuit(
    circuit,
    hover={"show_matrix": "auto", "matrix_max_qubits": 2},
)
```

Render a topology-aware 3D view:

```python
draw_quantum_circuit(
    circuit,
    view="3d",
    topology="grid",
    direct=False,
    hover=True,
)
```

Expand supported composite operations:

```python
draw_quantum_circuit(circuit, composite_mode="expand")
```

## Styles and themes

You can pass style settings as a mapping:

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

You can also pass a typed `DrawStyle` instance:

```python
from quantum_circuit_drawer import DrawStyle, draw_quantum_circuit

style = DrawStyle(show_params=False, max_page_width=6.0)
draw_quantum_circuit(circuit, style=style)
```

Unknown style keys and invalid values raise `StyleValidationError`.

### Built-in themes

| Theme | Use it when |
| --- | --- |
| `dark` | You want the default high-contrast black-background style |
| `light` | You want a bright neutral style |
| `paper` | You want a softer publication or documentation style |

### Style fields

| Field | Default | Meaning |
| --- | --- | --- |
| `font_size` | `12.0` | Base text size |
| `wire_spacing` | `1.2` | Vertical distance between wires |
| `layer_spacing` | `0.45` | Horizontal distance between layers |
| `gate_width` | `0.72` | Gate box width |
| `gate_height` | `0.72` | Gate box height |
| `line_width` | `1.6` | Main line thickness |
| `control_radius` | `0.08` | Controlled-gate dot radius |
| `show_params` | `True` | Show gate parameters |
| `show_wire_labels` | `True` | Show labels next to wires |
| `theme` | `dark` | Built-in theme name or a `DrawTheme` |
| `margin_left` | `0.85` | Left outer margin |
| `margin_right` | `0.35` | Right outer margin |
| `margin_top` | `0.8` | Top outer margin |
| `margin_bottom` | `0.8` | Bottom outer margin |
| `label_margin` | `0.18` | Space between wires and labels |
| `classical_wire_gap` | `0.75` | Separation inside classical-wire rendering |
| `swap_marker_size` | `0.14` | Size of swap markers |
| `max_page_width` | `20.0` | Page width before wrapping |
| `page_vertical_gap` | `1.8` | Vertical gap between wrapped pages |

## Exceptions

| Exception | Typical cause |
| --- | --- |
| `UnsupportedFrameworkError` | The object cannot be matched to a supported adapter, or `framework=...` does not match the object |
| `UnsupportedBackendError` | `backend` is not `"matplotlib"` |
| `UnsupportedOperationError` | An adapter found an operation that cannot be represented meaningfully |
| `StyleValidationError` | The style mapping contains an unknown key or invalid value |
| `RenderingError` | Saving the figure to `output` failed |
| `LayoutError` | Layout computation failed |
| `ValueError` | Runtime options are incompatible, such as `page_slider=True` with `ax=...` |

See [Troubleshooting](troubleshooting.md) for fixes for the most common cases.

## Advanced layout hook

Most users should ignore `layout`.

It exists for advanced integrations that want to provide a custom layout engine after the input circuit has been adapted to `CircuitIR`.

- For `view="2d"`, the object must provide `compute(circuit_ir, style)` and return a 2D `LayoutScene`.
- For `view="3d"`, the object must provide `compute(circuit_ir, style, *, topology_name, direct, hover_enabled)` and return a 3D `LayoutScene3D`.

If you only want to draw circuits, use the default layout engine.

## Public exports

The package root intentionally stays small:

- `draw_quantum_circuit`
- `HoverOptions`
- `DrawStyle`
- `DrawTheme`
- `__version__`
- exception classes such as `UnsupportedFrameworkError`, `StyleValidationError`, and `RenderingError`

IR types are exported from `quantum_circuit_drawer.ir`; see [Frameworks](frameworks.md#internal-ir) for an example.
