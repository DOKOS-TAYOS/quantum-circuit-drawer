from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit
from quantum_circuit_drawer._scene_pages import single_page_scenes
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    get_page_slider,
    get_page_window,
)
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_dense_rotation_ir, build_wrapped_ir, normalize_rendered_text


def test_draw_quantum_circuit_pages_mode_returns_one_figure_per_wrapped_page() -> None:
    result = draw_quantum_circuit(
        build_wrapped_ir(),
        config=DrawConfig(
            mode=DrawMode.PAGES,
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    assert result.mode is DrawMode.PAGES
    assert result.page_count > 1
    assert len(result.figures) == result.page_count
    assert len({id(figure) for figure in result.figures}) == result.page_count
    assert all(get_page_slider(figure) is None for figure in result.figures)
    assert all(get_page_window(figure) is None for figure in result.figures)

    for figure in result.figures:
        plt.close(figure)


def test_draw_quantum_circuit_pages_mode_renders_only_one_page_per_figure() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=1),
        config=DrawConfig(
            mode=DrawMode.PAGES,
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    assert result.page_count > 1

    visible_gate_counts = [
        sum(
            normalize_rendered_text(text_artist.get_text()) == "RX\n0.5"
            for text_artist in axes.texts
        )
        for axes in result.axes
    ]

    assert all(0 < visible_gate_count < 24 for visible_gate_count in visible_gate_counts)
    assert sum(visible_gate_counts) == 24

    for figure in result.figures:
        plt.close(figure)


def test_draw_quantum_circuit_pages_mode_adapts_page_count_to_window_width() -> None:
    circuit = build_dense_rotation_ir(layer_count=24, wire_count=4)
    narrow_result = draw_quantum_circuit(
        circuit,
        config=DrawConfig(
            mode=DrawMode.PAGES,
            style={"max_page_width": 4.0},
            show=False,
            figsize=(3.2, 12.0),
        ),
    )
    wide_result = draw_quantum_circuit(
        circuit,
        config=DrawConfig(
            mode=DrawMode.PAGES,
            style={"max_page_width": 4.0},
            show=False,
            figsize=(12.0, 4.0),
        ),
    )

    assert wide_result.page_count < narrow_result.page_count

    for figure in (*narrow_result.figures, *wide_result.figures):
        plt.close(figure)


def test_single_page_scenes_keep_a_shared_page_width_for_consistent_2d_spacing() -> None:
    source_scene = LayoutEngine().compute(build_wrapped_ir(), DrawStyle(max_page_width=4.0))

    assert len(source_scene.pages) > 1

    page_scenes = single_page_scenes(source_scene)
    shared_content_width = max(page.content_width for page in source_scene.pages)
    expected_scene_width = (
        source_scene.style.margin_left + shared_content_width + source_scene.style.margin_right
    )

    assert all(
        page_scene.width == pytest.approx(expected_scene_width) for page_scene in page_scenes
    )
    assert all(
        page_scene.pages[0].content_width == pytest.approx(shared_content_width)
        for page_scene in page_scenes
    )


def test_draw_quantum_circuit_pages_mode_on_existing_axes_keeps_single_axes_result() -> None:
    figure, axes = plt.subplots()

    result = draw_quantum_circuit(
        build_wrapped_ir(),
        config=DrawConfig(
            mode=DrawMode.PAGES,
            style={"max_page_width": 4.0},
            show=False,
        ),
        ax=axes,
    )

    assert result.primary_figure is figure
    assert result.primary_axes is axes
    assert result.figures == (figure,)
    assert result.axes == (axes,)
    assert result.page_count > 1

    plt.close(figure)


def test_draw_quantum_circuit_full_mode_avoids_wrapping_in_2d() -> None:
    result = draw_quantum_circuit(
        build_wrapped_ir(),
        config=DrawConfig(
            mode=DrawMode.FULL,
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    assert result.mode is DrawMode.FULL
    assert result.page_count == 1
    assert len(result.figures) == 1
    assert get_page_slider(result.primary_figure) is None
    assert get_page_window(result.primary_figure) is None

    plt.close(result.primary_figure)
