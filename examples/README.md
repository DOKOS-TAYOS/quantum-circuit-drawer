# Examples

This folder contains small runnable examples for the currently supported adapters in `quantum-circuit-drawer`.

## Requirements

Install the project in your local virtual environment with the extras you want to try.

**Windows** (PowerShell or CMD, from the repo root; adjust the path if your venv lives elsewhere):

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[qiskit,cirq,pennylane]
```

**Linux, macOS, or WSL2** (after `python -m venv .venv` and `source .venv/bin/activate`, or call the interpreter directly):

```bash
.venv/bin/python -m pip install -e ".[qiskit,cirq,pennylane]"
```

For CUDA-Q, use **Linux or WSL2** (CUDA-Q is not supported on native Windows the same way):

```bash
.venv/bin/python -m pip install -e ".[cudaq]"
```

If your shell is already activated, you can use `python -m pip install ...` instead of `.venv/bin/python -m pip install ...` on Linux/macOS/WSL2.

## Run An Example

From the **repository root**, run the script with the same Python you used for the install.

### Qiskit

**Windows:**

```powershell
.\.venv\Scripts\python.exe examples/qiskit_example.py
```

**Linux, macOS, or WSL2:**

```bash
.venv/bin/python examples/qiskit_example.py
```

### Cirq

**Windows:**

```powershell
.\.venv\Scripts\python.exe examples/cirq_example.py
```

**Linux, macOS, or WSL2:**

```bash
.venv/bin/python examples/cirq_example.py
```

This example now renders with the built-in dark theme.

### PennyLane

**Windows:**

```powershell
.\.venv\Scripts\python.exe examples/pennylane_example.py
```

**Linux, macOS, or WSL2:**

```bash
.venv/bin/python examples/pennylane_example.py
```

### CUDA-Q (Linux or WSL2)

```bash
.venv/bin/python examples/cudaq_example.py
```

Each example saves an image into `examples/output/`. Those generated files are not meant to be committed.

Long circuits now wrap into stacked sections automatically when they exceed the configured page width.
