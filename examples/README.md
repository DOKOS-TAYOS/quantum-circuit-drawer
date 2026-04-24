# Examples

The examples are organized around normal user workflows:

- build a circuit or result object with your framework
- call the public API directly
- use the shared runners only when you want discovery or a quick catalog launcher

OpenQASM 2 text and `.qasm` files do not need a separate runner. Install `quantum-circuit-drawer[qiskit]`, then pass text starting with `OPENQASM` or a `.qasm` path to `draw_quantum_circuit(...)`; use `framework="qasm"` when you want the parser path to be explicit.

## Start Here


| Demo                                  | Why run it first                                                                                                           | Platform                     |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| `qiskit-2d-exploration-showcase`      | Managed 2D exploration with `Wires: All/Active`, `Ancillas: Show/Hide`, folded-wire markers, and contextual block controls | Windows and Linux            |
| `qiskit-3d-exploration-showcase`      | Managed 3D exploration with topology-aware selection, persistent block highlights, and contextual block controls           | Windows and Linux            |
| `qiskit-control-flow-showcase`        | Native Qiskit control-flow boxes and open controls                                                                         | Windows and Linux            |
| `qiskit-composite-modes-showcase`     | Compact versus expanded composite instructions                                                                             | Windows and Linux            |
| `ir-basic-workflow`                   | Framework-free example built directly from `CircuitIR`                                                                     | Windows and Linux            |
| `cirq-native-controls-showcase`       | Native controls, classical control, and `CircuitOperation` provenance                                                      | Prefer Linux or WSL          |
| `pennylane-terminal-outputs-showcase` | `qml.cond(...)`, mid-measurement, and terminal output boxes                                                                | Prefer Linux or WSL          |
| `myqlm-structural-showcase`           | Native MyQLM adapter path with compact composite routines                                                                  | Windows and Linux with MyQLM |
| `cudaq-kernel-showcase`               | Supported closed-kernel subset for CUDA-Q                                                                                  | Linux or WSL2                |
| `compare-histograms-ideal-vs-sampled` | Quick tour of the public comparison API, including interactive legend toggles on supported backends                        | Windows and Linux            |


