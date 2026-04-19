from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from quantum_circuit_drawer import draw_quantum_circuit
from quantum_circuit_drawer._draw_managed_slider import Managed3DPageSliderState
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.renderers._matplotlib_figure import get_page_slider
from tests.support import build_dense_rotation_ir, build_sample_ir


def _single_qubit_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            )
        ],
    )


def test_draw_quantum_circuit_renders_3d_axes_for_line_topology() -> None:
    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        show=False,
    )

    assert axes.figure is figure
    assert axes.name == "3d"


def test_draw_quantum_circuit_accepts_page_slider_in_managed_3d_view() -> None:
    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        page_slider=True,
        show=False,
    )

    assert axes.figure is figure
    assert axes.name == "3d"


def test_draw_quantum_circuit_hides_3d_axes_chrome() -> None:
    _, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        show=False,
    )

    assert axes.axison is False
    assert axes.patch.get_visible() is False


def test_draw_quantum_circuit_3d_page_slider_preserves_view_and_limits_between_steps() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=4),
        view="3d",
        topology="line",
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert isinstance(page_slider, Managed3DPageSliderState)
    assert page_slider.horizontal_slider is not None
    assert page_slider.horizontal_slider.valmax >= 2.0

    try:
        axes.view_init(elev=31.0, azim=-22.0, vertical_axis="y")
    except TypeError:
        axes.view_init(elev=31.0, azim=-22.0)

    x_limits = tuple(float(value) for value in axes.get_xlim3d())
    y_limits = tuple(float(value) for value in axes.get_ylim3d())
    z_limits = tuple(float(value) for value in axes.get_zlim3d())
    adjusted_x_limits = (
        x_limits[0] + (x_limits[1] - x_limits[0]) * 0.12,
        x_limits[1] - (x_limits[1] - x_limits[0]) * 0.18,
    )
    adjusted_y_limits = (
        y_limits[0] + (y_limits[1] - y_limits[0]) * 0.09,
        y_limits[1] - (y_limits[1] - y_limits[0]) * 0.16,
    )
    adjusted_z_limits = (
        z_limits[0] + (z_limits[1] - z_limits[0]) * 0.08,
        z_limits[1] - (z_limits[1] - z_limits[0]) * 0.14,
    )
    axes.set_xlim3d(*adjusted_x_limits)
    axes.set_ylim3d(*adjusted_y_limits)
    axes.set_zlim3d(*adjusted_z_limits)
    initial_box_aspect = tuple(float(value) for value in axes.get_box_aspect())

    page_slider.horizontal_slider.set_val(1.0)

    assert axes.elev == pytest.approx(31.0)
    assert axes.azim == pytest.approx(-22.0)
    assert tuple(float(value) for value in axes.get_xlim3d()) == pytest.approx(adjusted_x_limits)
    assert tuple(float(value) for value in axes.get_ylim3d()) == pytest.approx(adjusted_y_limits)
    assert tuple(float(value) for value in axes.get_zlim3d()) == pytest.approx(adjusted_z_limits)
    assert tuple(float(value) for value in axes.get_box_aspect()) == pytest.approx(
        initial_box_aspect
    )

    page_slider.horizontal_slider.set_val(2.0)

    assert axes.elev == pytest.approx(31.0)
    assert axes.azim == pytest.approx(-22.0)
    assert tuple(float(value) for value in axes.get_xlim3d()) == pytest.approx(adjusted_x_limits)
    assert tuple(float(value) for value in axes.get_ylim3d()) == pytest.approx(adjusted_y_limits)
    assert tuple(float(value) for value in axes.get_zlim3d()) == pytest.approx(adjusted_z_limits)
    assert tuple(float(value) for value in axes.get_box_aspect()) == pytest.approx(
        initial_box_aspect
    )


def test_draw_quantum_circuit_rejects_topology_menu_in_2d_view() -> None:
    with pytest.raises(ValueError, match="topology_menu=True is only supported for view='3d'"):
        draw_quantum_circuit(
            build_sample_ir(),
            topology_menu=True,
            show=False,
        )


def test_draw_quantum_circuit_rejects_2d_axes_for_3d_view() -> None:
    _, axes = plt.subplots()

    with pytest.raises(ValueError, match="view='3d' requires a 3D Matplotlib axes"):
        draw_quantum_circuit(build_sample_ir(), view="3d", topology="line", ax=axes)


def test_draw_quantum_circuit_accepts_caller_managed_3d_axes() -> None:
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")

    result = draw_quantum_circuit(build_sample_ir(), view="3d", topology="line", ax=axes)

    assert result is axes


def test_draw_quantum_circuit_accepts_topology_menu_in_managed_3d_view() -> None:
    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
        show=False,
    )

    assert axes.figure is figure
    assert axes.name == "3d"


def test_draw_quantum_circuit_rejects_invalid_grid_qubit_count_in_3d() -> None:
    with pytest.raises(ValueError, match="topology 'grid' does not support 2 quantum wires"):
        draw_quantum_circuit(build_sample_ir(), view="3d", topology="grid", show=False)


def test_draw_quantum_circuit_rejects_invalid_star_topology_for_single_qubit() -> None:
    with pytest.raises(ValueError, match="topology 'star' does not support 1 quantum wire"):
        draw_quantum_circuit(_single_qubit_ir(), view="3d", topology="star", show=False)


def test_draw_quantum_circuit_rejects_invalid_star_tree_qubit_count() -> None:
    with pytest.raises(ValueError, match="topology 'star_tree' does not support 5 quantum wires"):
        draw_quantum_circuit(
            build_dense_rotation_ir(layer_count=2, wire_count=5),
            view="3d",
            topology="star_tree",
            show=False,
        )
