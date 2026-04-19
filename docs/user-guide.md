# User guide

This guide focuses on how the new API behaves in practice.

## Think in three pieces

1. the circuit object
2. a `DrawConfig`
3. the returned `DrawResult`

```python
from quantum_circuit_drawer import DrawConfig, draw_quantum_circuit

result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(show=False),
)
```

## Auto mode

`DrawMode.AUTO` resolves by runtime context:

- real notebook: `pages`
- normal `.py` execution: `pages_controls`

Interactive modes in notebooks only stay interactive when Matplotlib is using a widget-like notebook backend such as `nbagg`, `ipympl`, or `widget`.

## Choose the rendering path

### `pages`

Use this when you want explicit pages:

- notebooks
- export workflows
- direct access to every page from `DrawResult.figures`

In managed 2D mode, the library creates one figure per page. In managed 3D mode, it creates one figure per 3D page window.

### `pages_controls`

Use this when you want a managed page browser:

- 2D: `Page` and `Visible`
- 3D: `Page` and `Visible`, with several visible 3D pages stacked vertically

This is the default for normal script execution.

### `slider`

Use this when you want to move through the circuit as a discrete viewport:

- 2D: horizontal and vertical sliders when needed
- 3D: horizontal slider only

### `full`

Use this when you want the whole circuit at once with no paging and no slider.

## Caller-managed axes

Pass `ax=...` only for static rendering:

```python
fig, ax = plt.subplots()
result = draw_quantum_circuit(circuit, ax=ax, config=DrawConfig(mode=DrawMode.PAGES))
```

Do not combine `ax` with `pages_controls` or `slider`.

## Frozen layout rule

The library does not repaginate or recompute line widths just because the user resizes the figure.

Only these actions are allowed to change the scene:

- explicit mode changes
- explicit page changes
- explicit visible-page changes
- explicit slider changes
- topology changes in managed 3D

The existing 2D zoom-based text scaling remains available.

## Saving

`output_path` always saves a clean figure:

- `pages`, `pages_controls`, and `slider`: save the concatenated paged composition
- `full`: saves the full unpaged scene

```python
draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode=DrawMode.PAGES_CONTROLS,
        output_path="chip.png",
        show=False,
    ),
)
```

## 3D workflows

```python
result = draw_quantum_circuit(
    circuit,
    config=DrawConfig(
        view="3d",
        mode=DrawMode.PAGES_CONTROLS,
        topology="grid",
        topology_menu=True,
        direct=False,
        show=False,
    ),
)
```

What changes in 3D:

- `pages` works
- `pages_controls` works
- `slider` is horizontal only
- `full` works
- managed `pages_controls` preserves the shared camera while you navigate

## Style and theme

You can configure both geometry and visual families:

```python
config = DrawConfig(
    style={
        "theme": "paper",
        "max_page_width": 9.0,
        "wire_line_width": 1.8,
        "classical_wire_line_width": 1.5,
        "connection_line_width": 1.9,
        "measurement_line_width": 1.4,
    },
    hover={"enabled": True, "show_size": True},
)
```

`DrawTheme` now also covers:

- control markers
- control connections
- topology colors
- managed UI colors
- hover colors

## Working with the result

`DrawResult` gives you one stable shape across all modes:

```python
result.primary_figure
result.primary_axes
result.figures
result.axes
result.mode
result.page_count
```

Typical uses:

- `result.primary_figure` for save/show logic
- `result.figures` in notebook page mode
- `result.page_count` to report how many pages were produced
