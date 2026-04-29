# ruff: noqa: F403, F405
import math

from matplotlib.widgets import Button

import quantum_circuit_drawer.managed._adaptive_paging as adaptive_paging_module
import quantum_circuit_drawer.managed.controls as managed_controls_module
import quantum_circuit_drawer.managed.page_window as page_window_module
import quantum_circuit_drawer.renderers._matplotlib_text as matplotlib_text_module
from quantum_circuit_drawer.ir.lowering import (
    lower_semantic_circuit,
    semantic_circuit_from_circuit_ir,
)
from quantum_circuit_drawer.layout._layering import normalized_draw_circuit
from quantum_circuit_drawer.renderers.matplotlib_renderer import MatplotlibRenderer
from tests._api_managed_rendering_support import *


def test_draw_quantum_circuit_rejects_page_window_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="page_window"):
        draw_quantum_circuit(build_sample_ir(), ax=axes, page_window=True)

    plt.close(figure)


def test_fit_button_label_to_width_keeps_long_text_inside_button_bounds() -> None:
    figure = plt.figure(figsize=(3.2, 2.4))
    button_axes = figure.add_axes((0.1, 0.1, 0.2, 0.1))
    button = Button(button_axes, "Ancillas: Hide")

    managed_controls_module._fit_button_label_font_size(button)
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    label_bbox = button.label.get_window_extent(renderer=renderer)
    button_bbox = button_axes.get_window_extent(renderer=renderer)

    assert label_bbox.x0 >= button_bbox.x0
    assert label_bbox.x1 <= button_bbox.x1

    plt.close(figure)


def test_fit_button_label_uses_same_font_size_for_all_registered_button_states() -> None:
    figure = plt.figure(figsize=(3.2, 2.4))
    button_axes = figure.add_axes((0.1, 0.1, 0.2, 0.1))
    button = Button(button_axes, "Wires: All")

    managed_controls_module._fit_button_label_font_size(
        button,
        possible_labels=("Wires: All", "Wires: Active"),
    )
    font_size_for_short_label = button.label.get_fontsize()
    button.label.set_text("Wires: Active")
    managed_controls_module._fit_button_label_font_size(button)
    figure.canvas.draw()

    renderer = figure.canvas.get_renderer()
    label_bbox = button.label.get_window_extent(renderer=renderer)
    button_bbox = button_axes.get_window_extent(renderer=renderer)

    assert button.label.get_fontsize() == pytest.approx(font_size_for_short_label)
    assert label_bbox.x0 >= button_bbox.x0
    assert label_bbox.x1 <= button_bbox.x1

    plt.close(figure)


def test_draw_quantum_circuit_attaches_page_window_controls_without_auto_paging() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.page_box is not None
    assert page_window.visible_pages_box is not None
    assert page_window.visible_pages_decrement_button is not None
    assert page_window.visible_pages_increment_button is not None
    assert page_window.previous_page_button is not None
    assert page_window.next_page_button is not None
    assert page_window.total_pages > 1
    assert page_window.start_page == 0
    assert page_window.visible_page_count == 1
    assert len(page_window.page_cache) == 1
    assert page_window.page_axes is not None
    assert page_window.visible_pages_axes is not None
    assert page_window.page_axes.get_facecolor() == pytest.approx(mcolors.to_rgba("#171221"))
    assert page_window.visible_pages_axes.get_facecolor() == pytest.approx(
        mcolors.to_rgba("#171221")
    )
    assert page_window.previous_page_button.label.get_text() == "\u2039"
    assert page_window.next_page_button.label.get_text() == "\u203a"
    assert page_window.previous_page_button.label.get_color() == "#ab9fc0"
    assert page_window.next_page_button.label.get_color() == "#e6edf3"

    page_window.visible_pages_increment_button._observers.process("clicked", None)

    assert page_window.visible_page_count == 2

    page_window.visible_pages_decrement_button._observers.process("clicked", None)

    assert page_window.visible_page_count == 1
    plt.close(figure)


def test_draw_quantum_circuit_page_window_hides_noop_exploration_buttons_and_keeps_inputs_compact() -> (
    None
):
    figure, _ = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    try:
        page_window = get_page_window(figure)

        assert page_window is not None
        assert page_window.page_axes is not None
        assert page_window.visible_pages_axes is not None
        assert page_window.wire_filter_axes is None
        assert page_window.ancilla_toggle_axes is None
        assert page_window.block_toggle_axes is None

        page_width = page_window.page_axes.get_position().width
        visible_width = page_window.visible_pages_axes.get_position().width
        visible_gap = (
            page_window.visible_pages_axes.get_position().x0
            - page_window.page_axes.get_position().x1
        )

        assert page_width <= 0.064
        assert visible_width <= 0.064
        assert visible_gap <= 0.22
        assert len(figure.axes) == 8
    finally:
        plt.close(figure)


