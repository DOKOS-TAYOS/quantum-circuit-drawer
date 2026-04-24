# Recipes

These are copy-paste workflows for common tasks.

## Circuit Recipes

### Notebook: one figure per page

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
        side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.PAGES)),
        output=OutputOptions(show=False),
    ),
)

for figure in result.figures:
    display(figure)
```

### Script: managed page viewer

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    draw_quantum_circuit,
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.PAGES_CONTROLS)),
    ),
)
```

### Save a clean export from a script

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.PAGES_CONTROLS)),
        output=OutputOptions(output_path="circuit.png", show=False),
    ),
)
```

### Draw OpenQASM 2 text or a `.qasm` file

Install `quantum-circuit-drawer[qiskit]` first because OpenQASM parsing is delegated to Qiskit.

```python
from pathlib import Path

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

qasm_text = """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[1];
h q[0];
cx q[0],q[1];
measure q[1] -> c[0];
"""

text_result = draw_quantum_circuit(
    qasm_text,
    config=DrawConfig(output=OutputOptions(show=False)),
)

file_result = draw_quantum_circuit(
    Path("bell.qasm"),
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(framework="qasm")),
        output=OutputOptions(show=False),
    ),
)
```

### Draw inside your own Matplotlib axes

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

fig, ax = plt.subplots()

draw_quantum_circuit(
    circuit,
    ax=ax,
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.PAGES)),
        output=OutputOptions(show=False),
    ),
)
```

### Use a preset and keep hover enabled

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
                hover={"enabled": True, "show_size": True},
            ),
        ),
        output=OutputOptions(show=False),
    ),
)
```

### Keep rendering even with recoverable unsupported operations

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    UnsupportedPolicy,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                unsupported_policy=UnsupportedPolicy.PLACEHOLDER,
            ),
        ),
        output=OutputOptions(show=False),
    ),
)
```

### 2D slider for wide circuits

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    draw_quantum_circuit,
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.SLIDER)),
    ),
)
```

If you want the same mode wrapped around a circuit that already makes `Wires: All/Active`, `Ancillas: Show/Hide`, folded-wire markers, and contextual `Collapse` / `Expand` easy to inspect, run `qiskit-2d-exploration-showcase` from [Examples](../examples/README.md).

### 3D slider

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    draw_quantum_circuit,
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                view="3d",
                mode=DrawMode.SLIDER,
                topology="grid",
            ),
        ),
    ),
)
```

### 3D page viewer with topology selector

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    draw_quantum_circuit,
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                view="3d",
                mode=DrawMode.PAGES_CONTROLS,
                topology="line",
                topology_menu=True,
                direct=False,
            ),
        ),
    ),
)
```

### Full unpaged render

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
        side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.FULL)),
        output=OutputOptions(show=False),
    ),
)
```

### Compare an original circuit with an optimized one

```python
from quantum_circuit_drawer import (
    CircuitCompareConfig,
    CircuitCompareOptions,
    OutputOptions,
    compare_circuits,
)

result = compare_circuits(
    left_circuit,
    right_circuit,
    config=CircuitCompareConfig(
        compare=CircuitCompareOptions(
            left_title="Before",
            right_title="After",
        ),
        output=OutputOptions(show=False),
    ),
)
```

### Build a simple framework-free circuit

```python
from quantum_circuit_drawer import CircuitBuilder, DrawConfig, OutputOptions, draw_quantum_circuit

circuit = (
    CircuitBuilder(2, 1, name="recipe_builder")
    .h(0)
    .cx(0, 1)
    .measure(1, 0)
    .build()
)

draw_quantum_circuit(circuit, config=DrawConfig(output=OutputOptions(show=False)))
```

## Histogram Recipes

### Plot a counts histogram

```python
from quantum_circuit_drawer import HistogramConfig, OutputOptions, plot_histogram

result = plot_histogram(
    {"00": 51, "11": 49},
    config=HistogramConfig(output=OutputOptions(show=False)),
)
```

### Plot a quasi-probability distribution

```python
from quantum_circuit_drawer import HistogramConfig, HistogramDataOptions, HistogramKind, OutputOptions, plot_histogram

result = plot_histogram(
    {0: 0.52, 3: -0.08},
    config=HistogramConfig(
        data=HistogramDataOptions(kind=HistogramKind.QUASI),
        output=OutputOptions(show=False),
    ),
)
```

### Keep only the largest states

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

### Plot a joint marginal on selected qubits

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

### Show decimal labels for several registers

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
        view=HistogramViewOptions(state_label_mode=HistogramStateLabelMode.DECIMAL),
        output=OutputOptions(show=False),
    ),
)
```

If a state label uses spaces to separate registers, decimal mode converts each register independently, so `10 011` becomes `2 3`.

### Show a uniform reference line

```python
from quantum_circuit_drawer import HistogramAppearanceOptions, HistogramConfig, OutputOptions, plot_histogram

result = plot_histogram(
    {"00": 51, "01": 14, "10": 9, "11": 49},
    config=HistogramConfig(
        appearance=HistogramAppearanceOptions(show_uniform_reference=True),
        output=OutputOptions(show=False),
    ),
)
```

### Explore a large histogram interactively

```python
from quantum_circuit_drawer import HistogramAppearanceOptions, HistogramConfig, OutputOptions, plot_histogram

result = plot_histogram(
    {format(index, "07b"): ((index * 17) % 41) + ((index * 5) % 13) + 3 for index in range(2**7)},
    config=HistogramConfig(
        appearance=HistogramAppearanceOptions(show_uniform_reference=True),
        output=OutputOptions(show=False),
    ),
)
```

With the default `mode="auto"`, this becomes interactive in normal `.py` runs and in notebooks with a widget backend. It stays static on inline notebook backends.

### Plot framework-style probability vectors or samples directly

```python
from quantum_circuit_drawer import HistogramConfig, OutputOptions, plot_histogram

probabilities = [0.125, 0.375, 0.25, 0.25]  # e.g. PennyLane qml.probs(...)
samples = [[0, 1], [1, 1], [1, 1], [0, 1]]  # e.g. PennyLane qml.sample(...)

probability_result = plot_histogram(
    probabilities,
    config=HistogramConfig(output=OutputOptions(show=False)),
)

sample_result = plot_histogram(
    samples,
    config=HistogramConfig(output=OutputOptions(show=False)),
)
```

This also covers Cirq `Result` / `ResultDict` objects, MyQLM `qat.core.Result`, CUDA-Q `SampleResult`-style containers, and plain tuples or lists of several framework outputs when you select one with `HistogramConfig(data=HistogramDataOptions(result_index=...))`.

### Select one result payload from a tuple

```python
from quantum_circuit_drawer import HistogramConfig, HistogramDataOptions, OutputOptions, plot_histogram

payloads = (
    {"00": 20, "11": 12},
    {"00": 3, "01": 8, "11": 21},
)

result = plot_histogram(
    payloads,
    config=HistogramConfig(
        data=HistogramDataOptions(result_index=1),
        output=OutputOptions(show=False),
    ),
)
```

### Compare two histograms

```python
from quantum_circuit_drawer import (
    HistogramCompareConfig,
    HistogramCompareOptions,
    OutputOptions,
    compare_histograms,
)

result = compare_histograms(
    {"00": 0.5, "11": 0.5},
    {"00": 473, "01": 19, "10": 24, "11": 484},
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
