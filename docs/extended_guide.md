# Extended guide

This guide is the long-form user manual for `quantum-circuit-drawer`.

Use the shorter pages when you want a quick path:

- [Getting started](getting-started.md) for the first useful call.
- [Recipes](recipes.md) for copy-paste snippets.
- [API reference](api.md) for exact public types and fields.
- [Frameworks](frameworks.md) for framework support details.
- [Troubleshooting](troubleshooting.md) when something fails.

Use this page when you want the fuller picture: how the public functions fit together, which mode to choose, what each config block is for, how managed controls behave, how histograms work, and which examples are worth running first.

## The Public Mental Model

Most user code follows the same shape:

1. Build a circuit or result object in the tool you already use.
2. Choose a public config object only when defaults are not enough.
3. Call one public function.
4. Keep the returned result object for figures, axes, metrics, diagnostics, or export helpers.

The main entry points are:

| Task | Function | Config | Result |
| --- | --- | --- | --- |
| Analyze one circuit without rendering | `analyze_quantum_circuit(...)` | `DrawConfig` | `CircuitAnalysisResult` |
| Draw one circuit | `draw_quantum_circuit(...)` | `DrawConfig` | `DrawResult` |
| Compare circuits | `compare_circuits(...)` | `CircuitCompareConfig` | `CircuitCompareResult` |
| Plot one distribution | `plot_histogram(...)` | `HistogramConfig` | `HistogramResult` |
| Compare distributions | `compare_histograms(...)` | `HistogramCompareConfig` | `HistogramCompareResult` |

The package also installs the `qcd` command for quick image exports from the terminal.

## Structured Logging For Debugging

When a render resolves to an unexpected mode, a backend does not behave the way you thought, or a managed view seems to react oddly, the quickest next step is usually to enable structured logs:

```python
from quantum_circuit_drawer import LogProfile, configure_logging

configure_logging(level="INFO", profile=LogProfile.DETAIL)
```

Use `level` and `profile` for different jobs:

- `level` controls severity in the normal Python logging sense
- `profile` controls which structured event families are visible

The built-in profiles are:

- `summary`: public API lifecycle, `diagnostic.emitted`, `output.saved`, and all warnings/errors
- `detail`: everything in `summary` plus internal non-interactive events such as runtime resolution, adapter choice, IR lowering, layout, and render completion
- `interactive`: everything in `detail` plus `interactive.*` events from managed 2D/3D views and interactive histograms

For normal script debugging, start with `profile="summary"` or `profile="detail"` and `level="INFO"`.
For interactive debugging, use `profile="interactive"` and `level="DEBUG"` so ignored actions or no-op transitions can also surface.

The most useful correlation fields are:

- `request_id`: one public API call, such as one `draw_quantum_circuit(...)` or `compare_circuits(...)`
- `session_id`: one interactive figure session, so different managed figures from the same request can still be separated cleanly

In comparisons, the logs also preserve `scope` such as `left`, `right`, or `extra[n]`, which makes it easier to tell which side produced a given event.

When you want to consume the logs from code instead of reading them in the terminal, use `capture_logs(...)`:

```python
from quantum_circuit_drawer import capture_logs, draw_quantum_circuit

with capture_logs(level="INFO", profile="detail") as capture:
    result = draw_quantum_circuit(circuit)

print(len(capture.entries))
print(capture.entries[0].event)
print(capture.to_dicts()[0]["request_id"])
```

This capture path is useful for scripts, ad-hoc debugging, and lightweight tooling:

- `capture.records` keeps the raw `logging.LogRecord` objects
- `capture.entries` keeps only structured package events
- `capture.to_dicts()` returns a stable JSON-friendly shape, including fixed metadata plus a nested `fields` dictionary for extra event-specific data

`capture_logs(...)` does not replace `configure_logging(...)`; they can be used together when you want both visible logs and programmatic inspection in the same run.

## Installation Choices

The base package includes the Matplotlib renderer, framework-free IR support, circuit comparison, histogram plotting, and histogram comparison.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install quantum-circuit-drawer
```

Linux or WSL:

```bash
.venv/bin/python -m pip install quantum-circuit-drawer
```

Install optional extras only for frameworks you actually use:

| Extra | Install when you need |
| --- | --- |
| `qiskit` | Qiskit circuits and OpenQASM 2 text or `.qasm` files |
| `qasm3` | OpenQASM 3 text or `.qasm3` files |
| `cirq` | Cirq circuits and Cirq measurement results |
| `pennylane` | PennyLane tapes, scripts, materialized wrappers, and result outputs |
| `myqlm` | MyQLM circuits, programs, routines, and raw result data |
| `cudaq` | CUDA-Q kernels and samples on Linux or WSL2 |

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
.venv/bin/python -m pip install "quantum-circuit-drawer[cudaq]"
```

CUDA-Q is Linux/WSL2-only because the upstream CUDA-Q package is not available for native Windows.