## Discovery

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples/run_demo.py --list
.\.venv\Scripts\python.exe examples/run_histogram_demo.py --list
.\.venv\Scripts\python.exe examples/run_compare_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
.venv/bin/python examples/run_histogram_demo.py --list
.venv/bin/python examples/run_compare_demo.py --list
```

## Safe Run-All Blocks

These blocks are meant to be safe copy-paste starting points.

If you want the same commands without opening any GUI window, append `--no-show`.

### Windows Native

This block avoids CUDA-Q and the Cirq/PennyLane demos that are documented as less reliable on native Windows.

```powershell
.\.venv\Scripts\python.exe examples\qiskit_2d_exploration_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_3d_exploration_showcase.py
.\.venv\Scripts\python.exe examples\ir_basic_workflow.py
.\.venv\Scripts\python.exe examples\qiskit_control_flow_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_composite_modes_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_random.py --mode pages_controls
.\.venv\Scripts\python.exe examples\qiskit_qaoa.py --view 3d --topology grid --mode pages_controls
.\.venv\Scripts\python.exe examples\compare_circuits_qiskit_transpile.py
.\.venv\Scripts\python.exe examples\compare_circuits_composite_modes.py
.\.venv\Scripts\python.exe examples\histogram_binary_order.py
.\.venv\Scripts\python.exe examples\histogram_count_order.py
.\.venv\Scripts\python.exe examples\histogram_interactive_large.py
.\.venv\Scripts\python.exe examples\histogram_multi_register.py
.\.venv\Scripts\python.exe examples\histogram_uniform_reference.py
.\.venv\Scripts\python.exe examples\histogram_quasi.py
.\.venv\Scripts\python.exe examples\histogram_quasi_nonnegative.py
.\.venv\Scripts\python.exe examples\histogram_top_k.py
.\.venv\Scripts\python.exe examples\histogram_result_index.py
.\.venv\Scripts\python.exe examples\compare_histograms_ideal_vs_sampled.py
```

If you also have MyQLM installed, you can append:

```powershell
.\.venv\Scripts\python.exe examples\myqlm_structural_showcase.py
.\.venv\Scripts\python.exe examples\myqlm_random.py
.\.venv\Scripts\python.exe examples\histogram_myqlm_result.py
```

### Linux Or WSL

This block includes the full curated catalog.

```bash
.venv/bin/python examples/qiskit_2d_exploration_showcase.py
.venv/bin/python examples/qiskit_3d_exploration_showcase.py
.venv/bin/python examples/ir_basic_workflow.py
.venv/bin/python examples/qiskit_control_flow_showcase.py
.venv/bin/python examples/qiskit_composite_modes_showcase.py
.venv/bin/python examples/qiskit_random.py --mode pages_controls
.venv/bin/python examples/qiskit_qaoa.py --view 3d --topology grid --mode pages_controls
.venv/bin/python examples/cirq_native_controls_showcase.py
.venv/bin/python examples/cirq_random.py
.venv/bin/python examples/cirq_qaoa.py
.venv/bin/python examples/pennylane_terminal_outputs_showcase.py
.venv/bin/python examples/pennylane_random.py
.venv/bin/python examples/pennylane_qaoa.py
.venv/bin/python examples/myqlm_structural_showcase.py
.venv/bin/python examples/myqlm_random.py
.venv/bin/python examples/cudaq_kernel_showcase.py
.venv/bin/python examples/cudaq_random.py
.venv/bin/python examples/compare_circuits_qiskit_transpile.py
.venv/bin/python examples/compare_circuits_composite_modes.py
.venv/bin/python examples/histogram_binary_order.py
.venv/bin/python examples/histogram_count_order.py
.venv/bin/python examples/histogram_interactive_large.py
.venv/bin/python examples/histogram_multi_register.py
.venv/bin/python examples/histogram_uniform_reference.py
.venv/bin/python examples/histogram_quasi.py
.venv/bin/python examples/histogram_quasi_nonnegative.py
.venv/bin/python examples/histogram_top_k.py
.venv/bin/python examples/histogram_result_index.py
.venv/bin/python examples/histogram_marginal.py
.venv/bin/python examples/histogram_cirq_result.py
.venv/bin/python examples/histogram_pennylane_probs.py
.venv/bin/python examples/histogram_myqlm_result.py
.venv/bin/python examples/histogram_cudaq_sample.py
.venv/bin/python examples/compare_histograms_ideal_vs_sampled.py
```

## Circuit Workflows

### Catalog


| Demo                                  | Focus                                                                                                           | Notes                                                                                                                       |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `qiskit-2d-exploration-showcase`      | Managed 2D exploration, active-wire filtering, ancilla toggles, folded-wire markers, contextual collapse/expand | Best first demo for `pages_controls` and `slider` on a circuit with intentional idle wires and reusable composite structure |
| `qiskit-3d-exploration-showcase`      | Managed 3D exploration, topology-aware selection, and contextual block controls                                 | Best first demo for managed 3D exploration, selection, expand/collapse, and topology switching on the shared semantic path  |
| `qiskit-control-flow-showcase`        | Native `if_else`, `switch_case`, loops, open controls                                                           | Best first Qiskit demo                                                                                                      |
| `qiskit-composite-modes-showcase`     | Composite instructions that are useful with `--composite-mode compact\|expand`                                  | Shows compact versus expanded composite instructions on the same workflow                                                   |
| `qiskit-random`                       | Broad stress test                                                                                               | Good for modes, hover, presets, and large layouts                                                                           |
| `qiskit-qaoa`                         | Dense structured ansatz                                                                                         | Good as a secondary 3D stress test after the managed 3D exploration showcase                                                |
| `cirq-native-controls-showcase`       | Open controls, classical control, `CircuitOperation` provenance                                                 | Native Cirq semantics with rich CircuitOperation provenance                                                                 |
| `cirq-random`                         | Broad stress test                                                                                               | Good for larger Cirq scenes                                                                                                 |
| `cirq-qaoa`                           | Dense structured ansatz                                                                                         | Good for repeated cost/mixer layers                                                                                         |
| `pennylane-terminal-outputs-showcase` | `qml.cond(...)`, mid-measurement, terminal `EXPVAL` / `PROBS` / `COUNTS` / `DM`                                 | Best first PennyLane demo                                                                                                   |
| `pennylane-random`                    | Broad stress test                                                                                               | Good for layout variety                                                                                                     |
| `pennylane-qaoa`                      | Dense structured ansatz                                                                                         | Good for workflow parity with Qiskit/Cirq                                                                                   |
| `myqlm-structural-showcase`           | Native MyQLM adapter path, reusable routines                                                                    | Good for composite structure on the native MyQLM adapter path                                                               |
| `myqlm-random`                        | Broad stress test                                                                                               | Good for coverage                                                                                                           |
| `cudaq-kernel-showcase`               | Supported closed-kernel subset                                                                                  | Good for the supported closed-kernel subset, basis measurements, and reset                                                  |
| `cudaq-random`                        | Broad stress test                                                                                               | Linux/WSL2 only                                                                                                             |
| `ir-basic-workflow`                   | Pure public `CircuitIR` workflow                                                                                | Best demo when you want zero framework dependency                                                                           |


### Commands

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\qiskit_2d_exploration_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_3d_exploration_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_control_flow_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_composite_modes_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_random.py
.\.venv\Scripts\python.exe examples\qiskit_qaoa.py
.\.venv\Scripts\python.exe examples\ir_basic_workflow.py
.\.venv\Scripts\python.exe examples\cirq_native_controls_showcase.py
.\.venv\Scripts\python.exe examples\cirq_random.py
.\.venv\Scripts\python.exe examples\cirq_qaoa.py
.\.venv\Scripts\python.exe examples\pennylane_terminal_outputs_showcase.py
.\.venv\Scripts\python.exe examples\pennylane_random.py
.\.venv\Scripts\python.exe examples\pennylane_qaoa.py
.\.venv\Scripts\python.exe examples\myqlm_structural_showcase.py
.\.venv\Scripts\python.exe examples\myqlm_random.py
```

