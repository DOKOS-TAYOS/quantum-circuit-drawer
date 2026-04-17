from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

import quantum_circuit_drawer.renderers.matplotlib_primitives as matplotlib_primitives
from quantum_circuit_drawer._draw_managed_zoom import current_text_scale
from quantum_circuit_drawer.api import (
    _configure_page_slider,
    _figure_backend_name,
    _normalize_backend_name,
    _page_slider_figsize,
    _show_managed_figure_if_supported,
    _slider_viewport_width,
    draw_quantum_circuit,
)
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    create_managed_figure,
    get_auto_paging_state,
    get_base_font_size,
    get_page_slider,
    get_text_scaling_state,
)
from quantum_circuit_drawer.style import DrawStyle
from tests.support import (
    build_dense_rotation_ir,
    build_sample_ir,
    build_sample_scene,
    build_wrapped_ir,
)


def _zoom_text_scaling_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[
            WireIR(
                id="c0",
                index=0,
                kind=WireKind.CLASSICAL,
                label="c",
                metadata={"bundle_size": 23},
            )
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RZZ",
                        target_wires=("q0", "q1"),
                        parameters=(0.7,),
                    )
                ]
            ),
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                        metadata={"classical_bit_label": "dest"},
                    )
                ]
            ),
        ],
    )


def _font_size_by_text(axes: object, text: str) -> float:
    return next(
        text_artist.get_fontsize() for text_artist in axes.texts if text_artist.get_text() == text
    )


def _text_artist_by_text(axes: object, text: str) -> object:
    return next(text_artist for text_artist in axes.texts if text_artist.get_text() == text)


def _expected_box_fitted_font_size(
    axes: object,
    scene: object,
    *,
    text: str,
    width: float,
    height: float,
    height_fraction: float,
) -> float:
    text_artist = _text_artist_by_text(axes, text)
    text_scaling_state = get_text_scaling_state(axes)

    assert text_scaling_state is not None

    base_font_size = get_base_font_size(
        text_artist,
        default=float(text_artist.get_fontsize()),
    )
    return matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=matplotlib_primitives._build_gate_text_fitting_context(axes, scene),
        width=width,
        height=height,
        text=text,
        default_font_size=base_font_size,
        height_fraction=height_fraction,
        max_font_size=base_font_size * current_text_scale(axes, text_scaling_state),
        cache={},
    )


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


def test_draw_quantum_circuit_adds_continuous_page_slider_for_wrapped_managed_figures() -> None:
    paged_scene = LayoutEngine().compute(build_wrapped_ir(), DrawStyle(max_page_width=4.0))
    long_scene = LayoutEngine().compute(build_wrapped_ir(), DrawStyle(max_page_width=100.0))

    assert len(paged_scene.pages) > 1
    assert len(long_scene.pages) == 1

    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)
    slider_axes = figure.axes[1]
    _, slider_bottom, _, slider_height = slider_axes.get_position().bounds

    assert page_slider is not None
    assert len(figure.axes) == 2
    assert figure.subplotpars.bottom > 0.17
    assert slider_bottom < 0.1
    assert slider_height > 0.05
    assert axes.get_xlim()[0] == pytest.approx(0.0)
    assert axes.get_xlim()[1] > paged_scene.width
    assert axes.get_xlim()[1] <= long_scene.width
    assert axes.get_ylim() == pytest.approx((long_scene.height, 0.0))
    initial_viewport_width = axes.get_xlim()[1] - axes.get_xlim()[0]

    page_slider.set_val(page_slider.valmax)

    assert axes.get_xlim() == pytest.approx(
        (long_scene.width - initial_viewport_width, long_scene.width)
    )
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
    assert output.exists()
    assert output.stat().st_size > 0
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
    assert output.exists()
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

    _show_managed_figure_if_supported(figure, show=True)

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

    left, _, width, _ = axes.get_position().bounds
    right_gap = 1.0 - (left + width)

    assert width > 0.9
    assert left < 0.04
    assert right_gap < 0.04

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_normalizes_style_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer._draw_pipeline as pipeline_module
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

    gate_label = next(text for text in axes.texts if text.get_text() == "RX")

    assert gate_label.get_fontsize() < 10.0

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_keeps_gate_font_readable() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    gate_label = next(text for text in axes.texts if text.get_text() == "RX")

    assert gate_label.get_fontsize() > 10.0

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_keeps_text_size_stable_after_redraw() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )
    page_slider = get_page_slider(figure)

    assert page_slider is not None

    figure.canvas.draw()
    initial_font_size = max(text.get_fontsize() for text in axes.texts if text.get_text() == "RX")
    page_slider.set_val(page_slider.valmax / 2.0)
    figure.canvas.draw()
    resized_font_size = max(text.get_fontsize() for text in axes.texts if text.get_text() == "RX")

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

    gate_label = next(text for text in axes.texts if text.get_text() == "RX")

    assert gate_label.get_fontsize() < 20.0

    plt.close(figure)