## Supported Inputs At A Glance

Circuit drawing accepts:

- Qiskit `QuantumCircuit`
- OpenQASM 2 and OpenQASM 3 text starting with `OPENQASM`
- `.qasm` and `.qasm3` files
- Cirq `Circuit` and `FrozenCircuit`
- PennyLane `QuantumTape`, `QuantumScript`, and wrappers with a materialized tape
- MyQLM `Circuit`, `Program`, and `QRoutine`
- CUDA-Q closed kernels and scalar-argument kernels with `cudaq_args`
- public `CircuitIR` objects
- circuits built with `CircuitBuilder`

Histogram plotting accepts:

- plain mappings such as `dict` or `Counter`
- count distributions
- quasi-probability distributions, including negative values
- probability vectors and sample arrays
- Qiskit counts, quasi distributions, sampler containers, `BitArray`, and `DataBin`
- Cirq result measurement mappings
- PennyLane `counts`, `probs`, and `sample` outputs
- MyQLM `raw_data`
- CUDA-Q `SampleResult`-style containers

For the exact support contract, read [Frameworks](frameworks.md).

## Public Config Shape

The public configs are grouped by responsibility. This makes calls longer than a flat option list, but it keeps the API stable and easier to grow.

Circuit drawing:

```python
from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
)

config = DrawConfig(
    side=DrawSideConfig(
        render=CircuitRenderOptions(
            view="2d",
            mode="auto",
            composite_mode="compact",
        ),
        appearance=CircuitAppearanceOptions(
            preset="notebook",
            hover={"enabled": True, "show_size": True},
        ),
    ),
    output=OutputOptions(show=False),
)
```

Single histogram:

```python
from quantum_circuit_drawer import (
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramViewOptions,
    OutputOptions,
)

config = HistogramConfig(
    data=HistogramDataOptions(top_k=8),
    view=HistogramViewOptions(sort="value_desc"),
    appearance=HistogramAppearanceOptions(show_uniform_reference=True),
    output=OutputOptions(show=False),
)
```

Circuit comparison:

```python
from quantum_circuit_drawer import (
    CircuitCompareConfig,
    CircuitCompareOptions,
    OutputOptions,
)

config = CircuitCompareConfig(
    compare=CircuitCompareOptions(
        left_title="Before",
        right_title="After",
    ),
    output=OutputOptions(show=False),
)
```

Histogram comparison:

```python
from quantum_circuit_drawer import (
    HistogramCompareConfig,
    HistogramCompareOptions,
    OutputOptions,
)

config = HistogramCompareConfig(
    compare=HistogramCompareOptions(
        left_label="Ideal",
        right_label="Sampled",
        sort="delta_desc",
    ),
    output=OutputOptions(show=False),
)
```

## Drawing A Circuit

The simplest script call is:

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
```

The returned `DrawResult` gives you:

- `primary_figure`
- `primary_axes`
- `figures`
- `axes`
- `mode`
- `page_count`
- `detected_framework`
- `interactive_enabled`
- `hover_enabled`
- `diagnostics`
- `warnings`
- `saved_path`

Useful helpers:

```python
image_path = result.save("circuit.png")
page_paths = result.save_all_pages("circuit_pages")
summary = result.to_dict()
```

Use `output_path` when you already know where the file should go:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        output=OutputOptions(output_path="circuit.png", show=False),
    ),
)
```

## Analyzing Without Rendering

Use `analyze_quantum_circuit(...)` when you want a programmatic summary without opening windows or saving figures.

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, analyze_quantum_circuit

analysis = analyze_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(show=True, output_path="ignored.png")),
)

summary = analysis.to_dict()
```

The analysis path prepares the same normalized circuit pipeline as drawing, but it does not render, call `show()`, or save `output_path`.

`CircuitAnalysisResult` includes:

- detected framework
- resolved mode and view
- page count
- quantum, classical, and total wire counts
- layer count
- operation, gate, controlled-gate, multi-qubit, measurement, swap, and barrier counts
- diagnostics and warnings

This is useful before expensive rendering, in tests, in reports, and in pipelines that need a quick circuit summary.

## Draw Modes

`DrawMode.AUTO` is the best default until you have a reason to choose a specific mode.

| Mode | Best for | Notes |
| --- | --- | --- |
| `auto` | Normal use | Resolves to `pages` in notebooks and `pages_controls` in normal scripts |
| `pages` | Notebook display and export workflows | Creates explicit page figures |
| `pages_controls` | Normal scripts and interactive inspection | Adds managed page and visible-window controls |
| `slider` | Wide circuits | Uses viewport-style navigation instead of separate page figures |
| `full` | Small circuits that fit well in one scene | Draws the full unpaged circuit |

Explicit mode example:

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
            render=CircuitRenderOptions(mode=DrawMode.PAGES_CONTROLS),
        ),
        output=OutputOptions(show=False),
    ),
)
```