def test_draw_quantum_circuit_page_window_uses_narrow_page_arrows_and_tighter_visible_steppers() -> (
    None
):
    figure, _ = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    try:
        page_window = get_page_window(figure)

        assert page_window is not None
        assert page_window.previous_page_button_axes is not None
        assert page_window.next_page_button_axes is not None
        assert page_window.page_axes is not None
        assert page_window.visible_pages_axes is not None
        assert page_window.visible_pages_decrement_axes is not None

        page_gap = (
            page_window.page_axes.get_position().x0
            - page_window.previous_page_button_axes.get_position().x1
        )
        visible_gap = (
            page_window.visible_pages_decrement_axes.get_position().x0
            - page_window.visible_pages_axes.get_position().x1
        )

        assert page_window.previous_page_button_axes.get_position().width == pytest.approx(0.023)
        assert page_window.next_page_button_axes.get_position().width == pytest.approx(0.023)
        assert page_gap == pytest.approx(0.004)
        assert visible_gap == pytest.approx(page_gap)
    finally:
        plt.close(figure)


def test_draw_quantum_circuit_page_window_clamps_inputs_and_reuses_cached_pages() -> None:
    figure, _ = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.page_box is not None
    assert page_window.visible_pages_box is not None
    assert len(page_window.page_cache) == 1

    page_window.page_box.set_val(str(page_window.total_pages))

    assert page_window.start_page == page_window.total_pages - 1
    assert page_window.visible_page_count == 1
    assert len(page_window.page_cache) == 2

    page_window.visible_pages_box.set_val("999")

    assert page_window.visible_page_count == 1
    assert len(page_window.page_cache) == 2

    page_window.page_box.set_val("1")

    assert page_window.start_page == 0
    assert len(page_window.page_cache) == 2
    plt.close(figure)


def test_draw_quantum_circuit_page_window_visible_suffix_tracks_remaining_page_capacity() -> None:
    figure, _ = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    try:
        page_window = get_page_window(figure)

        assert page_window is not None
        assert page_window.page_box is not None
        assert page_window.visible_suffix_text is not None
        assert page_window.total_pages >= 2

        page_window.page_box.set_val("2")

        assert page_window.visible_suffix_text.get_text() == f"/ {page_window.total_pages - 1}"
    finally:
        plt.close(figure)


def test_draw_quantum_circuit_page_window_reuses_text_fit_cache_between_redraws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    figure, _ = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.page_box is not None

    page_window.page_box.set_val(str(page_window.total_pages))
    page_window.page_box.set_val("1")

    assert len(cache_ids) == 1
    plt.close(figure)


def test_configure_page_window_reuses_provided_initial_scene_without_recomputing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    circuit = build_wrapped_ir()
    style = DrawStyle(max_page_width=4.0)
    layout_engine = LayoutEngine()
    semantic_ir = semantic_circuit_from_circuit_ir(circuit)
    semantic_circuit = normalized_draw_circuit(lower_semantic_circuit(semantic_ir))
    initial_scene = layout_engine.compute(semantic_circuit, style)
    effective_page_width = max(
        (page.content_width for page in initial_scene.pages),
        default=initial_scene.style.max_page_width,
    )
    scene_lookup_calls = 0
    original_scene_for_page_width = page_window_module._Managed2DSceneFactory.scene_for_page_width

    def count_scene_for_page_width(
        self: object,
        page_width: float,
    ) -> LayoutScene:
        nonlocal scene_lookup_calls
        scene_lookup_calls += 1
        return original_scene_for_page_width(self, page_width)

    monkeypatch.setattr(
        page_window_module._Managed2DSceneFactory,
        "scene_for_page_width",
        count_scene_for_page_width,
    )
    figure, axes = create_managed_figure(initial_scene, use_agg=True)

    try:
        state = page_window_module.configure_page_window(
            figure=figure,
            axes=axes,
            circuit=circuit,
            layout_engine=layout_engine,
            renderer=MatplotlibRenderer(),
            scene=initial_scene,
            effective_page_width=effective_page_width,
            set_page_window=lambda _figure, _state: None,
            semantic_ir=semantic_ir,
            attach_controls=False,
        )

        assert state.base_scene is initial_scene
        assert scene_lookup_calls == 0
    finally:
        plt.close(figure)


def test_draw_quantum_circuit_page_window_keeps_initial_page_width_after_resize() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    initial_page_width = page_window.effective_page_width
    initial_total_pages = page_window.total_pages

    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    assert page_window.effective_page_width == pytest.approx(initial_page_width)
    assert page_window.total_pages == initial_total_pages
    plt.close(figure)


