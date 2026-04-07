# Getting started

This guide gets you from installation to a first rendered circuit as quickly as possible.

If you have not installed the package yet, start with [Installation](installation.md).

## First example

This example uses Qiskit because it shows the common workflow clearly: create a circuit, pass it to `draw_quantum_circuit(...)`, and receive a Matplotlib figure and axes.

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

figure, axes = draw_quantum_circuit(circuit)
```

By default:

- the library tries to detect the framework automatically
- the `matplotlib` backend is used
- a managed Matplotlib figure is created for you
- the default built-in theme is `dark`
- the window is shown when `show=True`

If you prefer a script-friendly first run, use `show=False`.

## Save an image without opening a window

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

figure, axes = draw_quantum_circuit(
    circuit,
    output="bell.png",
    show=False,
)
```

Use this pattern in scripts, automated jobs, or notebooks where you want an image file but not an interactive window.

## Draw on your own axes

If you already manage the Matplotlib figure yourself, pass `ax=...`.

```python
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit

from quantum_circuit_drawer import draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

figure, axes = plt.subplots(figsize=(7, 3))
returned_axes = draw_quantum_circuit(circuit, ax=axes)
```

In this mode, the function returns the same axes object instead of a `(figure, axes)` tuple.

The same managed-versus-caller-owned rule also applies to `view="3d"`: managed rendering returns `(figure, axes)`, while caller-managed rendering returns the 3D axes you pass in.

## What to read next

- Read the [User guide](user-guide.md) to understand the full API and style options.
- Read [Frameworks](frameworks.md) if you use Cirq, PennyLane, CUDA-Q, or the internal IR.
- Use [Recipes](recipes.md) when you want a quick solution for a specific task.