## Managed 2D Controls

`pages_controls` and `slider` are library-managed modes. They create their own Matplotlib figure and controls, so do not combine them with `ax=...`.

Managed 2D can include:

- page navigation
- visible-window controls
- horizontal and vertical sliders when needed
- keyboard shortcuts for navigation and selected-block toggling
- click-based operation selection
- double-click block expand/collapse when semantic provenance is available
- keyboard shortcuts for arrows, `Home` / `End`, `PageUp` / `PageDown`, `Tab` / `Shift+Tab`, `Esc`, `0`, `?`, and `+/-` where the mode supports them; in `pages_controls`, `Up` adds one visible page, `Down` removes one, and `Tab` / `Shift+Tab` keep moving column by column across page boundaries
- `Wires: All/Active`
- `Ancillas: Show/Hide`
- contextual `Collapse` / `Expand` when semantic provenance is available
- folded-wire markers such as `... N hidden wires ...`

If you want to disable those managed interactions explicitly, use `CircuitRenderOptions(keyboard_shortcuts=False, double_click_toggle=False)`.

Use these controls for:

- wide circuits
- circuits with idle wires
- circuits with many ancillas
- composite-heavy circuits
- inspecting the same operation while changing the visible window

The best first demo is:

```powershell
.\.venv\Scripts\python.exe examples\qiskit_2d_exploration_showcase.py
```

Linux or WSL:

```bash
.venv/bin/python examples/qiskit_2d_exploration_showcase.py
```

## Caller-Managed Axes

Use `ax=...` when the circuit is just one subplot inside a larger Matplotlib figure.

```python
import matplotlib.pyplot as plt

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

figure, axes = plt.subplots(figsize=(8, 3))

result = draw_quantum_circuit(
    circuit,
    ax=axes,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(mode=DrawMode.PAGES),
        ),
        output=OutputOptions(show=False),
    ),
)
```

Rules of thumb:

- caller-owned axes are static
- `pages_controls` and `slider` need library-managed figures
- 3D caller-owned rendering needs an axes created with `projection="3d"`
- when you pass `ax=...`, `result.primary_axes` is the axes object you passed in

## 3D Workflows

Use 3D when topology matters visually or when you want a hardware-layout view.

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
                direct=False,
            ),
        ),
        output=OutputOptions(show=False),
    ),
)
```

3D mode supports:

- `pages`
- `pages_controls`
- `slider`
- `full`
- shared camera state in managed page controls
- topology-aware selection
- keyboard shortcuts in managed `pages_controls` and `slider`, including arrows, `Home` / `End`, `PageUp` / `PageDown`, `Tab` / `Shift+Tab`, `Esc`, `0`, and `+/-` where supported
- double-click block expand/collapse in managed `pages_controls` and `slider`
- hover over selected operations when the backend supports interaction
- optional topology menu in managed 3D views

The best first demo is:

```powershell
.\.venv\Scripts\python.exe examples\qiskit_3d_exploration_showcase.py
```

Linux or WSL:

```bash
.venv/bin/python examples/qiskit_3d_exploration_showcase.py
```

## Topology Options

Built-in topology names:

- `"line"`
- `"grid"`
- `"star"`
- `"star_tree"`
- `"honeycomb"`

They are flexible builders, so they support arbitrary positive qubit counts.

`topology_qubits` controls whether inactive physical nodes are visible:

| Value | Behavior |
| --- | --- |
| `"used"` | Show only the allocated topology nodes used by the circuit |
| `"all"` | Show the full topology footprint, including inactive physical nodes |

`topology_resize` controls what happens if a topology is too small:

| Value | Behavior |
| --- | --- |
| `"error"` | Raise a clear size error |
| `"fit"` | Rebuild functional or periodic topologies for the circuit size |

Static `HardwareTopology` instances never resize. That is intentional because they usually represent a real backend or an exact physical layout.

For real Qiskit devices, build a static topology from a backend:

```python
from quantum_circuit_drawer import HardwareTopology

topology = HardwareTopology.from_qiskit_backend(backend)
```

Then pass it into a 3D render:

```python
from quantum_circuit_drawer import CircuitRenderOptions, DrawConfig, DrawSideConfig

config = DrawConfig(
    side=DrawSideConfig(
        render=CircuitRenderOptions(
            view="3d",
            topology=topology,
            topology_qubits="all",
            direct=False,
        ),
    ),
)
```

## OpenQASM 2 And 3

OpenQASM input is a convenience path through Qiskit parsers.

Install:

- `quantum-circuit-drawer[qiskit]` for OpenQASM 2
- `quantum-circuit-drawer[qasm3]` for OpenQASM 3

Accepted forms:

- a string that starts with `OPENQASM`
- `Path("circuit.qasm")`
- `"circuit.qasm"`
- `Path("circuit.qasm3")`
- `"circuit.qasm3"`

Text example:

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

File example:

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
        side=DrawSideConfig(
            render=CircuitRenderOptions(framework="qasm"),
        ),
        output=OutputOptions(show=False),
    ),
)
```

