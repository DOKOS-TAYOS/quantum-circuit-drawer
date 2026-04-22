# Examples

The example scripts cover both circuit rendering and histogram rendering.

## Empieza por aquí

These are the best first demos when you want to see what the library can do today.

| Demo id | Why it is a good first run | Platform note |
| --- | --- | --- |
| `qiskit-control-flow-showcase` | Compact `if_else`, `switch_case`, `for_loop`, `while_loop`, and open controls | Windows and Linux |
| `cirq-native-controls-showcase` | Native Cirq open controls, classical control, CircuitOperation provenance, and provenance-rich hover details | Prefer Linux or WSL for repeated runs |
| `pennylane-terminal-outputs-showcase` | Mid-measurement, `qml.cond(...)`, plus terminal `EXPVAL`, `PROBS`, `COUNTS`, and `DM` output boxes | Prefer Linux or WSL for repeated runs |
| `myqlm-structural-showcase` | Compact composite routines on the native MyQLM adapter path built from `Program().to_circ()` | Windows and Linux when MyQLM is installed |
| `cudaq-kernel-showcase` | Supported closed-kernel subset with reset and basis-specific measurements | Linux or WSL2 only |

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

## Recommended circuit demo commands

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-control-flow-showcase --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo cirq-native-controls-showcase --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo pennylane-terminal-outputs-showcase --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo myqlm-structural-showcase --mode pages_controls
.\.venv\Scripts\python.exe examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology grid
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-control-flow-showcase --mode pages_controls
.venv/bin/python examples/run_demo.py --demo cirq-native-controls-showcase --mode pages_controls
.venv/bin/python examples/run_demo.py --demo pennylane-terminal-outputs-showcase --mode pages_controls
.venv/bin/python examples/run_demo.py --demo myqlm-structural-showcase --mode pages_controls
.venv/bin/python examples/run_demo.py --demo cudaq-kernel-showcase --mode pages_controls
.venv/bin/python examples/run_demo.py --demo qiskit-random --view 3d --mode pages_controls --topology grid
```

The showcase demos are meant to look good immediately. The `random` and `qaoa` demos are still useful when you want broader stress tests or something more configurable.

## Circuit demo catalog

| Demo id | Description | Framework | Best for |
| --- | --- | --- | --- |
| `qiskit-control-flow-showcase` | Qiskit showcase for compact control-flow boxes and open controls | qiskit | Native control-flow boxes and open controls |
| `qiskit-random` | Configurable random Qiskit circuit | qiskit | Broad rendering stress test |
| `qiskit-qaoa` | Configurable QAOA / MaxCut circuit in Qiskit | qiskit | Dense structured ansatz |
| `cirq-native-controls-showcase` | Cirq showcase for native controls, classical control, and CircuitOperation provenance | cirq | Native Cirq semantics |
| `cirq-random` | Configurable random Cirq circuit | cirq | Broad rendering stress test |
| `cirq-qaoa` | Configurable QAOA / MaxCut circuit in Cirq | cirq | Dense structured ansatz |
| `pennylane-terminal-outputs-showcase` | PennyLane showcase for mid-measurement, `qml.cond(...)`, and terminal-output boxes | pennylane | `qml.cond(...)` plus terminal outputs |
| `pennylane-random` | Configurable random PennyLane tape | pennylane | Broad rendering stress test |
| `pennylane-qaoa` | Configurable QAOA / MaxCut tape in PennyLane | pennylane | Dense structured ansatz |
| `myqlm-structural-showcase` | myQLM showcase for compact composite routines on the native adapter path | myqlm | Composite structure backed by `gateDic` |
| `myqlm-random` | Configurable random myQLM circuit | myqlm | Broad rendering stress test |
| `cudaq-kernel-showcase` | CUDA-Q showcase for the supported closed-kernel subset with reset and basis measurements | cudaq | Supported closed-kernel subset |
| `cudaq-random` | Configurable random CUDA-Q kernel | cudaq | Broad rendering stress test |

## Useful render flags

- `--mode`: `pages`, `pages_controls`, `slider`, `full`
- `--view`: `2d`, `3d`
- `--topology` in 3D: `line`, `grid`, `star`, `star_tree`, `honeycomb`
- `--hover-matrix auto|never|always`: especially useful when comparing lighter vs richer hover detail

Recommended defaults:

- `pages_controls` is the nicest managed view in normal scripts.
- `slider` is useful for very wide circuits.
- `full` is best when the circuit is compact enough already.
- `view 3d` works especially well with the random and QAOA demos when you want to show topology-aware layouts.

## Histogram demo catalog

| Demo id | Description | Dependency |
| --- | --- | --- |
| `histogram-binary-order` | Counts histogram in the natural binary-state order | none |
| `histogram-count-order` | Counts histogram ordered from highest to lowest counts | none |
| `histogram-interactive-large` | Large 7-bit histogram with auto controls, conditional slider, and marginal help | none |
| `histogram-multi-register` | Counts histogram with several registers and decimal labels per register | none |
| `histogram-uniform-reference` | Counts histogram with the uniform reference line | none |
| `histogram-quasi` | Quasi-probability histogram with negative bars | none |
| `histogram-marginal` | Qiskit result histogram reduced to a joint marginal | qiskit |
| `histogram-cirq-result` | Cirq measurement-result histogram with several registers | cirq |
| `histogram-pennylane-probs` | PennyLane probability-vector histogram from `qml.probs()` | pennylane |
| `histogram-myqlm-result` | myQLM result histogram built directly from `raw_data` | myqlm |
| `histogram-cudaq-sample` | CUDA-Q sample-result histogram from `cudaq.sample()` | cudaq |

## Recommended histogram commands

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_histogram_demo.py --demo histogram-interactive-large
.\.venv\Scripts\python.exe examples/run_histogram_demo.py --demo histogram-quasi
.\.venv\Scripts\python.exe examples/run_histogram_demo.py --demo histogram-multi-register
```

Linux or WSL:

```bash
.venv/bin/python examples/run_histogram_demo.py --demo histogram-interactive-large
.venv/bin/python examples/run_histogram_demo.py --demo histogram-quasi
.venv/bin/python examples/run_histogram_demo.py --demo histogram-cudaq-sample
```

Each histogram demo opens with a slightly wider default figure so larger state spaces remain readable.
