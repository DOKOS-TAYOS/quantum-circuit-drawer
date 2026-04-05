from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from quantum_circuit_drawer.api import draw_quantum_circuit
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.renderers._matplotlib_figure import get_page_slider
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_dense_rotation_ir, build_sample_ir, build_wrapped_ir


def test_draw_quantum_circuit_shows_managed_figures_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show_calls: list[bool] = []

    def fake_show(*args: object, **kwargs: object) -> None:
        show_calls.append(True)

    monkeypatch.setattr(plt, "show", fake_show)

    figure, axes = draw_quantum_circuit(build_sample_ir())

    assert figure is not None
    assert axes.figure is figure
    assert show_calls == [True]
    plt.close(figure)


def test_draw_quantum_circuit_skips_show_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_show(*args: object, **kwargs: object) -> None:
        raise AssertionError("matplotlib.pyplot.show should not be called when show=False")

    monkeypatch.setattr(plt, "show", fail_show)

    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure is not None
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

    assert hasattr(page_slider, "set_val")
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
    assert saved_axes_counts == [1]
    assert len(figure.axes) == 2
    plt.close(figure)


def test_draw_quantum_circuit_skips_show_warning_on_non_interactive_backend() -> None:
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        figure, axes = draw_quantum_circuit(build_sample_ir())

    show_warnings = [
        warning for warning in caught_warnings if "cannot be shown" in str(warning.message)
    ]

    assert figure is not None
    assert axes.figure is figure
    assert not show_warnings
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
