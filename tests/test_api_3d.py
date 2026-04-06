from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from quantum_circuit_drawer import draw_quantum_circuit
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
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


def test_draw_quantum_circuit_rejects_page_slider_in_3d_view() -> None:
    with pytest.raises(ValueError, match="page_slider=True is only supported for view='2d'"):
        draw_quantum_circuit(
            build_sample_ir(),
            view="3d",
            topology="line",
            page_slider=True,
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
