# quantum-circuit-drawer

[![PyPI version](https://img.shields.io/pypi/v/quantum-circuit-drawer)](https://pypi.org/project/quantum-circuit-drawer/)
[![Python versions](https://img.shields.io/pypi/pyversions/quantum-circuit-drawer)](https://pypi.org/project/quantum-circuit-drawer/)
[![CI](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/actions/workflows/ci.yml/badge.svg)](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`quantum-circuit-drawer` is a Python library for drawing quantum circuits from multiple ecosystems with one consistent Matplotlib-based visual style.

It gives you a single public entry point, `draw_quantum_circuit(...)`, for supported Qiskit, Cirq, PennyLane, CUDA-Q, and internal IR inputs, so you can keep the same visualization workflow even when your circuit source changes.

## Why this library

Quantum tooling is fragmented: each framework has its own circuit objects, drawing conventions, and export behavior. This project focuses on the visualization layer and gives you a neutral, reusable drawing API on top of that diversity.

Use it when you want to:

- keep a consistent look across circuits coming from different frameworks
- integrate circuit diagrams into existing Matplotlib scripts, notebooks, or reports
- save publication or documentation figures without rewriting framework-specific drawing code
- work with one small, typed API instead of learning multiple plotting entry points

## Highlights

- One public function: `draw_quantum_circuit(...)`
- Framework autodetection for supported circuit objects
- Matplotlib rendering with managed figures or caller-provided axes
- Built-in `dark`, `light`, and `paper` themes
- Optional file export through `output=...`
- Optional continuous horizontal slider for wide circuits with `page_slider=True`
- Clear exceptions for unsupported frameworks, unsupported backends, style validation issues, and render-write failures

## Supported frameworks

The package supports Python `3.11+`.

| Framework | Install | Notes |
| --- | --- | --- |
| Core package | `pip install quantum-circuit-drawer` | Includes Matplotlib renderer and the internal IR path |
| Qiskit | `pip install "quantum-circuit-drawer[qiskit]"` | Supports common gates, controlled gates, swap, barriers, and measurements |
| Cirq | `pip install "quantum-circuit-drawer[cirq]"` | Supports common gates, controlled gates, swap, and measurements |
| PennyLane | `pip install "quantum-circuit-drawer[pennylane]"` | Supports tape-like objects such as `QuantumTape`, `QuantumScript`, and objects exposing `.qtape` or `.tape` |
| CUDA-Q | `pip install "quantum-circuit-drawer[cudaq]"` | Linux/WSL2-first extra; supports closed kernels through Quake/MLIR |

## Installation

Install the base package inside your virtual environment:

```bash
python -m pip install quantum-circuit-drawer
```

Add only the framework extras you need:

```bash
python -m pip install "quantum-circuit-drawer[qiskit]"
python -m pip install "quantum-circuit-drawer[cirq]"
python -m pip install "quantum-circuit-drawer[pennylane]"
```

For CUDA-Q on Linux or WSL2:

```bash
python -m pip install "quantum-circuit-drawer[cudaq]"
```

## Quick start

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

fig, ax = draw_quantum_circuit(circuit)
```

By default, the library uses the built-in `dark` theme and opens a Matplotlib-managed window when `show=True`.

## Common usage patterns

### Render without opening a window

```python
fig, ax = draw_quantum_circuit(circuit, show=False)
```

### Save directly to a file

```python
draw_quantum_circuit(
    circuit,
    style={"show_params": True},
    output="circuit.png",
)
```

### Draw on existing Matplotlib axes

```python
import matplotlib.pyplot as plt

from quantum_circuit_drawer import draw_quantum_circuit

fig, ax = plt.subplots(figsize=(8, 3))
draw_quantum_circuit(circuit, ax=ax)
```

### Use a different built-in theme

```python
draw_quantum_circuit(circuit, style={"theme": "paper"})
```

### Add a continuous slider for wide circuits

```python
draw_quantum_circuit(
    circuit,
    style={"max_page_width": 4.0},
    page_slider=True,
    output="wide_circuit.png",
)
```

When `page_slider=True`, the interactive figure becomes horizontally scrollable while saved output still uses the paged circuit layout.

### CUDA-Q example

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
    show=True,
    page_slider=False,
    **options,
)
```

Current behavior for `backend="matplotlib"`:

- If `ax` is `None`, the function creates and returns `(figure, axes)`.
- If `show=True`, the managed figure is shown when the active Matplotlib backend is interactive.
- If `ax` is provided, the circuit is drawn in place and the function returns that axes object.
- If `output` is provided, the rendered figure is also saved to disk.
- If `page_slider=True`, the function requires a managed figure and raises `ValueError` when used with `ax=...`.

## Scope and current limitations

The current public surface is intentionally focused.

- Matplotlib is the only rendering backend today.
- Advanced classical control-flow visualization is outside the current scope.
- CUDA-Q support currently targets closed kernels only.
- Advanced CUDA-Q constructs such as reset, custom kernel composition, and broader control-flow handling are not yet part of the supported subset.

## Examples

Runnable examples live in [`examples/`](examples/).

List the demo catalog:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
```

Run one of the demos:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-balanced
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-balanced
```

The example gallery covers balanced, wide, deep, Grover, and QAOA-style circuits across the supported adapters. More details are in [`examples/README.md`](examples/README.md).

## Development

Create and use a local virtual environment, then install the project in editable mode:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip install -e ".[dev,qiskit,cirq,pennylane]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pip install -e ".[dev,qiskit,cirq,pennylane]"
```

For local CUDA-Q development on Linux or WSL2:

```bash
.venv/bin/python -m pip install -e ".[dev,cudaq]"
```

Run the main checks:

```bash
python -m pytest
python -m ruff check .
python -m mypy
```

Build distribution artifacts locally:

```bash
python -m build
python -m twine check dist/*
```

Run the synthetic render benchmark:

```bash
python scripts/benchmark_render.py --wires 16 --layers 120 --repeats 3
```

## Project links

- Repository: [github.com/DOKOS-TAYOS/quantum-circuit-drawer](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer)
- Issue tracker: [github.com/DOKOS-TAYOS/quantum-circuit-drawer/issues](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/issues)
- Changelog: [CHANGELOG.md](CHANGELOG.md)

## License

This project is distributed under the [MIT License](LICENSE).
