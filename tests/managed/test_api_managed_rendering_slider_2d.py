# ruff: noqa: F403, F405
import quantum_circuit_drawer.renderers._matplotlib_text as matplotlib_text_module
from tests._api_managed_rendering_support import *


def test_draw_quantum_circuit_shows_managed_figures_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show_calls: list[bool] = []

    def fake_show(*args: object, **kwargs: object) -> None:
        show_calls.append(True)

    monkeypatch.setattr(plt, "show", fake_show)

    figure, axes = draw_quantum_circuit(build_sample_ir())

    assert axes.figure is figure
    assert show_calls == [True]
    assert get_page_slider(figure) is None
    plt.close(figure)


def test_draw_quantum_circuit_skips_show_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_show(*args: object, **kwargs: object) -> None:
        raise AssertionError("matplotlib.pyplot.show should not be called when show=False")

    monkeypatch.setattr(plt, "show", fail_show)

    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert isinstance(figure.canvas, FigureCanvasAgg)
    assert axes.figure is figure
    plt.close(figure)


def test_draw_quantum_circuit_uses_agg_canvas_for_managed_show_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_figure(*args: object, **kwargs: object) -> None:
        raise AssertionError("matplotlib.pyplot.figure should not be called when show=False")

    monkeypatch.setattr(plt, "figure", fail_figure)

    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert isinstance(figure.canvas, FigureCanvasAgg)
    assert axes.figure is figure
    plt.close(figure)


def test_draw_quantum_circuit_uses_agg_canvas_and_skips_hover_state_for_hidden_2d_hover_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.renderers._matplotlib_figure as figure_support

    captured_use_agg: list[bool] = []
    original_create_managed_figure = figure_support.create_managed_figure

    def capture_create_managed_figure(*args: object, **kwargs: object) -> tuple[Figure, object]:
        captured_use_agg.append(bool(kwargs.get("use_agg", False)))
        return original_create_managed_figure(*args, **kwargs)

    monkeypatch.setattr(plt, "get_backend", lambda: "nbagg")
    monkeypatch.setattr(figure_support, "create_managed_figure", capture_create_managed_figure)

    figure, axes = draw_quantum_circuit(build_sample_ir(), hover=True, show=False)

    assert captured_use_agg == [True]
    assert isinstance(figure.canvas, FigureCanvasAgg)
    assert get_hover_state(axes) is None
    plt.close(figure)


def test_draw_quantum_circuit_does_not_show_existing_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    figure, axes = plt.subplots()

    def fail_show(*args: object, **kwargs: object) -> None:
        raise AssertionError("matplotlib.pyplot.show should not be called for caller-managed axes")

    monkeypatch.setattr(plt, "show", fail_show)

    result = draw_quantum_circuit(build_sample_ir(), ax=axes)

    assert result is axes
    plt.close(figure)


def test_draw_quantum_circuit_rejects_page_slider_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="page_slider"):
        draw_quantum_circuit(build_sample_ir(), ax=axes, page_slider=True)

    plt.close(figure)


def test_draw_quantum_circuit_adds_discrete_page_slider_for_wrapped_managed_figures() -> None:
    paged_scene = LayoutEngine().compute(build_wrapped_ir(), DrawStyle(max_page_width=4.0))

    assert len(paged_scene.pages) > 1

    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
    assert page_slider is not None
    slider_axes = page_slider.horizontal_axes
    assert slider_axes is not None
    _, slider_bottom, _, slider_height = slider_axes.get_position().bounds
    horizontal_slider = page_slider.horizontal_slider
    assert horizontal_slider is not None

    assert len(figure.axes) == 2
    assert page_slider.vertical_slider is None
    assert page_slider.start_column == 0
    assert page_slider.wire_filter_button is None
    assert page_slider.ancilla_toggle_button is None
    assert page_slider.block_toggle_button is None
    assert slider_axes.get_facecolor() == pytest.approx(mcolors.to_rgba("#171221"))
    assert horizontal_slider.label.get_text() == ""
    assert horizontal_slider._handle.get_markerfacecolor() == "#b794f6"
    assert slider_bottom > 0.1
    assert slider_height >= 0.04
    assert axes.get_xlim()[0] == pytest.approx(0.0)
    initial_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}

    assert "H" in initial_labels
    assert "Y" not in initial_labels

    horizontal_slider.set_val(horizontal_slider.valmax)

    moved_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}

    assert page_slider.start_column == page_slider.max_start_column
    assert axes.get_xlim()[0] == pytest.approx(0.0)
    assert "H" not in moved_labels
    assert "Y" in moved_labels
    plt.close(figure)


