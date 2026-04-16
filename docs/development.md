# Development

This page is for working on the repository locally.

## Contents

- [Set up the environment](#set-up-the-environment)
- [Run checks](#run-checks)
- [Run examples](#run-examples)
- [Build distributions](#build-distributions)
- [Run the render benchmark](#run-the-render-benchmark)

## Set up the environment

Create a `.venv` first; see [Installation](installation.md#create-a-virtual-environment) for the base commands.

Install the project in editable mode with development dependencies.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

For adapter work, install the relevant extras too.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,qiskit,cirq,pennylane,myqlm]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e ".[dev,qiskit,cirq,pennylane,myqlm]"
```

On native Windows, Cirq imports can fail inside SciPy/HiGHS. For Cirq adapter work, prefer Linux or WSL if you need to run that part of the suite.

For CUDA-Q development, use Linux or WSL2:

```bash
.venv/bin/python -m pip install -e ".[dev,cudaq]"
```

## Run checks

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
```

Linux or WSL:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy
```

Before finishing Python code changes, run Ruff with fixes and formatting:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m ruff check . --fix
.\.venv\Scripts\python.exe -m ruff format .
```

Linux or WSL:

```bash
.venv/bin/python -m ruff check . --fix
.venv/bin/python -m ruff format .
```

Documentation-only changes usually do not need Ruff, because Ruff only checks Python files here.

## Run examples

List available demos:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
```

Run one demo without opening a window:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-balanced --no-show --output examples/output/qiskit_balanced.png
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-balanced --no-show --output examples/output/qiskit_balanced.png
```

More details are in [`../examples/README.md`](../examples/README.md).

## Build distributions

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\python.exe -m twine check dist/*
```

Linux or WSL:

```bash
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

## Run the render benchmark

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_render.py --wires 16 --layers 120 --repeats 3
```

Linux or WSL:

```bash
.venv/bin/python scripts/benchmark_render.py --wires 16 --layers 120 --repeats 3
```
