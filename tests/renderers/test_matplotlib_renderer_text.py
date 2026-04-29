# ruff: noqa: F403, F405
from matplotlib.axes import Axes
from matplotlib.figure import Figure

import quantum_circuit_drawer.renderers._matplotlib_axes as matplotlib_axes_module
import quantum_circuit_drawer.renderers._matplotlib_gates as matplotlib_gates_module
import quantum_circuit_drawer.renderers._matplotlib_text as matplotlib_text_module
from tests._matplotlib_renderer_support import *


def _projected_gate_display_bounds(
    figure: Figure,
    axes: Axes,
    gate: SceneGate,
) -> tuple[float, float, float, float]:
    del figure
    x0, y0 = axes.transData.transform((gate.x - (gate.width / 2.0), gate.y - (gate.height / 2.0)))
    x1, y1 = axes.transData.transform((gate.x + (gate.width / 2.0), gate.y + (gate.height / 2.0)))
    return min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)


def test_matplotlib_renderer_keeps_visible_circuit_text_plain_by_default() -> None:
    figure, axes = plt.subplots()

    scene = build_sample_scene()
    MatplotlibRenderer().render(scene, ax=axes)

    assert {"H", "M", "q0", "q1", "c0"}.issubset({text.get_text() for text in axes.texts})
    assert not any(text.get_text().startswith("$") for text in axes.texts)


def test_matplotlib_renderer_keeps_numeric_gate_parameters_plain_by_default() -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=1, wire_count=1),
        DrawStyle(show_params=True),
    )
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    assert "RX\n0.5" in {text.get_text() for text in axes.texts}


def test_matplotlib_renderer_formats_symbolic_gate_parameters_with_mathtext_in_auto_mode() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RX",
                        target_wires=("q0",),
                        parameters=("theta",),
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(show_params=True))
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    assert "RX\n$\\theta$" in {text.get_text() for text in axes.texts}


def test_matplotlib_renderer_keeps_visible_text_plain_when_mathtext_is_disabled() -> None:
    figure, axes = plt.subplots()

    scene = LayoutEngine().compute(build_sample_ir(), DrawStyle(use_mathtext=False))
    MatplotlibRenderer().render(scene, ax=axes)

    assert {"H", "M", "q0", "q1", "c0"}.issubset({text.get_text() for text in axes.texts})
    assert not any(text.get_text().startswith("$") for text in axes.texts)


def test_matplotlib_renderer_preserves_legacy_mathtext_behavior_when_enabled() -> None:
    figure, axes = plt.subplots()

    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=1, wire_count=1),
        DrawStyle(show_params=True, use_mathtext=True),
    )
    MatplotlibRenderer().render(scene, ax=axes)

    assert r"$\mathrm{0}$" in {text.get_text() for text in axes.texts}
    assert r"$\mathrm{RX}$" + "\n" + r"$0.5$" in {text.get_text() for text in axes.texts}


def test_matplotlib_renderer_draws_measurement_destination_arrow_and_label() -> None:
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(build_sample_scene(), ax=axes)

    assert any(isinstance(patch, FancyArrowPatch) for patch in axes.patches)
    assert sum(normalize_rendered_text(text.get_text()) == "c0" for text in axes.texts) >= 2


def test_matplotlib_renderer_draws_classical_condition_with_arrow_and_bottom_label() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q0",),
                        classical_conditions=(
                            ClassicalConditionIR(wire_ids=("c0",), expression="if c[0]=1"),
                        ),
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    label = _find_axis_text(axes, "if c[0]=1")

    assert abs(label.get_position()[1] - scene.wire_y_positions["c0"]) < abs(
        label.get_position()[1] - scene.wire_y_positions["q0"]
    )
    assert (
        scene.wire_y_positions["c0"] - 0.3 < label.get_position()[1] < scene.wire_y_positions["c0"]
    )
    assert any(isinstance(patch, FancyArrowPatch) for patch in axes.patches)
    assert axes.collections[-1].get_linestyle()[0][1] is None


def test_matplotlib_renderer_repeats_wire_labels_when_wrapping_pages() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q1",))]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    )
                ]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Z", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Y", target_wires=("q1",))]
            ),
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    assert sum(normalize_rendered_text(text.get_text()) == "q0" for text in axes.texts) == len(
        scene.pages
    )
    assert sum(normalize_rendered_text(text.get_text()) == "q1" for text in axes.texts) == len(
        scene.pages
    )


