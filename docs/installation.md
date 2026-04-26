# Installation

This guide covers the recommended install paths for `quantum-circuit-drawer`.

All commands assume you are working inside a local `.venv`, because that is the cleanest way to keep this package and any optional quantum frameworks isolated from the rest of your Python setup.

## Requirements

- Python `3.11+`; the core package is tested on Python 3.11, 3.12, and 3.13
- A virtual environment such as `.venv`
- Optional extras only for the frameworks you actually want to draw directly

The base package already includes:

- the Matplotlib renderer
- the internal IR path
- histogram plotting and histogram comparison
- circuit comparison

## Create A Virtual Environment

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Linux or WSL:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
```

If your machine exposes Python through `python` instead of `python3.11`, use the command that points to a Python `3.11+` interpreter.

## Install The Base Package

Use the base package when you want:

- framework-free IR workflows
- histogram plotting from plain mappings or arrays
- histogram comparison
- public configs and result objects

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install quantum-circuit-drawer
```

Linux or WSL:

```bash
.venv/bin/python -m pip install quantum-circuit-drawer
```

## Install Optional Framework Extras

Install only the extras you need.

| Extra | Package spec | Typical use |
| --- | --- | --- |
| `qiskit` | `quantum-circuit-drawer[qiskit]` | Draw `qiskit.QuantumCircuit` objects and parse OpenQASM 2 text or `.qasm` files |
| `qasm3` | `quantum-circuit-drawer[qasm3]` | Parse OpenQASM 3 text or `.qasm3` files through Qiskit and `qiskit-qasm3-import` |
| `cirq` | `quantum-circuit-drawer[cirq]` | Draw `cirq.Circuit` and `cirq.FrozenCircuit` objects |
| `pennylane` | `quantum-circuit-drawer[pennylane]` | Draw PennyLane tapes, scripts, and wrappers with a materialized tape |
| `myqlm` | `quantum-circuit-drawer[myqlm]` | Draw `qat.core.Circuit`, `Program`, and `QRoutine` objects |
| `cudaq` | `quantum-circuit-drawer[cudaq]` | Draw supported CUDA-Q kernels on Linux or WSL2, including scalar runtime arguments through `cudaq_args` |

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qasm3]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[cirq]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[pennylane]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[myqlm]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[qiskit]"
.venv/bin/python -m pip install "quantum-circuit-drawer[qasm3]"
.venv/bin/python -m pip install "quantum-circuit-drawer[cirq]"
.venv/bin/python -m pip install "quantum-circuit-drawer[pennylane]"
.venv/bin/python -m pip install "quantum-circuit-drawer[myqlm]"
```

CUDA-Q is currently Linux/WSL2-only; the upstream package does not support native Windows:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[cudaq]"
```

MyQLM is distributed upstream under its own EULA. This project only provides the optional adapter.

## Support matrix

Use this table as the release support contract when choosing an install path.

| Input path | Support level | Platform notes |
| --- | --- | --- |
| Internal IR | Strong support | Core built-in path on Windows and Linux |
| Qiskit | Strong support | Primary external backend on Windows and Linux |
| OpenQASM 2 text and `.qasm` files | Strong support through the Qiskit extra | Install `quantum-circuit-drawer[qiskit]`; works on Windows and Linux |
| OpenQASM 3 text and `.qasm3` files | Strong support through Qiskit plus `qiskit-qasm3-import` | Install `quantum-circuit-drawer[qasm3]`; works on Windows and Linux when Qiskit's importer is available |
| Cirq | Best-effort on native Windows | Accepts `cirq.Circuit` and `cirq.FrozenCircuit`; Linux or WSL remains the safer production path |
| PennyLane | Best-effort on native Windows | Linux or WSL remains the safer production path |
| MyQLM | Scoped adapter + contract support | Accepts `qat.core.Circuit`, `Program`, and `QRoutine`; adapter contract is covered, but it is not a first-class multiplatform CI backend |
| CUDA-Q | Linux/WSL2 only | Supports closed kernels plus scalar `cudaq_args`; upstream CUDA-Q is not available for native Windows |

## Jupyter Setup

There is no separate `quantum-circuit-drawer[jupyter]` extra. Install normal notebook tools in the same virtual environment.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install jupyter ipykernel
.\.venv\Scripts\python.exe -m ipykernel install --user --name quantum-circuit-drawer --display-name "Python (.venv quantum-circuit-drawer)"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install jupyter ipykernel
.venv/bin/python -m ipykernel install --user --name quantum-circuit-drawer --display-name "Python (.venv quantum-circuit-drawer)"
```

For notebook work:

- use `show=False` when you want to control display yourself
- use a widget backend if you want Matplotlib hover or interactive histogram controls

## Quick Install Check

Check that the package imports correctly:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -c "from quantum_circuit_drawer import draw_quantum_circuit, plot_histogram, compare_circuits, compare_histograms; print(draw_quantum_circuit.__name__, plot_histogram.__name__, compare_circuits.__name__, compare_histograms.__name__)"
```

Linux or WSL:

```bash
.venv/bin/python -c "from quantum_circuit_drawer import draw_quantum_circuit, plot_histogram, compare_circuits, compare_histograms; print(draw_quantum_circuit.__name__, plot_histogram.__name__, compare_circuits.__name__, compare_histograms.__name__)"
```

Expected output:

```text
draw_quantum_circuit plot_histogram compare_circuits compare_histograms
```

## Install From A Local Checkout

If you are working from the repository instead of PyPI, use editable mode.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e .
```

Install development tools and extras the same way:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,qiskit,qasm3,cirq,pennylane,myqlm]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e ".[dev,qiskit,qasm3,cirq,pennylane,myqlm]"
```

For CUDA-Q development, use Linux or WSL2:

```bash
.venv/bin/python -m pip install -e ".[dev,cudaq]"
```

## Where To Go Next

- [Getting started](getting-started.md) for your first successful draw or histogram
- [Frameworks](frameworks.md) if you want to choose a backend path deliberately
- [Examples](../examples/README.md) if you prefer runnable scripts over snippets
- [Troubleshooting](troubleshooting.md) if an install or import step fails