def test_draw_quantum_circuit_page_slider_uses_width_budgeted_column_windows() -> None:
    figure, axes = draw_quantum_circuit(
        _variable_width_slider_ir(),
        style={"max_page_width": 4.5},
        page_slider=True,
        show=False,
        figsize=(7.0, 4.0),
    )

    page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))

    assert page_slider is not None
    assert page_slider.horizontal_slider is not None

    initial_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}
    assert {label for label in initial_labels if label in {"H", "X", "Y", "Z"}} == {"H"}

    page_slider.horizontal_slider.set_val(2.0)

    moved_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}
    assert {label for label in moved_labels if label in {"H", "X", "Y", "Z"}} == {"X", "Y", "Z"}

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_tracks_normalized_draw_columns() -> None:
    circuit = _overlapping_raw_layer_ir(raw_layer_count=4)
    figure, _ = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 2.0},
        page_slider=True,
        show=False,
        figsize=(4.0, 3.0),
    )

    page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
    normalized_column_count = len(normalize_draw_layers(circuit))

    assert page_slider is not None
    assert page_slider.horizontal_slider is not None
    assert page_slider.total_column_count == normalized_column_count
    assert len(page_slider.column_widths) == normalized_column_count
    assert page_slider.max_start_column > max(0, len(circuit.layers) - 1)

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_uses_user_figsize_for_initial_window_budget() -> None:
    default_figure, _ = draw_quantum_circuit(
        _variable_width_slider_ir(),
        style={"max_page_width": 4.5},
        page_slider=True,
        show=False,
    )
    figure, axes = draw_quantum_circuit(
        _variable_width_slider_ir(),
        style={"max_page_width": 4.5},
        page_slider=True,
        show=False,
        figsize=(12.0, 4.0),
    )

    default_page_slider = cast(Managed2DPageSliderState | None, get_page_slider(default_figure))
    page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))

    assert default_page_slider is not None
    assert page_slider is not None
    assert page_slider.horizontal_slider is not None
    assert page_slider.viewport_width > default_page_slider.viewport_width
    assert axes.get_xlim()[1] - axes.get_xlim()[0] == pytest.approx(page_slider.viewport_width)

    page_slider.horizontal_slider.set_val(2.0)

    visible_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}

    assert {label for label in visible_labels if label in {"H", "X", "Y", "Z"}} == {"X", "Y", "Z"}

    plt.close(default_figure)
    plt.close(figure)


def test_draw_quantum_circuit_saves_paged_figure_before_adding_continuous_slider(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path,
) -> None:
    output = sandbox_tmp_path / "wrapped-circuit.png"
    original_savefig = Figure.savefig
    saved_axes_counts: list[int] = []

    def count_savefig(self: Figure, *args: object, **kwargs: object) -> None:
        saved_axes_counts.append(len(self.axes))
        original_savefig(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", count_savefig)

    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        output=output,
        page_slider=True,
        show=False,
    )

    assert axes.figure is figure
    assert_saved_image_has_visible_content(output)
    assert saved_axes_counts == [1]
    assert len(figure.axes) == 2
    plt.close(figure)


def test_draw_quantum_circuit_page_slider_with_output_reuses_single_managed_figure(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path,
) -> None:
    import quantum_circuit_drawer.renderers._matplotlib_figure as figure_support
    import quantum_circuit_drawer.renderers.matplotlib_renderer as renderer_module

    output = sandbox_tmp_path / "wrapped-circuit.png"
    create_calls = 0
    original_create_managed_figure = figure_support.create_managed_figure

    def count_create_managed_figure(*args: object, **kwargs: object) -> tuple[Figure, object]:
        nonlocal create_calls
        create_calls += 1
        return original_create_managed_figure(*args, **kwargs)

    monkeypatch.setattr(figure_support, "create_managed_figure", count_create_managed_figure)
    monkeypatch.setattr(renderer_module, "create_managed_figure", count_create_managed_figure)

    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        output=output,
        page_slider=True,
        show=False,
    )

    assert axes.figure is figure
    assert_saved_image_has_visible_content(output)
    assert create_calls == 1
    plt.close(figure)


def test_draw_quantum_circuit_skips_show_warning_on_non_interactive_backend() -> None:
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        figure, axes = draw_quantum_circuit(build_sample_ir())

    show_warnings = [
        warning for warning in caught_warnings if "cannot be shown" in str(warning.message)
    ]

    assert axes.figure is figure
    assert not show_warnings
    plt.close(figure)


def test_show_managed_figure_calls_patched_show_on_non_interactive_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show_calls: list[bool] = []
    figure, _ = draw_quantum_circuit(build_sample_ir(), show=False)

    def fake_show(*args: object, **kwargs: object) -> None:
        show_calls.append(True)

    monkeypatch.setattr(plt, "show", fake_show)

    show_figure_if_supported(figure, show=True)

    assert show_calls == [True]
    plt.close(figure)


