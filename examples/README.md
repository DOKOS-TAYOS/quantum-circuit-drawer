# Examples

This folder contains long runnable examples for the currently supported adapters in `quantum-circuit-drawer`.

All examples now do the same two things by default:

- They render in an interactive Matplotlib window when you run them.
- They use the library default dark theme.

Saving is optional. If you also want an image file, pass `--output <path>`.

## Requirements

Install the project in your local virtual environment with the extras you want to try.

Windows PowerShell in a native Windows checkout:

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

## Run an example

Qiskit on Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/qiskit_example.py
```

Qiskit on Linux or WSL:

```bash
.venv/bin/python examples/qiskit_example.py
```

Cirq:

```bash
.venv/bin/python examples/cirq_example.py
```

PennyLane:

```bash
.venv/bin/python examples/pennylane_example.py
```

CUDA-Q on Linux or WSL:

```bash
.venv/bin/python examples/cudaq_example.py
```

## Save while showing

Any example can optionally save the rendered figure too:

```bash
.venv/bin/python examples/qiskit_example.py --output examples/output/qiskit_circuit.png
```

The output directory is not committed. Long circuits wrap into stacked sections automatically when they exceed the configured page width.