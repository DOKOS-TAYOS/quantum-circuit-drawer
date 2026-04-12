# Frameworks

This guide explains how `quantum-circuit-drawer` works with each supported input path.

In most cases, the rendering call stays the same:

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(circuit)
```

Use `framework=...` when you want to be explicit or when a wrapper object makes autodetection unclear.

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

Install extras as shown in [Installation](installation.md#install-optional-framework-extras).

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

Use this when you want a clear framework check:

```python
draw_quantum_circuit(circuit, framework="qiskit")
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

from quantum_circuit_drawer import draw_quantum_circuit

q0, q1 = cirq.LineQubit.range(2)
circuit = cirq.Circuit(
    cirq.H(q0),
    cirq.CNOT(q0, q1),
    cirq.measure(q1, key="m"),
)

draw_quantum_circuit(circuit, framework="cirq")
```

Current support includes common gates, controlled gates, classically controlled operations, `CircuitOperation`, swap, and measurements.

Use `composite_mode="expand"` when you want supported `CircuitOperation` contents to appear as separate operations.

## PennyLane

Install:

```bash
python -m pip install "quantum-circuit-drawer[pennylane]"
```

Typical inputs:

- `qml.tape.QuantumTape`
- `qml.tape.QuantumScript`
- objects exposing `.qtape` or `.tape`

Example:

```python
import pennylane as qml

from quantum_circuit_drawer import draw_quantum_circuit

with qml.tape.QuantumTape() as tape:
    qml.Hadamard(wires=0)
    qml.CNOT(wires=[0, 1])
    qml.probs(wires=[1])

draw_quantum_circuit(tape, framework="pennylane")
```

Current support includes tape-like objects, mid-circuit measurements, `qml.cond(...)` classical conditions, and optional expansion for decomposable composite operations such as `QFT`.

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

from quantum_circuit_drawer import draw_quantum_circuit

program = Program()
qbits = program.qalloc(2)

H(qbits[0])
CNOT(qbits[0], qbits[1])

circuit = program.to_circ()
draw_quantum_circuit(circuit, framework="myqlm")
```

Current support includes common gates, controlled gates backed by gate definitions, measurements, quantum resets, simple single-bit classical control, and compact or expanded composite gates backed by `gateDic`.

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

from quantum_circuit_drawer import draw_quantum_circuit


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

See [Troubleshooting](troubleshooting.md#cuda-q-kernels-with-arguments-do-not-draw) for the most common CUDA-Q issue.

## Internal IR

The internal IR path is useful when:

- your framework is not directly supported
- you want full control over the circuit structure before rendering
- you want to build an adapter or preprocessing step in your own code

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

draw_quantum_circuit(ir, show=False)
```

Useful IR rules:

- Wire ids must be unique across quantum and classical wires.
- Classical conditions reference classical wire ids through `ClassicalConditionIR`.
- Measurements require a `classical_target`.
- Non-barrier operations need at least one target wire.

If you already built a `CircuitIR`, autodetection is enough. You can also pass `framework="ir"` when you want the intent to be explicit.

## Choosing the IR path

Choose the IR path when adapting your own circuit model is easier than waiting for native framework support.

For common rendering tasks, continue with [Recipes](recipes.md). For exact API behavior, see [API reference](api.md).
