# Frameworks

This guide explains how `quantum-circuit-drawer` works with each supported input path.

In most cases, the rendering call stays the same:

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(circuit)
```

Use `DrawConfig(framework=...)` when you want to be explicit or when a wrapper object makes autodetection unclear.

## Contents

- [Overview](#overview)
- [Qiskit](#qiskit)
- [Cirq](#cirq)
- [PennyLane](#pennylane)
- [MyQLM](#myqlm)
- [CUDA-Q](#cuda-q)
- [Internal IR](#internal-ir)
- [Choosing the IR path](#choosing-the-ir-path)

## Overview

The current user-facing input paths are:

| Input path | Typical object | Extra |
| --- | --- | --- |
| Qiskit | `qiskit.QuantumCircuit` | `qiskit` |
| Cirq | `cirq.Circuit` | `cirq` |
| PennyLane | `QuantumTape`, `QuantumScript`, or tape-like objects | `pennylane` |
| MyQLM | `qat.core.Circuit` | `myqlm` |
| CUDA-Q | closed CUDA-Q kernels | `cudaq` |
| Internal IR | `CircuitIR` | none |

Across those paths, the drawer now uses a shared internal flow that can host both adapter styles: framework object -> semantic IR -> render IR for richer adapters, or framework object -> `CircuitIR` for legacy adapters. That lets comparison, diagnostics, hover, and annotations preserve framework-native details longer where native adapters exist, without breaking narrower legacy adapters that still emit `CircuitIR` directly.

Cirq and PennyLane currently use the richer semantic adapter path. MyQLM and CUDA-Q continue through the legacy `to_ir(...)` path in this phase. That shared base is already in place so future semantic migrations can happen without changing the public API first.

## Support matrix

Use this table as the release support contract when choosing a framework path.

| Input path | Support level | Platform notes |
| --- | --- | --- |
| Internal IR | Strong support | Core built-in path on Windows and Linux |
| Qiskit | Strong support | Primary external backend on Windows and Linux |
| Cirq | Best-effort on native Windows | Linux or WSL remains the safer production path |
| PennyLane | Best-effort on native Windows | Linux or WSL remains the safer production path |
| MyQLM | Scoped adapter + contract support | Adapter contract is covered, but it is not a first-class multiplatform CI backend |
| CUDA-Q | Linux/WSL2 only | Not intended for native Windows installs |

Install extras as shown in [Installation](installation.md#install-optional-framework-extras).

`plot_histogram(...)` also accepts several framework-native result payloads directly, not only raw `dict` data:

- Qiskit counts and quasi-distributions, plus sampler result containers
- Cirq `Result` / `ResultDict` measurement payloads
- PennyLane `qml.counts()` dictionaries, `qml.probs()` vectors, and `qml.sample()` arrays
- MyQLM `qat.core.Result` objects with `raw_data`
- CUDA-Q `SampleResult`-style count containers

When a framework returns several measurement outputs at once, pass the tuple or list directly and select one entry with `HistogramConfig(result_index=...)`.

## Qiskit

Install:

```bash
python -m pip install "quantum-circuit-drawer[qiskit]"
```

Typical input:

- `qiskit.QuantumCircuit`

Example:

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

draw_quantum_circuit(circuit)
```

Current support includes common gates, controlled gates, classical `if` conditions, composite instructions, swap, barriers, and measurements.

Histogram support also accepts direct Qiskit result payloads such as `Counts`, `QuasiDistribution`, `SamplerResult`, `PrimitiveResult`, `SamplerPubResult`, `BitArray`, and `DataBin`.

Use this when you want a clear framework check:

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

draw_quantum_circuit(circuit, config=DrawConfig(framework="qiskit"))
```

If the object is not a Qiskit circuit, the call raises `UnsupportedFrameworkError`.

## Cirq

Install:

```bash
python -m pip install "quantum-circuit-drawer[cirq]"
```

Typical input:

- `cirq.Circuit`

Example:

```python
import cirq