def test_draw_quantum_circuit_page_window_navigation_buttons_step_between_pages() -> None:
    figure, _ = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.previous_page_button is not None
    assert page_window.next_page_button is not None

    page_window.next_page_button._observers.process("clicked", None)

    assert page_window.start_page == 1

    page_window.previous_page_button._observers.process("clicked", None)

    assert page_window.start_page == 0
    plt.close(figure)


def test_draw_quantum_circuit_page_window_uses_larger_page_and_visible_labels() -> None:
    figure, _ = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    try:
        labels_by_text = {
            text_artist.get_text(): text_artist
            for text_artist in figure.texts
            if text_artist.get_text() in {"Page", "Visible"}
        }

        assert labels_by_text["Page"].get_fontsize() == pytest.approx(12.0)
        assert labels_by_text["Visible"].get_fontsize() == pytest.approx(12.0)
    finally:
        plt.close(figure)


def test_draw_quantum_circuit_page_window_resizes_navigation_button_font_with_figure() -> None:
    figure, _ = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    try:
        page_window = get_page_window(figure)

        assert page_window is not None
        assert page_window.next_page_button is not None

        figure.canvas.draw()
        initial_font_size = page_window.next_page_button.label.get_fontsize()

        figure.set_size_inches(10.0, 6.0, forward=True)
        _dispatch_resize_event(figure)
        figure.canvas.draw()

        resized_font_size = page_window.next_page_button.label.get_fontsize()

        assert resized_font_size > initial_font_size
    finally:
        plt.close(figure)


def test_draw_quantum_circuit_page_window_uses_viewport_adaptive_initial_paging() -> None:
    circuit = build_dense_rotation_ir(layer_count=64, wire_count=2)
    strict_scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))

    figure, _ = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 4.0},
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.effective_page_width > 4.0
    assert page_window.total_pages < len(strict_scene.pages)
    plt.close(figure)


def test_draw_quantum_circuit_page_window_fills_vertical_space_from_visible_page_height() -> None:
    circuit = build_dense_rotation_ir(layer_count=40, wire_count=12)
    strict_scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
    figure_height = max(2.1, strict_scene.page_height * 0.72) + 1.0
    probe_figure, probe_axes = create_managed_figure(
        strict_scene,
        figure_width=4.6,
        figure_height=figure_height,
        use_agg=True,
    )
    probe_axes.set_position((0.02, 0.18, 0.96, 0.8))
    full_scene_adaptive, full_scene_page_width = managed_module.viewport_adaptive_paged_scene(
        circuit,
        LayoutEngine(),
        strict_scene.style,
        probe_axes,
        hover_enabled=strict_scene.hover.enabled,
        initial_scene=strict_scene,
    )
    plt.close(probe_figure)

    figure, _ = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 4.0},
        figsize=(4.6, figure_height),
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.total_pages > len(full_scene_adaptive.pages)
    assert page_window.effective_page_width < full_scene_page_width
    plt.close(figure)


def test_page_window_adaptive_paging_uses_early_exit_shortcuts_and_keeps_visible_page_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    style = DrawStyle(max_page_width=4.0)
    scene_factory = adaptive_paging_module._Managed2DSceneFactory(
        circuit=build_sample_ir(),
        layout_engine=LayoutEngine(),
        style=style,
        hover_enabled=False,
    )
    figure, axes = plt.subplots(figsize=(6.0, 3.0))
    metrics_calls: list[float] = []
    sizing_calls: list[tuple[str, int, float]] = []

    def fake_metrics_for_page_width(
        _scene_factory: adaptive_paging_module._Managed2DSceneFactory,
        page_width: float,
    ) -> object:
        metrics_calls.append(page_width)
        if math.isinf(page_width):
            return adaptive_paging_module._AdaptivePagingMetrics(
                pages=(
                    adaptive_paging_module.ScenePage(
                        index=0,
                        start_column=0,
                        end_column=0,
                        content_x_start=0.0,
                        content_x_end=20.0,
                        content_width=20.0,
                        y_offset=0.0,
                    ),
                    adaptive_paging_module.ScenePage(
                        index=1,
                        start_column=1,
                        end_column=1,
                        content_x_start=0.0,
                        content_x_end=20.0,
                        content_width=20.0,
                        y_offset=0.0,
                    ),
                ),
                scene_width=20.0,
                scene_height=10.0,
            )
        raise AssertionError(f"unexpected finite width evaluation: {page_width}")

    def fake_viewport_size_for_mode(
        candidate_metrics: object,
        paging_inputs: object,
        *,
        mode: str,
        visible_page_count: int,
    ) -> tuple[float, float]:
        del paging_inputs
        sizing_calls.append((mode, visible_page_count, candidate_metrics.scene_width))
        if mode != "page_window":
            raise AssertionError(f"unexpected mode: {mode}")
        assert visible_page_count == 2
        return candidate_metrics.scene_width, candidate_metrics.scene_height

    monkeypatch.setattr(
        adaptive_paging_module._Managed2DSceneFactory,
        "metrics_for_page_width",
        fake_metrics_for_page_width,
    )
    monkeypatch.setattr(adaptive_paging_module, "axes_viewport_ratio", lambda _axes: 2.0)
    monkeypatch.setattr(
        adaptive_paging_module,
        "_viewport_size_for_mode",
        fake_viewport_size_for_mode,
    )

    try:
        best_page_width = scene_factory.best_page_width_for_axes(
            axes,
            mode="page_window",
            visible_page_count=2,
        )
    finally:
        plt.close(figure)

    assert best_page_width == pytest.approx(20.0)
    assert metrics_calls == [float("inf")]
    assert sizing_calls == [("page_window", 2, 20.0)]