Use `framework="qasm"` when you want to force the parser path explicitly. The same value is used for OpenQASM 2 and OpenQASM 3; the header and file extension decide which Qiskit parser runs.

## Composite Operations And Unsupported Operations

`composite_mode` controls how supported composite operations are presented.

| Value | Behavior |
| --- | --- |
| `"compact"` | Keep a composite as a compact box when possible |
| `"expand"` | Expand supported composite contents into separate operations |

Compact mode is usually better for readability. Expanded mode is useful when you want to inspect the internal steps of decomposable operations.

Unsupported operations use a strict policy by default:

```python
from quantum_circuit_drawer import CircuitRenderOptions, DrawConfig, DrawSideConfig

strict_config = DrawConfig(
    side=DrawSideConfig(
        render=CircuitRenderOptions(unsupported_policy="raise"),
    ),
)
```

For exploratory workflows, use placeholders for recoverable unsupported operations:

```python
from quantum_circuit_drawer import CircuitRenderOptions, DrawConfig, DrawSideConfig

placeholder_config = DrawConfig(
    side=DrawSideConfig(
        render=CircuitRenderOptions(unsupported_policy="placeholder"),
    ),
)
```

Structural errors still raise. The placeholder policy is for recoverable cases where a best-effort visual is meaningful.

## Hover

Hover is configured through `CircuitAppearanceOptions`.

```python
from quantum_circuit_drawer import CircuitAppearanceOptions, DrawConfig, DrawSideConfig

config = DrawConfig(
    side=DrawSideConfig(
        appearance=CircuitAppearanceOptions(
            hover={
                "enabled": True,
                "show_size": True,
                "show_matrix": "auto",
                "matrix_max_qubits": 2,
            },
        ),
    ),
)
```

Useful hover fields:

| Field | Meaning |
| --- | --- |
| `enabled` | Enable or disable hover |
| `show_size` | Include operation size details when available |
| `show_matrix` | Matrix display mode: commonly `"never"`, `"auto"`, or `"always"` |
| `matrix_max_qubits` | Maximum gate size for matrix display |

Use `show_matrix="never"` for the lightest path. This is especially useful on native Windows with heavier optional frameworks.

Hover needs an interactive Matplotlib backend. Saved images and non-interactive backends stay static.

## Presets, Style, And Theme

Presets give you a practical baseline:

- `paper`
- `notebook`
- `compact`
- `presentation`
- `accessible`

Circuit preset example:

```python
from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    StylePreset,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            appearance=CircuitAppearanceOptions(
                preset=StylePreset.PRESENTATION,
            ),
        ),
        output=OutputOptions(show=False),
    ),
)
```

Style mapping example:

```python
from quantum_circuit_drawer import CircuitAppearanceOptions, DrawConfig, DrawSideConfig

config = DrawConfig(
    side=DrawSideConfig(
        appearance=CircuitAppearanceOptions(
            preset="paper",
            style={
                "max_page_width": 9.0,
                "wire_line_width": 1.8,
                "classical_wire_line_width": 1.5,
                "connection_line_width": 1.9,
                "measurement_line_width": 1.4,
            },
        ),
    ),
)
```

Themes affect colors for circuit elements, topology elements, hover labels, managed UI widgets, and histogram plots. Built-in theme names are:

- `light`
- `paper`
- `dark`
- `accessible`

Use `accessible` for high-contrast output that relies less on color alone.

## Saving And Exports

`OutputOptions(output_path=...)` saves during rendering:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        output=OutputOptions(output_path="circuit.png", show=False),
    ),
)
```

Result objects can export after rendering:

```python
image_path = result.save("circuit.png")
summary = result.to_dict()
```

Circuit results also support all-page export:

```python
page_paths = result.save_all_pages(
    "pages",
    filename_prefix="circuit",
    extension=".png",
)
```

Histogram results support CSV export:

```python
csv_path = histogram_result.to_csv("histogram.csv")
```

Comparison results also expose `save(...)` and `to_dict()`.

## Diagnostics And Warnings

Every main result object can carry diagnostics. Diagnostics are meant to be user-visible hints, not internal tracebacks.

Common diagnostic situations:

- `auto` mode resolved to a concrete mode
- hover was requested but disabled because the backend is non-interactive
- histogram auto mode fell back to static mode in an inline notebook backend
- recoverable unsupported operations were drawn as placeholders

Circuit result pattern:

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(show=False)),
)

for warning in result.warnings:
    print(warning.code, warning.message)
```

Analysis result pattern:

```python
analysis = analyze_quantum_circuit(circuit)
summary = analysis.to_dict()
```

## Command Line Interface

The `qcd` command is best for direct file exports.

Draw an OpenQASM circuit:

```powershell
qcd draw bell.qasm --output bell.png --view 3d
```

Plot a JSON histogram:

```powershell
qcd histogram counts.json --output counts.png
```

The CLI saves without opening a window by default. Add `--show` when you also want Matplotlib to display the figure.

Useful `qcd draw` flags:

| Flag | Values |
| --- | --- |
| `--output` | output image path, required |
| `--view` | `2d`, `3d` |
| `--mode` | `auto`, `pages`, `pages_controls`, `slider`, `full` |
| `--framework` | optional input framework override |
| `--topology` | `line`, `grid`, `star`, `star_tree`, `honeycomb` |
| `--topology-qubits` | `used`, `all` |
| `--topology-resize` | `error`, `fit` |
| `--preset` | `paper`, `notebook`, `compact`, `presentation`, `accessible` |
| `--composite-mode` | `compact`, `expand` |
| `--unsupported-policy` | `raise`, `placeholder` |
| `--figsize` | width and height in inches |
| `--show` | open the Matplotlib window |

Useful `qcd histogram` flags:

| Flag | Values |
| --- | --- |
| `--output` | output image path, required |
| `--kind` | `auto`, `counts`, `quasi` |
| `--sort` | `state`, `state_desc`, `value_desc`, `value_asc` |
| `--top-k` | positive integer |
| `--qubits` | one or more non-negative qubit indices |
| `--data-key` | nested JSON field to plot |
| `--state-label-mode` | `binary`, `decimal` |
| `--preset` | `paper`, `notebook`, `compact`, `presentation`, `accessible` |
| `--theme` | `light`, `dark`, `paper`, `accessible` |
| `--draw-style` | `solid`, `outline`, `soft` |
| `--uniform-reference` | show a uniform reference line |
| `--figsize` | width and height in inches |
| `--show` | open the Matplotlib window |

For nested JSON:

```powershell
qcd histogram result.json --data-key counts --output counts.png
```

## Plotting One Histogram

Counts example:

```python
from quantum_circuit_drawer import (
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
        output=OutputOptions(show=False),
    ),
)
```

Quasi-probability example:

```python
from quantum_circuit_drawer import (
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
        output=OutputOptions(show=False),
    ),
)
```

`HistogramKind.AUTO` infers counts when values are non-negative integers. Otherwise it treats the input as quasi-probabilities.

## Histogram Sorting, Labels, And Top-K

Sorting options:

| Sort | Behavior |
| --- | --- |
| `state` | Natural ascending state order |
| `state_desc` | Reverse state order |
| `value_desc` | Largest values first |
| `value_asc` | Smallest values first |

Label modes:

| Mode | Behavior |
| --- | --- |
| `binary` | Keep normalized bitstring labels |
| `decimal` | Convert labels to decimal display |

If a label contains space-separated registers, decimal mode converts each register independently.

```python
from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramStateLabelMode,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)

result = plot_histogram(
    {"10 011": 7, "01 101": 3},
    config=HistogramConfig(
        view=HistogramViewOptions(
            state_label_mode=HistogramStateLabelMode.DECIMAL,
        ),
        output=OutputOptions(show=False),
    ),
)
```

Use `top_k` after sorting when you only want the most relevant states:

```python
from quantum_circuit_drawer import HistogramConfig, HistogramDataOptions

config = HistogramConfig(data=HistogramDataOptions(top_k=8))
```

## Histogram Marginals

Use `HistogramDataOptions(qubits=(...))` for a joint marginal over selected qubits.

```python
from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramDataOptions,
    OutputOptions,
    plot_histogram,
)

result = plot_histogram(
    {"101": 2, "001": 1, "111": 3},
    config=HistogramConfig(
        data=HistogramDataOptions(qubits=(0, 2)),
        output=OutputOptions(show=False),
    ),
)
```

The qubit order is preserved exactly as passed. For example, `qubits=(0, 2)` means the output labels are built from `q0` followed by `q2`.

## Interactive Histograms

`HistogramMode.AUTO` resolves by runtime context:

- normal script: `interactive`
- notebook widget backend such as `nbagg`, `ipympl`, or `widget`: `interactive`
- inline or non-widget notebook backend: `static`

Interactive mode can add:

- a slider viewport
- per-bin hover
- an order button
- a binary/decimal label button
- a `Mode: Counts` / `Mode: Quasi` toggle when the original input is counts
- a slider visibility button when hidden bins exist
- a marginal-qubits text box

Explicit interactive example:

```python
from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramMode,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)

result = plot_histogram(
    {format(index, "07b"): index + 1 for index in range(2**7)},
    config=HistogramConfig(
        view=HistogramViewOptions(mode=HistogramMode.INTERACTIVE),
        output=OutputOptions(show=False),
    ),
)
```

Interactive histograms require a library-managed figure. Do not combine interactive mode with `ax=...`.

## Comparing Circuits

