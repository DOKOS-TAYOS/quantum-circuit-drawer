# Examples

The example scripts now cover both circuit rendering and histogram rendering.

## Circuit demo catalog

| Demo id              | Description                                    | Framework  |
| -------------------- | ---------------------------------------------- | ---------- |
| `qiskit-random`      | Configurable random Qiskit circuit             | qiskit     |
| `qiskit-qaoa`        | Configurable QAOA / MaxCut circuit in Qiskit   | qiskit     |
| `cirq-random`        | Configurable random Cirq circuit               | cirq       |
| `cirq-qaoa`          | Configurable QAOA / MaxCut circuit in Cirq     | cirq       |
| `pennylane-random`   | Configurable random PennyLane tape             | pennylane  |
| `pennylane-qaoa`     | Configurable QAOA / MaxCut tape in PennyLane   | pennylane  |
| `myqlm-random`       | Configurable random myQLM circuit              | myqlm      |
| `cudaq-random`       | Configurable random CUDA-Q kernel              | cudaq      |

## Histogram demo catalog

| Demo id                      | Description                                       | Dependency |
| ---------------------------- | ------------------------------------------------- | ---------- |
| `histogram-counts`           | Counts histogram from a plain mapping             | none       |
| `histogram-quasi`            | Quasi-probability histogram with negative bars    | none       |
| `histogram-qiskit-marginal`  | Qiskit result histogram reduced to a joint marginal | qiskit   |

## Main axes

- `--mode`: `pages`, `pages_controls`, `slider`, `full`
- `--view`: `2d`, `3d`
- `--topology` (only used when `--view 3d`): `line`, `grid`, `star`, `star_tree`, `honeycomb`

## Discovery

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
.\.venv\Scripts\python.exe examples/run_histogram_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
.venv/bin/python examples/run_histogram_demo.py --list
```

## Histogram demo commands

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_histogram_demo.py --demo histogram-counts
.\.venv\Scripts\python.exe examples/run_histogram_demo.py --demo histogram-quasi
.\.venv\Scripts\python.exe examples/run_histogram_demo.py --demo histogram-qiskit-marginal
```

Linux or WSL:

```bash
.venv/bin/python examples/run_histogram_demo.py --demo histogram-counts
.venv/bin/python examples/run_histogram_demo.py --demo histogram-quasi
.venv/bin/python examples/run_histogram_demo.py --demo histogram-qiskit-marginal
```

## All commands, copy-paste ready

For every demo the same set of runs is listed: the four 2D modes, the four 3D
modes with the default `line` topology, and the five 3D topologies under
`pages_controls`. Pick the block you need and paste it as-is.

### qiskit-random

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology honeycomb
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-random --mode pages
.venv/bin/python examples/run_demo.py --demo qiskit-random --mode pages_controls
.venv/bin/python examples/run_demo.py --demo qiskit-random --mode slider
.venv/bin/python examples/run_demo.py --demo qiskit-random --mode full
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode slider
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode full
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology line
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology star
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology star_tree
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology honeycomb
```

### qiskit-qaoa

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology honeycomb
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --mode pages
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --mode pages_controls
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --mode slider
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --mode full
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode slider
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode full
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology line
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology star
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology star_tree
.venv/bin/python examples/run_demo.py --demo qiskit-qaoa --view 3d --mode pages_controls --topology honeycomb
```

### cirq-random

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology honeycomb
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo cirq-random --mode pages
.venv/bin/python examples/run_demo.py --demo cirq-random --mode pages_controls
.venv/bin/python examples/run_demo.py --demo cirq-random --mode slider
.venv/bin/python examples/run_demo.py --demo cirq-random --mode full
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode pages
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode slider
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode full
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology line
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology star
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology star_tree
.venv/bin/python examples/run_demo.py --demo cirq-random --view 3d --mode pages_controls --topology honeycomb
```

### cirq-qaoa

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology honeycomb
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --mode pages
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --mode pages_controls
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --mode slider
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --mode full
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode slider
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode full
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology line
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology star
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology star_tree
.venv/bin/python examples/run_demo.py --demo cirq-qaoa --view 3d --mode pages_controls --topology honeycomb
```

### pennylane-random

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology honeycomb
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo pennylane-random --mode pages
.venv/bin/python examples/run_demo.py --demo pennylane-random --mode pages_controls
.venv/bin/python examples/run_demo.py --demo pennylane-random --mode slider
.venv/bin/python examples/run_demo.py --demo pennylane-random --mode full
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode pages
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode slider
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode full
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology line
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology star
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology star_tree
.venv/bin/python examples/run_demo.py --demo pennylane-random --view 3d --mode pages_controls --topology honeycomb
```

### pennylane-qaoa

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology honeycomb
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --mode pages
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --mode pages_controls
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --mode slider
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --mode full
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode slider
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode full
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology line
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology star
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology star_tree
.venv/bin/python examples/run_demo.py --demo pennylane-qaoa --view 3d --mode pages_controls --topology honeycomb
```

### myqlm-random

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology honeycomb
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo myqlm-random --mode pages
.venv/bin/python examples/run_demo.py --demo myqlm-random --mode pages_controls
.venv/bin/python examples/run_demo.py --demo myqlm-random --mode slider
.venv/bin/python examples/run_demo.py --demo myqlm-random --mode full
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode pages
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode slider
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode full
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology line
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology star
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology star_tree
.venv/bin/python examples/run_demo.py --demo myqlm-random --view 3d --mode pages_controls --topology honeycomb
```

### cudaq-random

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode pages
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode slider
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode full
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology line
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology star
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology star_tree
.\.venv\Scripts\python.exe examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology honeycomb
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo cudaq-random --mode pages
.venv/bin/python examples/run_demo.py --demo cudaq-random --mode pages_controls
.venv/bin/python examples/run_demo.py --demo cudaq-random --mode slider
.venv/bin/python examples/run_demo.py --demo cudaq-random --mode full
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode pages
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode slider
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode full
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology line
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology star
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology star_tree
.venv/bin/python examples/run_demo.py --demo cudaq-random --view 3d --mode pages_controls --topology honeycomb
```

## Notes

- `pages` is the notebook-friendly mode
- `pages_controls` is the script-friendly managed viewer
- `slider` stays available in 2D and 3D
- `full` renders the whole circuit without paging
- in 3D, `pages_controls` can also expose the topology selector
- `--topology` only applies to `--view 3d`; it is ignored in 2D
