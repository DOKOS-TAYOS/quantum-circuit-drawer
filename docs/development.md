# Development

This page is for working on the repository locally.

## Contents

- [Set up the environment](#set-up-the-environment)
- [Package layout](#package-layout)
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

On native Windows, Cirq and PennyLane can still fail inside SciPy/HiGHS during import or teardown. The demo path now avoids eager exact-matrix extraction for those frameworks by default, which reduces startup cost, but it does not remove the upstream Windows instability. For Cirq or PennyLane adapter work, prefer Linux or WSL if you need reliable end-to-end runs.

For CUDA-Q development, use Linux or WSL2:

```bash
.venv/bin/python -m pip install -e ".[dev,cudaq]"
```

## Package layout

The package root keeps the stable public surface small:

- `quantum_circuit_drawer.__init__`
- `quantum_circuit_drawer.api`
- `quantum_circuit_drawer.histogram`
- public config, result, exception, style, IR, layout, renderer, and adapter modules

Most implementation now lives in focused internal subpackages:

- `quantum_circuit_drawer.drawing`: draw request normalization, runtime mode resolution, page helpers, and pipeline preparation
- `quantum_circuit_drawer.managed`: managed Matplotlib figures, sliders, fixed page windows, viewport logic, zoom scaling, and 3D view state
- `quantum_circuit_drawer.plots`: histogram plotting implementation
- `quantum_circuit_drawer.export`: shared figure-saving helpers

The managed and 3D internals are now split more finely so the older orchestration modules can stay small and readable:

- `quantum_circuit_drawer.managed.slider` stays as the stable internal facade for slider-related imports
- `quantum_circuit_drawer.managed.controls` owns shared widget bounds, layout, and styling helpers
- `quantum_circuit_drawer.managed.slider_2d_windowing` owns 2D scene slicing and row/column window helpers
- `quantum_circuit_drawer.managed.slider_3d` owns 3D slider state, circuit windows, and 3D slider setup
- `quantum_circuit_drawer.managed.page_window_3d` stays as the orchestration layer for managed 3D page windows
- `quantum_circuit_drawer.managed.page_window_3d_ranges` owns 3D page-range calculation and aspect-ratio balancing
- `quantum_circuit_drawer.managed.page_window_3d_controls` owns button/textbox wiring and navigation state sync
- `quantum_circuit_drawer.managed.page_window_3d_render` owns display-axes lifecycle and rerender helpers

The heaviest 3D layout and rendering modules follow the same pattern:

- `quantum_circuit_drawer.layout.engine_3d` keeps the public `LayoutEngine3D` entrypoint
- `quantum_circuit_drawer.layout._engine_3d_metrics`, `_engine_3d_topology`, `_engine_3d_operations`, and `_engine_3d_classical` hold focused private helpers used by `LayoutEngine3D`
- `quantum_circuit_drawer.renderers.matplotlib_renderer_3d` keeps `MatplotlibRenderer3D` and `_MANAGED_3D_VIEWPORT_BOUNDS_ATTR` importable
- `quantum_circuit_drawer.renderers._matplotlib_renderer_3d_viewport`, `_geometry`, `_text`, `_hover`, and `_segments` hold private support code for the 3D Matplotlib renderer

Compatibility bridge modules still exist for older internal imports, but new internal code and new tests should target the domain packages directly.

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
