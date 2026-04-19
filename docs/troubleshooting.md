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

Replace `qiskit` with `cirq`, `pennylane`, `myqlm`, or `cudaq` as needed. See [Installation](installation.md#install-optional-framework-extras).

## Cirq or PennyLane demos are slow or unstable on native Windows

On native Windows, Cirq and PennyLane can still hit upstream SciPy/HiGHS issues during import or shutdown. This project now skips eager exact-matrix extraction for those demo paths by default on Windows, so startup should be lighter than before, but the underlying framework instability can still appear.

Try this first:

- Re-run the same demo in WSL or Linux if you need the most reliable behavior.
- On native Windows, keep the default hover-matrix mode (`auto`) or use `never` for the lightest path.
- Only use `--hover-matrix always` when you really need exact framework matrices in the tooltip.

## CUDA-Q does not install on Windows

CUDA-Q support is Linux/WSL2-first in this project. On native Windows, the optional dependency is not expected to install.

Recommended options:

- Use WSL2 for CUDA-Q examples.
- Use Qiskit, Cirq, PennyLane, or MyQLM on native Windows.
- Keep CUDA-Q-specific demo commands on Linux or WSL2.

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
