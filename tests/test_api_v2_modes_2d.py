from __future__ import annotations

import matplotlib.pyplot as plt

from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    get_page_slider,
    get_page_window,
)
from tests.support import build_wrapped_ir


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
