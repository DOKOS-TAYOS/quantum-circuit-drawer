# 3D Topology Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in public API menu that lets users switch valid 3D chip topologies inside a managed Matplotlib figure and redraw the same 3D view immediately.

**Architecture:** Extend the public draw request with a `topology_menu` flag, carry that option through the prepared 3D pipeline, and attach a managed-figure-only topology selector in the 3D rendering path. The selector reuses the existing 3D topology builders and layout engine, disables invalid topologies for the current qubit count, and redraws the same `Axes3D` when the selection changes.

**Tech Stack:** Python 3.12, Matplotlib managed figures/widgets, existing 3D layout engine and draw pipeline, pytest.

---

### Task 1: Add Public API Support For `topology_menu`

**Files:**
- Modify: `src/quantum_circuit_drawer/api.py`
- Modify: `src/quantum_circuit_drawer/_draw_request.py`
- Modify: `src/quantum_circuit_drawer/_draw_pipeline.py`
- Test: `tests/test_api_contracts.py`
- Test: `tests/test_api_3d.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_validate_public_options_rejects_non_boolean_topology_menu() -> None:
    with pytest.raises(ValueError, match="topology_menu must be a boolean"):
        draw_quantum_circuit(build_sample_ir(), topology_menu="yes")


def test_draw_quantum_circuit_rejects_topology_menu_in_2d_view() -> None:
    with pytest.raises(ValueError, match="topology_menu=True is only supported for view='3d'"):
        draw_quantum_circuit(build_sample_ir(), topology_menu=True, show=False)


def test_draw_quantum_circuit_accepts_topology_menu_in_managed_3d_view() -> None:
    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
        show=False,
    )

    assert axes.figure is figure
    assert axes.name == "3d"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `C:\Users\aleja\Documents\quantum_circuit_visualization\.venv\Scripts\python.exe -m pytest tests/test_api_contracts.py tests/test_api_3d.py -q`

Expected: FAIL because `topology_menu` is not part of the public signature or validation yet.

- [ ] **Step 3: Write the minimal implementation**

```python
def draw_quantum_circuit(
    ...,
    topology: Literal["line", "grid", "star", "star_tree", "honeycomb"] = "line",
    topology_menu: bool = False,
    direct: bool = True,
    ...
) -> RenderResult:
    request = build_draw_request(
        ...,
        topology=topology,
        topology_menu=topology_menu,
        direct=direct,
        ...
    )
```

```python
@dataclass(frozen=True, slots=True)
class DrawPipelineOptions:
    ...
    topology_menu: bool = False

    def to_mapping(self) -> dict[str, object]:
        return {
            ...,
            "topology_menu": self.topology_menu,
            ...
        }

    def adapter_options(self) -> dict[str, object]:
        for key in ("view", "topology", "topology_menu", "direct", "hover"):
            options.pop(key, None)
        return options
```

```python
def validate_public_options(..., topology_menu: object, ...) -> None:
    _validate_bool("topology_menu", topology_menu)


def validate_draw_request(request: DrawRequest) -> None:
    ...
    if request.pipeline_options.view != "3d" and request.pipeline_options.topology_menu:
        raise ValueError("topology_menu=True is only supported for view='3d'")
```

```python
@dataclass(frozen=True, slots=True)
class PreparedDrawPipeline:
    ...
    draw_options: DrawPipelineOptions
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `C:\Users\aleja\Documents\quantum_circuit_visualization\.venv\Scripts\python.exe -m pytest tests/test_api_contracts.py tests/test_api_3d.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_api_contracts.py tests/test_api_3d.py src/quantum_circuit_drawer/api.py src/quantum_circuit_drawer/_draw_request.py src/quantum_circuit_drawer/_draw_pipeline.py
git commit -m "feat: add topology menu draw option"
```

### Task 2: Add Managed-Figure Topology Menu State And Redraw Support

**Files:**
- Modify: `src/quantum_circuit_drawer/_draw_pipeline.py`
- Modify: `src/quantum_circuit_drawer/renderers/_matplotlib_figure.py`
- Create: `src/quantum_circuit_drawer/_draw_managed_topology_menu.py`
- Modify: `src/quantum_circuit_drawer/_draw_managed.py`
- Test: `tests/test_api_managed_rendering.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_draw_quantum_circuit_attaches_topology_menu_state_for_managed_interactive_3d(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "TkAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
    )

    menu_state = get_topology_menu_state(figure)

    assert axes.figure is figure
    assert menu_state is not None
    assert menu_state.active_topology == "line"
    assert menu_state.valid_topologies == ("line", "star")
```

```python
def test_draw_quantum_circuit_skips_topology_menu_for_caller_managed_3d_axes() -> None:
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")

    draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
        ax=axes,
    )

    assert get_topology_menu_state(figure) is None
```