def test_matplotlib_renderer_draws_canonical_cx_without_gate_box_text() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        canonical_family=CanonicalGateFamily.X,
                        target_wires=("q1",),
                        control_wires=("q0",),
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    assert not any(isinstance(patch, FancyBboxPatch) for patch in axes.patches)
    assert not any(isinstance(patch, Circle) for patch in axes.patches)
    assert len(_ellipse_collections(axes)) >= 2
    assert not any(text.get_text() == "X" for text in axes.texts)


def test_matplotlib_renderer_keeps_four_letter_gate_label_inside_box() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="SWAP", target_wires=("q0",))]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots(figsize=(2.5, 2.0))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    gate_text = _find_axis_text(axes, "SWAP")
    patch_x, _, patch_width, _ = _display_bounds(figure, gate_patch)
    text_x, _, text_width, _ = _display_bounds(figure, gate_text)

    assert text_x >= patch_x
    assert text_x + text_width <= patch_x + patch_width


def test_matplotlib_renderer_keeps_four_letter_labels_inside_boxes_on_wrapped_managed_figures() -> (
    None
):
    quantum_wires = [
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(4)
    ]
    circuit = CircuitIR(
        quantum_wires=quantum_wires,
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="SWAP",
                        target_wires=(f"q{layer_index % 4}",),
                    )
                ]
            )
            for layer_index in range(20)
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))

    renderer = MatplotlibRenderer()
    figure, axes = renderer.render(scene)
    figure.canvas.draw()

    projected_gate_bounds = [
        _projected_gate_display_bounds(figure, axes, gate)
        for page in renderer._project_pages(scene)
        for gate in page.gates
    ]
    gate_texts = sorted(
        (text for text in axes.texts if normalize_rendered_text(text.get_text()) == "SWAP"),
        key=lambda text: text.get_position()[1],
    )

    assert len(projected_gate_bounds) == len(gate_texts) == 20

    for gate_text in gate_texts:
        text_x, _, text_width, _ = _display_bounds(figure, gate_text)
        assert any(
            text_x >= patch_x and text_x + text_width <= patch_x + patch_width
            for patch_x, _, patch_width, _ in projected_gate_bounds
        )


def test_matplotlib_renderer_keeps_four_letter_labels_inside_boxes_on_narrow_wrapped_figures() -> (
    None
):
    quantum_wires = [
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=str(index))
        for index in range(4)
    ]
    circuit = CircuitIR(
        quantum_wires=quantum_wires,
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="SWAP",
                        target_wires=(f"q{layer_index % 4}",),
                    )
                ]
            )
            for layer_index in range(24)
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
    figure, axes = plt.subplots(figsize=(2.1, 18.0))

    renderer = MatplotlibRenderer()
    renderer.render(scene, ax=axes)
    figure.canvas.draw()

    projected_gate = next(gate for page in renderer._project_pages(scene) for gate in page.gates)
    gate_text = _find_axis_text(axes, "SWAP")
    patch_x, _, patch_width, _ = _projected_gate_display_bounds(figure, axes, projected_gate)
    text_x, _, text_width, _ = _display_bounds(figure, gate_text)

    assert text_x >= patch_x
    assert text_x + text_width <= patch_x + patch_width


def test_matplotlib_renderer_keeps_tiny_dense_labels_inside_boxes() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="SWAP", target_wires=("q0",))]
            )
            for _ in range(40)
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=200.0, use_mathtext=False))
    figure, axes = plt.subplots(figsize=(4.0, 1.2))

    renderer = MatplotlibRenderer()
    renderer.render(scene, ax=axes)
    figure.canvas.draw()

    projected_gate = next(gate for page in renderer._project_pages(scene) for gate in page.gates)
    gate_text = _find_axis_text(axes, "SWAP")
    patch_x, _, patch_width, _ = _projected_gate_display_bounds(figure, axes, projected_gate)
    text_x, _, text_width, _ = _display_bounds(figure, gate_text)

    assert text_width <= patch_width
    assert text_x >= patch_x
    assert text_x + text_width <= patch_x + patch_width


