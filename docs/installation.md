# Installation

This guide covers the recommended install paths for `quantum-circuit-drawer`.

All examples assume you are working inside a local `.venv`, because that keeps this project and your quantum framework dependencies isolated from the rest of your Python setup.

## Contents

- [Requirements](#requirements)
- [Create a virtual environment](#create-a-virtual-environment)
- [Install the package](#install-the-package)
- [Install optional framework extras](#install-optional-framework-extras)
- [Use the library in Jupyter](#use-the-library-in-jupyter)
- [Check the installation](#check-the-installation)
- [Install from a local checkout](#install-from-a-local-checkout)
- [Next step](#next-step)

## Requirements

- Python `3.11+`
- A virtual environment such as `.venv`
- One optional framework extra if you want to draw objects from Qiskit, Cirq, PennyLane, MyQLM, or CUDA-Q

The base package includes the Matplotlib renderer and the internal IR path.

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

If your system uses `python` instead of `python3.11`, use the command that points to your Python `3.11+` interpreter.

## Install the package

Install the base package from PyPI:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install quantum-circuit-drawer
```

Linux or WSL:

```bash
.venv/bin/python -m pip install quantum-circuit-drawer
```

Use the base package when you want the renderer and internal IR support first. To draw framework objects directly, install the matching extra below.

## Install optional framework extras

Install only the extras you need.

| Extra | Package spec | Typical use |
| --- | --- | --- |
| `qiskit` | `quantum-circuit-drawer[qiskit]` | Draw `qiskit.QuantumCircuit` objects |
| `cirq` | `quantum-circuit-drawer[cirq]` | Draw `cirq.Circuit` objects |
| `pennylane` | `quantum-circuit-drawer[pennylane]` | Draw PennyLane tape-like objects |
| `myqlm` | `quantum-circuit-drawer[myqlm]` | Draw `qat.core.Circuit` objects, usually produced by `Program().to_circ()` |
| `cudaq` | `quantum-circuit-drawer[cudaq]` | Draw supported closed CUDA-Q kernels on Linux or WSL2 |

## Support matrix

Use this table as the release support contract when choosing an install path.

| Input path | Support level | Platform notes |
| --- | --- | --- |
| Internal IR | Strong support | Core built-in path on Windows and Linux |
| Qiskit | Strong support | Primary external backend on Windows and Linux |
| Cirq | Best-effort on native Windows | Linux or WSL remains the safer production path |
| PennyLane | Best-effort on native Windows | Linux or WSL remains the safer production path |
| MyQLM | Scoped adapter + contract support | Adapter contract is covered, but it is not a first-class multiplatform CI backend |
| CUDA-Q | Linux/WSL2 only | Not intended for native Windows installs |

Windows PowerShell examples:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[cirq]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[pennylane]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[myqlm]"
```

Linux or WSL examples:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[qiskit]"
.venv/bin/python -m pip install "quantum-circuit-drawer[cirq]"
.venv/bin/python -m pip install "quantum-circuit-drawer[pennylane]"
.venv/bin/python -m pip install "quantum-circuit-drawer[myqlm]"
```

CUDA-Q is currently Linux/WSL2-first. On native Windows, the `cudaq` dependency is not expected to install because the extra is declared only for Linux environments.

Linux or WSL:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[cudaq]"
```

MyQLM is distributed upstream under its own EULA. This project only provides the optional adapter.

## Use the library in Jupyter

There is no separate `quantum-circuit-drawer[jupyter]` extra. Install normal notebook tools in the same virtual environment where you installed the library.

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

In notebooks, `show=False` is often convenient when you want to control display yourself or save files without opening an external Matplotlib window.

## Check the installation

Check that the public function imports correctly.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -c "from quantum_circuit_drawer import draw_quantum_circuit; print(draw_quantum_circuit.__name__)"
```

Linux or WSL:

```bash
.venv/bin/python -c "from quantum_circuit_drawer import draw_quantum_circuit; print(draw_quantum_circuit.__name__)"
```

Expected output:

```text
draw_quantum_circuit
```

## Install from a local checkout

If you are working from the repository instead of PyPI, install it in editable mode.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e .
```

Install extras the same way:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,qiskit,cirq,pennylane,myqlm]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e ".[dev,qiskit,cirq,pennylane,myqlm]"
```

For CUDA-Q development, use Linux or WSL2:

```bash
.venv/bin/python -m pip install -e ".[dev,cudaq]"
```

## Next step

Continue with [Getting started](getting-started.md) for the first successful render, or go to [Troubleshooting](troubleshooting.md) if an install command fails.
