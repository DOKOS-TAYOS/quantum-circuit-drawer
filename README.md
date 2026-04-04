# quantum-circuit-drawer

`quantum-circuit-drawer` is a Python library for rendering quantum circuits from different frameworks with one consistent Matplotlib-based visual style. The current public release target is `v0.1.0`.

Project links:

- Repository: [github.com/DOKOS-TAYOS/quantum-circuit-drawer](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer)
- Issue tracker: [github.com/DOKOS-TAYOS/quantum-circuit-drawer/issues](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/issues)

## What v0.1.0 supports

- A small public API centered on `draw_quantum_circuit(...)`
- Matplotlib rendering
- Qiskit and Cirq adapters for common gates, controlled gates, swap, barriers, and measurements
- Conservative PennyLane support for tape-like objects such as `QuantumTape`, `QuantumScript`, or objects exposing `.qtape` / `.tape`
- Initial CUDA-Q support for closed kernels through Quake/MLIR, including common gates, controlled gates, swap, and `mz` / `mx` / `my` measurements
- Built-in `light`, `paper`, and `dark` themes
- Windows and Linux as the initial supported platforms

## What is intentionally out of scope

- Backends other than Matplotlib
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

CUDA-Q is Linux/WSL2-first in this release:

```bash
pip install "quantum-circuit-drawer[cudaq]"
```

For local development inside a virtual environment:

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[dev,qiskit,cirq,pennylane]"
```

For local CUDA-Q development on Linux or WSL2:

```bash
python -m pip install -e ".[dev,cudaq]"
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

CUDA-Q example:

```python
import cudaq

from quantum_circuit_drawer import draw_quantum_circuit


@cudaq.kernel
def bell_pair() -> None:
    qubits = cudaq.qvector(2)
    h(qubits[0])
    x.ctrl(qubits[0], qubits[1])
    mz(qubits)


draw_quantum_circuit(bell_pair)
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

CUDA-Q support notes for v0.1.0:

- The adapter accepts closed kernels only. Kernels that still need runtime arguments raise a clear error.
- The optional `cudaq` dependency is wired Linux/WSL2-first so the base package stays safe on standard Windows installs.
- Classical control flow, `reset`, custom kernel composition, and other advanced CUDA-Q constructs are still outside the supported subset.

## Development

Run the core checks:

```bash
python -m pytest
python -m ruff check .
python -m mypy
```

`pytest` now enforces the package coverage floor configured in `pyproject.toml`, so local development and CI use the same baseline.

Build the distribution artifacts locally:

```bash
python -m build
python -m twine check dist/*
```

Run the synthetic layout/render benchmark:

```bash
python scripts/benchmark_render.py --wires 16 --layers 120 --repeats 3
```

Runnable framework examples live in `examples/`. Generated images are intentionally not committed.
