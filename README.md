<p align="center">
  <img
    src="https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/Quantum_Circuit_Drawer_logo.png"
    alt="Quantum Circuit Drawer logo"
    width="560"
  />
</p>

# quantum-circuit-drawer

`quantum-circuit-drawer` is a Matplotlib-based library for drawing quantum circuits, plotting measurement results, and comparing outputs across several quantum ecosystems with one consistent public API.

The main idea is simple:

- build your circuit or result object the way you normally would
- call one public function
- get a stable result object back

## What You Can Do

The library is centered on four user workflows:

| Workflow | Public API | Typical use |
| --- | --- | --- |
| Draw one circuit | `draw_quantum_circuit(...)` | Render a Qiskit, Cirq, PennyLane, MyQLM, CUDA-Q, or IR circuit |
| Compare two circuits | `compare_circuits(...)` | Show before/after structure, for example before and after transpilation |
| Plot one result distribution | `plot_histogram(...)` | Plot counts, quasi-probabilities, marginals, or framework-native result objects |
| Compare two result distributions | `compare_histograms(...)` | Overlay ideal vs sampled, baseline vs new run, or counts vs quasi |

The public configuration is also intentionally small:

- `DrawConfig` for circuit rendering
- `HistogramConfig` for single histograms
- `CircuitCompareConfig` for side-by-side circuit comparison
- `HistogramCompareConfig` for histogram comparison

Each public config is now grouped into typed blocks ordered by responsibility:

- circuit drawing uses `DrawConfig(side=..., output=...)`
- circuit comparison uses `CircuitCompareConfig(shared=..., compare=..., output=...)`
- single histograms use `HistogramConfig(data=..., view=..., appearance=..., output=...)`
- histogram comparison uses `HistogramCompareConfig(data=..., compare=..., output=...)`

## Install

Inside your local `.venv`:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install quantum-circuit-drawer
```

Linux or WSL:

```bash
.venv/bin/python -m pip install quantum-circuit-drawer
```

Install only the extras you need:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[cirq]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[pennylane]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[myqlm]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[qiskit]"
.venv/bin/python -m pip install "quantum-circuit-drawer[cirq]"
.venv/bin/python -m pip install "quantum-circuit-drawer[pennylane]"
.venv/bin/python -m pip install "quantum-circuit-drawer[myqlm]"
```

CUDA-Q remains a Linux or WSL2 path:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[cudaq]"
```

## Support matrix

This is the production support contract for the current release.

| Input path | Support level | Platform notes |
| --- | --- | --- |
| Internal IR | Strong support | Core built-in path on Windows and Linux |
| Qiskit | Strong support | Primary external backend on Windows and Linux |
| Cirq | Best-effort on native Windows | Prefer Linux or WSL for the most reliable repeated runs |
| PennyLane | Best-effort on native Windows | Prefer Linux or WSL for the most reliable repeated runs |
| MyQLM | Scoped adapter + contract support | Adapter contract is covered, but it is not a first-class multiplatform CI backend |
| CUDA-Q | Linux/WSL2 only | Not intended for native Windows installs |

## Choose Your First Task

| If you want to... | Start here |
| --- | --- |
| Draw a circuit from a supported framework | [Draw one circuit](#draw-one-circuit) |
| Save a render from a script without opening a window | [Save directly to a file](#save-directly-to-a-file) |
| Plot counts or probabilities | [Plot one histogram](#plot-one-histogram) |
| Compare two versions of a circuit | [Compare two circuits](#compare-two-circuits) |
| Compare two distributions | [Compare two histograms](#compare-two-histograms) |
| Build a circuit without a framework dependency | [Build with public IR tools](#build-with-public-ir-tools) |
| Explore framework-specific demos | [Recommended demos](#recommended-demos) |

## Draw One Circuit

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(show=False)),
)

figure = result.primary_figure
axes = result.primary_axes
```

This same shape works for the supported framework objects and for the public IR types.

## Save Directly To A File

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(output_path="bell.png", show=False)),
)
```

This is the most common script workflow when you want a deterministic export without opening a GUI window.

## Plot One Histogram

### Counts

```python
from quantum_circuit_drawer import (
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)