def test_draw_quantum_circuit_managed_figures_use_more_horizontal_canvas_space() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        show=False,
    )

    left, _, width, _ = axes.get_position().bounds
    right_gap = 1.0 - (left + width)

    assert width > 0.68
    assert left < 0.16
    assert right_gap < 0.16

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_uses_more_horizontal_space_for_taller_circuits() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )
    page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))

    left, _, width, _ = axes.get_position().bounds
    right_gap = 1.0 - (left + width)

    assert page_slider is not None
    assert axes.get_xlim()[1] - axes.get_xlim()[0] == pytest.approx(page_slider.viewport_width)
    assert axes.get_xlim()[1] - axes.get_xlim()[0] > 4.5
    assert width > 0.6
    assert left < 0.16
    assert right_gap < 0.16

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_normalizes_style_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.drawing.pipeline as pipeline_module
    import quantum_circuit_drawer.layout.engine as engine_module

    normalize_style_calls = 0
    original_pipeline_normalize_style = pipeline_module.normalize_style
    original_engine_normalize_style = engine_module.normalize_style

    def count_pipeline_normalize_style(style: object) -> DrawStyle:
        nonlocal normalize_style_calls
        normalize_style_calls += 1
        return original_pipeline_normalize_style(style)

    def count_engine_normalize_style(style: DrawStyle) -> DrawStyle:
        nonlocal normalize_style_calls
        normalize_style_calls += 1
        return original_engine_normalize_style(style)

    monkeypatch.setattr(pipeline_module, "normalize_style", count_pipeline_normalize_style)
    monkeypatch.setattr(engine_module, "normalize_style", count_engine_normalize_style)

    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    assert axes.figure is figure
    assert normalize_style_calls == 1
    plt.close(figure)


def test_draw_quantum_circuit_reduces_gate_font_size_for_many_wrapped_pages() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        show=False,
    )

    gate_label = _text_artist_by_text(axes, "RX\n0.5")

    assert gate_label.get_fontsize() < 10.0

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_keeps_gate_font_readable() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    gate_label = _text_artist_by_text(axes, "RX\n0.5")

    assert gate_label.get_fontsize() > 10.0

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_keeps_text_size_stable_after_redraw() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )
    page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))

    assert page_slider is not None
    horizontal_slider = page_slider.horizontal_slider
    assert horizontal_slider is not None

    figure.canvas.draw()
    initial_font_size = _font_size_by_text(axes, "RX\n0.5")
    horizontal_slider.set_val(horizontal_slider.valmax / 2.0)
    figure.canvas.draw()
    resized_font_size = _font_size_by_text(axes, "RX\n0.5")

    assert initial_font_size < 20.0
    assert resized_font_size < 20.0

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_uses_stable_gate_font_size_before_first_draw() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    gate_label = _text_artist_by_text(axes, "RX\n0.5")

    assert gate_label.get_fontsize() < 20.0

    plt.close(figure)


def test_draw_quantum_circuit_uses_wider_pages_on_wide_axes_without_slider() -> None:
    circuit = build_dense_rotation_ir(layer_count=24)
    style = DrawStyle(max_page_width=12.0)
    narrow_figure, narrow_axes = plt.subplots(figsize=(3.2, 12.0))
    wide_figure, wide_axes = plt.subplots(figsize=(12.0, 3.2))

    draw_quantum_circuit(
        circuit,
        style=style,
        ax=narrow_axes,
    )
    draw_quantum_circuit(
        circuit,
        style=style,
        ax=wide_axes,
    )

    narrow_scene, narrow_page_width = _adapted_scene_for_axes(
        circuit,
        narrow_axes,
        style=style,
    )
    wide_scene, wide_page_width = _adapted_scene_for_axes(
        circuit,
        wide_axes,
        style=style,
    )

    assert len(wide_scene.pages) < len(narrow_scene.pages)
    assert wide_page_width > narrow_page_width
    assert get_viewport_width(wide_figure, default=0.0) > get_viewport_width(
        narrow_figure,
        default=0.0,
    )

    plt.close(narrow_figure)
    plt.close(wide_figure)


def test_draw_quantum_circuit_initial_2d_layout_expands_past_initial_page_width_on_wide_axes() -> (
    None
):
    circuit = build_dense_rotation_ir(layer_count=24)
    style = DrawStyle(max_page_width=4.0)
    figure, axes = plt.subplots(figsize=(18.0, 3.0))

    draw_quantum_circuit(
        circuit,
        style=style,
        ax=axes,
    )

    _, effective_page_width = _adapted_scene_for_axes(circuit, axes, style=style)

    assert effective_page_width > 4.0
    assert get_viewport_width(figure, default=0.0) > 4.0

    plt.close(figure)


def test_draw_quantum_circuit_keeps_caller_owned_2d_layout_frozen_after_resize() -> None:
    figure, axes = plt.subplots(figsize=(3.2, 12.0))

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 20.0},
        ax=axes,
    )

    initial_xlim = axes.get_xlim()
    initial_ylim = axes.get_ylim()
    initial_viewport_width = get_viewport_width(figure, default=0.0)

    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    assert axes.get_xlim() == pytest.approx(initial_xlim)
    assert axes.get_ylim() == pytest.approx(initial_ylim)
    assert get_viewport_width(figure, default=0.0) == pytest.approx(initial_viewport_width)

    plt.close(figure)


