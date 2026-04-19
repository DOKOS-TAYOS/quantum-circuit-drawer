# User guide

This guide explains how to use `quantum-circuit-drawer` in everyday workflows.

For the exact public signature, style table, and exception list, use the [API reference](api.md). This page focuses on how the pieces fit together when you are drawing circuits.

## Contents

- [Core idea](#core-idea)
- [Choose a rendering workflow](#choose-a-rendering-workflow)
- [Scripts and batch exports](#scripts-and-batch-exports)
- [Notebooks](#notebooks)
- [Reports and custom Matplotlib figures](#reports-and-custom-matplotlib-figures)
- [Styling in practice](#styling-in-practice)
- [Wide circuits](#wide-circuits)
- [Interactive hover](#interactive-hover)
- [Topology-aware 3D view](#topology-aware-3d-view)
- [Composite operations](#composite-operations)
- [Classical conditions](#classical-conditions)
- [Framework selection](#framework-selection)
- [Practical tips](#practical-tips)

## Core idea

The library is built around one public function:

```python
from quantum_circuit_drawer import draw_quantum_circuit

figure, axes = draw_quantum_circuit(circuit)
```

The input can be a supported framework object or the internal `CircuitIR`. In normal use, the library adapts the circuit, computes a drawable layout, and renders it with Matplotlib.

Most users only need these options regularly:

- `show=False` to avoid opening a window
- `output="path.png"` to save a file
- `ax=axes` to draw inside an existing Matplotlib figure
- `style={...}` to change theme, spacing, labels, or pagination
- `page_slider=True` for managed interactive navigation in 2D or 3D
- `view="3d"` for topology-aware 3D views
- `composite_mode="expand"` when you want to inspect supported decompositions

## Choose a rendering workflow

There are two main workflows.

Managed rendering:

```python
figure, axes = draw_quantum_circuit(circuit, show=False)
```

The library creates the Matplotlib figure and axes. Use this when you want the simplest path, or when you need features that require a managed figure such as `page_slider=True`.

Caller-managed rendering:

```python
import matplotlib.pyplot as plt

figure, axes = plt.subplots(figsize=(8, 3))
returned_axes = draw_quantum_circuit(circuit, ax=axes)
```

You create the figure and the library draws into it. Use this when the circuit is part of a larger Matplotlib layout.

## Scripts and batch exports

For scripts, tests, and batch jobs, prefer `show=False`.

```python
draw_quantum_circuit(
    circuit,
    output="circuit.png",
    show=False,
)
```

This avoids depending on an interactive Matplotlib backend. If saving fails, the library raises `RenderingError`; see [Troubleshooting](troubleshooting.md#saving-output-fails).

## Notebooks

Install Jupyter tooling in the same virtual environment as the library; see [Installation](installation.md#use-the-library-in-jupyter).

In notebooks, it is often clearest to request a figure without opening an external window:

```python
figure, axes = draw_quantum_circuit(circuit, show=False)
figure
```

If you use `%matplotlib widget` or another notebook-interactive backend, managed figures no longer call the built-in `pyplot.show()` automatically. This avoids getting both an interactive widget and an extra static output for the same circuit, while keeping hover available on the returned figure.

If you save files from a notebook, keep paths simple at first:

```python
draw_quantum_circuit(circuit, output="notebook_circuit.png", show=False)
```

## Reports and custom Matplotlib figures

Use `ax=...` when the circuit is one panel in a larger figure.

```python
import matplotlib.pyplot as plt

figure, axes = plt.subplots(1, 2, figsize=(12, 4))
draw_quantum_circuit(circuit_a, ax=axes[0], style={"theme": "paper"})
draw_quantum_circuit(circuit_b, ax=axes[1], style={"theme": "paper"})
figure.tight_layout()
```

When you pass `ax`, `draw_quantum_circuit(...)` returns that same axes object. This is useful in helper functions because you can keep working with the same Matplotlib object.

## Styling in practice

You can pass a style mapping:

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

Useful starting points:

- `theme="dark"` for the default high-contrast look
- `theme="light"` for bright backgrounds
- `theme="paper"` for reports and documentation
- `show_params=False` for cleaner diagrams when parameters are not the focus
- `show_wire_labels=False` when labels are already explained in surrounding text
- `max_page_width=...` when wide circuits wrap too late or too early

For all accepted style fields, see [API reference](api.md#style-fields).

## Wide circuits

Wide circuits can either wrap across pages or use managed sliders.

Wrapped rendering is controlled mainly by `max_page_width`:

```python
draw_quantum_circuit(
    circuit,
    style={"max_page_width": 5.0},
    show=False,
)
```

Interactive 2D navigation uses `page_slider=True`:

```python
figure, axes = draw_quantum_circuit(
    circuit,
    style={"max_page_width": 4.0},
    page_slider=True,
)
```

Important rules:

- `page_slider=True` requires a managed figure, so do not combine it with `ax=...`.
- In 2D, the library shows a bottom slider, a left slider, or both, depending on which axis overflows.
- In 3D, `page_slider=True` moves through circuit columns with a horizontal slider.
- If you also pass `output=...`, the saved file uses the clean paged layout without the slider UI.

Gate labels and subtitles in 2D also adapt to zoom. When you zoom into dense pages, gate text grows only as far as the visible gate body allows, so labels stay inside the box instead of becoming oversized.

## Interactive hover

In interactive 2D figures, you can show gate details on hover without changing the saved output:

```python
from quantum_circuit_drawer import HoverOptions, draw_quantum_circuit

figure, axes = draw_quantum_circuit(
    circuit,
    hover=HoverOptions(show_matrix="auto", matrix_max_qubits=2),
)
```

What hover can show in 2D:

- the gate name
- the matrix dimensions
- the affected qubits
- a matrix, when the framework exposes it or the gate matches a supported canonical fallback and the hover rules allow it

`hover=True` uses the defaults. If you want to hide one part, pass `HoverOptions(...)` or a mapping:

```python
draw_quantum_circuit(
    circuit,
    hover={"show_matrix": "never", "show_size": True},
)
```

In 2D, the hover area covers the full logical gate drawing, including controlled-gate controls, the `X` target, and the vertical connection between them.

## Topology-aware 3D view

Use `view="3d"` when you want the qubits placed on a chip-like topology while the circuit evolves along a depth axis.

```python
draw_quantum_circuit(
    circuit,
    view="3d",
    topology="grid",
    topology_menu=True,
    direct=False,
    hover=True,
)
```

If the circuit is too deep to inspect comfortably in one view, combine the 3D controls:

```python
draw_quantum_circuit(
    circuit,
    view="3d",
    topology="grid",
    topology_menu=True,
    style={"max_page_width": 4.0},
    page_slider=True,
)
```

3D options:

- `topology="line"` works for any qubit count and is the safest first choice.
- `topology="grid"` is useful when your qubit count forms a suitable rectangle.
- `topology="star"` and `topology="star_tree"` highlight hub-like structures.
- `topology="honeycomb"` currently targets a 53-qubit reference layout.
- `topology_menu=True` adds a managed-figure selector for switching between valid topologies on the fly.
- `direct=True` draws straight connections.
- `direct=False` routes connections along topology paths.
- `hover=True` keeps the current compact 3D tooltip behavior; saved or non-interactive renders fall back to visible labels.

When `topology_menu=True`, the menu is only shown when the library owns the figure and the render stays interactive. Invalid topologies remain visible but disabled. If you save to `output=...`, use `ax=...`, or render off-screen, the circuit still draws normally without the menu.

If you provide your own axes with `ax=...`, it must be a 3D Matplotlib axes. See [Troubleshooting](troubleshooting.md#view3d-raises-an-axes-error).

## Composite operations

Some frameworks can provide subcircuits, composite instructions, or decomposable operations.

Use the default compact mode when you want a high-level diagram:

```python
draw_quantum_circuit(circuit, composite_mode="compact")
```

Use expanded mode when you want to inspect supported decompositions:

```python
draw_quantum_circuit(circuit, composite_mode="expand")
```

This is especially useful for Qiskit instructions built from subcircuits, Cirq `CircuitOperation`, PennyLane operations such as `QFT`, and MyQLM gates backed by `gateDic`.

## Classical conditions

For supported frameworks, classical conditions are rendered as a classical double-line connection plus a short condition label.

The goal is to show that an operation depends on classical data. The current renderer does not try to represent full branching control flow.

## Framework selection

Autodetection is usually enough:

```python
draw_quantum_circuit(circuit)
```

Use `framework=...` when you want your code to fail clearly if the wrong object is passed:

```python
draw_quantum_circuit(circuit, framework="cirq")
```

Supported user-facing framework names are covered in [Frameworks](frameworks.md).

## Practical tips

- Start with a small circuit and default settings before changing styles.
- Use `show=False` in scripts, CI, and notebooks unless you explicitly want an interactive window.
- Use `theme="paper"` for figures that will go into reports.
- Use `page_slider=True` for exploration, then save a clean figure with `output=...`.
- Start 3D work with `topology="line"` before moving to stricter topology shapes.
- Keep `framework=...` explicit in reusable code if different framework objects may flow through the same function.
- Use [Recipes](recipes.md) when you need a quick pattern, and [Troubleshooting](troubleshooting.md) when an option combination fails.