def test_draw_quantum_circuit_page_window_renders_requested_page_inside_viewport() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.page_box is not None
    assert page_window.total_pages >= 2

    initial_x_max = axes.get_xlim()[1]
    page_window.page_box.set_val("2")

    x_min, x_max = axes.get_xlim()
    y_label = _text_artist_by_text(axes, "Y")

    assert x_max < initial_x_max
    assert x_min <= y_label.get_position()[0] <= x_max
    plt.close(figure)


def test_draw_quantum_circuit_page_window_renders_all_requested_pages_inside_viewport() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=64, wire_count=2),
        style={"max_page_width": 4.0},
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.page_box is not None
    assert page_window.visible_pages_box is not None
    assert page_window.total_pages >= 4

    page_window.page_box.set_val("2")

    single_page_gate_count = len(_matching_text_artists(axes, "RX\n0.5"))

    page_window.visible_pages_box.set_val("2")

    x_min, x_max = axes.get_xlim()
    gate_positions = [
        text_artist.get_position()[0] for text_artist in _matching_text_artists(axes, "RX\n0.5")
    ]

    assert len(gate_positions) == single_page_gate_count * 2
    assert all(x_min <= x_position <= x_max for x_position in gate_positions)
    plt.close(figure)


def test_draw_quantum_circuit_page_window_keeps_variable_width_gate_labels_inside_viewport() -> (
    None
):
    figure, axes = draw_quantum_circuit(
        _variable_width_slider_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.2, 3.0),
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None
    assert page_window.visible_pages_box is not None
    assert page_window.total_pages >= 2

    page_window.visible_pages_box.set_val("2")

    x_min, x_max = axes.get_xlim()
    rendered_long_labels = [
        text_artist.get_position()[0]
        for text_artist in axes.texts
        if normalize_rendered_text(text_artist.get_text()).startswith("LONGSUPERGATE")
    ]

    assert rendered_long_labels
    assert all(x_min <= x_position <= x_max for x_position in rendered_long_labels)
    plt.close(figure)


def test_draw_quantum_circuit_page_window_keeps_scaled_named_gate_font_at_style_size() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="Circuit - 42",
                        target_wires=("q0",),
                        metadata={"compact_width": True},
                    )
                ]
            ),
            *[
                LayerIR(
                    operations=[
                        OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q0",))
                    ]
                )
                for _ in range(8)
            ],
        ],
    )
    style = DrawStyle(max_page_width=4.0)
    figure, axes = draw_quantum_circuit(
        circuit,
        style=style,
        figsize=(10.0, 4.0),
        page_window=True,
        show=False,
    )

    try:
        page_window = get_page_window(figure)
        assert page_window is not None
        assert page_window.page_box is not None
        page_window.page_box.set_val("2")
        rendered_label = next(
            text_artist
            for text_artist in axes.texts
            if normalize_rendered_text(text_artist.get_text()) == "circuit 42"
        )

        assert page_window.total_pages > 1
        assert rendered_label.get_fontsize() == pytest.approx(style.font_size)
    finally:
        plt.close(figure)


def test_draw_quantum_circuit_page_window_preserves_columns_from_expanded_raw_layers() -> None:
    raw_layer_count = 10
    figure, axes = draw_quantum_circuit(
        _overlapping_raw_layer_ir(raw_layer_count=raw_layer_count),
        style={"max_page_width": 4.0},
        figsize=(3.0, 3.0),
        page_window=True,
        show=False,
    )

    page_window = get_page_window(figure)

    assert page_window is not None

    seen_labels: set[str] = set()
    for page_number in range(1, page_window.total_pages + 1):
        page_window.page_box.set_val(str(page_number))
        seen_labels.update(
            normalize_rendered_text(text_artist.get_text())
            for text_artist in axes.texts
            if normalize_rendered_text(text_artist.get_text()).startswith("H")
        )

    assert seen_labels == {f"H{layer_index}" for layer_index in range(raw_layer_count)}
    plt.close(figure)
