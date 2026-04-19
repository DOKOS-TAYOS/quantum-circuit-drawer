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
- `--mode pages|slider|window`: wrapped pages, slider mode, or the fixed 2D page window
- `--view 2d|3d`: standard 2D view or topology-aware 3D view
- `--topology line|grid|star|star_tree|honeycomb`: only used in 3D
- `--seed`: random seed for the random demos
- `--hover` or `--no-hover`: enable or disable hover tooltips
- `--hover-matrix never|auto|always`: control when the tooltip shows a full matrix
- `--hover-matrix-max-qubits <n>`: maximum gate width for full matrices in hover
- `--hover-show-size`: also include the visual gate size in the tooltip
- `--figsize <width> <height>`: override the managed demo window size
- `--output <path>`: save the figure too
- `--no-show`: render without opening the Matplotlib window

Notes:

- In the QAOA demos, `--columns` means QAOA layers.
- `--topology` has no effect in 2D.
- In 2D, `--mode slider` redraws a discrete window of circuit columns and rows as you move the sliders.
- In 2D, `--mode window` opens the fixed page-window viewer with `Page` and `Visible` boxes and reuses cached pages as you move around.
- In 3D, `--mode slider` moves through circuit columns and keeps the topology selector available.
- `--mode window` is only available in 2D.
- Hover is enabled by default in both 2D and 3D when the Matplotlib backend is interactive.
- By default, hover tooltips show gate name, matrix dimensions, and affected qubits, and they add the full matrix automatically for small gates.
- The shared demo window now opens at `10 x 5.5` inches by default; use `--figsize` when you want a larger or smaller managed figure.
- In 2D, the base layout is frozen when the figure opens; if you resize later, the circuit is not recomputed automatically.
- In `--mode window`, the current wrapped page layout also stays as-is after resize.
- The 3D examples still use routed connections to show the topology engine better.
- When you open a 3D demo, the topology selector is enabled automatically so you can switch chip layouts without rerunning the command.
- On native Windows, Cirq and PennyLane demos now avoid eager exact-matrix extraction by default to improve startup. Use `--hover-matrix always` only when you specifically want exact framework matrices, and prefer WSL or Linux if those frameworks are still unstable in your environment.
- If you want to see the page-window controls themselves, run without `--no-show`. Saved images keep the clean circuit figure without the UI chrome.

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
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 12 --columns 40 --mode window
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --qubits 18 --columns 12 --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 6 --columns 8 --hover-matrix always
```

### Cirq

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --qubits 24 --columns 6 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --qubits 6 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --qubits 24 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --qubits 12 --columns 40 --mode window
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --qubits 18 --columns 12 --mode slider
```

### PennyLane

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --qubits 24 --columns 6 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --qubits 6 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --qubits 24 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --qubits 12 --columns 40 --mode window
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --qubits 18 --columns 12 --mode slider
```

### myQLM

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 24 --columns 6 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 6 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 24 --columns 32 --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 12 --columns 40 --mode window
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --qubits 18 --columns 32 --mode slider
```

### CUDA-Q

CUDA-Q remains Linux or WSL oriented:

```bash
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 24 --columns 6 --mode pages
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 6 --columns 32 --mode pages
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 24 --columns 32 --mode pages
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 12 --columns 40 --mode window
.venv/bin/python examples/run_demo.py --demo cudaq-random --qubits 18 --columns 32 --mode slider
```

## 3D topology recipes

Use `--view 3d` with the topology that matches the wire count you want to inspect best. `--mode pages` keeps the existing full-scene view, while `--mode slider` is the best option when the circuit has many columns. Once the figure is open, you can switch to any other supported topology from the built-in selector.

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 12 --columns 12 --view 3d --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 9 --columns 12 --view 3d --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 8 --columns 12 --view 3d --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 10 --columns 12 --view 3d --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 53 --columns 8 --view 3d --topology honeycomb
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --qubits 9 --columns 8 --view 3d --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --qubits 12 --columns 24 --view 3d --mode slider --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --qubits 14 --columns 16 --view 3d --mode slider --topology line
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
