# Frameworks

This guide explains how `quantum-circuit-drawer` behaves across the supported input paths.

In the common case, your call still looks the same:

```python
from quantum_circuit_drawer import draw_quantum_circuit

draw_quantum_circuit(circuit)
```

Set `DrawConfig.side.render.framework` only when you want to be explicit or when a wrapper object makes autodetection ambiguous.

## Overview

The current user-facing input paths are:

| Input path | Typical object | Extra |
| --- | --- | --- |
| Qiskit | `qiskit.QuantumCircuit` | `qiskit` |
| Cirq | `cirq.Circuit` | `cirq` |
| PennyLane | `QuantumTape`, `QuantumScript`, or tape-like wrappers | `pennylane` |
| MyQLM | `qat.core.Circuit` | `myqlm` |
| CUDA-Q | closed CUDA-Q kernels | `cudaq` |
| Internal IR | `CircuitIR` | none |

Across those paths, the drawer now uses a shared internal flow that can host both adapter styles: framework object -> semantic IR -> render IR for richer adapters, or framework object -> `CircuitIR` for legacy adapters. That lets comparison, diagnostics, hover, and annotations preserve framework-native details longer where native adapters exist, without breaking narrower legacy adapters that still emit `CircuitIR` directly.

All built-in framework adapters now use the richer semantic adapter path. The legacy `to_ir(...)` route remains a supported extension point for narrower adapters and third-party integrations.

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

`plot_histogram(...)` also accepts several framework-native result payloads directly:

- Qiskit counts and quasi-distributions, plus sampler result containers
- Cirq `Result` / `ResultDict` measurement payloads
- PennyLane `qml.counts()` dictionaries, `qml.probs()` vectors, and `qml.sample()` arrays
- MyQLM `qat.core.Result` objects with `raw_data`
- CUDA-Q `SampleResult`-style count containers

When a framework returns several measurement outputs at once, pass the tuple or list directly and select one entry with `HistogramConfig(data=HistogramDataOptions(result_index=...))`.

## Choosing Between Native Frameworks And IR

Use a native adapter when:

- you already have a framework circuit object
- you want native autodetection
- you want framework-specific semantics to survive longer through hover, diagnostics, or comparison

Use the public IR path when:

- your source is not one of the built-in frameworks
- you want complete structural control
- you are building a custom preprocessor or adapter
- you want a framework-free workflow in tests or tooling

Use `CircuitBuilder` when you want a lightweight middle ground for small or generated circuits.

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

Current support includes common gates, controlled gates including open-control states from `ctrl_state`, classical `if` conditions including modern Qiskit expression trees when they can be normalized safely, compact native boxes for `if_else`, `switch_case`, `for_loop`, and `while_loop`, composite instructions, swap, barriers, and measurements.

For Qiskit control-flow, the drawer keeps the expanded behavior for simple `if_test(...)` blocks without an `else` when the condition can still be normalized into exact classical conditions. If a simple `if_test(...)` uses a modern condition shape that cannot be normalized safely, it falls back to a compact `IF` box with native hover details instead of failing.

Richer control-flow such as `if_else` with an `else`, `switch_case`, `for_loop`, and `while_loop` is intentionally rendered as compact boxes with hover details instead of pretending that branches were executed or loops were unrolled.

Bundled demos:

- `qiskit-2d-exploration-showcase` is the best first demo for managed 2D exploration, active-wire filtering, ancilla toggles, folded-wire markers, and contextual block controls on the strongest semantic adapter path.
- `qiskit-control-flow-showcase` is the best first demo for compact native control-flow boxes and open controls.
- `qiskit-composite-modes-showcase` is the best focused demo for compact versus expanded composite instructions.
- `qiskit-random` and `qiskit-qaoa` are the broad stress-test demos when you want denser scenes or topology-aware 3D renders.

Histogram support also accepts direct Qiskit result payloads such as `Counts`, `QuasiDistribution`, `SamplerResult`, `PrimitiveResult`, `SamplerPubResult`, `BitArray`, and `DataBin`.

## Cirq

Install:

