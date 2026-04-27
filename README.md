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
| Analyze one circuit | `analyze_quantum_circuit(...)` | Inspect framework, size, mode, pages, operations, and diagnostics without rendering |
| Draw one circuit | `draw_quantum_circuit(...)` | Render a Qiskit, Cirq, PennyLane, MyQLM, CUDA-Q, OpenQASM 2/3, or IR circuit |
| Compare circuits | `compare_circuits(...)` | Show before/after or multi-circuit structure, for example transpilation levels |
| Plot one result distribution | `plot_histogram(...)` | Plot counts, quasi-probabilities, marginals, or framework-native result objects |
| Compare result distributions | `compare_histograms(...)` | Overlay two or more ideal, sampled, baseline, or hardware distributions |

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

## Visual Gallery

The library renders normal static images, managed exploration views, 3D topology scenes, and result distributions with the same public API shape. Gallery images use absolute raw GitHub URLs so they render from both GitHub Markdown and the PyPI project description.

| Static 2D circuit | Managed 2D exploration | 3D topology view |
| --- | --- | --- |
| ![Static 2D circuit render](https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/readme_circuit_2d.png) | ![Managed 2D controls with a selected expanded block](https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/readme_managed_controls_2d.png) | ![3D honeycomb topology render without gate labels](https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/readme_topology_3d.png) |
| Slider navigation | 3D selected gate hover | Histogram comparison |
| ![Managed slider with selected block and horizontal slider](https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/readme_slider_2d.png) | ![3D managed scene with a selected gate hover](https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/readme_3d_hover.png) | ![Histogram comparison render](https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/readme_histogram_compare.png) |

## Install

Inside your local `.venv`:

The core package supports Python 3.11, 3.12, and 3.13. Optional framework extras
can have narrower platform support depending on their upstream packages.

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
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qasm3]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[cirq]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[pennylane]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[myqlm]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[qiskit]"
.venv/bin/python -m pip install "quantum-circuit-drawer[qasm3]"
.venv/bin/python -m pip install "quantum-circuit-drawer[cirq]"
.venv/bin/python -m pip install "quantum-circuit-drawer[pennylane]"
.venv/bin/python -m pip install "quantum-circuit-drawer[myqlm]"
```

CUDA-Q is Linux/WSL2-only because the upstream package is not available for native Windows:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[cudaq]"
```

## Support matrix

This is the production support contract for the current release.

| Input path | Support level | Platform notes |
| --- | --- | --- |
| Internal IR | Strong support | Core built-in path on Windows and Linux |
| Qiskit | Strong support | Primary external backend on Windows and Linux |
| OpenQASM 2 text and `.qasm` files | Strong support through the Qiskit extra | Install `quantum-circuit-drawer[qiskit]`; works on Windows and Linux |
| OpenQASM 3 text and `.qasm3` files | Strong support through Qiskit plus `qiskit-qasm3-import` | Install `quantum-circuit-drawer[qasm3]`; works on Windows and Linux when Qiskit's importer is available |
| Cirq | Best-effort on native Windows | Accepts `cirq.Circuit` and `cirq.FrozenCircuit`; prefer Linux or WSL for the most reliable repeated runs |
| PennyLane | Best-effort on native Windows | Prefer Linux or WSL for the most reliable repeated runs |
| MyQLM | Scoped adapter + contract support | Accepts `qat.core.Circuit`, `Program`, and `QRoutine`; adapter contract is covered, but it is not a first-class multiplatform CI backend |
| CUDA-Q | Linux/WSL2 only | Supports closed kernels plus scalar `cudaq_args` for runtime-argument kernels; upstream CUDA-Q is not available for native Windows |

## Choose Your First Task

