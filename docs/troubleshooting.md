# Troubleshooting

This page lists common problems and the quickest fix to try first.

## Contents

- [Optional framework import fails](#optional-framework-import-fails)
- [Cirq or PennyLane demos are slow or unstable on native Windows](#cirq-or-pennylane-demos-are-slow-or-unstable-on-native-windows)
- [CUDA-Q does not install on Windows](#cuda-q-does-not-install-on-windows)
- [No Matplotlib window opens](#no-matplotlib-window-opens)
- [Saving output fails](#saving-output-fails)
- [`mode=DrawMode.SLIDER` raises `ValueError`](#modedrawmodeslider-raises-valueerror)
- [`view="3d"` raises an axes error](#view3d-raises-an-axes-error)
- [A 3D topology rejects the qubit count](#a-3d-topology-rejects-the-qubit-count)
- [MyQLM `Program` objects do not draw directly](#myqlm-program-objects-do-not-draw-directly)
- [CUDA-Q kernels with arguments do not draw](#cuda-q-kernels-with-arguments-do-not-draw)
- [Style validation fails](#style-validation-fails)
- [Unsupported operations](#unsupported-operations)

## Optional framework import fails

Symptom:

```text
UnsupportedFrameworkError
```

or an import error for `qiskit`, `cirq`, `pennylane`, `qat`, or `cudaq`.

Fix: install the extra for the framework you are using.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install "quantum-circuit-drawer[qiskit]"
```

Linux or WSL:

```bash
.venv/bin/python -m pip install "quantum-circuit-drawer[qiskit]"
```

Replace `qiskit` with `cirq`, `pennylane`, or `myqlm` as needed. Keep CUDA-Q installs on Linux or WSL2 only. See [Installation](installation.md#install-optional-framework-extras).

Good first smoke demos after installing an extra:

- `qiskit-control-flow-showcase`
- `cirq-native-controls-showcase`
- `pennylane-terminal-outputs-showcase`
- `myqlm-structural-showcase`
- `cudaq-kernel-showcase` on Linux or WSL2

## Support matrix

Use this table to decide whether an issue is inside the strong support path or on a narrower compatibility path.

| Input path | Support level | Platform notes |
| --- | --- | --- |
| Internal IR | Strong support | Core built-in path on Windows and Linux |
| Qiskit | Strong support | Primary external backend on Windows and Linux |
| Cirq | Best-effort on native Windows | Linux or WSL remains the safer production path |
| PennyLane | Best-effort on native Windows | Linux or WSL remains the safer production path |
| MyQLM | Scoped adapter + contract support | Adapter contract is covered, but it is not a first-class multiplatform CI backend |
| CUDA-Q | Linux/WSL2 only | Not intended for native Windows installs |

At the moment, all built-in framework adapters use the richer semantic-adapter path internally. Legacy `to_ir(...)` adapters still work, but framework-native provenance and annotations now survive longer for the built-in adapters before lowering to the shared render IR.

For Qiskit specifically, modern control-flow is preserved as compact native boxes instead of being flattened aggressively:

- simple `if_test(...)` blocks without an `else` still expand into classically conditioned gates when the condition can be normalized safely;
- non-normalizable simple `if_test(...)` blocks now fall back to a compact `IF` box with native hover details instead of failing;
- `if_else` with an `else`, `switch_case`, `for_loop`, and `while_loop` now render as compact boxes with hover details;
- those compact boxes are descriptive only, so the drawer does not execute branches or unroll loops for display.

For controlled gates across Qiskit, Cirq, and PennyLane:

- binary singleton control states now draw as real open/closed controls, so control-on-`0` no longer looks like control-on-`1`;
- hover details include the resolved control states for those simple binary cases;
- broader control-value sets that do not map cleanly to open/closed markers fall back to a compact controlled-gate drawing and keep the native control values in hover details instead of showing misleading symbols.

## Cirq or PennyLane demos are slow or unstable on native Windows

On native Windows, Cirq and PennyLane can still hit upstream SciPy/HiGHS issues during import or shutdown. This project now skips eager exact-matrix extraction for those demo paths by default on Windows, so startup should be lighter than before, but the underlying framework instability can still appear.

Try this first:

- Re-run the same demo in WSL or Linux if you need the most reliable behavior.
- On native Windows, keep the default hover-matrix mode (`auto`) or use `never` for the lightest path.
- Only use `--hover-matrix always` when you really need exact framework matrices in the tooltip.

For PennyLane wrappers and QNode-like objects:

- Pass a `QuantumTape` / `QuantumScript` directly when possible.
- Wrapper objects are supported only when they already expose a materialized `.qtape`, `.tape`, or `._tape`.
- The adapter does not call `construct()` or trigger lazy wrapper properties implicitly.
- Terminal PennyLane results such as `expval`, `var`, `probs`, `sample`, `counts`, `state`, and `density_matrix` now draw as compact output boxes instead of fake projective `M` measurements.
- Mid-circuit `qml.measure(...)` still draws as a measurement, while terminal-result boxes keep observable or wire-scope details in hover metadata.
- Composite PennyLane observables such as `Tensor` / `Prod`, `SProd`, and Hamiltonian-like linear combinations now keep readable compact summaries with deterministic truncation and deterministic fallback labels instead of a vague generic box name.
- Controlled PennyLane operations can now draw open controls when the tape exposes explicit binary `control_values`.
- When a Cirq or PennyLane-native construct has no exact shared drawing primitive, the library keeps that native meaning in hover details, annotations, comparison, or diagnostics instead of silently flattening it away.

If you just want to sanity-check the current support quickly, start with `cirq-native-controls-showcase` or `pennylane-terminal-outputs-showcase` and only then move on to the broader `random` demos.

## CUDA-Q does not install on Windows

CUDA-Q support is Linux/WSL2-first in this project. On native Windows, the optional dependency is not expected to install.

Recommended options:

- Use WSL2 for CUDA-Q examples.
- Use Qiskit, Cirq, PennyLane, or MyQLM on native Windows.
- Keep CUDA-Q-specific demo commands on Linux or WSL2.
- Start with `cudaq-kernel-showcase` before trying the broader `cudaq-random` stress demo.

## No Matplotlib window opens

If `show=True` does not open a window, the active Matplotlib backend may be non-interactive. This is common in notebooks, headless scripts, remote shells, and CI.

For scripts and automated exports, use:

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

draw_quantum_circuit(circuit, config=DrawConfig(show=False))
```

For notebooks, let the notebook display the returned figure:

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

result = draw_quantum_circuit(circuit, config=DrawConfig(show=False))
result.primary_figure
```

If the backend is interactive, `show=False` only skips the automatic `pyplot.show()` call. The returned figure can still keep hover and other Matplotlib interactivity.

## Hover does not appear

Hover only works on interactive Matplotlib backends. In a notebook, the safest setup is:

```python
%matplotlib widget

from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(hover=True, show=False),
)
result.primary_figure
```

If you are saving to `output_path=...` or running on a non-interactive backend such as `Agg`, the figure stays static and tooltips are intentionally disabled.

## Saving output fails

Symptom:

```text
RenderingError
```

Common causes:

- The output folder does not exist.
- The file is open in another program.
- You do not have permission to write to that path.
- The extension is not supported by your Matplotlib installation.

Try saving to a simple local path first:

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(output_path="circuit.png", show=False),
)
```

## `mode=DrawMode.SLIDER` raises `ValueError`

`DrawMode.SLIDER` only works when the library manages the figure.

Do this:

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        mode=DrawMode.SLIDER,
        style={"max_page_width": 4.0},
    ),
)
```

Do not combine it with `ax=...`:

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    ax=axes,
    config=DrawConfig(mode=DrawMode.SLIDER),
)
```

If you want a 3D column slider, keep the figure managed and use a smaller `max_page_width`, for example:

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode=DrawMode.SLIDER,
        style={"max_page_width": 4.0},
    ),
)
```

## `view="3d"` raises an axes error

If you pass `ax=...` with `view="3d"`, the axes must already be a 3D Matplotlib axes.

Managed 3D path:

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

result = draw_quantum_circuit(circuit, config=DrawConfig(view="3d"))
```

Caller-managed 3D path:

```python
import matplotlib.pyplot as plt

figure = plt.figure(figsize=(8, 5))
axes = figure.add_subplot(111, projection="3d")
draw_quantum_circuit(
    circuit,
    ax=axes,
    config=DrawConfig(view="3d"),
)
```

## A 3D topology rejects the qubit count

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
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(view="3d", topology="line"),
)
```

## MyQLM `Program` objects do not draw directly

The MyQLM adapter targets `qat.core.Circuit` inputs.

Use the usual MyQLM flow:

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

## CUDA-Q kernels with arguments do not draw

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

For supported closed kernels, the adapter now also preserves Quake provenance, measurement basis, `reset`, structured control flow (`cc.if`, `scf.if`, `scf.for`, `cc.loop`) as compact descriptive boxes, controlled `swap` as a compact controlled `SWAP` box, and compact callable boxes for `apply`, `compute_action`, and `adjoint` internally. Low-level CFG control flow and unresolved dynamic qvector sizes are still outside the supported subset.

## Style validation fails

Symptom:

```text
StyleValidationError
```

Common causes:

- A typo in a style key.
- A non-positive numeric value for a size or spacing field.
- An unknown theme name.

Example:

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(style={"theme": "paper", "show_params": False}),
)
```

See [API reference](api.md#styles-and-themes) for the accepted style fields.

## Unsupported operations

Symptom:

```text
UnsupportedOperationError
```

This means the adapter found a framework operation that the renderer cannot represent clearly yet.

Useful first checks:

- Try `DrawConfig(composite_mode="compact")` if expansion exposes unsupported internals.
- Try `DrawConfig(composite_mode="expand")` if a composite operation can be decomposed.
- Check [Frameworks](frameworks.md) for the supported subset of your framework.
- If the operation is essential, consider building a `CircuitIR` representation for that case.

Framework-specific notes:

- Qiskit now normalizes many modern classical expressions into readable ASCII conditions, and control-flow hover details preserve branch/body counts and case summaries when available. If a simple `if_test(...)` condition still cannot be normalized safely, the drawer falls back to a compact `IF` box with native hover text instead of failing.
- Open controls from Qiskit `ctrl_state`, Cirq singleton binary `control_values`, and PennyLane boolean/binary `control_values` now draw explicitly as open controls. Non-binary control patterns still degrade to a compact controlled-gate drawing with hover details instead of a fake exact symbol.
- Cirq classically controlled operations now keep exact `classical_conditions` only when every native condition can be normalized safely; otherwise the drawer still renders the operation and keeps the native condition text in hover instead of failing.
- Cirq now also keeps non-trivial native `control_values` and operation tags in hover details so that tagged or product-of-sums controls remain drawable and inspectable.
- MyQLM now supports drawable classical formulas, compact `REMAP` boxes, compact ancilla-heavy composites with hover annotations, compact classical `BREAK` / `CLASSIC` boxes on the bundled classical register, and qubit-targeted `RESET` operations keep rendering as quantum resets even if MyQLM carries extra classical metadata. If a MyQLM classical formula cannot be normalized safely, the drawer keeps the raw formula in hover instead of raising, while classical-only reset metadata without qubit targets stays outside the supported subset.
- CUDA-Q now supports `reset`, structured control flow (`cc.if`, `scf.if`, `scf.for`, `cc.loop`), controlled `swap`, and compact callable boxes for `apply`, `compute_action`, and `adjoint` in the supported closed-kernel subset. Those control-flow boxes are descriptive only, so the drawer does not execute branches or unroll loops for display. Low-level CFG control flow and unresolved dynamic qvector sizes are still rejected.