result = plot_histogram(
    {"000": 51, "001": 14, "010": 9, "111": 49},
    config=HistogramConfig(
        data=HistogramDataOptions(top_k=3),
        view=HistogramViewOptions(sort="value_desc"),
        appearance=HistogramAppearanceOptions(show_uniform_reference=True),
        output=OutputOptions(show=False),
    ),
)
```

### Quasi-probabilities

```python
from quantum_circuit_drawer import (
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramKind,
    OutputOptions,
    plot_histogram,
)

result = plot_histogram(
    {0: 0.52, 3: -0.08, 4: 0.17, 7: 0.39},
    config=HistogramConfig(
        data=HistogramDataOptions(kind=HistogramKind.QUASI),
        appearance=HistogramAppearanceOptions(
            draw_style="soft",
            show_uniform_reference=True,
        ),
        output=OutputOptions(show=False),
    ),
)
```

### Joint marginal on selected qubits

```python
from quantum_circuit_drawer import HistogramConfig, HistogramDataOptions, OutputOptions, plot_histogram

result = plot_histogram(
    {"101": 2, "001": 1, "111": 3},
    config=HistogramConfig(
        data=HistogramDataOptions(qubits=(0, 2)),
        output=OutputOptions(show=False),
    ),
)
```

`qubits=(0, 2)` keeps the requested order, so the marginal labels are built as `q0` followed by `q2`.

## Compare Two Circuits

```python
from qiskit import QuantumCircuit, transpile

from quantum_circuit_drawer import (
    CircuitCompareConfig,
    CircuitCompareOptions,
    OutputOptions,
    compare_circuits,
)

source = QuantumCircuit(3, 3)
source.h(0)
source.cx(0, 1)
source.cx(1, 2)
source.measure(range(3), range(3))

transpiled = transpile(source, basis_gates=["u", "cx"], optimization_level=2)

result = compare_circuits(
    source,
    transpiled,
    config=CircuitCompareConfig(
        compare=CircuitCompareOptions(
            left_title="Original",
            right_title="Transpiled",
        ),
        output=OutputOptions(show=False),
    ),
)
```

`CircuitCompareResult` gives you:

- one comparison figure in the default/static path, or a compact summary figure when you request managed modes
- one `DrawResult` per side, including normal `pages`, `pages_controls`, and `slider` figures when those modes are requested
- structural metrics such as operation counts, measurement counts, swap counts, and differing layers

## Compare Two Histograms

```python
from quantum_circuit_drawer import (
    HistogramCompareConfig,
    HistogramCompareOptions,
    OutputOptions,
    compare_histograms,
)

ideal = {"00": 0.5, "11": 0.5}
sampled = {"00": 473, "01": 19, "10": 24, "11": 484}

result = compare_histograms(
    ideal,
    sampled,
    config=HistogramCompareConfig(
        compare=HistogramCompareOptions(
            sort="delta_desc",
            left_label="Ideal",
            right_label="Sampled",
        ),
        output=OutputOptions(show=False),
    ),
)
```

This is useful when you want one aligned state space and quick metrics such as total variation distance. On interactive Matplotlib backends, the compare legend is clickable so you can hide or restore either series while keeping the axes and hover state in sync.

## Build With Public IR Tools

If you do not want to depend on a framework, you can build directly with the public IR tools or use `CircuitBuilder`.

### `CircuitBuilder`

```python
from quantum_circuit_drawer import CircuitBuilder, DrawConfig, OutputOptions, draw_quantum_circuit

circuit = (
    CircuitBuilder(2, 1, name="builder_demo")
    .h(0)
    .cx(0, 1)
    .measure(1, 0)
    .build()
)

draw_quantum_circuit(circuit, config=DrawConfig(output=OutputOptions(show=False)))
```

### Raw `CircuitIR`

If you need complete control over wires, operations, and metadata, use the public `quantum_circuit_drawer.ir` types directly. The best minimal example for that path is the bundled `ir-basic-workflow` demo.

## Modes, Hover, And 3D

The most common choices are:

- `DrawMode.AUTO`: notebook -> `pages`, normal script -> `pages_controls`
- `DrawMode.PAGES`: easiest for notebook display and export-oriented flows
- `DrawMode.PAGES_CONTROLS`: best default for normal scripts
- `DrawMode.SLIDER`: best when you want a viewport through a wide circuit
- `DrawMode.FULL`: best when the circuit fits comfortably in one scene

Example:

```python
from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(mode=DrawMode.PAGES_CONTROLS),
            appearance=CircuitAppearanceOptions(
                hover={"enabled": True, "show_size": True},
            ),
        ),
        output=OutputOptions(show=False),
    ),
)
```

For 3D:

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                view="3d",
                mode=DrawMode.PAGES_CONTROLS,
                topology="grid",
                topology_qubits="used",
                topology_resize="error",
                topology_menu=True,
            ),
        ),
        output=OutputOptions(show=False),
    ),
)
```

