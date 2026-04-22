# Recipes

These are copy-paste workflows for common tasks.

## Circuit Recipes

### Notebook: one figure per page

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.PAGES, show=False),
)

for figure in result.figures:
    display(figure)
```

### Script: managed page viewer

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.PAGES_CONTROLS),
)
```

### Save a clean export from a script

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        mode=DrawMode.PAGES_CONTROLS,
        output_path="circuit.png",
        show=False,
    ),
)
```

### Draw inside your own Matplotlib axes

```python
import matplotlib.pyplot as plt

from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

fig, ax = plt.subplots()

draw_quantum_circuit(
    circuit,
    ax=ax,
    config=DrawConfig(mode=DrawMode.PAGES, show=False),
)
```

### Use a preset and keep hover enabled

```python
from quantum_circuit_drawer import DrawConfig, StylePreset, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        preset=StylePreset.PRESENTATION,
        hover={"enabled": True, "show_size": True},
        show=False,
    ),
)
```

### Keep rendering even with recoverable unsupported operations

```python
from quantum_circuit_drawer import DrawConfig, UnsupportedPolicy, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        unsupported_policy=UnsupportedPolicy.PLACEHOLDER,
        show=False,
    ),
)
```

### 2D slider for wide circuits

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        mode=DrawMode.SLIDER,
        show=True,
    ),
)
```

### 3D slider

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode=DrawMode.SLIDER,
        topology="grid",
        show=True,
    ),
)
```

### 3D page viewer with topology selector

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode=DrawMode.PAGES_CONTROLS,
        topology="line",
        topology_menu=True,
        direct=False,
        show=True,
    ),
)
```

### Full unpaged render

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.FULL, show=False),
)
```

### Compare an original circuit with an optimized one

```python
from quantum_circuit_drawer import CircuitCompareConfig, compare_circuits

result = compare_circuits(
    left_circuit,
    right_circuit,
    config=CircuitCompareConfig(
        left_title="Before",
        right_title="After",
        show=False,
    ),
)
```

### Build a simple framework-free circuit

```python
from quantum_circuit_drawer import CircuitBuilder, DrawConfig, draw_quantum_circuit

circuit = (
    CircuitBuilder(2, 1, name="recipe_builder")
    .h(0)
    .cx(0, 1)
    .measure(1, 0)
    .build()
)

draw_quantum_circuit(circuit, config=DrawConfig(show=False))
```

## Histogram Recipes

### Plot a counts histogram

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

result = plot_histogram(
    {"00": 51, "11": 49},
    config=HistogramConfig(show=False),
)
```

### Plot a quasi-probability distribution

```python
from quantum_circuit_drawer import HistogramConfig, HistogramKind, plot_histogram

result = plot_histogram(
    {0: 0.52, 3: -0.08},
    config=HistogramConfig(kind=HistogramKind.QUASI, show=False),
)
```

### Keep only the largest states

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

result = plot_histogram(
    {"000": 51, "001": 14, "010": 9, "111": 49},
    config=HistogramConfig(
        sort="value_desc",
        top_k=3,
        show=False,
    ),
)
```

### Plot a joint marginal on selected qubits

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

result = plot_histogram(
    {"101": 2, "001": 1, "111": 3},
    config=HistogramConfig(qubits=(0, 2), show=False),
)
```

### Show decimal labels for several registers

```python
from quantum_circuit_drawer import HistogramConfig, HistogramStateLabelMode, plot_histogram

result = plot_histogram(
    {"10 011": 7, "01 101": 3},
    config=HistogramConfig(
        state_label_mode=HistogramStateLabelMode.DECIMAL,
        show=False,
    ),
)
```

If a state label uses spaces to separate registers, decimal mode converts each register independently, so `10 011` becomes `2 3`.

### Show a uniform reference line

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

result = plot_histogram(
    {"00": 51, "01": 14, "10": 9, "11": 49},
    config=HistogramConfig(
        show_uniform_reference=True,
        show=False,
    ),
)
```

### Explore a large histogram interactively

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

result = plot_histogram(
    {format(index, "07b"): ((index * 17) % 41) + ((index * 5) % 13) + 3 for index in range(2**7)},
    config=HistogramConfig(
        show_uniform_reference=True,
        show=False,
    ),
)
```

With the default `mode="auto"`, this becomes interactive in normal `.py` runs and in notebooks with a widget backend. It stays static on inline notebook backends.

### Plot framework-style probability vectors or samples directly

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

probabilities = [0.125, 0.375, 0.25, 0.25]  # e.g. PennyLane qml.probs(...)
samples = [[0, 1], [1, 1], [1, 1], [0, 1]]  # e.g. PennyLane qml.sample(...)

probability_result = plot_histogram(
    probabilities,
    config=HistogramConfig(show=False),
)

sample_result = plot_histogram(
    samples,
    config=HistogramConfig(show=False),
)
```

This also covers Cirq `Result` / `ResultDict` objects, MyQLM `qat.core.Result`, CUDA-Q `SampleResult`-style containers, and plain tuples or lists of several framework outputs when you select one with `HistogramConfig(result_index=...)`.

### Select one result payload from a tuple

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

payloads = (
    {"00": 20, "11": 12},
    {"00": 3, "01": 8, "11": 21},
)

result = plot_histogram(
    payloads,
    config=HistogramConfig(result_index=1, show=False),
)
```

### Compare two histograms

```python
from quantum_circuit_drawer import HistogramCompareConfig, compare_histograms

result = compare_histograms(
    {"00": 0.5, "11": 0.5},
    {"00": 473, "01": 19, "10": 24, "11": 484},
    config=HistogramCompareConfig(
        left_label="Ideal",
        right_label="Sampled",
        sort="delta_desc",
        show=False,
    ),
)
```
