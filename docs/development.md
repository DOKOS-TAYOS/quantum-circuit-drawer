# Development

This page is for working on the repository locally.

It is written for contributors who want to run the project confidently without having to reverse-engineer the repo structure first.

## Set Up The Environment

Create a local `.venv` first; see [Installation](installation.md#create-a-virtual-environment) for the base commands.

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

For CUDA-Q development, use Linux or WSL2:

```bash
.venv/bin/python -m pip install -e ".[dev,cudaq]"
```

On native Windows, Cirq and PennyLane can still be limited by upstream SciPy/HiGHS behavior. For reliable end-to-end adapter work on those frameworks, Linux or WSL is the safer path.

## Repository Layout

The package root keeps the stable public surface intentionally small:

- `quantum_circuit_drawer.__init__`
- `quantum_circuit_drawer.api`
- `quantum_circuit_drawer.histogram`
- public config, result, exception, style, IR, layout, renderer, and adapter modules

Most implementation lives in focused internal subpackages:

- `quantum_circuit_drawer.drawing`: draw request normalization, runtime mode resolution, page helpers, and pipeline preparation
- `quantum_circuit_drawer.managed`: managed Matplotlib figures, sliders, page windows, viewport logic, zoom scaling, and 3D view state
- `quantum_circuit_drawer.plots`: histogram plotting implementation, normalization, comparison, and interactive helpers
- `quantum_circuit_drawer.export`: shared figure-saving helpers

Compatibility bridge modules still exist for older internal imports, but new internal code and new tests should target the real owner modules directly.

## Test Layout

The test suite mirrors the package domains:

- `tests/core`: public contracts, imports, docs policy, and cross-cutting behavior
- `tests/drawing`: draw request and pipeline behavior
- `tests/managed`: managed Matplotlib rendering, page windows, sliders, and zoom
- `tests/layout`: 2D and 3D layout behavior
- `tests/plots`: histogram plotting, comparison, and interactivity
- `tests/renderers`: Matplotlib renderer primitives and helpers
- `tests/adapters`: framework adapters and adapter registry coverage
- `tests/examples`: example runners, demo catalogs, and smoke tests

## Run Checks

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

Before finishing work, run Ruff with fixes and formatting:

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

## Run Documentation-Sensitive Checks

If you touched docs, these are the fastest focused checks:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\core\test_support_policy.py tests\examples\test_examples_runner.py -q
```

Linux or WSL:

```bash
.venv/bin/python -m pytest tests/core/test_support_policy.py tests/examples/test_examples_runner.py -q
```

## Run Examples

List available demos:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\run_demo.py --list
.\.venv\Scripts\python.exe examples\run_histogram_demo.py --list
.\.venv\Scripts\python.exe examples\run_compare_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
.venv/bin/python examples/run_histogram_demo.py --list
.venv/bin/python examples/run_compare_demo.py --list
```

Run one demo without opening a window:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\qiskit_control_flow_showcase.py --no-show --output examples\output\qiskit_control_flow_showcase.png
```

Linux or WSL:

```bash
.venv/bin/python examples/qiskit_control_flow_showcase.py --no-show --output examples/output/qiskit_control_flow_showcase.png
```

The full catalog and safe copy-paste bundles live in [../examples/README.md](../examples/README.md).

## Build Distributions

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

## Run The Render Benchmark

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_render.py --wires 16 --layers 120 --repeats 3
```

Linux or WSL:

```bash
.venv/bin/python scripts/benchmark_render.py --wires 16 --layers 120 --repeats 3
```

The small dated report in [benchmarking-results.md](benchmarking-results.md) is a snapshot for context, not a promise of stable performance across machines or dependency versions.
