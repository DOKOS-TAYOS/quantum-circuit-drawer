from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from quantum_circuit_drawer import DrawConfig, DrawMode, draw_quantum_circuit
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    get_page_window,
    get_topology_menu_state,
)
from tests.support import build_dense_rotation_ir


def test_draw_quantum_circuit_3d_pages_controls_attaches_navigation_state() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=DrawConfig(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    page_window = get_page_window(result.primary_figure)

    assert result.mode is DrawMode.PAGES_CONTROLS
    assert page_window is not None
    assert page_window.total_pages > 1
    assert page_window.visible_page_count == 1
    assert page_window.page_box is not None
    assert page_window.visible_pages_box is not None
    assert page_window.previous_page_button is not None
    assert page_window.next_page_button is not None
    assert len(page_window.display_axes) == 1
    assert all(axes.name == "3d" for axes in page_window.display_axes)

    page_window.visible_pages_box.set_val("2")

    assert page_window.visible_page_count == 2
    assert len(page_window.display_axes) == 2

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_3d_pages_controls_preserves_view_between_navigation() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=DrawConfig(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    page_window = get_page_window(result.primary_figure)

    assert page_window is not None
    assert page_window.next_page_button is not None
    assert len(page_window.display_axes) == 1

    active_axes = page_window.display_axes[0]
    try:
        active_axes.view_init(elev=29.0, azim=-17.0, vertical_axis="y")
    except TypeError:
        active_axes.view_init(elev=29.0, azim=-17.0)
    x_limits = tuple(float(value) for value in active_axes.get_xlim3d())
    y_limits = tuple(float(value) for value in active_axes.get_ylim3d())
    z_limits = tuple(float(value) for value in active_axes.get_zlim3d())
    active_axes.set_xlim3d(x_limits[0] + 0.1, x_limits[1] - 0.1)
    active_axes.set_ylim3d(y_limits[0] + 0.1, y_limits[1] - 0.1)
    active_axes.set_zlim3d(z_limits[0] + 0.1, z_limits[1] - 0.1)
    adjusted_x_limits = tuple(float(value) for value in active_axes.get_xlim3d())
    adjusted_y_limits = tuple(float(value) for value in active_axes.get_ylim3d())
    adjusted_z_limits = tuple(float(value) for value in active_axes.get_zlim3d())

    page_window.next_page_button._observers.process("clicked", None)

    assert page_window.start_page == 1
    assert len(page_window.display_axes) == 1
    navigated_axes = page_window.display_axes[0]
    assert navigated_axes.elev == pytest.approx(29.0)
    assert navigated_axes.azim == pytest.approx(-17.0)
    assert tuple(float(value) for value in navigated_axes.get_xlim3d()) == pytest.approx(
        adjusted_x_limits
    )
    assert tuple(float(value) for value in navigated_axes.get_ylim3d()) == pytest.approx(
        adjusted_y_limits
    )
    assert tuple(float(value) for value in navigated_axes.get_zlim3d()) == pytest.approx(
        adjusted_z_limits
    )

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_3d_pages_controls_supports_topology_menu() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=DrawConfig(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            topology_menu=True,
            style={"max_page_width": 4.0},
            show=True,
        ),
    )

    page_window = get_page_window(result.primary_figure)
    menu_state = get_topology_menu_state(result.primary_figure)

    assert page_window is not None
    assert menu_state is not None
    assert menu_state.radio is not None

    menu_state.select_topology("grid")

    assert page_window.pipeline.draw_options.topology == "grid"
    assert menu_state.active_topology == "grid"
    assert len(page_window.display_axes) == 1

    plt.close(result.primary_figure)