def test_draw_quantum_circuit_uses_wider_pages_on_wide_axes_without_slider() -> None:
    narrow_figure, narrow_axes = plt.subplots(figsize=(3.2, 12.0))
    wide_figure, wide_axes = plt.subplots(figsize=(12.0, 3.2))

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 12.0},
        ax=narrow_axes,
    )
    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 12.0},
        ax=wide_axes,
    )

    narrow_state = get_auto_paging_state(narrow_axes)
    wide_state = get_auto_paging_state(wide_axes)

    assert narrow_state is not None
    assert wide_state is not None
    assert len(wide_state.scene.pages) < len(narrow_state.scene.pages)
    assert wide_state.effective_page_width > narrow_state.effective_page_width

    plt.close(narrow_figure)
    plt.close(wide_figure)


def test_draw_quantum_circuit_auto_paging_expands_past_initial_page_width_on_wide_axes() -> None:
    figure, axes = plt.subplots(figsize=(18.0, 3.0))

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        ax=axes,
    )

    auto_paging_state = get_auto_paging_state(axes)

    assert auto_paging_state is not None
    assert auto_paging_state.effective_page_width > 4.0

    plt.close(figure)


def test_draw_quantum_circuit_repages_when_axes_resize_without_slider() -> None:
    figure, axes = plt.subplots(figsize=(3.2, 12.0))

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 20.0},
        ax=axes,
    )

    initial_state = get_auto_paging_state(axes)

    assert initial_state is not None
    initial_page_count = len(initial_state.scene.pages)
    initial_page_width = initial_state.effective_page_width

    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    resized_state = get_auto_paging_state(axes)

    assert resized_state is not None
    assert len(resized_state.scene.pages) < initial_page_count
    assert resized_state.effective_page_width > initial_page_width

    plt.close(figure)


def test_draw_quantum_circuit_managed_figure_uses_viewport_adaptive_paging_without_slider() -> None:
    circuit = build_dense_rotation_ir(layer_count=24)
    strict_scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
    figure, axes = draw_quantum_circuit(circuit, style={"max_page_width": 4.0}, show=False)

    auto_paging_state = get_auto_paging_state(axes)
    _, figure_height = figure.get_size_inches()

    assert auto_paging_state is not None
    assert figure_height == pytest.approx(max(2.1, strict_scene.page_height * 0.72))
    assert len(auto_paging_state.scene.pages) <= len(strict_scene.pages) // 2
    assert auto_paging_state.effective_page_width > strict_scene.pages[0].content_width * 2.0

    plt.close(figure)