def test_matplotlib_renderer_keeps_tiny_dense_label_and_subtitle_inside_box() -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=80, wire_count=4),
        DrawStyle(max_page_width=200.0, show_params=True, use_mathtext=False),
    )
    figure, axes = plt.subplots(figsize=(5.0, 1.8))

    renderer = MatplotlibRenderer()
    renderer.render(scene, ax=axes)
    figure.canvas.draw()

    projected_gate = next(gate for page in renderer._project_pages(scene) for gate in page.gates)
    gate_text = _find_axis_text(axes, "RX\n0.5")
    patch_x, patch_y, patch_width, patch_height = _projected_gate_display_bounds(
        figure,
        axes,
        projected_gate,
    )
    text_x, text_y, text_width, text_height = _display_bounds(figure, gate_text)

    assert text_width <= patch_width
    assert text_height <= patch_height
    assert text_x >= patch_x
    assert text_x + text_width <= patch_x + patch_width
    assert text_y >= patch_y
    assert text_y + text_height <= patch_y + patch_height


def test_gate_text_fitting_context_matches_existing_font_fit_for_wrapped_gate_text() -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=24),
        DrawStyle(max_page_width=4.0, show_params=True, use_mathtext=False),
    )
    figure, axes = plt.subplots(figsize=(2.1, 18.0))
    gate = next(gate for gate in scene.gates if gate.subtitle == "0.5")
    gate_text = f"{gate.label}\n{gate.subtitle}"

    matplotlib_primitives.prepare_axes(axes, scene)
    context = matplotlib_primitives._build_gate_text_fitting_context(axes, scene)
    cache: dict[tuple[object, ...], float] = {}

    multiline_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=context,
        width=gate.width,
        height=gate.height,
        text=gate_text,
        default_font_size=scene.style.font_size,
        height_fraction=matplotlib_primitives._STACKED_TEXT_USABLE_HEIGHT_FRACTION,
        cache=cache,
    )

    assert len(scene.pages) > 1
    assert multiline_size == approx(
        matplotlib_primitives._fit_gate_text_font_size(
            ax=axes,
            scene=scene,
            width=gate.width,
            height=gate.height,
            text=gate_text,
            default_font_size=scene.style.font_size,
            height_fraction=matplotlib_primitives._STACKED_TEXT_USABLE_HEIGHT_FRACTION,
        )
    )


def test_gate_text_fitting_context_caches_repeated_inputs(monkeypatch) -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=8),
        DrawStyle(show_params=True),
    )
    figure, axes = plt.subplots(figsize=(2.5, 4.0))
    gate = scene.gates[0]
    text_width_calls = 0

    matplotlib_primitives.prepare_axes(axes, scene)
    context = matplotlib_primitives._build_gate_text_fitting_context(axes, scene)
    original_text_width = matplotlib_text_module._text_width_in_points

    def count_text_width(text: str) -> float:
        nonlocal text_width_calls
        text_width_calls += 1
        return original_text_width(text)

    monkeypatch.setattr(matplotlib_text_module, "_text_width_in_points", count_text_width)

    cache: dict[tuple[object, ...], float] = {}
    first_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=context,
        width=gate.width,
        text=gate.label,
        default_font_size=scene.style.font_size,
        cache=cache,
    )
    second_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=context,
        width=gate.width,
        text=gate.label,
        default_font_size=scene.style.font_size,
        cache=cache,
    )

    assert first_size == approx(second_size)
    assert text_width_calls == 1
    assert len(cache) == 1
    assert next(iter(cache.values())) == approx(first_size)


def test_gate_text_fitting_fast_path_reuses_numeric_shape_measurements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=1, wire_count=1),
        DrawStyle(show_params=True),
    )
    figure, axes = plt.subplots(figsize=(3.2, 2.4))
    measured_texts: list[str] = []
    original_text_path = matplotlib_text_module.TextPath

    class CountingTextPath:
        def __init__(self, xy: tuple[float, float], text: str, **kwargs: object) -> None:
            measured_texts.append(text)
            self._path = original_text_path(xy, text, **kwargs)

        def get_extents(self) -> object:
            return self._path.get_extents()

    monkeypatch.setattr(matplotlib_text_module, "TextPath", CountingTextPath)
    matplotlib_text_module._text_width_in_points.cache_clear()
    matplotlib_text_module._text_height_in_points.cache_clear()
    matplotlib_primitives.prepare_axes(axes, scene)
    context = matplotlib_primitives._build_gate_text_fitting_context(axes, scene)

    numeric_subtitles = ("0.11", "1.22", "2.33", "3.44", "4.55", "5.66")
    for subtitle in numeric_subtitles:
        fitted_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
            context=context,
            width=scene.style.gate_width,
            height=scene.style.gate_height,
            text=subtitle,
            default_font_size=scene.style.font_size * 0.78,
            height_fraction=0.4,
            cache={},
        )
        assert fitted_size > 0.0

    assert len(measured_texts) < len(numeric_subtitles)


