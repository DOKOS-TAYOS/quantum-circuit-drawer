# Installation

This guide shows the recommended installation paths for `quantum-circuit-drawer`.

All command examples below assume you are working inside a local `.venv`.

## Requirements

- Python `3.11+`
- A virtual environment
- Optional framework extras, depending on which circuit objects you want to draw

The base package already includes the Matplotlib renderer.

## Create a virtual environment

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

## Install the base package

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install quantum-circuit-drawer
```

Linux or WSL:

```bash
.venv/bin/python -m pip install quantum-circuit-drawer
```

Use the base package if you will draw the internal IR directly or if you only want the shared rendering functionality first.

## Install optional extras

Install only the extras you need for your circuit source.

| Extra | Package spec | Typical use |
| --- | --- | --- |
| `qiskit` | `quantum-circuit-drawer[qiskit]` | Draw `QuantumCircuit` objects |
| `cirq` | `quantum-circuit-drawer[cirq]` | Draw `cirq.Circuit` objects |
| `pennylane` | `quantum-circuit-drawer[pennylane]` | Draw tape-like PennyLane objects |
| `cudaq` | `quantum-circuit-drawer[cudaq]` | Draw supported CUDA-Q kernels on Linux or WSL2 |

Windows PowerShell examples:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[cirq]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[pennylane]"
```

Linux or WSL examples:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[qiskit]"
.venv/bin/python -m pip install "quantum-circuit-drawer[cirq]"
.venv/bin/python -m pip install "quantum-circuit-drawer[pennylane]"
```

CUDA-Q is currently Linux/WSL2-first. On native Windows, this extra is not expected to install because the dependency is declared only for Linux environments:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[cudaq]"
```

## Check that the installation works

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -c "from quantum_circuit_drawer import draw_quantum_circuit; print(draw_quantum_circuit.__name__)"
```

Linux or WSL:

```bash
.venv/bin/python -c "from quantum_circuit_drawer import draw_quantum_circuit; print(draw_quantum_circuit.__name__)"
```

If the command prints `draw_quantum_circuit`, the package import is working.

## Installing from a local checkout

If you are working from the repository instead of PyPI, install it in editable mode.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e .
```

Add extras the same way:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[qiskit]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e ".[qiskit]"
```

You can combine extras when that matches your workflow, for example `".[dev,qiskit,cirq]"`.

## Next step

Continue with [Getting started](getting-started.md) for the first successful example.