def test_draw_quantum_circuit_resize_keeps_hover_disabled_when_hover_is_disabled() -> None:
    figure, axes = plt.subplots(figsize=(3.2, 12.0))

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 20.0},
        ax=axes,
        show=False,
    )

    assert get_hover_state(axes) is None

    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    assert get_hover_state(axes) is None

    plt.close(figure)


def test_draw_quantum_circuit_hidden_hover_render_skips_hover_metadata_even_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        hover=True,
        show=False,
        figsize=(3.2, 12.0),
    )

    assert get_hover_state(axes) is None

    plt.close(figure)


def test_draw_quantum_circuit_hidden_output_hover_render_skips_hover_metadata() -> None:
    output = Path.cwd() / ".hidden-hover-output.png"
    figure: Figure | None = None
    try:
        figure, axes = draw_quantum_circuit(
            build_dense_rotation_ir(layer_count=24),
            style={"max_page_width": 4.0},
            hover=True,
            show=False,
            output=output,
        )

        assert_saved_image_has_visible_content(output)
        assert get_hover_state(axes) is None
    finally:
        if figure is not None:
            plt.close(figure)
        output.unlink(missing_ok=True)


def test_draw_quantum_circuit_managed_figure_uses_viewport_adaptive_paging_without_slider() -> None:
    circuit = build_dense_rotation_ir(layer_count=24)
    style = DrawStyle(max_page_width=4.0)
    strict_scene = LayoutEngine().compute(circuit, style)
    figure, axes = draw_quantum_circuit(circuit, style=style, show=False)
    adapted_scene, adapted_page_width = _adapted_scene_for_axes(circuit, axes, style=style)
    _, figure_height = figure.get_size_inches()

    assert figure_height == pytest.approx(max(2.1, strict_scene.page_height * 0.72))
    assert len(adapted_scene.pages) <= len(strict_scene.pages) // 2
    assert adapted_page_width > strict_scene.pages[0].content_width * 2.0
    assert get_viewport_width(figure, default=0.0) == pytest.approx(adapted_scene.width)

    plt.close(figure)


def test_draw_quantum_circuit_managed_figure_adapts_paging_to_explicit_figsize() -> None:
    circuit = build_dense_rotation_ir(layer_count=24)
    style = DrawStyle(max_page_width=12.0)
    narrow_figure, narrow_axes = draw_quantum_circuit(
        circuit,
        style=style,
        show=False,
        figsize=(3.2, 12.0),
    )
    wide_figure, wide_axes = draw_quantum_circuit(
        circuit,
        style=style,
        show=False,
        figsize=(12.0, 3.2),
    )

    _, narrow_page_width = _adapted_scene_for_axes(circuit, narrow_axes, style=style)
    _, wide_page_width = _adapted_scene_for_axes(circuit, wide_axes, style=style)

    assert wide_page_width > narrow_page_width
    assert get_viewport_width(wide_figure, default=0.0) > get_viewport_width(
        narrow_figure,
        default=0.0,
    )

    plt.close(narrow_figure)
    plt.close(wide_figure)


def test_draw_quantum_circuit_uses_explicit_figsize_for_managed_figures() -> None:
    circuit = build_dense_rotation_ir(layer_count=18, wire_count=10)
    figure, axes = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 8.0},
        show=False,
        figsize=(7.5, 2.75),
    )

    assert figure.get_size_inches() == pytest.approx((7.5, 2.75))
    assert get_viewport_width(figure, default=0.0) > 0.0

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_keeps_viewport_width_attached_to_figure() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    assert get_page_slider(figure) is not None
    assert get_viewport_width(figure, default=0.0) == pytest.approx(
        axes.get_xlim()[1] - axes.get_xlim()[0]
    )
    plt.close(figure)


