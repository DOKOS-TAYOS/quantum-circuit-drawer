# Examples

This folder contains runnable galleries for the supported adapters in `quantum-circuit-drawer`.

Use the shared entrypoint:

- `examples/run_demo.py`

Use `--list` whenever you want the current source-of-truth catalog directly from the runner.

The available demo ids are:

- `qiskit-balanced`
- `qiskit-wide`
- `qiskit-deep`
- `qiskit-grover`
- `qiskit-qaoa`
- `qiskit-conditional-composite`
- `qiskit-3d-line`
- `qiskit-3d-grid`
- `qiskit-3d-honeycomb`
- `cirq-balanced`
- `cirq-wide`
- `cirq-deep`
- `cirq-grover`
- `cirq-qaoa`
- `cirq-conditional-composite`
- `pennylane-balanced`
- `pennylane-wide`
- `pennylane-deep`
- `pennylane-grover`
- `pennylane-qaoa`
- `pennylane-conditional-composite`
- `myqlm-balanced`
- `myqlm-wide`
- `myqlm-conditional-composite`
- `cudaq-balanced`
- `cudaq-wide`
- `cudaq-deep`

## Default behavior

- Balanced, deep, Grover, and QAOA demos use wrapped paged views by default.
- The `*-conditional-composite` demos focus on classical conditions and composite operations.
- The `qiskit-3d-*` demos showcase the new topological 3D view with different chip layouts.
- Only the `wide` demos open with a horizontal slider.
- The conditional/composite demos request `composite_mode="expand"` so the decomposition is visible.
- The default theme is the library dark theme with the black background.
- Saving is optional. Pass `--output <path>` if you also want an image file.
- Pass `--no-show` when you want to render without opening a Matplotlib window.

## Requirements

Install the project in your local virtual environment with the extras you want to try.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[qiskit,cirq,pennylane,myqlm]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e ".[qiskit,cirq,pennylane,myqlm]"
```

For CUDA-Q on Linux or WSL2:

```bash
.venv/bin/python -m pip install -e ".[cudaq]"
```

On native Windows, Qiskit, Cirq, PennyLane, and MyQLM are the main optional demo paths.

## List demos

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
```

## Full command list

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-balanced
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-wide
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-deep
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-grover
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-conditional-composite
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-3d-line
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-3d-grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-3d-honeycomb
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-balanced
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-wide
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-deep
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-grover
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-conditional-composite
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-balanced
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-wide
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-deep
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-grover
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-conditional-composite
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-balanced
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-wide
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-conditional-composite
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-balanced
.venv/bin/python examples/run_demo.py --demo qiskit-wide
.venv/bin/python examples/run_demo.py --demo qiskit-deep
.venv/bin/python examples/run_demo.py --demo qiskit-grover
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa
.venv/bin/python examples/run_demo.py --demo qiskit-conditional-composite
.venv/bin/python examples/run_demo.py --demo qiskit-3d-line
.venv/bin/python examples/run_demo.py --demo qiskit-3d-grid
.venv/bin/python examples/run_demo.py --demo qiskit-3d-honeycomb
.venv/bin/python examples/run_demo.py --demo cirq-balanced
.venv/bin/python examples/run_demo.py --demo cirq-wide
.venv/bin/python examples/run_demo.py --demo cirq-deep
.venv/bin/python examples/run_demo.py --demo cirq-grover
.venv/bin/python examples/run_demo.py --demo cirq-qaoa
.venv/bin/python examples/run_demo.py --demo cirq-conditional-composite
.venv/bin/python examples/run_demo.py --demo pennylane-balanced
.venv/bin/python examples/run_demo.py --demo pennylane-wide
.venv/bin/python examples/run_demo.py --demo pennylane-deep
.venv/bin/python examples/run_demo.py --demo pennylane-grover
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa
.venv/bin/python examples/run_demo.py --demo pennylane-conditional-composite
.venv/bin/python examples/run_demo.py --demo myqlm-balanced
.venv/bin/python examples/run_demo.py --demo myqlm-wide
.venv/bin/python examples/run_demo.py --demo myqlm-conditional-composite
.venv/bin/python examples/run_demo.py --demo cudaq-balanced
.venv/bin/python examples/run_demo.py --demo cudaq-wide
.venv/bin/python examples/run_demo.py --demo cudaq-deep
```

CUDA-Q demo commands are intentionally listed only for Linux or WSL2.

## Save without showing

Any demo can optionally save the rendered figure too:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --no-show --output examples/output/qiskit_qaoa.png
```

Generated images are not committed.
