# API reference

## Main function

```python
draw_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult
```

This is the only public entry point for drawing.

## `DrawConfig`

`DrawConfig` groups the public options in one stable object:

```python
DrawConfig(
    framework=None,
    backend="matplotlib",
    layout=None,
    view="2d",
    mode=DrawMode.AUTO,
    composite_mode="compact",
    topology="line",
    topology_menu=False,
    direct=True,
    show=True,
    output_path=None,
    figsize=None,
    style=None,
    hover=False,
)
```

### Field order

The fields are ordered by responsibility:

1. framework and backend
2. layout and view
3. mode selection
4. 3D topology options
5. display and saving
6. style and hover

### Important fields

- `view`: `"2d"` or `"3d"`
- `mode`: `DrawMode.AUTO`, `PAGES`, `PAGES_CONTROLS`, `SLIDER`, or `FULL`
- `topology`: only used in 3D
- `topology_menu`: managed interactive 3D topology selector
- `show`: whether the library should show the figure
- `output_path`: optional file path for saving
- `figsize`: managed figure size in inches
- `style`: `DrawStyle`, mapping, or `None`
- `hover`: `bool`, `HoverOptions`, mapping, or `None`

## `DrawMode`

- `AUTO`
  - notebook: `pages`
  - normal script: `pages_controls`
- `PAGES`
  - 2D: one managed figure per page
  - 3D: one managed figure per page window
- `PAGES_CONTROLS`
  - 2D: managed `Page` / `Visible` controls
  - 3D: managed `Page` / `Visible` controls with vertically stacked 3D pages
- `SLIDER`
  - 2D: discrete horizontal / vertical slider navigation
  - 3D: horizontal slider navigation
- `FULL`
  - full unpaged render

## `DrawResult`

`draw_quantum_circuit(...)` always returns `DrawResult`.

Fields:

- `primary_figure`
- `primary_axes`
- `figures`
- `axes`
- `mode`
- `page_count`

Examples:

- simple managed render: one figure and one axes
- `pages` in a notebook: several figures, one per page
- caller-managed `ax=...`: one figure and one axes, wrapped in `DrawResult`

## `ax`

`ax` is reserved for static rendering paths:

- allowed with `pages` and `full`
- not allowed with `pages_controls` or `slider`

When `ax` is provided:

- 2D `pages` draws the static paged composition in that axes
- 3D requires a 3D Matplotlib axes

## Style and theme

`DrawStyle` controls geometry and line widths. The main stroke families are:

- `wire_line_width`
- `classical_wire_line_width`
- `gate_edge_line_width`
- `barrier_line_width`
- `measurement_line_width`
- `connection_line_width`
- `topology_edge_line_width`

`DrawTheme` controls colors for:

- figure and axes backgrounds
- text
- quantum and classical wires
- gates and measurements
- controls and control connections
- topology edges and topology planes
- hover labels
- managed UI widgets

## Hover

`HoverOptions` stays public and is always nested under `DrawConfig.hover`.

```python
DrawConfig(
    hover={
        "enabled": True,
        "show_size": True,
        "show_matrix": "auto",
        "matrix_max_qubits": 2,
    }
)
```

## Examples

### Minimal managed draw

```python
result = draw_quantum_circuit(circuit, config=DrawConfig(show=False))
```

### 2D managed page viewer

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.PAGES_CONTROLS),
)
```

### 3D slider

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode=DrawMode.SLIDER,
        topology="grid",
        show=False,
    ),
)
```

### Full unpaged render

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(mode=DrawMode.FULL, show=False),
)
```
