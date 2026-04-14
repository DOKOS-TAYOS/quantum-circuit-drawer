# Examples

This folder now keeps one configurable random demo and one configurable QAOA demo per framework when that framework already had QAOA support.

Included scripts:

- `examples/qiskit_random.py`
- `examples/qiskit_qaoa.py`
- `examples/cirq_random.py`
- `examples/cirq_qaoa.py`
- `examples/pennylane_random.py`
- `examples/pennylane_qaoa.py`
- `examples/myqlm_random.py`
- `examples/cudaq_random.py`
- `examples/run_demo.py`

QAOA demos are available for Qiskit, Cirq, and PennyLane.

## Shared flags

Every script and `examples/run_demo.py` accepts the same main flags:

- `--qubits`: number of quantum wires
- `--columns`: random depth, or QAOA layers `p`
- `--mode pages|slider`: wrapped pages or horizontal slider
- `--view 2d|3d`: standard 2D view or topology-aware 3D view
- `--topology line|grid|star|star_tree|honeycomb`: only used in 3D
- `--seed`: random seed for the random demos
- `--output <path>`: save the figure too
- `--no-show`: render without opening the Matplotlib window

Notes:

- In the QAOA demos, `--columns` means QAOA layers.
- `--topology` has no effect in 2D.
- `--mode slider` is only available in 2D.
- The 3D examples use routed connections with hover enabled to show the topology engine better.

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

## List demos

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
```

## Command recipes

### Qiskit

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 24 --columns 6 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 6 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 24 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --qubits 18 --columns 12 --mode slider
```

### Cirq

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --qubits 24 --columns 6 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --qubits 6 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --qubits 24 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --qubits 18 --columns 12 --mode slider
```

### PennyLane

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --qubits 24 --columns 6 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --qubits 6 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --qubits 24 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --qubits 18 --columns 12 --mode slider
```

### myQLM

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 24 --columns 6 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 6 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 24 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 18 --columns 32 --mode slider
```

### CUDA-Q

CUDA-Q remains Linux or WSL oriented:

```bash
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 24 --columns 6 --mode pages
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 6 --columns 32 --mode pages
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 24 --columns 32 --mode pages
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 18 --columns 32 --mode slider
```

## 3D topology recipes

Use `--view 3d --mode pages` with the topology that matches the wire count you want to inspect best.

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 12 --columns 12 --view 3d --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 9 --columns 12 --view 3d --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 8 --columns 12 --view 3d --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 10 --columns 12 --view 3d --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 53 --columns 8 --view 3d --topology honeycomb
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --qubits 9 --columns 8 --view 3d --topology grid
```

The same 3D flags also work with:

- `cirq-random`
- `cirq-qaoa`
- `pennylane-random`
- `pennylane-qaoa`
- `myqlm-random`
- `cudaq-random` on Linux or WSL

Honeycomb requires exactly 53 qubits.

## Save without showing

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --qubits 14 --columns 10 --mode slider --no-show --output examples/output/qiskit_qaoa_slider.png
```

Generated images are not committed.