```bash
python -m pip install "quantum-circuit-drawer[cirq]"
```

Typical input:

- `cirq.Circuit`

Example:

```python
from cirq.circuits import Circuit, Moment
from cirq.devices import LineQubit
from cirq.ops import CNOT, H, measure

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    draw_quantum_circuit,
)

q0, q1 = LineQubit.range(2)
circuit = Circuit(
    Moment(H(q0)),
    Moment(CNOT(q0, q1)),
    Moment(measure(q1, key="m")),
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(framework="cirq")),
    ),
)
```

Current support includes common gates, controlled gates including open controls when Cirq exposes singleton binary `control_values`, classically controlled operations with safe hover fallback for non-normalizable conditions, `CircuitOperation`, swap, measurements, and native tags preserved in hover metadata.

The Cirq path now preserves moment grouping and `CircuitOperation` provenance internally. It also preserves indexed `KeyCondition` details such as `m[0]=0` when Cirq exposes them, keeps non-trivial native `control_values` in hover text when they cannot be shown as plain open/closed markers, and keeps tags or non-normalizable classical conditions as compact hover annotations instead of dropping them silently.

Bundled demos:

- `cirq-native-controls-showcase` is the best first demo for open controls, classical control, and `CircuitOperation` provenance.
- `cirq-random` and `cirq-qaoa` remain useful when you want larger or denser Cirq scenes.

Histogram support also accepts `cirq.Result` / `cirq.ResultDict` objects through their `measurements` mapping. If several measurement keys are present, `plot_histogram(...)` keeps them as space-separated registers in the visible state labels.

Use `CircuitRenderOptions(composite_mode="expand")` inside `DrawConfig.side.render` when you want supported `CircuitOperation` contents to appear as separate operations.

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
from pennylane.measurements import ProbabilityMP
from pennylane.ops import CNOT, Hadamard
from pennylane.tape import QuantumTape

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    draw_quantum_circuit,
)

with QuantumTape() as tape:
    Hadamard(wires=0)
    CNOT(wires=[0, 1])
    ProbabilityMP(wires=[1])

draw_quantum_circuit(
    tape,
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(framework="pennylane")),
    ),
)
```

Current support includes tape-like objects, mid-circuit measurements, `qml.cond(...)` classical conditions, controlled operations with explicit `control_values` when PennyLane exposes them, optional expansion for decomposable composite operations such as `QFT`, and compact terminal-output boxes for `qml.expval()`, `qml.var()`, `qml.probs()`, `qml.sample()`, `qml.counts()`, `qml.state()`, and `qml.density_matrix()`.

Those terminal results are intentionally not drawn as fake projective `M` measurements. Mid-circuit `qml.measure(...)` still appears as a measurement, while terminal results are rendered as compact output boxes across the affected wires and keep their observable or wire-scope details in hover metadata.

Composite observables such as `Tensor` / `Prod`, `SProd`, and Hamiltonian-like linear combinations now keep readable compact summaries with deterministic truncation and deterministic class-based or native-type fallback labels instead of a vague generic box name.

For QNode-like wrappers, the adapter only reads an already-materialized tape. It does not call `construct()` or trigger lazy wrapper properties on your behalf.

Bundled demos:

- `pennylane-terminal-outputs-showcase` is the best first demo for `qml.measure(...)`, `qml.cond(...)`, and compact output boxes.
- `pennylane-random` and `pennylane-qaoa` remain useful when you want broader layout stress tests.

Histogram support also accepts direct execution outputs from `qml.counts()`, `qml.probs()`, and `qml.sample()`. If a QNode returns several payloads, pass the full tuple or list and use `HistogramConfig(data=HistogramDataOptions(result_index=...))` to choose which one to plot.

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

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    draw_quantum_circuit,
)

program = Program()
qbits = program.qalloc(2)

H(qbits[0])
CNOT(qbits[0], qbits[1])

circuit = program.to_circ()
draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(framework="myqlm")),
    ),
)
```