Linux or WSL:

```bash
.venv/bin/python examples/qiskit_2d_exploration_showcase.py
.venv/bin/python examples/qiskit_3d_exploration_showcase.py
.venv/bin/python examples/qiskit_control_flow_showcase.py
.venv/bin/python examples/qiskit_composite_modes_showcase.py
.venv/bin/python examples/qiskit_random.py
.venv/bin/python examples/qiskit_qaoa.py
.venv/bin/python examples/ir_basic_workflow.py
.venv/bin/python examples/cirq_native_controls_showcase.py
.venv/bin/python examples/cirq_random.py
.venv/bin/python examples/cirq_qaoa.py
.venv/bin/python examples/pennylane_terminal_outputs_showcase.py
.venv/bin/python examples/pennylane_random.py
.venv/bin/python examples/pennylane_qaoa.py
.venv/bin/python examples/myqlm_structural_showcase.py
.venv/bin/python examples/myqlm_random.py
.venv/bin/python examples/cudaq_kernel_showcase.py
.venv/bin/python examples/cudaq_random.py
```

## I Want To See Modes And Options

Use the broad Qiskit demos for option sweeps because they are the most reliable multiplatform path.

When you specifically want the managed 2D controls, use `qiskit-2d-exploration-showcase` first and then widen out to `qiskit-random`.

