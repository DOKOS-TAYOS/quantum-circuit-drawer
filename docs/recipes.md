# Recipes

This page collects small examples for common tasks.

## Draw a circuit without opening a window

```python
from quantum_circuit_drawer import draw_quantum_circuit

figure, axes = draw_quantum_circuit(circuit, show=False)
```

Use this in scripts, tests, and batch jobs.

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

## Use the `paper` theme for reports

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    style={"theme": "paper"},
)
```

## Hide gate parameters for a cleaner diagram

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
    direct=False,
    hover=True,
)
```

Supported 3D topologies in this first version are `line`, `grid`, `star`, `star_tree`, and `honeycomb`.

## Draw a wide circuit with a horizontal slider

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

## Save a wide circuit while keeping the interactive slider view

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

This can be helpful when you want your code to be easier to read or to fail clearly if the wrong object is passed.

## Use a `DrawStyle` instance instead of a mapping

```python
from quantum_circuit_drawer import DrawStyle, draw_quantum_circuit

style = DrawStyle(
    show_params=False,
    max_page_width=6.0,
)

draw_quantum_circuit(circuit, style=style)
```

## Render from the internal IR

```python
from quantum_circuit_drawer import draw_quantum_circuit
from quantum_circuit_drawer.ir import CircuitIR

draw_quantum_circuit(ir_circuit)
```

If your own pipeline can build a `CircuitIR`, this gives you a framework-neutral route into the renderer.

## Explore the full example gallery

The repository includes runnable examples for balanced, wide, deep, Grover, and QAOA-style circuits across the supported adapters.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
```

For more detail, see [`../examples/README.md`](../examples/README.md).
