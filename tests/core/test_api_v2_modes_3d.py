from __future__ import annotations

import matplotlib.pyplot as plt

from quantum_circuit_drawer import DrawMode, draw_quantum_circuit
from quantum_circuit_drawer.renderers._matplotlib_figure import get_page_window
from tests.support import build_dense_rotation_ir, build_public_draw_config


def test_draw_quantum_circuit_pages_mode_returns_one_3d_figure_per_window() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=build_public_draw_config(
            mode=DrawMode.PAGES,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    assert result.mode is DrawMode.PAGES
    assert result.page_count > 1
    assert len(result.figures) == result.page_count
    assert all(axes.name == "3d" for axes in result.axes)
    assert all(get_page_window(figure) is not None for figure in result.figures)
    assert all(
        getattr(get_page_window(figure), "page_box", None) is None for figure in result.figures
    )

    for figure in result.figures:
        plt.close(figure)


def test_draw_quantum_circuit_full_mode_keeps_single_3d_figure() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=build_public_draw_config(
            mode=DrawMode.FULL,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    assert result.mode is DrawMode.FULL
    assert result.page_count == 1
    assert len(result.figures) == 1
    assert result.primary_axes.name == "3d"

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_3d_pages_mode_adapts_page_count_to_window_width() -> None:
    circuit = build_dense_rotation_ir(layer_count=24, wire_count=4)
    narrow_result = draw_quantum_circuit(
        circuit,
        config=build_public_draw_config(
            mode=DrawMode.PAGES,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
            figsize=(3.2, 12.0),
        ),
    )
    wide_result = draw_quantum_circuit(
        circuit,
        config=build_public_draw_config(
            mode=DrawMode.PAGES,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
            figsize=(12.0, 4.0),
        ),
    )

    assert wide_result.page_count < narrow_result.page_count
    assert all(axes.name == "3d" for axes in narrow_result.axes)
    assert all(axes.name == "3d" for axes in wide_result.axes)

    for figure in (*narrow_result.figures, *wide_result.figures):
        plt.close(figure)