def test_draw_quantum_circuit_adds_vertical_page_slider_for_tall_managed_figures() -> None:
    figure, axes = draw_quantum_circuit(
        _tall_measured_ir(quantum_wire_count=24, layer_count=2),
        style={"max_page_width": 12.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert page_slider is not None
    assert page_slider.horizontal_slider is None
    assert page_slider.vertical_slider is not None
    assert page_slider.vertical_axes is not None
    assert page_slider.visible_qubits_box is not None
    assert page_slider.visible_qubits_decrement_button is not None
    assert page_slider.visible_qubits_increment_button is not None
    assert page_slider.visible_qubits_axes is not None
    assert page_slider.visible_qubits == 15
    assert page_slider.vertical_axes.get_position().width < 0.025
    assert page_slider.visible_qubits_axes.get_position().width < 0.06
    assert page_slider.visible_qubits_axes.get_position().height < 0.05
    assert page_slider.visible_qubits_axes.get_title() == ""
    assert page_slider.vertical_axes.get_facecolor() == pytest.approx(mcolors.to_rgba("#171221"))
    assert page_slider.visible_qubits_axes.get_facecolor() == pytest.approx(
        mcolors.to_rgba("#171221")
    )
    assert page_slider.vertical_slider.label.get_text() == ""
    assert page_slider.start_row == 0
    assert len(figure.axes) == 6
    assert page_slider.wire_filter_button is not None
    assert page_slider.ancilla_toggle_button is None
    assert page_slider.block_toggle_button is None

    visible_qubits_box = page_slider.visible_qubits_box
    assert visible_qubits_box is not None
    assert mcolors.to_rgba(visible_qubits_box.cursor.get_color()) == pytest.approx(
        mcolors.to_rgba(visible_qubits_box.text_disp.get_color())
    )

    initial_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}
    assert "q0" in initial_labels
    assert "q23" not in initial_labels

    vertical_slider = page_slider.vertical_slider
    assert vertical_slider is not None

    main_bounds = axes.get_position().bounds
    vertical_bounds = page_slider.vertical_axes.get_position().bounds
    assert vertical_bounds[1] > main_bounds[1] + 0.03
    assert vertical_bounds[1] + vertical_bounds[3] < (main_bounds[1] + main_bounds[3]) - 0.03

    vertical_slider.set_val(vertical_slider.valmin)

    moved_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}

    assert page_slider.start_row == page_slider.max_start_row
    assert axes.get_xlim()[0] == pytest.approx(0.0)
    assert axes.get_ylim()[1] == pytest.approx(0.0)
    assert "q0" not in moved_labels
    assert "q23" in moved_labels

    vertical_slider.set_val(vertical_slider.valmax)

    reset_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}

    assert page_slider.start_row == 0
    assert "q0" in reset_labels
    assert "q23" not in reset_labels
    plt.close(figure)