def test_draw_quantum_circuit_managed_figure_adapts_paging_to_explicit_figsize() -> None:
    circuit = build_dense_rotation_ir(layer_count=24)
    narrow_figure, narrow_axes = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 12.0},
        show=False,
        figsize=(3.2, 12.0),
    )
    wide_figure, wide_axes = draw_quantum_circuit(
        circuit,
        style={"max_page_width": 12.0},
        show=False,
        figsize=(12.0, 3.2),
    )

    narrow_state = get_auto_paging_state(narrow_axes)
    wide_state = get_auto_paging_state(wide_axes)

    assert narrow_state is not None
    assert wide_state is not None
    assert len(wide_state.scene.pages) < len(narrow_state.scene.pages)
    assert wide_state.effective_page_width > narrow_state.effective_page_width

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
    assert get_auto_paging_state(axes) is not None

    plt.close(figure)


def test_draw_quantum_circuit_page_slider_skips_auto_paging_state() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    assert get_auto_paging_state(axes) is None
    plt.close(figure)


def test_draw_quantum_circuit_managed_figure_expands_beyond_initial_page_width_when_resized() -> (
    None
):
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        show=False,
    )

    initial_state = get_auto_paging_state(axes)

    assert initial_state is not None
    initial_page_count = len(initial_state.scene.pages)
    initial_page_width = initial_state.effective_page_width

    figure.set_size_inches(12.0, 3.2, forward=True)
    figure.canvas.draw()

    resized_state = get_auto_paging_state(axes)

    assert resized_state is not None
    assert len(resized_state.scene.pages) < initial_page_count
    assert resized_state.effective_page_width > initial_page_width

    plt.close(figure)


def test_draw_quantum_circuit_managed_figure_reconciles_auto_paging_on_first_draw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer._draw_managed as draw_managed

    circuit = build_dense_rotation_ir(layer_count=24)
    initial_scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
    reconciled_scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=12.0))
    viewport_calls = 0

    def fake_viewport_adaptive_paged_scene(
        _circuit: object,
        _layout_engine: object,
        _style: object,
        _axes: object,
    ) -> tuple[object, float]:
        nonlocal viewport_calls
        viewport_calls += 1
        if viewport_calls == 1:
            return initial_scene, 4.0
        return reconciled_scene, 12.0

    monkeypatch.setattr(
        draw_managed,
        "viewport_adaptive_paged_scene",
        fake_viewport_adaptive_paged_scene,
    )

    figure, axes = draw_quantum_circuit(circuit, style={"max_page_width": 4.0}, show=False)
    initial_state = get_auto_paging_state(axes)

    assert initial_state is not None
    assert len(initial_state.scene.pages) == len(initial_scene.pages)

    figure.canvas.draw()

    reconciled_state = get_auto_paging_state(axes)

    assert reconciled_state is not None
    assert viewport_calls >= 2
    assert len(reconciled_state.scene.pages) == len(reconciled_scene.pages)
    assert reconciled_state.effective_page_width == pytest.approx(12.0)

    plt.close(figure)


def test_draw_quantum_circuit_rescales_2d_text_when_zooming() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12),
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    gate_label = next(text for text in axes.texts if text.get_text() == "RX")
    initial_font_size = gate_label.get_fontsize()

    axes.set_xlim(0.0, 2.5)
    axes.set_ylim(3.5, 0.0)
    figure.canvas.draw()

    assert gate_label.get_fontsize() > initial_font_size

    plt.close(figure)


def test_draw_quantum_circuit_rescales_all_2d_text_when_zooming() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))

    draw_quantum_circuit(
        _zoom_text_scaling_ir(),
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    tracked_labels = ("RZZ", "0.7", "M", "q0", "q1", "c", "0", "1", "dest", "23")
    initial_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}

    axes.set_xlim(0.0, 2.5)
    axes.set_ylim(3.5, 0.0)
    figure.canvas.draw()

    for label in tracked_labels:
        assert _font_size_by_text(axes, label) > initial_font_sizes[label]

    plt.close(figure)


