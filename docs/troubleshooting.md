# Troubleshooting

This page is organized by symptom so you can get to the likely fix quickly.

## Optional framework import fails

Typical symptoms:

- `UnsupportedFrameworkError`
- `ImportError` for `qiskit`, `cirq`, `pennylane`, `qat`, or `cudaq`

Quick fix: install the extra for the framework you are using.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[qiskit]"
```

Replace `qiskit` with `cirq`, `pennylane`, or `myqlm` as needed. Keep CUDA-Q installs on Linux or WSL2 only.

Good first smoke demos after installing an extra:

- `qiskit-control-flow-showcase`
- `cirq-native-controls-showcase`
- `pennylane-terminal-outputs-showcase`
- `myqlm-structural-showcase`
- `cudaq-kernel-showcase` on Linux or WSL2

## Support matrix

Use this table to decide whether the issue is on the main support path or on a narrower compatibility path.

| Input path | Support level | Platform notes |
| --- | --- | --- |
| Internal IR | Strong support | Core built-in path on Windows and Linux |
| Qiskit | Strong support | Primary external backend on Windows and Linux |
| Cirq | Best-effort on native Windows | Linux or WSL remains the safer production path |
| PennyLane | Best-effort on native Windows | Linux or WSL remains the safer production path |
| MyQLM | Scoped adapter + contract support | Adapter contract is covered, but it is not a first-class multiplatform CI backend |
| CUDA-Q | Linux/WSL2 only | Not intended for native Windows installs |

At the moment, all built-in framework adapters use the richer semantic-adapter path internally. Legacy `to_ir(...)` adapters still work, but framework-native provenance and annotations now survive longer for the built-in adapters before lowering to the shared render IR.

## Cirq Or PennyLane Demos Are Slow Or Unstable On Native Windows

On native Windows, Cirq and PennyLane can still hit upstream SciPy/HiGHS issues during import or shutdown. This project now skips eager exact-matrix extraction for those demo paths by default on Windows, so startup should be lighter than before, but the underlying framework instability can still appear.

Try this first:

- rerun the same demo in WSL or Linux if you need the most reliable behavior
- on native Windows, keep the default hover-matrix mode (`auto`) or use `never` for the lightest path
- only use `--hover-matrix always` when you really need exact framework matrices in the tooltip

For PennyLane wrappers and QNode-like objects:

- pass a `QuantumTape` / `QuantumScript` directly when possible
- wrapper objects are supported only when they already expose a materialized `.qtape`, `.tape`, or `._tape`
- the adapter does not call `construct()` or trigger lazy wrapper properties implicitly
- terminal PennyLane results such as `expval`, `var`, `probs`, `sample`, `counts`, `state`, and `density_matrix` now draw as compact output boxes instead of fake projective `M` measurements
- mid-circuit `qml.measure(...)` still draws as a measurement, while terminal-result boxes keep observable or wire-scope details in hover metadata
- composite PennyLane observables such as `Tensor` / `Prod`, `SProd`, and Hamiltonian-like linear combinations now keep readable compact summaries with deterministic truncation and deterministic fallback labels instead of a vague generic box name

If you just want to sanity-check the current support quickly, start with `cirq-native-controls-showcase` or `pennylane-terminal-outputs-showcase` and only then move on to the broader `random` demos.

## CUDA-Q Does Not Install On Windows

CUDA-Q support is Linux/WSL2-first in this project. On native Windows, the optional dependency is not expected to install.

Recommended options:

- use WSL2 for CUDA-Q examples
- use Qiskit, Cirq, PennyLane, or MyQLM on native Windows
- keep CUDA-Q-specific demo commands on Linux or WSL2
- start with `cudaq-kernel-showcase` before trying the broader `cudaq-random` stress demo

## No Matplotlib Window Opens

If `show=True` does not open a window, the active Matplotlib backend may be non-interactive. This is common in notebooks, headless scripts, remote shells, and CI.

For scripts and automated exports, use:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

draw_quantum_circuit(circuit, config=DrawConfig(output=OutputOptions(show=False)))
```

For notebooks, let the notebook display the returned figure:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

result = draw_quantum_circuit(circuit, config=DrawConfig(output=OutputOptions(show=False)))
result.primary_figure
```

If the backend is interactive, `show=False` only skips the automatic `pyplot.show()` call. The returned figure can still keep hover and other Matplotlib interactivity.

## Hover Does Not Appear

Hover only works on interactive Matplotlib backends. In a notebook, the safest setup is:

```python
%matplotlib widget

from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(appearance=CircuitAppearanceOptions(hover=True)),
        output=OutputOptions(show=False),
    ),
)
result.primary_figure
```

If you are saving through `OutputOptions(output_path=...)` or running on a non-interactive backend such as `Agg`, the figure stays static and tooltips are intentionally disabled.

## Saving Output Fails

Typical symptom:

- `RenderingError`

Common causes:

- the output folder does not exist
- the file is open in another program
- you do not have permission to write to that path
- the extension is not supported by your Matplotlib installation

Try saving to a simple local path first:

```python
from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(output=OutputOptions(output_path="circuit.png", show=False)),
)
```

## `mode=DrawMode.SLIDER` Raises `ValueError`

`DrawMode.SLIDER` only works when the library manages the figure.

Do this:

```python
from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(mode=DrawMode.SLIDER),
            appearance=CircuitAppearanceOptions(style={"max_page_width": 4.0}),
        ),
    ),
)
```

Do not combine it with `ax=...`.

If you want a 3D slider, keep the figure managed and use a narrower page width when needed.

## `view="3d"` Raises An Axes Error

If you pass `ax=...` with `view="3d"`, the axes must already be a 3D Matplotlib axes.

Managed 3D path:

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    draw_quantum_circuit,
)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(side=DrawSideConfig(render=CircuitRenderOptions(view="3d"))),
)
```

