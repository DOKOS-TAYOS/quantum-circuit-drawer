<p align="center">
  <img
    src="https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/Quantum_Circuit_Drawer_logo.png"
    alt="Quantum Circuit Drawer — neon logo with a circuit-style atom icon and glowing typography (transparent background)"
    width="640"
  />
</p>

# quantum-circuit-drawer

[![PyPI version](https://img.shields.io/pypi/v/quantum-circuit-drawer)](https://pypi.org/project/quantum-circuit-drawer/)
[![Python versions](https://img.shields.io/pypi/pyversions/quantum-circuit-drawer)](https://pypi.org/project/quantum-circuit-drawer/)
[![CI](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/actions/workflows/ci.yml/badge.svg)](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`quantum-circuit-drawer` is a small Python library for drawing quantum circuits from different ecosystems with one consistent Matplotlib-based visual style.

It gives you one public entry point, `draw_quantum_circuit(...)`, for supported Qiskit, Cirq, PennyLane, MyQLM, CUDA-Q, and internal IR inputs. The goal is simple: keep your visualization code stable even when the circuit source changes.

## Why this library

Quantum frameworks do not all expose the same drawing workflow. This project focuses on the visualization layer, so you can:

- keep the same look across different circuit frameworks
- save circuit diagrams for reports, notebooks, and documentation
- draw into your own Matplotlib figures when you need larger layouts
- use one typed API instead of several framework-specific drawing calls

## Supported inputs

| Input path | Install | Typical object | Notes |
| --- | --- | --- | --- |
| Internal IR | `python -m pip install quantum-circuit-drawer` | `CircuitIR` | Included in the base package |
| Qiskit | `python -m pip install "quantum-circuit-drawer[qiskit]"` | `qiskit.QuantumCircuit` | Good default if you mainly use Qiskit |
| Cirq | `python -m pip install "quantum-circuit-drawer[cirq]"` | `cirq.Circuit` | Works with explicit or automatic framework detection |
| PennyLane | `python -m pip install "quantum-circuit-drawer[pennylane]"` | tape-like objects | Supports `QuantumTape`, `QuantumScript`, and wrappers exposing `.qtape` or `.tape` |
| MyQLM | `python -m pip install "quantum-circuit-drawer[myqlm]"` | `qat.core.Circuit` | Convert from `Program().to_circ()` first |
| CUDA-Q | `python -m pip install "quantum-circuit-drawer[cudaq]"` | closed CUDA-Q kernels | Linux or WSL2 oriented |

## Install

Install the base package inside your virtual environment:

```bash
python -m pip install quantum-circuit-drawer
```

Install the framework extra you need, for example Qiskit:

```bash
python -m pip install "quantum-circuit-drawer[qiskit]"
```

For notebooks, install Jupyter tools in the same environment:

```bash
python -m pip install jupyter ipykernel
```

See the full [installation guide](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/installation.md) for Windows PowerShell commands, Linux/WSL commands, optional extras, CUDA-Q notes, and local editable installs.

## Basic usage

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

figure, axes = draw_quantum_circuit(circuit)
```

By default, the library detects the circuit framework, creates a Matplotlib figure, uses the built-in `dark` theme, and shows the figure when the active Matplotlib backend is interactive.

For script-friendly output:

```python
draw_quantum_circuit(circuit, output="bell.png", show=False)
```

## Documentation

- [Documentation index](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/index.md): the full map.
- [Getting started](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/getting-started.md): the shortest first successful example.
- [Installation](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/installation.md): virtual environments, extras, notebooks, and local installs.
- [API reference](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/api.md): `draw_quantum_circuit(...)`, style options, return values, and exceptions.
- [User guide](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/user-guide.md): workflows, examples, tips, 2D/3D views, sliders, and reports.
- [Frameworks](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/frameworks.md): Qiskit, Cirq, PennyLane, MyQLM, CUDA-Q, and internal IR notes.
- [Recipes](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/recipes.md): copy-paste solutions for common tasks.
- [Troubleshooting](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/troubleshooting.md): common errors and fixes.
- [Development](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/docs/development.md): local checks, build commands, and benchmark notes.

Runnable example scripts live in [`examples/`](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/tree/main/examples), with more detail in [`examples/README.md`](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/examples/README.md).

## Project links

- Repository: [github.com/DOKOS-TAYOS/quantum-circuit-drawer](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer)
- Issue tracker: [github.com/DOKOS-TAYOS/quantum-circuit-drawer/issues](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/issues)
- Changelog: [CHANGELOG.md](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/CHANGELOG.md)

## License

This project is distributed under the [MIT License](https://github.com/DOKOS-TAYOS/quantum-circuit-drawer/blob/main/LICENSE).