```python
def test_topology_menu_redraws_same_axes_with_new_valid_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "TkAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=2, wire_count=4),
        view="3d",
        topology="line",
        topology_menu=True,
    )
    menu_state = get_topology_menu_state(figure)

    assert menu_state is not None
    menu_state.select_topology("grid")

    assert menu_state.active_topology == "grid"
    assert axes is menu_state.axes
    assert menu_state.scene.topology.name == "grid"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `C:\Users\aleja\Documents\quantum_circuit_visualization\.venv\Scripts\python.exe -m pytest tests/test_api_managed_rendering.py -q`

Expected: FAIL because there is no topology menu state, helper module, or redraw callback yet.

- [ ] **Step 3: Write the minimal implementation**

```python
@dataclass(slots=True)
class TopologyMenuState:
    figure: Figure | SubFigure
    axes: Axes
    active_topology: TopologyName
    valid_topologies: tuple[TopologyName, ...]
    scene: LayoutScene3D
    select_topology: Callable[[TopologyName], None]
```

```python
def build_topology_menu_state(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    output: OutputPath | None,
    show: bool,
) -> TopologyMenuState | None:
    if output is not None or not pipeline.draw_options.topology_menu:
        return None
    if figure_backend_name(figure) in NON_INTERACTIVE_BACKENDS:
        return None
    ...
```

```python
def _render_3d_pipeline_into_existing_axes(
    *,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
) -> None:
    axes.clear()
    pipeline.renderer.render(pipeline.paged_scene, ax=axes)
```

```python
def _pipeline_for_topology(
    pipeline: PreparedDrawPipeline,
    topology: TopologyName,
) -> PreparedDrawPipeline:
    draw_options = replace(pipeline.draw_options, topology=topology)
    return replace(
        pipeline,
        draw_options=draw_options,
        paged_scene=_compute_3d_scene(
            cast(LayoutEngine3DLike, pipeline.layout_engine),
            pipeline.ir,
            pipeline.normalized_style,
            topology_name=topology,
            direct=draw_options.direct,
            hover_enabled=draw_options.hover.enabled,
        ),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `C:\Users\aleja\Documents\quantum_circuit_visualization\.venv\Scripts\python.exe -m pytest tests/test_api_managed_rendering.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_api_managed_rendering.py src/quantum_circuit_drawer/_draw_managed.py src/quantum_circuit_drawer/_draw_managed_topology_menu.py src/quantum_circuit_drawer/_draw_pipeline.py src/quantum_circuit_drawer/renderers/_matplotlib_figure.py
git commit -m "feat: add managed 3d topology menu"
```

### Task 3: Finish Menu UX, Disabled States, And Documentation

**Files:**
- Modify: `src/quantum_circuit_drawer/_draw_managed_topology_menu.py`
- Modify: `docs/api.md`
- Modify: `docs/user-guide.md`
- Modify: `docs/recipes.md`
- Test: `tests/test_api_managed_rendering.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_topology_menu_keeps_invalid_topologies_visible_but_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "TkAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, _ = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
    )
    menu_state = get_topology_menu_state(figure)

    assert menu_state is not None
    assert menu_state.is_enabled("line") is True
    assert menu_state.is_enabled("grid") is False
    assert set(menu_state.topologies) == {"line", "grid", "star", "star_tree", "honeycomb"}
```

```python
def test_topology_menu_ignores_invalid_selection_without_changing_active_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "TkAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, _ = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
    )
    menu_state = get_topology_menu_state(figure)

    assert menu_state is not None
    menu_state.select_topology("grid")

    assert menu_state.active_topology == "line"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `C:\Users\aleja\Documents\quantum_circuit_visualization\.venv\Scripts\python.exe -m pytest tests/test_api_managed_rendering.py -q`

Expected: FAIL because disabled-topology state and invalid-selection handling are not finalized yet.

- [ ] **Step 3: Write the minimal implementation and docs**

```python
def available_topology_states(
    quantum_wires: tuple[WireIR, ...],
) -> dict[TopologyName, bool]:
    return {
        topology_name: _supports_topology(topology_name, quantum_wires)
        for topology_name in ("line", "grid", "star", "star_tree", "honeycomb")
    }
```

```python
def select_topology(topology: TopologyName) -> None:
    if not topology_state_map[topology]:
        _refresh_button_styles()
        return
    ...
```

```python
draw_quantum_circuit(
    circuit,
    view="3d",
    topology="line",
    topology_menu=True,
)
```

- [ ] **Step 4: Run the focused tests and docs-adjacent regressions**

Run: `C:\Users\aleja\Documents\quantum_circuit_visualization\.venv\Scripts\python.exe -m pytest tests/test_api_managed_rendering.py tests/test_api_3d.py tests/test_api_contracts.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_api_managed_rendering.py tests/test_api_3d.py tests/test_api_contracts.py docs/api.md docs/user-guide.md docs/recipes.md src/quantum_circuit_drawer/_draw_managed_topology_menu.py
git commit -m "docs: document 3d topology menu"
```