Caller-managed 3D path:

```python
import matplotlib.pyplot as plt

from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    draw_quantum_circuit,
)

figure = plt.figure(figsize=(8, 5))
axes = figure.add_subplot(111, projection="3d")
draw_quantum_circuit(
    circuit,
    ax=axes,
    config=DrawConfig(side=DrawSideConfig(render=CircuitRenderOptions(view="3d"))),
)
```

## A 3D Topology Rejects The Qubit Count

Some 3D topologies have shape constraints:

| Topology | Constraint |
| --- | --- |
| `line` | Works for any number of qubits |
| `grid` | Needs an exact rectangular factorization with at least `2 x 2` |
| `star` | Needs at least 2 qubits |
| `star_tree` | Accepts sizes of the form `3 * 2^d - 2` |
| `honeycomb` | Currently targets a 53-qubit reference layout |

If a topology does not fit your circuit, start with:

```python
from quantum_circuit_drawer import (
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    draw_quantum_circuit,
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(view="3d", topology="line"),
        ),
    ),
)
```

## MyQLM `Program` Objects Do Not Draw Directly

The MyQLM adapter targets `qat.core.Circuit` inputs.

Use the usual MyQLM flow:

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

## CUDA-Q Kernels With Arguments Do Not Draw

CUDA-Q support currently targets closed kernels, meaning kernels that can be inspected without runtime arguments.

If your kernel needs arguments, create a closed wrapper or use a simpler example first:

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

For supported closed kernels, CUDA-Q now supports `reset`, measurement basis preservation, structured control flow (`cc.if`, `scf.if`, `scf.for`, `cc.loop`), controlled `swap` as a compact controlled `SWAP` box, and compact callable boxes for `apply`, `compute_action`, and `adjoint`. Those control-flow boxes are descriptive only, so the drawer does not execute branches or unroll loops for display.

Low-level CFG control flow and unresolved dynamic qvector sizes are still outside the supported subset.

## Style Validation Fails

Typical symptom:

- `StyleValidationError`

Common causes:

- a typo in a style key
- a non-positive numeric value for a size or spacing field
- an unknown theme name

Example:

```python
from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    DrawConfig,
    DrawSideConfig,
    draw_quantum_circuit,
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        side=DrawSideConfig(
            appearance=CircuitAppearanceOptions(
                style={"theme": "paper", "show_params": False},
            ),
        ),
    ),
)
```

See [API reference](api.md#style-and-theme) for the accepted public style surface.

## Unsupported Operations

Typical symptom:

- `UnsupportedOperationError`

This means the adapter found a framework operation that the renderer cannot represent clearly yet.

Useful first checks:

- try `CircuitRenderOptions(composite_mode="compact")` inside `DrawConfig.side.render` if expansion exposes unsupported internals
- try `CircuitRenderOptions(composite_mode="expand")` inside `DrawConfig.side.render` if a composite operation can be decomposed
- try `CircuitRenderOptions(unsupported_policy="placeholder")` inside `DrawConfig.side.render` when a best-effort visual is enough
- check [Frameworks](frameworks.md) for the supported subset of your framework
- if the operation is essential, consider building a `CircuitIR` representation for that case

Framework-specific notes:

- Qiskit now normalizes many modern classical expressions into readable ASCII conditions. If a simple `if_test(...)` condition still cannot be normalized safely, the drawer falls back to a compact `IF` box with native hover text instead of failing.
- open controls from Qiskit `ctrl_state`, Cirq singleton binary `control_values`, and PennyLane boolean or binary `control_values` now draw explicitly as open controls. Non-binary control patterns still degrade to a compact controlled-gate drawing with hover details instead of a fake exact symbol.
- Cirq classically controlled operations keep exact classical conditions only when every native condition can be normalized safely. Otherwise the drawer still renders the operation and keeps the native condition text in hover instead of failing.
- Cirq also keeps non-trivial native `control_values` and operation tags in hover details so tagged or richer controls remain inspectable.
- MyQLM now supports drawable classical formulas, compact `REMAP` boxes, compact ancilla-heavy composites with hover annotations, compact classical `BREAK` / `CLASSIC` boxes on the bundled classical register, and qubit-targeted `RESET` operations keep rendering as quantum resets even if MyQLM carries extra classical metadata. If a MyQLM classical formula cannot be normalized safely, the raw formula in hover instead of raising is preserved; classical-only reset metadata without qubit targets stays outside the supported subset.
- CUDA-Q now supports `reset`, structured control flow (`cc.if`, `scf.if`, `scf.for`, `cc.loop`), controlled `swap`, and compact callable boxes for `apply`, `compute_action`, and `adjoint` in the supported closed-kernel subset. Those control-flow boxes are descriptive only, so the drawer does not execute branches or unroll loops for display.