Current support includes common gates, controlled gates backed by gate definitions, measurements, quantum resets, compact or expanded composite gates backed by `gateDic`, compact `REMAP` boxes, compact composites that use ancillas, drawable `BREAK` / `CLASSIC` classical boxes on the bundled classical register, and classical-control conditions that can be expressed cleanly from MyQLM control bits or formulas. Qubit-targeted quantum resets keep drawing even when MyQLM attaches extra classical metadata, with those raw classical details preserved in hover instead of raising.

Support note:

- MyQLM is currently a scoped adapter + contract support path rather than a first-class multiplatform CI backend.
- MyQLM now preserves gate provenance, composite provenance, decomposition origin, and supported classical-control expressions through the shared semantic adapter pipeline.

Bundled demos:

- `myqlm-structural-showcase` is the best first demo for compact composite routines on the native MyQLM adapter path.
- `myqlm-random` remains the broader stress-test demo.

Current limits:

- `Program` and `QRoutine` objects are not the main adapter input; convert with `to_circ()` first.
- `BREAK` and `CLASSIC` now render as compact classical boxes on the classical register, keeping formulas and native details in hover; when a formula cannot be normalized safely, the raw native formula is preserved instead of raising.
- `REMAP` and ancilla-using composites are rendered as compact annotated boxes rather than expanded internal structure.
- classical-only resets without qubit targets still remain outside the supported subset.
- MyQLM is installed from the upstream package under its own EULA terms.

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

Support note:

- Supported closed-kernel parsing now preserves Quake provenance, measurement basis, reset operations, structured control-flow boxes, value-form wire flow, and compact callable blocks for `apply`, `adjoint`, and `compute_action` through the shared semantic adapter pipeline.

Bundled demos:

- `cudaq-kernel-showcase` is the best first demo for the currently supported closed-kernel subset.
- `cudaq-random` remains the broader stress-test demo on Linux or WSL2.

Current limits:

- CUDA-Q support is Linux/WSL2-first and is not intended for native Windows installs.
- Kernels that still require runtime arguments are not supported.
- Structured `cc.if`, `scf.if`, `scf.for`, and `cc.loop` now render as compact descriptive boxes with hover details instead of being expanded.
- Low-level CFG control flow such as `cf.cond_br` and broader advanced constructs are still outside the supported subset.
- `apply`, `compute_action`, and `adjoint` are currently rendered as compact callable boxes with hover details rather than expanded internal structure.
- Controlled `swap` now renders as a compact controlled `SWAP` box, while unresolved dynamic qvector sizes are still rejected because they do not map cleanly into the current shared IR.

Histogram support also accepts CUDA-Q `SampleResult`-style objects that expose count pairs through `items()`, so `cudaq.sample(...)` outputs can be passed straight into `plot_histogram(...)`.

## Internal IR

The internal IR path is useful when:

- your framework is not directly supported
- you want full control over the circuit structure before rendering
- you want to build an adapter or preprocessing step in your own code

If you want to add a reusable third-party input path instead of building IR inline every time, see [Extension API](extensions.md).

Import the IR types from `quantum_circuit_drawer.ir`.

Example:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit
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
                    target_wires=("q0",),
                )
            ]
        ),
        LayerIR(
            operations=[
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name="X",
                    control_wires=("q0",),
                    target_wires=("q1",),
                    classical_conditions=(
                        ClassicalConditionIR(
                            wire_ids=("c0",),
                            expression="if c[0]=1",
                        ),
                    ),
                )
            ]
        ),
        LayerIR(
            operations=[
                MeasurementIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=("q1",),
                    classical_target="c0",
                )
            ]
        ),
    ],
    name="bell_pair_ir",
)

draw_quantum_circuit(ir, config=DrawConfig(output=OutputOptions(show=False)))
```

Useful IR rules:

- wire ids must be unique across quantum and classical wires
- classical conditions reference classical wire ids through `ClassicalConditionIR`
- measurements require a `classical_target`
- non-barrier operations need at least one target wire
- controlled operations can optionally set `control_values`; when omitted, controls default to standard closed-on-`1`

Bundled demo:

- `ir-basic-workflow` is the best first demo for a framework-free workflow built directly from the public `CircuitIR` types.