The built-in 3D topologies (`"line"`, `"grid"`, `"star"`, `"star_tree"`, and `"honeycomb"`) are flexible builders, so they can be used with arbitrary positive qubit counts. If a topology has more physical nodes than the circuit uses, `topology_qubits="used"` shows only the allocated nodes while `topology_qubits="all"` shows the full hardware footprint. If a functional or periodic topology is too small, `topology_resize="fit"` rebuilds it for the circuit size; static `HardwareTopology` instances stay fixed and raise a clear error when they are too small.

If you want to see the managed 2D controls intentionally exercised instead of configuring them from scratch, start with `qiskit-2d-exploration-showcase`.

If you want the same style of managed exploration in 3D, start with `qiskit-3d-exploration-showcase`.

## Recommended Demos

The fastest way to see the current strengths of the library is to run one of the bundled showcase demos:

| Demo id | What it highlights |
| --- | --- |
| `qiskit-2d-exploration-showcase` | Managed 2D exploration with `Wires: All/Active`, `Ancillas: Show/Hide`, folded-wire markers, and contextual `Collapse` / `Expand` |
| `qiskit-3d-exploration-showcase` | Managed 3D exploration with topology-aware selection, persistent expanded-block highlights, and contextual `Collapse` / `Expand` |
| `qiskit-control-flow-showcase` | Compact Qiskit control-flow boxes plus open controls |
| `qiskit-composite-modes-showcase` | Compact versus expanded composite instructions on the same workflow |
| `ir-basic-workflow` | Framework-free rendering from the public `CircuitIR` types |
| `cirq-native-controls-showcase` | Cirq native controls, classical conditions, and CircuitOperation provenance |
| `pennylane-terminal-outputs-showcase` | PennyLane mid-measurement, `qml.cond(...)`, plus terminal output boxes |
| `myqlm-structural-showcase` | Compact composite routines on the native MyQLM adapter path |
| `cudaq-kernel-showcase` | The supported closed-kernel CUDA-Q subset with reset and basis measurements |
| `compare-histograms-ideal-vs-sampled` | A lightweight comparison workflow with no framework extra required, including clickable legend toggles on interactive backends |
| `histogram-quasi-nonnegative` | A compact histogram demo for non-negative quasi-probabilities that keep the vertical axis anchored at zero |

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\qiskit_2d_exploration_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_3d_exploration_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_control_flow_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_composite_modes_showcase.py --composite-mode expand
.\.venv\Scripts\python.exe examples\ir_basic_workflow.py
.\.venv\Scripts\python.exe examples\compare_histograms_ideal_vs_sampled.py
.\.venv\Scripts\python.exe examples\histogram_quasi_nonnegative.py
```

Linux or WSL:

```bash
.venv/bin/python examples/qiskit_2d_exploration_showcase.py
.venv/bin/python examples/qiskit_3d_exploration_showcase.py
.venv/bin/python examples/qiskit_control_flow_showcase.py
.venv/bin/python examples/qiskit_composite_modes_showcase.py --composite-mode expand
.venv/bin/python examples/ir_basic_workflow.py
.venv/bin/python examples/compare_histograms_ideal_vs_sampled.py
.venv/bin/python examples/histogram_quasi_nonnegative.py
```

The full curated catalog, including direct script commands, histogram demos, compare demos, and per-framework recommendations, lives in [examples/README.md](examples/README.md).

## Documentation

Use these pages depending on what you need:

- [Documentation index](docs/index.md)
- [Installation](docs/installation.md)
- [Getting started](docs/getting-started.md)
- [User guide](docs/user-guide.md)
- [API reference](docs/api.md)
- [Frameworks](docs/frameworks.md)
- [Recipes](docs/recipes.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Examples](examples/README.md)
- [Extension API](docs/extensions.md)
- [Development](docs/development.md)
- [Changelog](CHANGELOG.md)