def test_gate_text_fitting_context_reuses_numeric_shape_cache_entries() -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=1, wire_count=1),
        DrawStyle(show_params=True),
    )
    figure, axes = plt.subplots(figsize=(3.2, 2.4))

    matplotlib_primitives.prepare_axes(axes, scene)
    context = matplotlib_primitives._build_gate_text_fitting_context(axes, scene)
    cache: dict[tuple[object, ...], float] = {}
    numeric_subtitles = ("0.11", "1.22", "2.33", "3.44", "4.55", "5.66")

    for subtitle in numeric_subtitles:
        fitted_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
            context=context,
            width=scene.style.gate_width,
            height=scene.style.gate_height,
            text=subtitle,
            default_font_size=scene.style.font_size * 0.78,
            height_fraction=0.4,
            cache=cache,
        )
        assert fitted_size > 0.0

    assert len(cache) < len(numeric_subtitles)


def test_matplotlib_renderer_reuses_gate_text_context_per_wrapped_page(monkeypatch) -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=24),
        DrawStyle(max_page_width=4.0, show_params=True),
    )
    figure, axes = plt.subplots(figsize=(2.1, 18.0))
    viewport_calls = 0
    original_get_viewport_width = matplotlib_text_module.get_viewport_width

    def count_viewport_width(*args, **kwargs) -> float:
        nonlocal viewport_calls
        viewport_calls += 1
        return original_get_viewport_width(*args, **kwargs)

    monkeypatch.setattr(matplotlib_text_module, "get_viewport_width", count_viewport_width)

    MatplotlibRenderer().render(scene, ax=axes)

    assert len(scene.pages) > 1
    assert 0 < viewport_calls <= len(scene.pages)


def test_matplotlib_renderer_reuses_text_fit_cache_across_repeated_renders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=24),
        DrawStyle(max_page_width=4.0, show_params=True),
    )
    figure, axes = plt.subplots(figsize=(2.1, 18.0))
    renderer = MatplotlibRenderer()
    cache_ids: set[int] = set()
    original_fit = matplotlib_text_module._fit_gate_text_font_size_with_context

    def track_cache_ids(**kwargs: object) -> float:
        cache_ids.add(id(kwargs["cache"]))
        return original_fit(**kwargs)

    monkeypatch.setattr(
        matplotlib_text_module,
        "_fit_gate_text_font_size_with_context",
        track_cache_ids,
    )

    renderer.render(scene, ax=axes)
    axes.clear()
    renderer.render(scene, ax=axes)

    assert len(cache_ids) == 1
    plt.close(figure)


def test_matplotlib_renderer_reuses_prepared_gate_text_for_repeated_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",)),
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RX",
                        target_wires=("q1",),
                        parameters=(0.5,),
                    ),
                ]
            )
            for _ in range(12)
        ],
    )
    scene = LayoutEngine().compute(
        circuit,
        DrawStyle(show_params=True, show_wire_labels=False),
    )
    figure, axes = plt.subplots(figsize=(4.0, 8.0))
    visible_label_calls = 0
    gate_text_block_calls = 0
    original_visible_label = matplotlib_gates_module.format_visible_label
    original_gate_text_block = matplotlib_gates_module.format_gate_text_block

    def count_visible_label(text: str, *, use_mathtext: bool) -> str:
        nonlocal visible_label_calls
        visible_label_calls += 1
        return original_visible_label(text, use_mathtext=use_mathtext)

    def count_gate_text_block(label: str, subtitle: str, *, use_mathtext: bool) -> str:
        nonlocal gate_text_block_calls
        gate_text_block_calls += 1
        return original_gate_text_block(label, subtitle, use_mathtext=use_mathtext)

    monkeypatch.setattr(
        matplotlib_renderer_module,
        "format_visible_label",
        count_visible_label,
        raising=False,
    )
    monkeypatch.setattr(
        matplotlib_renderer_module,
        "format_gate_text_block",
        count_gate_text_block,
        raising=False,
    )
    monkeypatch.setattr(matplotlib_gates_module, "format_visible_label", count_visible_label)
    monkeypatch.setattr(matplotlib_gates_module, "format_gate_text_block", count_gate_text_block)

    MatplotlibRenderer().render(scene, ax=axes)

    axis_texts = [normalize_rendered_text(text.get_text()) for text in axes.texts]

    assert axis_texts.count("H") == 12
    assert axis_texts.count("RX\n0.5") == 12
    assert visible_label_calls == 1
    assert gate_text_block_calls == 1