def test_draw_quantum_circuit_updates_gate_text_immediately_when_zoom_changes() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))

    draw_quantum_circuit(
        _zoom_text_scaling_ir(),
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    tracked_labels = ("RZZ", "0.7", "M", "q0", "q1", "c", "0", "1", "dest", "23")
    initial_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}

    axes.set_xlim(0.0, 2.5)
    axes.set_ylim(3.5, 0.0)
    immediate_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}
    figure.canvas.draw()
    drawn_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}

    for label in tracked_labels:
        assert immediate_font_sizes[label] > initial_font_sizes[label]
        assert immediate_font_sizes[label] == pytest.approx(
            drawn_font_sizes[label],
            rel=1e-3,
            abs=1e-3,
        )

    plt.close(figure)


def test_draw_quantum_circuit_fits_zoom_scaled_text_to_reference_boxes() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))
    circuit = _zoom_text_scaling_ir()
    style = DrawStyle(max_page_width=12.0)
    scene = LayoutEngine().compute(circuit, style)

    draw_quantum_circuit(
        circuit,
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    axes.set_xlim(0.0, 2.5)
    axes.set_ylim(3.5, 0.0)

    full_gate_box_labels = ("q0", "q1", "c")
    half_gate_box_labels = ("M", "dest", "0", "1", "23")

    for label in full_gate_box_labels:
        assert _font_size_by_text(axes, label) == pytest.approx(
            _expected_box_fitted_font_size(
                axes,
                scene,
                text=label,
                width=scene.style.gate_width,
                height=scene.style.gate_height,
                height_fraction=matplotlib_primitives._SINGLE_LINE_HEIGHT_FRACTION,
            ),
            rel=1e-3,
            abs=1e-3,
        )

    for label in half_gate_box_labels:
        assert _font_size_by_text(axes, label) == pytest.approx(
            _expected_box_fitted_font_size(
                axes,
                scene,
                text=label,
                width=scene.style.gate_width * 0.5,
                height=scene.style.gate_height * 0.5,
                height_fraction=1.0,
            ),
            rel=1e-3,
            abs=1e-3,
        )

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

    _show_managed_figure_if_supported(figure, show=True)

    assert show_calls == []
    plt.close(figure)


def test_draw_quantum_circuit_reduces_wrapped_gate_font_progressively_with_page_count() -> None:
    page_to_font_size: dict[int, float] = {}

    for layer_count in (5, 8, 29):
        circuit = build_dense_rotation_ir(layer_count=layer_count, wire_count=1)
        figure, axes = plt.subplots(figsize=(3.2, 12.0))
        draw_quantum_circuit(circuit, style={"max_page_width": 4.0}, ax=axes)
        auto_paging_state = get_auto_paging_state(axes)

        assert auto_paging_state is not None
        page_to_font_size[len(auto_paging_state.scene.pages)] = next(
            text.get_fontsize() for text in axes.texts if text.get_text() == "RX"
        )
        plt.close(figure)

    assert page_to_font_size[3] > page_to_font_size[4] > page_to_font_size[8]
    assert page_to_font_size[8] < page_to_font_size[3] * 0.85


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

    assert _slider_viewport_width(axes, scene) == scene.width
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

    assert _slider_viewport_width(axes, scene) == pytest.approx(
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

    assert _slider_viewport_width(axes, scene) == pytest.approx(
        min(scene.width, scene.height * expected_ratio)
    )
    plt.close(figure)


def test_configure_page_slider_skips_slider_when_viewport_already_fits_scene() -> None:
    scene = build_sample_scene()
    figure, axes = plt.subplots()
    attached_sliders: list[object] = []

    _configure_page_slider(
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
    assert _normalize_backend_name(backend_name) == expected


def test_page_slider_figsize_respects_minimum_dimensions() -> None:
    assert _page_slider_figsize(1.0, 0.5) == pytest.approx((4.8, 3.0))


def test_figure_backend_name_prefers_canvas_type_name() -> None:
    figure, _ = draw_quantum_circuit(build_sample_ir(), show=False)

    assert _figure_backend_name(figure) == "agg"
    plt.close(figure)
