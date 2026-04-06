# Frameworks

This guide explains how `quantum-circuit-drawer` works with each supported input path.

## Overview

The library currently supports these user-facing inputs:

- Qiskit circuits
- Cirq circuits
- PennyLane tape-like objects
- CUDA-Q closed kernels
- The internal `CircuitIR` representation

The most important practical idea is that you do not need to change your rendering workflow when the circuit source changes. In most cases, you still call `draw_quantum_circuit(...)` the same way.

## Qiskit

Install the `qiskit` extra as shown in [Installation](installation.md#install-optional-extras), using `quantum-circuit-drawer[qiskit]`.

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

## Cirq

Install the `cirq` extra as shown in [Installation](installation.md#install-optional-extras), using `quantum-circuit-drawer[cirq]`.

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

Explicit `framework="cirq"` is optional, but many users like it because it makes the code more readable.

Current support also includes `ClassicallyControlledOperation` and compact or expanded `CircuitOperation` rendering through `composite_mode`.

## PennyLane

Install the `pennylane` extra as shown in [Installation](installation.md#install-optional-extras), using `quantum-circuit-drawer[pennylane]`.

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

PennyLane support includes mid-circuit measurements, `qml.cond(...)` classical conditions, and optional expansion for decomposable composite operations such as `QFT`.

## CUDA-Q

Install the `cudaq` extra as shown in [Installation](installation.md#install-optional-extras), using `quantum-circuit-drawer[cudaq]` on Linux or WSL2.

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

Important limits:

- this extra is Linux/WSL2-first
- kernels that still require runtime arguments are not supported
- advanced CUDA-Q control flow and other advanced constructs are outside the supported subset

## Internal IR

The internal IR path is especially useful when:

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

Some useful IR rules to remember:

- wire ids must be unique across quantum and classical wires
- classical conditions reference classical wire ids through `ClassicalConditionIR`
- measurements require a `classical_target`
- non-barrier operations need at least one target wire

## When to choose the IR path

Use the IR path when adapting your own circuit model is easier than waiting for native framework support. It is the most practical advanced-user extension point in the current library.

## Next step

Use [Recipes](recipes.md) for concrete rendering tasks.
