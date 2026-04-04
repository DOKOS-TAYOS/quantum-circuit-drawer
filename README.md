# quantum-circuit-drawer

`quantum-circuit-drawer` is a Python library for rendering quantum circuits from different frameworks with one consistent Matplotlib-based visual style. The current public release target is `v0.1.0`.

## What v0.1.0 supports

- A small public API centered on `draw_quantum_circuit(...)`
- Matplotlib rendering
- Qiskit and Cirq adapters for common gates, controlled gates, swap, barriers, and measurements
- Conservative PennyLane support for tape-like objects such as `QuantumTape`, `QuantumScript`, or objects exposing `.qtape` / `.tape`
- Built-in `light`, `paper`, and `dark` themes
- Windows and Linux as the initial supported platforms

## What is intentionally out of scope

- Backends other than Matplotlib
- CUDA-Q support
- Advanced classical control-flow visualization
- Broad framework-specific formatting beyond the neutral IR used by the library

## Installation

Install the published package:

```bash
pip install quantum-circuit-drawer
```

Install optional framework adapters only when you need them:

```bash
pip install "quantum-circuit-drawer[qiskit]"
pip install "quantum-circuit-drawer[cirq]"
pip install "quantum-circuit-drawer[pennylane]"
```

For local development inside a virtual environment:

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[dev,qiskit,cirq,pennylane]"
```

## Quick start

Autodetect the framework:

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

fig, ax = draw_quantum_circuit(circuit)
```

Draw onto an existing Matplotlib axes:

```python
import matplotlib.pyplot as plt

from quantum_circuit_drawer import draw_quantum_circuit

fig, ax = plt.subplots(figsize=(8, 3))
draw_quantum_circuit(circuit, ax=ax)
```

Save directly to a file:

```python
draw_quantum_circuit(
    circuit,
    style={"theme": "paper", "show_params": True},
    output="circuit.png",
)
```

## Public API

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
    **options,
)
```

Behavior for `backend="matplotlib"`:

- If `ax` is `None`, it returns `(figure, axes)`.
- If `ax` is provided, it draws in place and returns `ax`.
- If `output` is provided, it saves the rendered figure and raises `RenderingError` if writing fails.

## Development

Run the core checks:

```bash
python -m pytest
python -m ruff check .
python -m mypy
```

Build the distribution artifacts locally:

```bash
python -m build
python -m twine check dist/*
```

Runnable framework examples live in `examples/`. Generated images are intentionally not committed.