When you want managed 3D exploration, start with `qiskit-3d-exploration-showcase` before using `qiskit-qaoa` as the denser follow-up.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\qiskit_2d_exploration_showcase.py --mode pages_controls
.\.venv\Scripts\python.exe examples\qiskit_2d_exploration_showcase.py --mode slider --columns 9
.\.venv\Scripts\python.exe examples\qiskit_3d_exploration_showcase.py --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples\qiskit_3d_exploration_showcase.py --view 3d --mode slider --topology star
.\.venv\Scripts\python.exe examples\qiskit_random.py --mode auto
.\.venv\Scripts\python.exe examples\qiskit_random.py --mode pages_controls --hover-matrix always
.\.venv\Scripts\python.exe examples\qiskit_random.py --mode slider --columns 28
.\.venv\Scripts\python.exe examples\qiskit_qaoa.py --view 3d --topology grid --mode pages_controls
.\.venv\Scripts\python.exe examples\qiskit_qaoa.py --view 3d --topology honeycomb --mode slider --qubits 17
.\.venv\Scripts\python.exe examples\qiskit_random.py --preset presentation
.\.venv\Scripts\python.exe examples\qiskit_composite_modes_showcase.py --composite-mode expand
```

Linux or WSL:

```bash
.venv/bin/python examples/qiskit_2d_exploration_showcase.py --mode pages_controls
.venv/bin/python examples/qiskit_2d_exploration_showcase.py --mode slider --columns 9
.venv/bin/python examples/qiskit_3d_exploration_showcase.py --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/qiskit_3d_exploration_showcase.py --view 3d --mode slider --topology star
.venv/bin/python examples/qiskit_random.py --mode auto
.venv/bin/python examples/qiskit_random.py --mode pages_controls --hover-matrix always
.venv/bin/python examples/qiskit_random.py --mode slider --columns 28
.venv/bin/python examples/qiskit_qaoa.py --view 3d --topology grid --mode pages_controls
.venv/bin/python examples/qiskit_qaoa.py --view 3d --topology honeycomb --mode slider --qubits 17
.venv/bin/python examples/qiskit_random.py --preset presentation
.venv/bin/python examples/qiskit_composite_modes_showcase.py --composite-mode expand
```

Useful circuit flags:

- `--mode auto|pages|pages_controls|slider|full`
- `--view 2d|3d`
- `--topology line|grid|star|star_tree|honeycomb`
- `--preset paper|notebook|compact|presentation`
- `--composite-mode compact|expand`
- `--unsupported-policy raise|placeholder`
- `--hover-matrix never|auto|always`

The built-in 3D topologies are flexible, so demo qubit counts are chosen for the circuit you want to inspect rather than for old topology limits.

## I Want To See Histogram Workflows

### Catalog


| Demo                          | Focus                                                            | Dependency |
| ----------------------------- | ---------------------------------------------------------------- | ---------- |
| `histogram-binary-order`      | Natural binary ordering                                          | none       |
| `histogram-count-order`       | Descending counts                                                | none       |
| `histogram-interactive-large` | Interactive mode with many bins                                  | none       |
| `histogram-multi-register`    | Decimal labels per register                                      | none       |
| `histogram-uniform-reference` | Uniform reference line                                           | none       |
| `histogram-quasi`             | Negative quasi-probabilities                                     | none       |
| `histogram-quasi-nonnegative` | Non-negative quasi-probabilities with a zero-based vertical axis | none       |
| `histogram-top-k`             | Top-k filtering and ordering                                     | none       |
| `histogram-result-index`      | Selecting one payload from several results                       | none       |
| `histogram-marginal`          | Joint marginal from a Qiskit result                              | qiskit     |
| `histogram-cirq-result`       | Cirq measurement result                                          | cirq       |
| `histogram-pennylane-probs`   | `qml.probs()` vector                                             | pennylane  |
| `histogram-myqlm-result`      | `raw_data` result object                                         | myqlm      |
| `histogram-cudaq-sample`      | `cudaq.sample()` result                                          | cudaq      |


### Commands

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\histogram_binary_order.py
.\.venv\Scripts\python.exe examples\histogram_count_order.py
.\.venv\Scripts\python.exe examples\histogram_interactive_large.py
.\.venv\Scripts\python.exe examples\histogram_multi_register.py
.\.venv\Scripts\python.exe examples\histogram_uniform_reference.py
.\.venv\Scripts\python.exe examples\histogram_quasi.py
.\.venv\Scripts\python.exe examples\histogram_quasi_nonnegative.py
.\.venv\Scripts\python.exe examples\histogram_top_k.py
.\.venv\Scripts\python.exe examples\histogram_result_index.py
.\.venv\Scripts\python.exe examples\histogram_marginal.py
```

Linux or WSL:

