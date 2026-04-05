# Examples

This folder contains runnable galleries for the supported adapters in `quantum-circuit-drawer`.

Use the shared entrypoint:

- `examples/run_demo.py`

The available demo ids are:

- `qiskit-balanced`
- `qiskit-wide`
- `qiskit-deep`
- `qiskit-grover`
- `qiskit-qaoa`
- `cirq-balanced`
- `cirq-wide`
- `cirq-deep`
- `cirq-grover`
- `cirq-qaoa`
- `pennylane-balanced`
- `pennylane-wide`
- `pennylane-deep`
- `pennylane-grover`
- `pennylane-qaoa`
- `cudaq-balanced`
- `cudaq-wide`
- `cudaq-deep`

## Default behavior

- Balanced, deep, Grover, and QAOA demos use wrapped paged views by default.
- Only the `wide` demos open with a horizontal slider.
- The windows are tuned to be a bit wider and less tall than before.
- The default theme is the library dark theme with the black background.
- Saving is optional. Pass `--output <path>` if you also want an image file.
- Use `--list` to print the catalog without running anything.

## Requirements

Install the project in your local virtual environment with the extras you want to try.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[qiskit,cirq,pennylane]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install -e ".[qiskit,cirq,pennylane]"
```

For CUDA-Q on Linux or WSL2:

```bash
.venv/bin/python -m pip install -e ".[cudaq]"
```

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
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-balanced
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-wide
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-deep
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-grover
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-balanced
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-wide
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-deep
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-grover
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-balanced
.venv/bin/python examples/run_demo.py --demo qiskit-wide
.venv/bin/python examples/run_demo.py --demo qiskit-deep
.venv/bin/python examples/run_demo.py --demo qiskit-grover
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa
.venv/bin/python examples/run_demo.py --demo cirq-balanced
.venv/bin/python examples/run_demo.py --demo cirq-wide
.venv/bin/python examples/run_demo.py --demo cirq-deep
.venv/bin/python examples/run_demo.py --demo cirq-grover
.venv/bin/python examples/run_demo.py --demo cirq-qaoa
.venv/bin/python examples/run_demo.py --demo pennylane-balanced
.venv/bin/python examples/run_demo.py --demo pennylane-wide
.venv/bin/python examples/run_demo.py --demo pennylane-deep
.venv/bin/python examples/run_demo.py --demo pennylane-grover
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa
.venv/bin/python examples/run_demo.py --demo cudaq-balanced
.venv/bin/python examples/run_demo.py --demo cudaq-wide
.venv/bin/python examples/run_demo.py --demo cudaq-deep
```

## Save while showing

Any demo can optionally save the rendered figure too:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --output examples/output/qiskit_qaoa.png
```

Generated images are not committed.