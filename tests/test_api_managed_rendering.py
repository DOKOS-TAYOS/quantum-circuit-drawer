from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

from quantum_circuit_drawer.api import (
    _configure_page_slider,
    _figure_backend_name,
    _normalize_backend_name,
    _page_slider_figsize,
    _show_managed_figure_if_supported,
    _slider_viewport_width,
    draw_quantum_circuit,
)
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    create_managed_figure,
    get_auto_paging_state,
    get_page_slider,
)
from quantum_circuit_drawer.style import DrawStyle
from tests.support import (
    build_dense_rotation_ir,
    build_sample_ir,
    build_sample_scene,
    build_wrapped_ir,
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


def test_draw_quantum_circuit_auto_paging_respects_user_page_width_cap() -> None:
    figure, axes = plt.subplots(figsize=(18.0, 3.0))

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        ax=axes,
    )

    auto_paging_state = get_auto_paging_state(axes)

    assert auto_paging_state is not None
    assert auto_paging_state.effective_page_width <= 4.0 + 1e-6

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
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24),
        style={"max_page_width": 4.0},
        show=False,
    )

    auto_paging_state = get_auto_paging_state(axes)

    assert auto_paging_state is not None
    assert auto_paging_state.effective_page_width <= 4.0 + 1e-6

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


def test_draw_quantum_circuit_reduces_wrapped_gate_font_progressively_with_page_count() -> None:
    page_to_font_size: dict[int, float] = {}

    for layer_count in (5, 8, 29):
        circuit = build_dense_rotation_ir(layer_count=layer_count, wire_count=1)
        scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
        figure, axes = draw_quantum_circuit(
            circuit,
            style={"max_page_width": 4.0},
            show=False,
        )
        page_to_font_size[len(scene.pages)] = next(
            text.get_fontsize() for text in axes.texts if text.get_text() == "RX"
        )
        plt.close(figure)

    assert page_to_font_size[2] > page_to_font_size[3] > page_to_font_size[10]
    assert page_to_font_size[10] < page_to_font_size[2] * 0.75


def test_slider_viewport_width_falls_back_to_scene_width_for_zero_sized_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = build_sample_scene()
    figure, axes = create_managed_figure(scene, use_agg=True)

    monkeypatch.setattr(axes, "get_position", lambda: Bbox.from_bounds(0.0, 0.0, 0.0, 0.0))

    assert _slider_viewport_width(axes, scene) == scene.width
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
