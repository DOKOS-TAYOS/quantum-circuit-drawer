from __future__ import annotations

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import MouseEvent

from quantum_circuit_drawer import DrawMode, draw_quantum_circuit
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    get_page_window,
    get_topology_menu_state,
)
from tests.support import build_dense_rotation_ir, build_public_draw_config


def test_draw_quantum_circuit_3d_pages_controls_attaches_navigation_state() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=build_public_draw_config(
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
    assert page_window.visible_pages_decrement_button is not None
    assert page_window.visible_pages_increment_button is not None
    assert page_window.previous_page_button is not None
    assert page_window.next_page_button is not None
    assert len(page_window.display_axes) == 1
    assert all(axes.name == "3d" for axes in page_window.display_axes)

    page_window.visible_pages_increment_button._observers.process("clicked", None)

    assert page_window.visible_page_count == 2
    assert len(page_window.display_axes) == 2

    page_window.visible_pages_decrement_button._observers.process("clicked", None)

    assert page_window.visible_page_count == 1
    assert len(page_window.display_axes) == 1

    page_window.visible_pages_box.set_val("2")

    assert page_window.visible_page_count == 2
    assert len(page_window.display_axes) == 2

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_3d_pages_controls_preserves_view_between_navigation() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=build_public_draw_config(
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
        config=build_public_draw_config(
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
    assert menu_state.menu_axes is not None
    assert menu_state.radio is not None
    assert tuple(menu_state.menu_axes.get_position().bounds) == pytest.approx(
        (0.86, 0.215, 0.12, 0.29),
        abs=1e-3,
    )

    menu_state.select_topology("grid")

    assert page_window.pipeline.draw_options.topology == "grid"
    assert menu_state.active_topology == "grid"
    assert len(page_window.display_axes) == 1

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_3d_pages_controls_keeps_adapted_page_count_after_topology_switch() -> (
    None
):
    circuit = build_dense_rotation_ir(layer_count=24, wire_count=4)
    result = draw_quantum_circuit(
        circuit,
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            topology_menu=True,
            style={"max_page_width": 4.0},
            show=True,
            figsize=(12.0, 4.0),
        ),
    )
    expected_pages = draw_quantum_circuit(
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

    page_window = get_page_window(result.primary_figure)
    menu_state = get_topology_menu_state(result.primary_figure)

    assert page_window is not None
    assert menu_state is not None
    assert page_window.page_suffix_text is not None
    assert page_window.visible_suffix_text is not None
    assert page_window.total_pages == expected_pages.page_count
    assert page_window.page_suffix_text.get_text() == f"/ {expected_pages.page_count}"
    assert page_window.visible_suffix_text.get_text() == f"/ {expected_pages.page_count}"

    menu_state.select_topology("grid")

    assert page_window.total_pages == expected_pages.page_count
    assert page_window.page_suffix_text.get_text() == f"/ {expected_pages.page_count}"
    assert page_window.visible_suffix_text.get_text() == f"/ {expected_pages.page_count}"

    plt.close(expected_pages.primary_figure)
    plt.close(result.primary_figure)


def test_draw_quantum_circuit_3d_pages_controls_keeps_honeycomb_pages_wide_enough() -> None:
    from quantum_circuit_drawer.managed.page_window_3d import (
        _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO,
        _projected_scene_aspect_ratio,
    )

    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=120, wire_count=53),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="honeycomb",
            style={"max_page_width": 4.0},
            show=False,
            figsize=(10.0, 5.5),
        ),
    )

    page_window = get_page_window(result.primary_figure)

    assert page_window is not None
    assert page_window.page_scenes
    assert (
        _projected_scene_aspect_ratio(
            scene=page_window.page_scenes[0],
            renderer=page_window.pipeline.renderer,
            figure_size=(10.0, 5.5),
        )
        >= _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO
    )

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_3d_pages_controls_detaches_removed_axes_mouse_release() -> None:
    result = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=4),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    page_window = get_page_window(result.primary_figure)

    assert page_window is not None
    assert page_window.visible_pages_increment_button is not None
    assert page_window.visible_pages_decrement_button is not None

    page_window.visible_pages_increment_button._observers.process("clicked", None)
    page_window.visible_pages_decrement_button._observers.process("clicked", None)

    result.primary_figure.canvas.callbacks.process(
        "button_release_event",
        MouseEvent(
            "button_release_event",
            result.primary_figure.canvas,
            x=0,
            y=0,
            button=1,
        ),
    )

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_3d_pages_controls_caps_dense_page_visual_load() -> None:
    wire_count = 10
    layer_count = 50
    repeated_operations = tuple(
        OperationIR(kind=OperationKind.GATE, name=name, target_wires=(wire_id,))
        for name, wire_id in (("X", "q0"), ("Y", "q4"), ("Z", "q8"))
    )
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(wire_count)
        ],
        layers=[LayerIR(operations=repeated_operations) for _ in range(layer_count)],
    )

    result = draw_quantum_circuit(
        circuit,
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
            figsize=(10.0, 5.5),
        ),
    )

    page_window = get_page_window(result.primary_figure)

    assert page_window is not None
    assert page_window.page_scenes
    assert len(page_window.page_scenes[0].gates) <= 50

    plt.close(result.primary_figure)