def test_draw_quantum_circuit_visible_qubits_stepper_buttons_adjust_row_window() -> None:
    figure, _ = draw_quantum_circuit(
        _tall_measured_ir(quantum_wire_count=24, layer_count=2),
        style={"max_page_width": 12.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert page_slider is not None
    assert page_slider.visible_qubits_decrement_button is not None
    assert page_slider.visible_qubits_increment_button is not None

    page_slider.visible_qubits_increment_button._observers.process("clicked", None)

    assert page_slider.visible_qubits == 16
    assert page_slider.visible_qubits_increment_button is not None

    page_slider.visible_qubits_decrement_button._observers.process("clicked", None)

    assert page_slider.visible_qubits == 15
    plt.close(figure)


def test_draw_quantum_circuit_adds_horizontal_and_vertical_page_sliders_for_dense_managed_figures() -> (
    None
):
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert page_slider is not None
    assert page_slider.horizontal_slider is not None
    assert page_slider.vertical_slider is not None
    assert page_slider.horizontal_axes is not None
    assert page_slider.vertical_axes is not None
    assert page_slider.visible_qubits_box is not None
    assert page_slider.visible_qubits_decrement_button is not None
    assert page_slider.visible_qubits_increment_button is not None
    assert len(figure.axes) == 6
    assert page_slider.wire_filter_button is None
    assert page_slider.ancilla_toggle_button is None
    assert page_slider.block_toggle_button is None

    initial_xlim = axes.get_xlim()
    initial_ylim = axes.get_ylim()
    initial_figure_size = tuple(float(value) for value in figure.get_size_inches())
    horizontal_slider = page_slider.horizontal_slider
    vertical_slider = page_slider.vertical_slider
    visible_qubits_box = page_slider.visible_qubits_box
    assert horizontal_slider is not None
    assert vertical_slider is not None
    assert visible_qubits_box is not None

    initial_horizontal_max = horizontal_slider.valmax
    initial_vertical_max = vertical_slider.valmax

    horizontal_track_bounds = horizontal_slider.track.get_bbox().bounds
    vertical_track_bounds = vertical_slider.track.get_bbox().bounds
    assert horizontal_track_bounds[0] == pytest.approx(0.0, abs=0.02)
    assert horizontal_track_bounds[2] == pytest.approx(1.0, abs=0.02)
    assert vertical_track_bounds[1] == pytest.approx(0.0, abs=0.02)
    assert vertical_track_bounds[3] == pytest.approx(1.0, abs=0.02)

    visible_qubits_box.set_val("8")

    assert page_slider.visible_qubits == 8
    assert page_slider.horizontal_slider is not None
    assert page_slider.vertical_slider is not None
    assert page_slider.horizontal_slider.valmax == initial_horizontal_max
    assert page_slider.vertical_slider.valmax > initial_vertical_max
    assert axes.get_xlim()[1] - axes.get_xlim()[0] < initial_xlim[1] - initial_xlim[0]
    assert axes.get_ylim()[0] - axes.get_ylim()[1] < initial_ylim[0] - initial_ylim[1]
    assert tuple(float(value) for value in figure.get_size_inches()) != pytest.approx(
        initial_figure_size
    )

    visible_qubits_box = page_slider.visible_qubits_box
    assert visible_qubits_box is not None

    visible_qubits_box.set_val("24")

    assert page_slider.visible_qubits == 24
    assert page_slider.vertical_slider is None
    assert page_slider.vertical_axes is None

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_preserves_control_widgets_during_scroll() -> None:
    figure, _ = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert page_slider is not None
    assert page_slider.horizontal_slider is not None
    assert page_slider.vertical_slider is not None
    assert page_slider.visible_qubits_box is not None
    assert page_slider.visible_qubits_decrement_button is not None
    assert page_slider.visible_qubits_increment_button is not None

    horizontal_slider = page_slider.horizontal_slider
    vertical_slider = page_slider.vertical_slider
    visible_qubits_box = page_slider.visible_qubits_box
    visible_qubits_decrement_button = page_slider.visible_qubits_decrement_button
    visible_qubits_increment_button = page_slider.visible_qubits_increment_button

    horizontal_slider.set_val(min(horizontal_slider.valmax, 2.0))
    vertical_slider.set_val(min(vertical_slider.valmax, 2.0))

    assert page_slider.horizontal_slider is horizontal_slider
    assert page_slider.vertical_slider is vertical_slider
    assert page_slider.visible_qubits_box is visible_qubits_box
    assert page_slider.visible_qubits_decrement_button is visible_qubits_decrement_button
    assert page_slider.visible_qubits_increment_button is visible_qubits_increment_button

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_keeps_main_axes_above_slider_row() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert page_slider is not None
    assert page_slider.horizontal_axes is not None
    assert axes.get_zorder() > page_slider.horizontal_axes.get_zorder()

    plt.close(figure)


def test_draw_quantum_circuit_visible_qubits_box_counts_classical_register_row() -> None:
    figure, _ = draw_quantum_circuit(
        _tall_measured_ir(quantum_wire_count=18),
        style={"max_page_width": 12.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert page_slider is not None
    assert page_slider.vertical_slider is not None
    assert page_slider.visible_qubits_box is not None
    assert page_slider.visible_qubits == 15

    page_slider.visible_qubits_box.set_val("19")

    assert page_slider.visible_qubits == 19
    assert page_slider.vertical_slider is None
    assert page_slider.vertical_axes is None

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_clips_windowed_multiqubit_text() -> None:
    figure, axes = draw_quantum_circuit(
        _vertical_window_multiqubit_ir(),
        style={"max_page_width": 12.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert page_slider is not None
    assert page_slider.visible_qubits_box is not None
    page_slider.visible_qubits_box.set_val("2")
    assert page_slider.vertical_slider is not None

    page_slider.vertical_slider.set_val(float(page_slider.max_start_row - 1))

    visible_labels = {normalize_rendered_text(text_artist.get_text()) for text_artist in axes.texts}

    assert "BIG" in visible_labels
    assert "q0" not in visible_labels
    assert "q1" in visible_labels
    assert all(text_artist.get_clip_on() for text_artist in axes.texts)

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_keeps_qiskit_measurement_tail_in_one_window() -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the QAOA slider regression test")

    from examples._shared import ExampleRequest
    from examples.qiskit_qaoa import build_circuit

    figure, _ = draw_quantum_circuit(
        build_circuit(
            ExampleRequest(
                qubits=18,
                columns=12,
                mode="slider",
                view="2d",
                topology="line",
                seed=7,
                output=None,
                show=False,
                figsize=(10.0, 5.5),
                hover=False,
                hover_matrix="auto",
                hover_matrix_max_qubits=6,
                hover_show_size=True,
            )
        ),
        page_slider=True,
        show=False,
    )

    page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))

    assert page_slider is not None
    assert page_slider.horizontal_slider is not None

    split_window_starts = [
        start_column
        for start_column in range(page_slider.max_start_column + 1)
        if len(_horizontal_scene_for_start_column(page_slider, start_column).pages) > 1
    ]

    assert split_window_starts == []

    for start_column in range(
        max(0, page_slider.max_start_column - 50), page_slider.max_start_column + 1
    ):
        page_slider.horizontal_slider.set_val(float(start_column))
        assert len(page_slider.scene.pages) == 1

    plt.close(figure)


def test_draw_quantum_circuit_keeps_managed_2d_layout_frozen_after_resize() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        show=False,
        figsize=(3.2, 12.0),
    )

    initial_xlim = axes.get_xlim()
    initial_ylim = axes.get_ylim()
    initial_viewport_width = get_viewport_width(figure, default=0.0)

    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    assert axes.get_xlim() == pytest.approx(initial_xlim)
    assert axes.get_ylim() == pytest.approx(initial_ylim)
    assert get_viewport_width(figure, default=0.0) == pytest.approx(initial_viewport_width)

    plt.close(figure)


def test_draw_quantum_circuit_managed_figure_resize_keeps_hover_cleanup_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        hover=True,
        figsize=(3.2, 12.0),
    )

    initial_hover_state = get_hover_state(axes)

    assert initial_hover_state is not None

    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    resized_hover_state = get_hover_state(axes)

    assert resized_hover_state is not None

    plt.close(figure)


def test_draw_quantum_circuit_managed_figure_computes_adaptive_layout_once_even_after_resize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.managed.viewport as viewport_module

    circuit = build_dense_rotation_ir(layer_count=24)
    viewport_calls = 0
    original_viewport_adaptive_paged_scene = viewport_module.viewport_adaptive_paged_scene

    def count_viewport_adaptive_paged_scene(
        _circuit: CircuitIR,
        _layout_engine: object,
        _style: DrawStyle,
        _axes: object,
        *,
        hover_enabled: bool = True,
        initial_scene: LayoutScene | None = None,
    ) -> tuple[LayoutScene, float]:
        nonlocal viewport_calls
        viewport_calls += 1
        return original_viewport_adaptive_paged_scene(
            _circuit,
            cast("LayoutEngine", _layout_engine),
            _style,
            cast("Axes", _axes),
            hover_enabled=hover_enabled,
            initial_scene=initial_scene,
        )

    monkeypatch.setattr(
        viewport_module,
        "viewport_adaptive_paged_scene",
        count_viewport_adaptive_paged_scene,
    )

    figure, _ = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 4.0},
        show=False,
        figsize=(3.2, 12.0),
    )

    assert viewport_calls == 1

    figure.canvas.draw()
    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    assert viewport_calls == 1

    plt.close(figure)