| If you want to... | Start here |
| --- | --- |
| Inspect a circuit before rendering | [Analyze a circuit](#analyze-a-circuit-without-rendering) |
| Draw a circuit from a supported framework | [Draw one circuit](#draw-one-circuit) |
| Draw OpenQASM 2/3 text or a `.qasm` / `.qasm3` file | [Draw OpenQASM](#draw-openqasm) |
| Generate images from your terminal | [Command line](#command-line) |
| Save a render from a script without opening a window | [Save directly to a file](#save-directly-to-a-file) |
| Plot counts or probabilities | [Plot one histogram](#plot-one-histogram) |
| Compare circuit versions | [Compare circuits](#compare-two-or-more-circuits) |
| Compare distributions | [Compare histograms](#compare-two-or-more-histograms) |
| Build a circuit without a framework dependency | [Build with public IR tools](#build-with-public-ir-tools) |
| Learn the full user-facing feature set | [Extended guide](docs/extended_guide.md) |
| Explore framework-specific demos | [Recommended demos](#recommended-demos) |

## Command Line

The package installs a small `qcd` command for the common "make me an image" workflow. It saves files without opening Matplotlib windows by default; add `--show` when you also want a window.

Windows PowerShell:

```powershell
qcd draw bell.qasm --output bell.png --view 3d
qcd histogram counts.json --output counts.png
```

Linux or WSL:

```bash
qcd draw bell.qasm --output bell.png --view 3d
qcd histogram counts.json --output counts.png
```

`qcd draw` accepts OpenQASM text or `.qasm` / `.qasm3` files. `qcd histogram` accepts JSON mappings such as `{"00": 10, "11": 6}` and can select nested payloads with `--data-key counts`.

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

## Analyze A Circuit Without Rendering

Use `analyze_quantum_circuit(...)` when you want a quick summary before opening windows or saving images:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, analyze_quantum_circuit

analysis = analyze_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(show=True, output_path="ignored.png")),
)

summary = analysis.to_dict()
```

The analysis path prepares the same normalized circuit pipeline as drawing, but it does not render, call `show()`, or save `output_path`.

All public result objects also support post-render export helpers. Circuit results can call `result.save("circuit.png")`, `result.save_all_pages("pages")`, and `result.to_dict()`. Histogram results can also call `result.to_csv("histogram.csv")`.

## Draw OpenQASM

OpenQASM input uses Qiskit as the parser. Install the Qiskit extra for OpenQASM 2, and install the `qasm3` extra when you want OpenQASM 3 support:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qasm3]"
```

You can pass OpenQASM 2 or OpenQASM 3 text directly:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

qasm = """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[1];
h q[0];
cx q[0],q[1];
measure q[1] -> c[0];
"""

result = draw_quantum_circuit(
    qasm,
    config=DrawConfig(output=OutputOptions(show=False)),
)
```

Or draw a `.qasm` / `.qasm3` file directly. `framework="qasm"` is optional when the path ends in `.qasm` or `.qasm3`, but it is useful when you want to be explicit:

```python
from pathlib import Path

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    Path("bell.qasm"),
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(framework="qasm")),
        output=OutputOptions(show=False),
    ),
)
```

## Draw CUDA-Q With Runtime Arguments

CUDA-Q is Linux/WSL2-only because the upstream package is not available for native Windows. Closed kernels work directly; kernels that take scalar runtime arguments use `adapter_options={"cudaq_args": (...)}`:

```python
import cudaq

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

kernel, size, theta = cudaq.make_kernel(int, float)
qubits = kernel.qalloc(size)
kernel.rx(theta, qubits[0])
kernel.mz(qubits)

result = draw_quantum_circuit(
    kernel,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                framework="cudaq",
                adapter_options={"cudaq_args": (3, 0.25)},
            )
        ),
        output=OutputOptions(show=False),
    ),
)
```

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

## Compare Two Or More Circuits

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

- a compact summary figure by default
- one `DrawResult` per circuit, with each circuit rendered in its own normal `pages_controls` figure unless you request `mode="full"` or pass caller-owned axes
- structural metrics such as operation counts, measurement counts, swap counts, and differing layers

For three or more circuits, pass the extra circuits as positional arguments and provide `compare.titles`. The summary table switches from a two-side delta column to one column per circuit; lower aggregate counts are highlighted in green and higher aggregate counts in red for each row.

## Compare Two Or More Histograms

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

This is useful when you want one aligned state space and quick metrics such as total variation distance. On interactive Matplotlib backends, the compare legend is clickable so you can focus one selected series at a time while keeping the axes and hover state in sync.

For three or more distributions, pass extra data objects after the first two and set `HistogramCompareOptions(series_labels=(...))`. Sorting with `sort="delta_desc"` uses the largest spread across all visible series.

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

Managed `pages_controls` and `slider` figures now enable keyboard navigation and block toggling by default. That includes arrows, `Home` / `End`, `PageUp` / `PageDown`, `Tab` / `Shift+Tab`, `Esc`, `0`, `?`, and `+/-` where the mode supports them. In `pages_controls`, `Up` grows the visible page stack, `Down` shrinks it, and `Tab` / `Shift+Tab` move column by column even when that means stepping to the next or previous page. Use `CircuitRenderOptions(keyboard_shortcuts=False, double_click_toggle=False)` if you want to turn those interactions off.

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

The built-in 3D topologies (`"line"`, `"grid"`, `"star"`, `"star_tree"`, and `"honeycomb"`) are flexible builders, so they can be used with arbitrary positive qubit counts. The `"honeycomb"` builder uses an IBM-inspired compact hexagonal footprint. For real Qiskit devices, build a static topology with `HardwareTopology.from_qiskit_backend(backend)`. If a topology has more physical nodes than the circuit uses, `topology_qubits="used"` shows only the allocated nodes while `topology_qubits="all"` shows the full hardware footprint. If a functional or periodic topology is too small, `topology_resize="fit"` rebuilds it for the circuit size; static `HardwareTopology` instances stay fixed and raise a clear error when they are too small.

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
| `openqasm-showcase` | OpenQASM text input through the Qiskit parser path |
| `ir-basic-workflow` | Framework-free rendering from the public `CircuitIR` types |
| `public-api-utilities-showcase` | Analysis, result metadata, page exports, and histogram CSV export |
| `caller-managed-axes-showcase` | Circuit, histogram, and comparison rendering on caller-managed axes |
| `style-accessible-showcase` | Accessible circuit and histogram styling |
| `diagnostics-showcase` | Diagnostics, warnings, and resolved-mode metadata |
| `cli-export-showcase` | Terminal-oriented `qcd` JSON histogram export |
| `qiskit-backend-topology-showcase` | Qiskit backend topology conversion into a 3D hardware view |
| `cirq-native-controls-showcase` | Cirq native controls, classical conditions, and CircuitOperation provenance |
| `pennylane-terminal-outputs-showcase` | PennyLane mid-measurement, `qml.cond(...)`, plus terminal output boxes |
| `myqlm-structural-showcase` | Compact composite routines on the native MyQLM adapter path |
| `cudaq-kernel-showcase` | The supported CUDA-Q subset with scalar runtime arguments, reset, and basis measurements |
| `compare-circuits-multi-transpile` | One Qiskit source circuit compared with several transpilation optimization levels |
| `compare-histograms-ideal-vs-sampled` | A lightweight comparison workflow with no framework extra required, including clickable legend toggles on interactive backends |
| `compare-histograms-multi-series` | A multi-series overlay for ideal, noisy, raw hardware, and mitigated distributions |
| `histogram-quasi-nonnegative` | A compact histogram demo for non-negative quasi-probabilities that keep the vertical axis anchored at zero |

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe examples\qiskit_2d_exploration_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_3d_exploration_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_control_flow_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_composite_modes_showcase.py --composite-mode expand
.\.venv\Scripts\python.exe examples\openqasm_showcase.py
.\.venv\Scripts\python.exe examples\ir_basic_workflow.py
.\.venv\Scripts\python.exe examples\public_api_utilities_showcase.py
.\.venv\Scripts\python.exe examples\caller_managed_axes_showcase.py
.\.venv\Scripts\python.exe examples\style_accessible_showcase.py
.\.venv\Scripts\python.exe examples\diagnostics_showcase.py
.\.venv\Scripts\python.exe examples\cli_export_showcase.py
.\.venv\Scripts\python.exe examples\qiskit_backend_topology_showcase.py
.\.venv\Scripts\python.exe examples\compare_circuits_multi_transpile.py
.\.venv\Scripts\python.exe examples\compare_histograms_ideal_vs_sampled.py
.\.venv\Scripts\python.exe examples\compare_histograms_multi_series.py
.\.venv\Scripts\python.exe examples\histogram_quasi_nonnegative.py
```

Linux or WSL:

```bash
.venv/bin/python examples/qiskit_2d_exploration_showcase.py
.venv/bin/python examples/qiskit_3d_exploration_showcase.py
.venv/bin/python examples/qiskit_control_flow_showcase.py
.venv/bin/python examples/qiskit_composite_modes_showcase.py --composite-mode expand
.venv/bin/python examples/openqasm_showcase.py
.venv/bin/python examples/ir_basic_workflow.py
.venv/bin/python examples/public_api_utilities_showcase.py
.venv/bin/python examples/caller_managed_axes_showcase.py
.venv/bin/python examples/style_accessible_showcase.py
.venv/bin/python examples/diagnostics_showcase.py
.venv/bin/python examples/cli_export_showcase.py
.venv/bin/python examples/qiskit_backend_topology_showcase.py
.venv/bin/python examples/compare_circuits_multi_transpile.py
.venv/bin/python examples/compare_histograms_ideal_vs_sampled.py
.venv/bin/python examples/compare_histograms_multi_series.py
.venv/bin/python examples/histogram_quasi_nonnegative.py
```

The CLI export showcase writes `examples/output/cli-export-showcase.png` by default. Use `--output` to choose another PNG path.

The full curated catalog, including direct script commands, histogram demos, compare demos, and per-framework recommendations, lives in [examples/README.md](examples/README.md).

## Documentation

Use these pages depending on what you need:

- [Documentation index](docs/index.md)
- [Installation](docs/installation.md)
- [Getting started](docs/getting-started.md)
- [User guide](docs/user-guide.md)
- [Extended guide](docs/extended_guide.md)
- [API reference](docs/api.md)
- [Frameworks](docs/frameworks.md)
- [Recipes](docs/recipes.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Examples](examples/README.md)
- [Extension API](docs/extensions.md)
- [Development](docs/development.md)
- [Changelog](CHANGELOG.md)
