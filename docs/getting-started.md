# Getting started

This guide gets you from installation to a first useful result as quickly as possible.

If you have not installed the package yet, start with [Installation](installation.md).

## The Mental Model

Most user code has the same shape:

1. build your circuit or result object as usual
2. choose the public config object only if you need to override defaults
3. call the public API
4. keep the returned result object if you want figures, axes, metrics, or diagnostics

## Draw Your First Circuit

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

What happens by default:

- the framework is autodetected
- the Matplotlib backend is used
- a managed figure is created for you
- `DrawMode.AUTO` resolves to `pages` in notebooks and `pages_controls` in normal scripts
- the call returns `DrawResult` with the main figure, main axes, and any extra page figures

If you want to see the managed 2D controls already set up around a circuit that makes them useful, run `qiskit-2d-exploration-showcase` from the bundled examples.

## Draw OpenQASM 2 Text Or A `.qasm` File

OpenQASM input is supported for OpenQASM 2 programs. The library delegates parsing to Qiskit, so install the extra first:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
```

Then pass either text that starts with `OPENQASM` or a `.qasm` file path:

```python
from pathlib import Path

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

text_result = draw_quantum_circuit(
    qasm,
    config=DrawConfig(output=OutputOptions(show=False)),
)

file_result = draw_quantum_circuit(
    Path("bell.qasm"),
    config=DrawConfig(output=OutputOptions(show=False)),
)
```

Use `CircuitRenderOptions(framework="qasm")` when you want the input path to be explicit in your config. A `.qasm` file is read as UTF-8 and must start with `OPENQASM`.

## Save Without Opening A Window

This is the most common script workflow:

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

Use this in scripts, CI jobs, notebooks, or reports when you want a file but not a GUI pop-up.

## Draw Inside Your Own Matplotlib Figure

Use `ax=...` when the circuit is only one subplot inside a larger Matplotlib layout.

```python
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

figure, axes = plt.subplots(figsize=(7, 3))
result = draw_quantum_circuit(
    circuit,
    ax=axes,
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.PAGES)),
        output=OutputOptions(show=False),
    ),
)
```

Keep in mind:

- caller-owned axes are for static rendering paths
- do not combine `ax=...` with `pages_controls` or `slider`
- in this mode, `result.primary_axes` is the same axes object you passed in

## Plot Your First Histogram

```python
from quantum_circuit_drawer import HistogramConfig, OutputOptions, plot_histogram

result = plot_histogram(
    {"00": 51, "01": 14, "10": 9, "11": 49},
    config=HistogramConfig(output=OutputOptions(show=False)),
)
```

This same entry point also accepts:

- quasi-probabilities
- framework-native result payloads
- selected marginals through `HistogramDataOptions(qubits=(...))`
- interactive or static histogram mode

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

This is the quickest way to inspect structural differences without writing your own subplot logic.

## Compare Two Histograms

```python
from quantum_circuit_drawer import (
    HistogramCompareConfig,
    HistogramCompareOptions,
    OutputOptions,
    compare_histograms,
)

ideal = {"00": 0.5, "11": 0.5}
sampled = {"00": 478, "01": 19, "10": 21, "11": 482}

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

This returns one comparison figure and aligned values for both sides.

## Framework-Free Start With `CircuitBuilder`

If you want a lightweight path without a framework dependency:

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

This is often the easiest way to generate small circuits in tests, docs, or preprocessing pipelines.

## What To Read Next

- [User guide](user-guide.md): when to use each mode, hover, 3D, presets, and histogram options.
- [Frameworks](frameworks.md): what changes across Qiskit, Cirq, PennyLane, MyQLM, CUDA-Q, and internal IR.
- [API reference](api.md): exact fields, enums, return types, and extension-facing modules.
- [Recipes](recipes.md): copy-paste tasks for common usage patterns.
- [Examples](../examples/README.md): runnable scripts that reflect normal user workflows, including `qiskit-2d-exploration-showcase` for managed 2D exploration.
