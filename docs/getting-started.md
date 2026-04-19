# Getting started

This guide gets you from installation to a first rendered circuit as quickly as possible.

If you have not installed the package yet, start with [Installation](installation.md). For the example below, install the Qiskit extra.

## First example

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

result = draw_quantum_circuit(circuit)
```

By default:

- the library detects the framework automatically
- the `matplotlib` backend is used
- a managed Matplotlib figure is created for you
- the built-in `dark` theme is used
- the figure is shown when the active Matplotlib backend is interactive
- the function returns a `DrawResult` with the primary figure and axes plus any extra page figures

## Save an image without opening a window

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(output_path="bell.png", show=False),
)
```

Use this pattern in scripts, automated jobs, and notebooks where you want an image file without an external Matplotlib window.

## Draw on your own axes

Use `ax=...` when the circuit is one part of a larger Matplotlib figure.

```python
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit

from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

figure, axes = plt.subplots(figsize=(7, 3))
result = draw_quantum_circuit(
    circuit,
    ax=axes,
    config=DrawConfig(mode=DrawMode.PAGES),
)
```

In this mode, `result.primary_axes` is the same axes object you passed in.

## What to read next

- [API reference](api.md): exact parameters, return values, style fields, and exceptions.
- [User guide](user-guide.md): practical workflows for scripts, notebooks, reports, wide circuits, and 3D views.
- [Frameworks](frameworks.md): notes for Qiskit, Cirq, PennyLane, MyQLM, CUDA-Q, and internal IR.
- [Recipes](recipes.md): copy-paste examples for common tasks.
- [Troubleshooting](troubleshooting.md): fixes for common install and rendering issues.