def test_draw_quantum_circuit_slider_reuses_text_fit_cache_between_redraws(
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
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
        figsize=(4.0, 3.0),
    )

    page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))

    assert page_slider is not None
    assert page_slider.horizontal_slider is not None
    assert page_slider.max_start_column > 0

    page_slider.horizontal_slider.set_val(1.0)
    page_slider.horizontal_slider.set_val(0.0)

    assert len(cache_ids) == 1
    plt.close(figure)


def test_show_managed_figure_skips_builtin_show_for_notebook_backends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.renderers._render_support as render_support

    figure, _ = draw_quantum_circuit(build_sample_ir(), show=False)
    show_calls: list[bool] = []

    def fake_builtin_show(*args: object, **kwargs: object) -> None:
        show_calls.append(True)

    fake_builtin_show.__module__ = "matplotlib.pyplot"

    monkeypatch.setattr(plt, "show", fake_builtin_show)
    monkeypatch.setattr(render_support, "figure_backend_name", lambda _figure: "nbagg")

    show_figure_if_supported(figure, show=True)

    assert show_calls == []
    plt.close(figure)


def test_draw_quantum_circuit_reduces_wrapped_gate_font_progressively_with_page_count() -> None:
    page_to_font_size: dict[int, float] = {}

    for layer_count in (5, 8, 29):
        circuit = build_dense_rotation_ir(layer_count=layer_count, wire_count=1)
        figure, axes = plt.subplots(figsize=(3.2, 12.0))
        style = DrawStyle(max_page_width=4.0)
        draw_quantum_circuit(circuit, style=style, ax=axes)
        adapted_scene, _ = _adapted_scene_for_axes(circuit, axes, style=style)

        page_to_font_size[len(adapted_scene.pages)] = _font_size_by_text(axes, "RX\n0.5")
        plt.close(figure)

    assert page_to_font_size[3] > page_to_font_size[4] > page_to_font_size[8]
    assert page_to_font_size[8] < page_to_font_size[3] * 0.85


def test_draw_quantum_circuit_tightens_multiline_line_spacing_for_smaller_gate_fonts() -> None:
    sparse_figure, sparse_axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=5, wire_count=1),
        style={"max_page_width": 12.0},
        show=False,
        figsize=(8.0, 3.0),
    )
    dense_figure, dense_axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=1),
        style={"max_page_width": 4.0},
        show=False,
        figsize=(3.2, 12.0),
    )

    sparse_label = _text_artist_by_text(sparse_axes, "RX\n0.5")
    dense_label = _text_artist_by_text(dense_axes, "RX\n0.5")

    assert dense_label.get_fontsize() < sparse_label.get_fontsize()
    assert dense_label._linespacing < sparse_label._linespacing  # type: ignore[attr-defined]

    plt.close(sparse_figure)
    plt.close(dense_figure)


def test_draw_quantum_circuit_uses_thinner_default_line_width_for_denser_initial_scene() -> None:
    sparse_figure, sparse_axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=6, wire_count=2),
        style={"max_page_width": 12.0},
        show=False,
        figsize=(8.0, 3.0),
    )
    dense_figure, dense_axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=10),
        style={"max_page_width": 4.0},
        show=False,
        figsize=(3.2, 12.0),
    )

    assert _gate_box_line_width(dense_axes) < _gate_box_line_width(sparse_axes)

    plt.close(sparse_figure)
    plt.close(dense_figure)