```bash
.venv/bin/python examples/histogram_binary_order.py
.venv/bin/python examples/histogram_count_order.py
.venv/bin/python examples/histogram_interactive_large.py
.venv/bin/python examples/histogram_multi_register.py
.venv/bin/python examples/histogram_uniform_reference.py
.venv/bin/python examples/histogram_quasi.py
.venv/bin/python examples/histogram_quasi_nonnegative.py
.venv/bin/python examples/histogram_top_k.py
.venv/bin/python examples/histogram_result_index.py
.venv/bin/python examples/histogram_marginal.py
.venv/bin/python examples/histogram_cirq_result.py
.venv/bin/python examples/histogram_pennylane_probs.py
.venv/bin/python examples/histogram_myqlm_result.py
.venv/bin/python examples/histogram_cudaq_sample.py
```

Useful histogram flags:

- `--mode auto|static|interactive`
- `--sort state|state_desc|value_desc|value_asc`
- `--top-k <n>`
- `--qubits 0 2 5`
- `--result-index <n>`
- `--data-key <name>`
- `--preset paper|notebook|compact|presentation`
- `--theme light|dark|paper`
- `--draw-style solid|outline|soft`
- `--state-label-mode binary|decimal`
- `--hover` / `--no-hover`
- `--uniform-reference` / `--no-uniform-reference`

## I Want To Compare

### Catalog


| Demo                                  | Focus                                                                                                       | Dependency |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------- |
| `compare-circuits-qiskit-transpile`   | Before/after transpilation                                                                                  | qiskit     |
| `compare-circuits-composite-modes`    | Compact versus expanded composite views                                                                     | qiskit     |
| `compare-histograms-ideal-vs-sampled` | Ideal versus sampled distribution on one state space, with clickable legend toggles on interactive backends | none       |


### Commands

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\compare_circuits_qiskit_transpile.py
.\.venv\Scripts\python.exe examples\compare_circuits_composite_modes.py
.\.venv\Scripts\python.exe examples\compare_histograms_ideal_vs_sampled.py
```

Linux or WSL:

```bash
.venv/bin/python examples/compare_circuits_qiskit_transpile.py
.venv/bin/python examples/compare_circuits_composite_modes.py
.venv/bin/python examples/compare_histograms_ideal_vs_sampled.py
```

Circuit-compare demos default to `--mode pages_controls`, and every circuit-compare mode opens the left circuit, right circuit, and summary table as three normal Matplotlib windows when the example owns the figures.

On interactive Matplotlib backends, `compare-histograms-ideal-vs-sampled` lets you click either the legend swatch or the legend label to hide and restore each series.

Useful compare flags:

- `--mode auto|pages|pages_controls|slider|full`
- `--left-label <name>`
- `--right-label <name>`
- `--highlight-differences` / `--no-highlight-differences`
- `--show-summary` / `--no-show-summary`
- `--sort state|state_desc|delta_desc`
- `--top-k <n>`

## Runner Shortcuts

The direct scripts are the clearest examples to copy from. The runners are still handy when you want ids and quick catalog access.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\run_demo.py --demo qiskit-2d-exploration-showcase --mode slider --columns 9
.\.venv\Scripts\python.exe examples\run_demo.py --demo qiskit-3d-exploration-showcase --view 3d --mode pages_controls --topology grid
.\.venv\Scripts\python.exe examples\run_demo.py --demo qiskit-composite-modes-showcase --composite-mode expand
.\.venv\Scripts\python.exe examples\run_histogram_demo.py --demo histogram-quasi-nonnegative
.\.venv\Scripts\python.exe examples\run_compare_demo.py --demo compare-histograms-ideal-vs-sampled --sort delta_desc
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-2d-exploration-showcase --mode slider --columns 9
.venv/bin/python examples/run_demo.py --demo qiskit-3d-exploration-showcase --view 3d --mode pages_controls --topology grid
.venv/bin/python examples/run_demo.py --demo qiskit-composite-modes-showcase --composite-mode expand
.venv/bin/python examples/run_histogram_demo.py --demo histogram-quasi-nonnegative
.venv/bin/python examples/run_compare_demo.py --demo compare-histograms-ideal-vs-sampled --sort delta_desc
```