Use `compare_circuits(...)` to inspect structural differences, for example before and after transpilation or across several transpilation levels.

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

optimized = transpile(source, basis_gates=["u", "cx"], optimization_level=2)

result = compare_circuits(
    source,
    optimized,
    config=CircuitCompareConfig(
        compare=CircuitCompareOptions(
            left_title="Source",
            right_title="Optimized",
        ),
        output=OutputOptions(show=False),
    ),
)
```

By default, circuit comparison returns:

- one normal `DrawResult` for each compared circuit
- one compact summary figure
- structural metrics

Metrics include:

- layer counts and layer delta
- operation counts and operation delta
- multi-qubit counts and delta
- measurement counts and delta
- swap counts and delta
- differing layer count
- left-only and right-only layer counts

Use explicit `mode="full"` or caller-owned axes when you want one static side-by-side figure. Provide one axes object per circuit. If your Matplotlib layout has room for a dedicated summary panel, pass `summary_ax=...`; the library will place its built-in comparison summary card in that subplot.

For 3+ circuits:

- pass extra circuits as additional positional arguments
- set `CircuitCompareOptions(titles=(...))` with one title per circuit
- read all per-circuit `DrawResult` objects from `result.side_results`
- read all aggregate values from `result.side_metrics`
- the summary table uses one column per circuit and no delta column
- lower aggregate values are highlighted in green and higher aggregate values in red on each row

```python
result = compare_circuits(
    source,
    transpiled_level_0,
    transpiled_level_1,
    transpiled_level_3,
    config=CircuitCompareConfig(
        compare=CircuitCompareOptions(
            titles=("Source", "Opt 0", "Opt 1", "Opt 3"),
        ),
        output=OutputOptions(show=False),
    ),
)
```

## Comparing Histograms

Use `compare_histograms(...)` to align two or more distributions on the same state space.

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
            left_label="Ideal",
            right_label="Sampled",
            sort="delta_desc",
        ),
        output=OutputOptions(show=False),
    ),
)
```

`HistogramCompareResult` includes:

- `state_labels`
- `left_values`
- `right_values`
- `delta_values`
- `series_labels`
- `series_values`
- `metrics`
- `qubits`
- diagnostics
- export helpers

Metrics include:

- total variation distance
- maximum absolute delta

On interactive Matplotlib backends, the legend is clickable. Clicking a legend entry toggles that series on or off while keeping the legend anchored in the same position.

For 3+ histogram series:

- pass extra distributions as additional positional arguments
- set `HistogramCompareOptions(series_labels=(...))` with one label per distribution
- use `result.series_values` for all aligned values
- `left_values`, `right_values`, `delta_values`, and `metrics` remain the first-two compatibility view
- `sort="delta_desc"` orders by largest spread across all series

```python
result = compare_histograms(
    ideal,
    noisy_simulator,
    hardware_raw,
    mitigated,
    config=HistogramCompareConfig(
        compare=HistogramCompareOptions(
            series_labels=("Ideal", "Noisy sim", "Hardware raw", "Mitigated"),
            sort="delta_desc",
        ),
        output=OutputOptions(show=False),
    ),
)
```

## Framework Notes

This section summarizes day-to-day usage. For the full support contract, read [Frameworks](frameworks.md).

### Qiskit

Install:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
```

Typical input:

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
```

Useful Qiskit workflows:

- normal `QuantumCircuit` drawing
- compact control-flow boxes
- open controls from `ctrl_state`
- compact or expanded composite instructions
- backend-derived 3D topology with `HardwareTopology.from_qiskit_backend(...)`
- result histograms from counts, quasi distributions, sampler containers, `BitArray`, and `DataBin`

Recommended demos:

- `qiskit-2d-exploration-showcase`
- `qiskit-3d-exploration-showcase`
- `qiskit-control-flow-showcase`
- `qiskit-composite-modes-showcase`
- `openqasm-showcase`
- `qiskit-backend-topology-showcase`
- `compare-circuits-qiskit-transpile`
- `compare-circuits-multi-transpile`

### Cirq

Install:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[cirq]"
```

Typical input:

```python
from cirq.circuits import Circuit, Moment
from cirq.devices import LineQubit
from cirq.ops import CNOT, H, measure

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

q0, q1 = LineQubit.range(2)
circuit = Circuit(
    Moment(H(q0)),
    Moment(CNOT(q0, q1)),
    Moment(measure(q1, key="m")),
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(show=False)),
)
```

Useful Cirq workflows:

- `Circuit` and `FrozenCircuit`
- native controls when they can be represented clearly
- classically controlled operations with hover fallback for non-normalizable conditions
- `CircuitOperation` compact or expanded modes
- result histograms from Cirq measurement data

On native Windows, Cirq can still be affected by upstream SciPy/HiGHS behavior. Prefer Linux or WSL for repeated demos.

Recommended demo:

- `cirq-native-controls-showcase`

### PennyLane

Install:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[pennylane]"
```