def test_draw_quantum_circuit_uses_thicker_default_line_width_for_larger_initial_figsize() -> None:
    circuit = build_dense_rotation_ir(layer_count=18, wire_count=8)
    small_figure, small_axes = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 6.0},
        show=False,
        figsize=(4.0, 3.0),
    )
    large_figure, large_axes = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 6.0},
        show=False,
        figsize=(12.0, 6.0),
    )

    assert _gate_box_line_width(large_axes) > _gate_box_line_width(small_axes)

    plt.close(small_figure)
    plt.close(large_figure)


def test_draw_quantum_circuit_keeps_default_line_width_frozen_after_resize() -> None:
    figure, axes = plt.subplots(figsize=(3.2, 12.0))
    circuit = build_dense_rotation_ir(layer_count=24, wire_count=8)

    draw_quantum_circuit(
        circuit,
        style={"max_page_width": 6.0},
        ax=axes,
    )

    initial_line_width = _gate_box_line_width(axes)

    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    assert _gate_box_line_width(axes) == pytest.approx(initial_line_width)

    plt.close(figure)


def test_draw_quantum_circuit_keeps_explicit_default_matching_line_width_unchanged() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=8),
        style=DrawStyle(max_page_width=6.0, line_width=1.6),
        show=False,
        figsize=(3.2, 12.0),
    )

    assert _gate_box_line_width(axes) == pytest.approx(1.6)

    plt.close(figure)


def test_draw_quantum_circuit_preserves_scene_margin_left_after_freezing_line_width() -> None:
    style = DrawStyle(max_page_width=6.0)
    figure, axes = draw_quantum_circuit(
        _long_label_margin_ir(),
        style=style,
        show=False,
        figsize=(6.0, 3.0),
    )

    adapted_scene, _ = _adapted_scene_for_axes(_long_label_margin_ir(), axes, style=style)

    assert adapted_scene.style.margin_left > DrawStyle().margin_left

    plt.close(figure)


def test_slider_viewport_width_falls_back_to_scene_width_for_zero_sized_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = build_sample_scene()
    figure, axes = create_managed_figure(scene, use_agg=True)

    monkeypatch.setattr(
        axes,
        "get_position",
        lambda *args, **kwargs: Bbox.from_bounds(0.0, 0.0, 0.0, 0.0),
    )

    assert managed_module.slider_viewport_width(axes, scene) == scene.width
    plt.close(figure)


def test_slider_viewport_width_tracks_subplots_adjusted_original_viewport() -> None:
    scene = build_sample_scene()
    figure, axes = create_managed_figure(scene, use_agg=True)
    figure.subplots_adjust(left=0.08, right=0.92, bottom=0.22, top=0.95)

    figure_width, figure_height = figure.get_size_inches()
    axes_position = axes.get_position(original=True)
    expected_ratio = (figure_width * figure.dpi * axes_position.width) / (
        figure_height * figure.dpi * axes_position.height
    )

    assert managed_module.slider_viewport_width(axes, scene) == pytest.approx(
        min(scene.width, scene.height * expected_ratio)
    )
    plt.close(figure)


def test_slider_viewport_width_remains_consistent_after_resize() -> None:
    scene = build_sample_scene()
    figure, axes = create_managed_figure(scene, use_agg=True)
    figure.subplots_adjust(left=0.06, right=0.94, bottom=0.2, top=0.96)
    figure.set_size_inches(11.5, 2.8, forward=True)

    figure_width, figure_height = figure.get_size_inches()
    axes_position = axes.get_position(original=True)
    expected_ratio = (figure_width * figure.dpi * axes_position.width) / (
        figure_height * figure.dpi * axes_position.height
    )

    assert managed_module.slider_viewport_width(axes, scene) == pytest.approx(
        min(scene.width, scene.height * expected_ratio)
    )
    plt.close(figure)


def test_configure_page_slider_skips_slider_when_viewport_already_fits_scene() -> None:
    scene = build_sample_scene()
    figure, axes = plt.subplots()
    attached_sliders: list[object] = []

    managed_module.configure_page_slider(
        figure=figure,
        axes=axes,
        scene=scene,
        viewport_width=scene.width,
        set_page_slider=lambda _figure, slider: attached_sliders.append(slider),
    )

    assert len(figure.axes) == 1
    assert attached_sliders == []
    plt.close(figure)


@pytest.mark.parametrize(
    ("backend_name", "expected"),
    [
        ("module://matplotlib.backends.backend_agg", "agg"),
        ("matplotlib.backends.backend_svg", "svg"),
        ("backend_qt5agg", "qt5agg"),
        ("Agg", "agg"),
    ],
)
def test_normalize_backend_name_strips_known_prefixes(
    backend_name: str,
    expected: str,
) -> None:
    assert normalize_backend_name(backend_name) == expected


def test_page_slider_figsize_respects_minimum_dimensions() -> None:
    assert managed_module.page_slider_figsize(1.0, 0.5) == pytest.approx((4.8, 3.0))


def test_figure_backend_name_prefers_canvas_type_name() -> None:
    figure, _ = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure_backend_name(figure) == "agg"
    plt.close(figure)
