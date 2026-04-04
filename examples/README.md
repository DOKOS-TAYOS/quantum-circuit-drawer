# Examples

This folder contains small runnable examples for the currently supported adapters in `quantum-circuit-drawer`.

## Requirements

Install the project in your local virtual environment with the extras you want to try:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[qiskit,cirq,pennylane]
```

## Run An Example

Qiskit:

```powershell
.\.venv\Scripts\python.exe examples/qiskit_example.py
```

Cirq:

```powershell
.\.venv\Scripts\python.exe examples/cirq_example.py
```

This example now renders with the built-in dark theme.

PennyLane:

```powershell
.\.venv\Scripts\python.exe examples/pennylane_example.py
```

Each example saves an image into `examples/output/`. Those generated files are not meant to be committed.

Long circuits now wrap into stacked sections automatically when they exceed the configured page width.