from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

q0, q1 = cirq.LineQubit.range(2)
circuit = cirq.Circuit(
    cirq.H(q0),
    cirq.CNOT(q0, q1),
    cirq.measure(q1, key="m"),
)

draw_quantum_circuit(circuit, config=DrawConfig(framework="cirq"))
```

Current support includes common gates, controlled gates, classically controlled operations, `CircuitOperation`, swap, and measurements.

The Cirq path now preserves moment grouping and `CircuitOperation` provenance internally. When a native structure does not have one perfect common visual shape, the drawer keeps that detail in compare signatures, diagnostics, hover text, or lightweight annotations instead of dropping it silently.

Histogram support also accepts `cirq.Result` / `cirq.ResultDict` objects through their `measurements` mapping. If several measurement keys are present, `plot_histogram(...)` keeps them as space-separated registers in the visible state labels.

Use `DrawConfig(composite_mode="expand")` when you want supported `CircuitOperation` contents to appear as separate operations.

On native Windows, Cirq imports and teardown can still be limited by upstream SciPy/HiGHS behavior. The bundled demos reduce exact-matrix work by default there, but WSL or Linux remains the more reliable option for repeated demo runs.

## PennyLane

Install:

```bash
python -m pip install "quantum-circuit-drawer[pennylane]"
```

Typical inputs:

- `qml.tape.QuantumTape`
- `qml.tape.QuantumScript`
- wrappers exposing a materialized `.qtape`, `.tape`, or `._tape`

Example:

```python
import pennylane as qml

from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

with qml.tape.QuantumTape() as tape:
    qml.Hadamard(wires=0)
    qml.CNOT(wires=[0, 1])
    qml.probs(wires=[1])

draw_quantum_circuit(tape, config=DrawConfig(framework="pennylane"))
```

Current support includes tape-like objects, mid-circuit measurements, `qml.cond(...)` classical conditions, and optional expansion for decomposable composite operations such as `QFT`.

The PennyLane path now preserves conditional provenance, decomposition origin, and safe wrapper semantics internally. When a PennyLane-native construct cannot be shown as one exact shared visual primitive, the drawer keeps the native meaning in compare signatures, hover, annotations, or diagnostics.

For QNode-like wrappers, the adapter only reads an already-materialized tape. It does not call `construct()` or trigger lazy wrapper properties on your behalf.

Histogram support also accepts direct execution outputs from `qml.counts()`, `qml.probs()`, and `qml.sample()`. If a QNode returns several payloads, pass the full tuple or list and use `HistogramConfig(result_index=...)` to choose which one to plot.

On native Windows, PennyLane can still be limited by upstream SciPy/HiGHS behavior. The bundled demos reduce exact-matrix work by default there, but WSL or Linux remains the more reliable option for repeated demo runs.

## MyQLM

Install:

```bash
python -m pip install "quantum-circuit-drawer[myqlm]"
```

Typical input:

- `qat.core.Circuit`

Recommended workflow:

1. Build with `Program()`.
2. Export with `to_circ()`.
3. Draw the resulting circuit.

Example:

```python
from qat.lang.AQASM import CNOT, H, Program

from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

program = Program()
qbits = program.qalloc(2)

H(qbits[0])
CNOT(qbits[0], qbits[1])

