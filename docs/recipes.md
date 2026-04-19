# Recipes

## Notebook: one figure per page

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.PAGES, show=False),
)

for figure in result.figures:
    display(figure)
```

## Script: managed page viewer

```python
from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit

draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.PAGES_CONTROLS),
)
```

## Save a clean paged export

```python
draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        mode=DrawMode.PAGES_CONTROLS,
        output_path="circuit.png",
        show=False,
    ),
)
```

## Draw inside your own Matplotlib axes

```python
fig, ax = plt.subplots()

draw_quantum_circuit(
    circuit,
    ax=ax,
    config=DrawConfig(mode=DrawMode.PAGES),
)
```

## 2D slider

```python
draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        mode=DrawMode.SLIDER,
        show=True,
    ),
)
```

## 3D slider

```python
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

## 3D page viewer with topology selector

```python
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

## Full unpaged render

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.FULL, show=False),
)
```

## Custom widths and hover

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        style={
            "wire_line_width": 1.8,
            "classical_wire_line_width": 1.5,
            "gate_edge_line_width": 1.7,
            "measurement_line_width": 1.3,
            "connection_line_width": 1.9,
        },
        hover={
            "enabled": True,
            "show_size": True,
            "show_matrix": "auto",
        },
        show=False,
    ),
)
```

## Custom theme object

```python
from quantum_circuit_drawer import DrawConfig, DrawTheme, draw_quantum_circuit

theme = DrawTheme(
    name="custom",
    figure_facecolor="#ffffff",
    axes_facecolor="#ffffff",
    wire_color="#1f2933",
    classical_wire_color="#52606d",
    gate_facecolor="#f8fafc",
    gate_edgecolor="#0f172a",
    measurement_facecolor="#e2eef9",
    text_color="#0f172a",
    barrier_color="#94a3b8",
    measurement_color="#0f172a",
    accent_color="#0f766e",
    control_color="#0f172a",
    control_connection_color="#0f766e",
    topology_edge_color="#b45309",
    topology_plane_color="#0f766e",
)

draw_quantum_circuit(
    circuit,
    config=DrawConfig(style={"theme": theme}, show=False),
)
```