def test_matplotlib_renderer_uses_one_font_size_for_grouped_sqrt_pauli_gate_labels() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name=gate_name,
                        target_wires=("q0",),
                    )
                ]
            )
            for gate_name in ("SX", "SY", "SZ") * 12
        ],
    )
    scene = LayoutEngine().compute(
        circuit,
        DrawStyle(max_page_width=200.0, show_params=False, use_mathtext=False),
    )
    figure, axes = plt.subplots(figsize=(2.2, 1.4))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    grouped_font_sizes = {
        gate_name: _find_axis_text(axes, gate_name).get_fontsize()
        for gate_name in ("SX", "SY", "SZ")
    }

    assert len(set(round(font_size, 6) for font_size in grouped_font_sizes.values())) == 1
    plt.close(figure)


def test_draw_gate_label_centers_label_and_subtitle_block() -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=1, wire_count=1),
        DrawStyle(show_params=True),
    )
    figure, axes = plt.subplots(figsize=(4.0, 2.0))

    MatplotlibRenderer().render(scene, ax=axes)

    gate = scene.gates[0]
    gate_label = _find_axis_text(axes, "RX\n0.5")

    assert gate_label.get_position()[1] == approx(
        gate.y,
        abs=0.02,
    )


def test_draw_quantum_circuit_keeps_gate_label_inside_box_after_zoom() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="SWAP", target_wires=("q0",))]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots(figsize=(2.5, 2.0))

    draw_quantum_circuit(circuit, ax=axes)
    axes.set_xlim(scene.gates[0].x - 0.32, scene.gates[0].x + 0.32)
    axes.set_ylim(scene.gates[0].y + 0.4, scene.gates[0].y - 0.4)
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    gate_text = _find_axis_text(axes, "SWAP")
    patch_x, _, patch_width, _ = _display_bounds(figure, gate_patch)
    text_x, _, text_width, _ = _display_bounds(figure, gate_text)

    assert text_x >= patch_x
    assert text_x + text_width <= patch_x + patch_width


def test_matplotlib_renderer_rescales_gate_and_wire_text_when_zooming() -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=6),
        DrawStyle(),
    )
    figure, axes = plt.subplots(figsize=(8.0, 3.0))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    gate_label = _find_axis_text(axes, "RX\n0.5")
    wire_label = _find_axis_text(axes, "0")
    initial_gate_font_size = gate_label.get_fontsize()
    initial_wire_font_size = wire_label.get_fontsize()
    left, right = axes.get_xlim()
    bottom, top = axes.get_ylim()

    axes.set_xlim(left, left + ((right - left) / 3.0))
    axes.set_ylim(bottom, bottom + ((top - bottom) / 3.0))
    figure.canvas.draw()

    assert gate_label.get_fontsize() > initial_gate_font_size
    assert wire_label.get_fontsize() > initial_wire_font_size


