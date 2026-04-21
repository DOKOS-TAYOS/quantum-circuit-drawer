<p align="center">
  <img
    src="https://raw.githubusercontent.com/DOKOS-TAYOS/quantum-circuit-drawer/main/docs/images/Quantum_Circuit_Drawer_logo.png"
    alt="Quantum Circuit Drawer logo"
    width="560"
  />
</p>

# quantum-circuit-drawer

`quantum-circuit-drawer` draws quantum circuits from several ecosystems with one Matplotlib-based API.

The public API is now centered on two workflows:

- `DrawConfig`: one ordered configuration object for view, mode, saving, style, and hover
- `DrawResult`: one consistent return object for managed figures, caller-owned axes, 2D, and 3D
- `HistogramConfig`: configuration for counts, quasi-probabilities, and marginals
- `HistogramResult`: one stable return object for histogram figures and normalized values

## Install

Inside your virtual environment:

```bash
python -m pip install quantum-circuit-drawer
```

For framework extras:

```bash
python -m pip install "quantum-circuit-drawer[qiskit]"
python -m pip install "quantum-circuit-drawer[cirq]"
python -m pip install "quantum-circuit-drawer[pennylane]"
python -m pip install "quantum-circuit-drawer[myqlm]"
```

## Basic usage

```python
from qiskit import QuantumCircuit

from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

circuit = QuantumCircuit(2, 1)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure(1, 0)

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(show=False),
)

figure = result.primary_figure
axes = result.primary_axes
```

## Histogram from counts

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

result = plot_histogram(
    {"000": 51, "001": 14, "010": 9, "111": 49},
    config=HistogramConfig(
        sort="value_desc",
        top_k=3,
        show_uniform_reference=True,
        show=False,
    ),
)
```

## Histogram from quasi-probabilities

```python
from quantum_circuit_drawer import HistogramConfig, HistogramKind, plot_histogram

result = plot_histogram(
    {0: 0.52, 3: -0.08, 4: 0.17, 7: 0.39},
    config=HistogramConfig(
        kind=HistogramKind.QUASI,
        draw_style="soft",
        show_uniform_reference=True,
        show=False,
    ),
)
```

## Joint marginal over selected qubits

```python
from quantum_circuit_drawer import HistogramConfig, plot_histogram

result = plot_histogram(
    {"101": 2, "001": 1, "111": 3},
    config=HistogramConfig(qubits=(0, 2), show=False),
)
```

`qubits=(0, 2)` keeps the requested order, so the marginal labels are built as `q0` followed by `q2`.

Histogram plots also accept `theme="dark" | "light" | "paper"` so the default look now matches the circuit drawer theme family.

## Interactive histogram mode

```python
from quantum_circuit_drawer import HistogramConfig, HistogramMode, plot_histogram

result = plot_histogram(
    {format(index, "07b"): ((index * 17) % 41) + ((index * 5) % 13) + 3 for index in range(2**7)},
    config=HistogramConfig(
        mode=HistogramMode.INTERACTIVE,
        show_uniform_reference=True,
        show=False,
    ),
)
```

Interactive histogram mode adds a slider viewport, hover labels per bin, a cyclic order button, a slider toggle button, and a marginal-qubits text box such as `0,2,5`.

## Modes

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.PAGES_CONTROLS, show=True),
)
```

Available modes:

- `DrawMode.AUTO`: notebooks default to `pages`; normal `.py` runs default to `pages_controls`
- `DrawMode.PAGES`: one figure per page when the library owns the figure
- `DrawMode.PAGES_CONTROLS`: managed `Page` / `Visible` controls
- `DrawMode.SLIDER`: discrete slider navigation
- `DrawMode.FULL`: full unpaged scene

Notes:

- In 2D, `pages` with `ax=...` renders the static paged composition into that axes.
- In 3D, `pages`, `pages_controls`, `slider`, and `full` are all supported.
- Interactive modes require a library-managed figure, so do not combine them with `ax=...`.

## 3D example

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode=DrawMode.PAGES_CONTROLS,
        topology="grid",
        topology_menu=True,
        show=False,
    ),
)
```

## Saving

```python
draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        mode=DrawMode.SLIDER,
        output_path="circuit.png",
        show=False,
    ),
)
```

Interactive modes save a clean figure without widgets. Paged modes save the concatenated paged composition. `full` saves the full unpaged view.

## Styling

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        style={
            "theme": "paper",
            "max_page_width": 10.0,
            "wire_line_width": 1.8,
            "measurement_line_width": 1.4,
            "connection_line_width": 1.9,
        },
        hover={"enabled": True, "show_size": True},
        show=False,
    ),
)
```

`DrawTheme` now also covers the managed UI colors, hover colors, control colors, control-connection colors, and topology colors.

## Documentation

- [API reference](docs/api.md)
- [User guide](docs/user-guide.md)
- [Recipes](docs/recipes.md)
- [Examples](examples/README.md)
- [Changelog](CHANGELOG.md)
