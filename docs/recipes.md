# Recipes

This page collects small examples for common tasks.

For deeper explanation, read the [User guide](user-guide.md). For exact parameter details, read the [API reference](api.md).

## Contents

- [Draw without opening a window](#draw-without-opening-a-window)
- [Save a PNG file](#save-a-png-file)
- [Draw inside an existing Matplotlib figure](#draw-inside-an-existing-matplotlib-figure)
- [Display cleanly in a notebook](#display-cleanly-in-a-notebook)
- [Use configurable 2D hover](#use-configurable-2d-hover)
- [Use the `paper` theme for reports](#use-the-paper-theme-for-reports)
- [Hide gate parameters](#hide-gate-parameters)
- [Draw a topology-aware 3D circuit](#draw-a-topology-aware-3d-circuit)
- [Draw a wide circuit with a slider](#draw-a-wide-circuit-with-a-slider)
- [Save a wide circuit while keeping slider exploration](#save-a-wide-circuit-while-keeping-slider-exploration)
- [Be explicit about the framework](#be-explicit-about-the-framework)
- [Use a `DrawStyle` instance](#use-a-drawstyle-instance)
- [Render from the internal IR](#render-from-the-internal-ir)
- [Explore the example gallery](#explore-the-example-gallery)

## Draw without opening a window

```python
from quantum_circuit_drawer import draw_quantum_circuit

figure, axes = draw_quantum_circuit(circuit, show=False)
```

Use this in scripts, tests, notebooks, and batch jobs.

## Save a PNG file

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    output="circuit.png",
    show=False,
)
```

## Draw inside an existing Matplotlib figure

```python
import matplotlib.pyplot as plt

from quantum_circuit_drawer import draw_quantum_circuit

figure, axes = plt.subplots(figsize=(8, 3))
draw_quantum_circuit(circuit, ax=axes)
```

This is the right pattern when the circuit is part of a larger report figure or dashboard layout.

## Display cleanly in a notebook

```python
from quantum_circuit_drawer import draw_quantum_circuit

figure, axes = draw_quantum_circuit(circuit, show=False)
figure
```

Install notebook tools in the same `.venv`; see [Installation](installation.md#use-the-library-in-jupyter).

If you use `%matplotlib widget`, managed figures avoid the extra built-in `show()` call, so you do not get a duplicate static output next to the interactive one, and hover stays available on the returned figure.

## Use configurable 2D hover

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

`hover=True` uses the default settings. Tooltips are interactive only; saved files still contain the clean static circuit figure. The default hover shows gate name, matrix dimensions, qubits, and the matrix itself when it is small enough and available.

## Use the `paper` theme for reports

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    style={"theme": "paper"},
)
```

## Hide gate parameters

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    style={"show_params": False},
)
```

## Draw a topology-aware 3D circuit

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    view="3d",
    topology="star",
    topology_menu=True,
    direct=False,
    hover=True,
)
```

Supported 3D topologies are `line`, `grid`, `star`, `star_tree`, and `honeycomb`.

With `topology_menu=True`, managed interactive figures add a small selector that lets you switch between valid topologies without recreating the figure. Invalid options stay visible but disabled.

In 3D, `hover=True` keeps the compact tooltip behavior for interactive figures. Saved renders or non-interactive backends fall back to visible labels.

## Draw a wide circuit with a slider

```python
from quantum_circuit_drawer import draw_quantum_circuit

figure, axes = draw_quantum_circuit(
    circuit,
    style={"max_page_width": 4.0},
    page_slider=True,
)
```

Remember:

- this only works when the library creates the figure
- do not combine `page_slider=True` with `ax=...`
- do not combine `page_slider=True` with `view="3d"`

## Save a wide circuit while keeping slider exploration

```python
from quantum_circuit_drawer import draw_quantum_circuit

figure, axes = draw_quantum_circuit(
    circuit,
    style={"max_page_width": 4.0},
    page_slider=True,
    output="wide_circuit.png",
)
```

The saved file uses the paged circuit layout, while the interactive figure keeps the slider.

## Be explicit about the framework

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(circuit, framework="qiskit")
```

This can make reusable code easier to read. If the explicit framework does not match the object, the call raises `UnsupportedFrameworkError`.

## Use a `DrawStyle` instance

```python
from quantum_circuit_drawer import DrawStyle, draw_quantum_circuit

style = DrawStyle(
    show_params=False,
    max_page_width=6.0,
)

draw_quantum_circuit(circuit, style=style)
```

Mappings such as `style={"theme": "paper"}` are usually shorter. A `DrawStyle` instance is useful when you want typed configuration in your own code.

## Render from the internal IR

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(ir_circuit, framework="ir")
```

Passing `framework="ir"` is optional, but it can make your intent clear.

For a full IR construction example, see [Frameworks](frameworks.md#internal-ir).

## Explore the example gallery

The repository includes runnable examples for balanced, wide, deep, Grover, QAOA-style, 3D, and conditional/composite circuits across supported adapters.

List the demo catalog.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
```

Run one demo without opening a window.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-balanced --no-show
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-balanced --no-show
```

For the full demo list, see [`../examples/README.md`](../examples/README.md).