Typical input:

```python
from pennylane.measurements import ProbabilityMP
from pennylane.ops import CNOT, Hadamard
from pennylane.tape import QuantumTape

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

with QuantumTape() as tape:
    Hadamard(wires=0)
    CNOT(wires=[0, 1])
    ProbabilityMP(wires=[1])

result = draw_quantum_circuit(
    tape,
    config=DrawConfig(output=OutputOptions(show=False)),
)
```

Useful PennyLane workflows:

- `QuantumTape`
- `QuantumScript`
- wrappers that already expose a materialized `.qtape`, `.tape`, or `._tape`
- mid-circuit `qml.measure(...)`
- compact terminal output boxes for `expval`, `var`, `probs`, `sample`, `counts`, `state`, and `density_matrix`
- direct histogram plotting from `qml.counts()`, `qml.probs()`, and `qml.sample()`

The adapter does not call `construct()` or trigger lazy wrapper properties.

On native Windows, PennyLane can still be affected by upstream SciPy/HiGHS behavior. Prefer Linux or WSL for repeated demos.

Recommended demo:

- `pennylane-terminal-outputs-showcase`

### MyQLM

Install:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[myqlm]"
```

Typical input:

```python
from qat.lang.AQASM import CNOT, H, Program

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

program = Program()
qbits = program.qalloc(2)

H(qbits[0])
CNOT(qbits[0], qbits[1])

result = draw_quantum_circuit(
    program,
    config=DrawConfig(output=OutputOptions(show=False)),
)
```

Useful MyQLM workflows:

- `qat.core.Circuit`
- `Program`
- `QRoutine`
- compact composite routines
- direct result histograms from `qat.core.Result.raw_data`

MyQLM is a scoped adapter + contract support path rather than a first-class multiplatform CI backend.

Recommended demo:

- `myqlm-structural-showcase`

### CUDA-Q

Install on Linux or WSL2:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[cudaq]"
```

Closed kernel example:

```python
import cudaq

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit


@cudaq.kernel
def bell_pair() -> None:
    qubits = cudaq.qvector(2)
    h(qubits[0])
    x.ctrl(qubits[0], qubits[1])
    mz(qubits)


result = draw_quantum_circuit(
    bell_pair,
    config=DrawConfig(output=OutputOptions(show=False)),
)
```

Runtime-argument kernel example:

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
            ),
        ),
        output=OutputOptions(show=False),
    ),
)
```

CUDA-Q currently supports scalar `int`, `float`, and `bool` runtime arguments through `cudaq_args`. It is not available on native Windows.

Recommended demo:

- `cudaq-kernel-showcase`

### Framework-Free IR

Use `CircuitBuilder` when you want a small framework-free circuit:

```python
from quantum_circuit_drawer import (
    CircuitBuilder,
    DrawConfig,
    OutputOptions,
    draw_quantum_circuit,
)

circuit = (
    CircuitBuilder(2, 1, name="builder_demo")
    .h(0)
    .cx(0, 1)
    .measure(1, 0)
    .build()
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(show=False)),
)
```

Use public `quantum_circuit_drawer.ir` types when you need full control over wires, layers, operations, measurements, and classical conditions.

Recommended demo:

- `ir-basic-workflow`

## Working In Notebooks

Notebook recommendations:

- Use `OutputOptions(show=False)` and display the returned figure yourself.
- Use `DrawMode.PAGES` for explicit page figures.
- Use `%matplotlib widget` when you want hover or interactive histogram controls.
- Use a non-widget inline backend when you only need static images.

Circuit example:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(show=False)),
)

result.primary_figure
```

Paged display:

```python
for figure in result.figures:
    display(figure)
```

## Choosing Examples

Start with these demos:

| Demo id | What it shows |
| --- | --- |
| `qiskit-2d-exploration-showcase` | Managed 2D exploration, active wires, ancillas, folded-wire markers, collapse/expand |
| `qiskit-3d-exploration-showcase` | Managed 3D exploration, topology-aware selection, topology switching |
| `qiskit-control-flow-showcase` | Qiskit control-flow boxes and open controls |
| `qiskit-composite-modes-showcase` | Compact vs expanded composite instructions |
| `openqasm-showcase` | OpenQASM text input through the Qiskit parser path |
| `ir-basic-workflow` | Framework-free public IR workflow |
| `public-api-utilities-showcase` | Analysis, result helpers, page exports, and histogram CSV export |
| `caller-managed-axes-showcase` | Caller-managed axes for circuit, histogram, and comparison panels |
| `style-accessible-showcase` | Accessible circuit and histogram styling |
| `diagnostics-showcase` | Diagnostics, warnings, and resolved-mode metadata |
| `cli-export-showcase` | `qcd` CLI histogram export from JSON, saving `examples/output/cli-export-showcase.png` by default |
| `qiskit-backend-topology-showcase` | Qiskit backend topology conversion into a 3D hardware view |
| `cirq-native-controls-showcase` | Cirq controls, classical control, and `CircuitOperation` provenance |
| `pennylane-terminal-outputs-showcase` | PennyLane terminal outputs and mid-circuit measurement |
| `myqlm-structural-showcase` | MyQLM compact composite routines |
| `cudaq-kernel-showcase` | CUDA-Q supported subset and scalar runtime arguments |
| `compare-circuits-multi-transpile` | One Qiskit source circuit compared with several transpilation levels |
| `compare-histograms-ideal-vs-sampled` | Histogram comparison with clickable legend toggles |
| `compare-histograms-multi-series` | Multi-series histogram comparison with clickable legend toggles |