def test_matplotlib_renderer_uses_smaller_measurement_label_and_compact_classical_bits() -> None:
    figure, axes = plt.subplots(figsize=(3.5, 8.0))
    scene = LayoutEngine().compute(
        _measurement_register_ir(measurement_count=18),
        DrawStyle(use_mathtext=False),
    )

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    context = matplotlib_primitives._build_gate_text_fitting_context(axes, scene)
    measurement_label = _find_axis_text(axes, "M")
    classical_bundle_count = _find_axis_text(axes, "18")
    classical_bit_labels = sorted(
        [
            text
            for text in axes.texts
            if (
                normalize_rendered_text(text.get_text()).startswith("c[")
                or normalize_rendered_text(text.get_text()).startswith("[")
            )
        ],
        key=lambda text: text.get_position()[0],
    )

    assert measurement_label.get_fontsize() == approx(
        matplotlib_primitives._fit_gate_text_font_size_with_context(
            context=context,
            width=scene.style.gate_width * 0.5,
            height=scene.style.gate_height * 0.5,
            text="M",
            default_font_size=scene.style.font_size
            * matplotlib_primitives._MEASUREMENT_LABEL_FONT_SCALE,
            height_fraction=1.0,
            cache={},
        )
    )
    assert classical_bundle_count.get_fontsize() == approx(
        matplotlib_primitives._fit_gate_text_font_size_with_context(
            context=context,
            width=scene.style.gate_width * 0.5,
            height=scene.style.gate_height * 0.5,
            text="18",
            default_font_size=scene.style.font_size * 0.66,
            height_fraction=1.0,
            cache={},
        )
    )
    assert any(
        normalize_rendered_text(text.get_text()).startswith("[") for text in classical_bit_labels
    )
    assert all(
        not normalize_rendered_text(text.get_text()).startswith("c[")
        for text in classical_bit_labels
    )
    assert _overlap_count(figure, classical_bit_labels) == 0


def test_matplotlib_renderer_reuses_shared_text_cache_for_non_gate_texts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine().compute(_measurement_register_ir(measurement_count=18), DrawStyle())
    figure, axes = plt.subplots(figsize=(3.5, 8.0))
    observed_cache_ids: set[int] = set()
    original_fit = matplotlib_text_module._fit_gate_text_font_size_with_context

    def track_cache_ids(**kwargs: object) -> float:
        observed_cache_ids.add(id(kwargs["cache"]))
        return original_fit(**kwargs)

    monkeypatch.setattr(
        matplotlib_text_module,
        "_fit_gate_text_font_size_with_context",
        track_cache_ids,
    )

    MatplotlibRenderer().render(scene, ax=axes)

    assert len(observed_cache_ids) == 1


def test_matplotlib_renderer_keeps_full_measurement_classical_label_when_space_allows() -> None:
    circuit = _single_measurement_ir(classical_label="alpha", bit_label="alpha[1]")
    figure, axes = plt.subplots(figsize=(20.0, 10.0))

    draw_quantum_circuit(circuit, ax=axes, show=False)
    figure.canvas.draw()

    axis_texts = _normalized_axis_text_values(axes)

    assert "alpha[1]" in axis_texts
    assert "[1]" not in axis_texts


def test_matplotlib_renderer_does_not_add_empty_connection_labels() -> None:
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(build_sample_scene(), ax=axes)

    assert all(text.get_text() for text in axes.texts)


def test_add_text_artist_skips_clip_path_when_fast_path_available(
    monkeypatch: object,
) -> None:
    figure, axes = plt.subplots()
    clip_path_calls = 0
    original_set_clip_path = Text.set_clip_path

    def count_set_clip_path(self: Text, path: object, transform: object = None) -> object:
        nonlocal clip_path_calls
        clip_path_calls += 1
        return original_set_clip_path(self, path, transform)

    monkeypatch.setattr(Text, "set_clip_path", count_set_clip_path)

    text_artist = matplotlib_primitives._add_text_artist(
        axes,
        0.5,
        0.5,
        "H",
        ha="center",
        va="center",
        fontsize=12.0,
    )

    assert text_artist in axes.texts
    assert clip_path_calls == 0


def test_add_text_artist_falls_back_to_axes_text_when_fast_path_unavailable(
    monkeypatch: object,
) -> None:
    figure, axes = plt.subplots()
    fallback_calls = 0
    original_axes_text = axes.text

    def count_axes_text(*args: object, **kwargs: object) -> Text:
        nonlocal fallback_calls
        fallback_calls += 1
        return original_axes_text(*args, **kwargs)

    monkeypatch.setattr(
        matplotlib_axes_module,
        "_supports_fast_text_artist_path",
        lambda _: False,
    )
    monkeypatch.setattr(axes, "text", count_axes_text)

    text_artist = matplotlib_primitives._add_text_artist(
        axes,
        0.5,
        0.5,
        "fallback",
        fontsize=12.0,
    )

    assert fallback_calls == 1
    assert text_artist in axes.texts