circuit = program.to_circ()
draw_quantum_circuit(circuit, config=DrawConfig(framework="myqlm"))
```

Current support includes common gates, controlled gates backed by gate definitions, measurements, quantum resets, simple single-bit classical control, and compact or expanded composite gates backed by `gateDic`.

Histogram support also accepts `qat.core.Result` objects through their `raw_data` samples, so finite-shot counts and simulator probabilities can be plotted without manually rebuilding a dictionary.

Support note:

- MyQLM is currently a scoped adapter + contract support path rather than a first-class multiplatform CI backend.
- MyQLM remains on the legacy adapter path for now; future semantic migrations can build on the shared pipeline later without widening the current supported subset yet.

Current limits:

- `Program` and `QRoutine` objects are not the main adapter input; convert with `to_circ()` first.
- Advanced classical formulas, `BREAK`, `CLASSIC`, and `REMAP` operations are not rendered yet.
- MyQLM is installed from the upstream package under its own EULA terms.

See [Troubleshooting](troubleshooting.md#myqlm-program-objects-do-not-draw-directly) if a MyQLM object is not detected.

## CUDA-Q

Install on Linux or WSL2:

```bash
python -m pip install "quantum-circuit-drawer[cudaq]"
```

Typical input:

- a closed CUDA-Q kernel

Example:

```python
import cudaq

from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit


@cudaq.kernel
def bell_pair() -> None:
    qubits = cudaq.qvector(2)
    h(qubits[0])
    x.ctrl(qubits[0], qubits[1])
    mz(qubits)


draw_quantum_circuit(bell_pair)
```

Here, "closed" means the kernel can be inspected without additional runtime arguments.

Current limits:

- CUDA-Q support is Linux/WSL2-first and is not intended for native Windows installs.
- Kernels that still require runtime arguments are not supported.
- Advanced CUDA-Q control flow and broader advanced constructs are outside the supported subset.
- CUDA-Q also remains on the legacy adapter path in this phase while the shared semantic pipeline is being consolidated for future backend migrations.

Histogram support also accepts CUDA-Q `SampleResult`-style objects that expose count pairs through `items()`, so `cudaq.sample(...)` outputs can be passed straight into `plot_histogram(...)`.

See [Troubleshooting](troubleshooting.md#cuda-q-kernels-with-arguments-do-not-draw) for the most common CUDA-Q issue.

## Internal IR

The internal IR path is useful when:

- your framework is not directly supported
- you want full control over the circuit structure before rendering
- you want to build an adapter or preprocessing step in your own code

If you want to add a reusable third-party input path instead of building IR inline every time, see [Extension API](extensions.md).

Import the IR types from `quantum_circuit_drawer.ir`.

Example:

```python
from quantum_circuit_drawer import draw_quantum_circuit
from quantum_circuit_drawer.ir import (
    ClassicalConditionIR,
    CircuitIR,
    LayerIR,
    MeasurementIR,
    OperationIR,
    OperationKind,
    WireIR,
    WireKind,
)

ir = CircuitIR(
    quantum_wires=[
        WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
        WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
    ],
    classical_wires=[
        WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0"),
    ],
    layers=[
        LayerIR(
            operations=[
                OperationIR(
                    kind=OperationKind.GATE,
                    name="H",
                    target_wires=["q0"],
                )
            ]
        ),
        LayerIR(
            operations=[
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name="X",
                    control_wires=["q0"],
                    target_wires=["q1"],
                    classical_conditions=[
                        ClassicalConditionIR(
                            wire_ids=["c0"],
                            expression="if c[0]=1",
                        )
                    ],
                )
            ]
        ),
        LayerIR(
            operations=[
                MeasurementIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=["q1"],
                    classical_target="c0",
                )
            ]
        ),
    ],
    name="bell_pair_ir",
)

draw_quantum_circuit(ir, config=DrawConfig(show=False))
```

Useful IR rules:

- Wire ids must be unique across quantum and classical wires.
- Classical conditions reference classical wire ids through `ClassicalConditionIR`.
- Measurements require a `classical_target`.
- Non-barrier operations need at least one target wire.

If you already built a `CircuitIR`, autodetection is enough. You can also pass `DrawConfig(framework="ir")` when you want the intent to be explicit.

## Choosing the IR path

Choose the IR path when adapting your own circuit model is easier than waiting for native framework support.

For common rendering tasks, continue with [Recipes](recipes.md). For exact API behavior, see [API reference](api.md).