List available demos:

```powershell
.\.venv\Scripts\python.exe examples\run_demo.py --list
.\.venv\Scripts\python.exe examples\run_histogram_demo.py --list
.\.venv\Scripts\python.exe examples\run_compare_demo.py --list
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --list
.venv/bin/python examples/run_histogram_demo.py --list
.venv/bin/python examples/run_compare_demo.py --list
```

Run a specific demo:

```powershell
.\.venv\Scripts\python.exe examples\run_demo.py --demo qiskit-2d-exploration-showcase --mode slider --columns 9
```

Linux or WSL:

```bash
.venv/bin/python examples/run_demo.py --demo qiskit-2d-exploration-showcase --mode slider --columns 9
```

The full example catalog lives in [Examples](../examples/README.md).

## Troubleshooting Map

When something fails, start with the symptom:

| Symptom | First place to look |
| --- | --- |
| Optional framework import fails | [Troubleshooting: Optional framework import fails](troubleshooting.md#optional-framework-import-fails) |
| OpenQASM input fails | [Troubleshooting: OpenQASM input](troubleshooting.md#openqasm-or-qasm-qasm3-input-fails) |
| CUDA-Q does not install on Windows | [Troubleshooting: CUDA-Q](troubleshooting.md#cuda-q-does-not-install-on-windows) |
| No Matplotlib window opens | [Troubleshooting: No Matplotlib window opens](troubleshooting.md#no-matplotlib-window-opens) |
| Hover does not appear | [Troubleshooting: Hover does not appear](troubleshooting.md#hover-does-not-appear) |
| Saving fails | [Troubleshooting: Saving output fails](troubleshooting.md#saving-output-fails) |
| Slider mode raises an error | [Troubleshooting: slider mode](troubleshooting.md#modedrawmodeslider-raises-valueerror) |
| 3D axes fail | [Troubleshooting: 3D axes](troubleshooting.md#view3d-raises-an-axes-error) |
| Topology is too small | [Troubleshooting: topology size](troubleshooting.md#a-3d-topology-is-smaller-than-the-circuit) |
| Unsupported operation | [Troubleshooting: Unsupported operations](troubleshooting.md#unsupported-operations) |

Useful first checks:

- Make sure the correct optional extra is installed in the same `.venv`.
- Use `OutputOptions(show=False)` for scripts and automated exports.
- Use `framework="qasm"` for explicit OpenQASM parsing.
- Keep CUDA-Q on Linux or WSL2.
- Use `unsupported_policy="placeholder"` when a best-effort exploratory drawing is acceptable.
- Use `show_matrix="never"` for lighter hover on native Windows.

## Practical Defaults

For scripts:

```python
DrawConfig(output=OutputOptions(show=False))
```

For notebooks:

```python
DrawConfig(output=OutputOptions(show=False))
```

Then display `result.primary_figure` or loop over `result.figures`.

For wide circuits:

```python
DrawConfig(
    side=DrawSideConfig(
        render=CircuitRenderOptions(mode="slider"),
    ),
)
```

For 3D topology inspection:

```python
DrawConfig(
    side=DrawSideConfig(
        render=CircuitRenderOptions(
            view="3d",
            mode="pages_controls",
            topology="grid",
            topology_menu=True,
            direct=False,
        ),
    ),
)
```

For publication-style static output:

```python
DrawConfig(
    side=DrawSideConfig(
        appearance=CircuitAppearanceOptions(preset="paper"),
    ),
    output=OutputOptions(output_path="figure.png", show=False),
)
```

For accessible contrast:

```python
DrawConfig(
    side=DrawSideConfig(
        appearance=CircuitAppearanceOptions(preset="accessible"),
    ),
    output=OutputOptions(show=False),
)
```

For histogram comparison:

```python
HistogramCompareConfig(
    compare=HistogramCompareOptions(sort="delta_desc"),
    output=OutputOptions(show=False),
)
```

## Where This Guide Stops

This guide focuses on public usage: functions, configs, result objects, modes, supported inputs, exports, examples, and troubleshooting.

For extension contracts, use [Extension API](extensions.md). For exact dataclass fields and enum values, use [API reference](api.md). For repository maintenance and contributor commands, use [Development](development.md).
