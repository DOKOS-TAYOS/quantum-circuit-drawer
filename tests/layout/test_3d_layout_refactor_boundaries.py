from __future__ import annotations

from importlib import import_module

import matplotlib.pyplot as plt
import pytest

import quantum_circuit_drawer.layout._operation_layout as operation_layout_module
from quantum_circuit_drawer import CircuitBuilder
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.layout.engine_3d import LayoutEngine3D
from quantum_circuit_drawer.renderers.matplotlib_renderer_3d import MatplotlibRenderer3D
from quantum_circuit_drawer.style import DrawStyle


def build_simple_3d_scene() -> object:
    circuit = CircuitBuilder(2, name="three-d-boundaries").h(0).cx(0, 1).build()
    return LayoutEngine3D().compute(
        circuit,
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )


def build_repeated_layout_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        canonical_family=CanonicalGateFamily.H,
                        target_wires=("q0",),
                    ),
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        canonical_family=CanonicalGateFamily.X,
                        target_wires=("q1",),
                    ),
                ]
            )
            for _ in range(4)
        ],
    )


def test_second_pass_3d_renderer_split_modules_are_importable() -> None:
    renderer_axes = import_module("quantum_circuit_drawer.renderers._matplotlib_renderer_3d_axes")
    renderer_topology = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_topology"
    )
    renderer_wires = import_module("quantum_circuit_drawer.renderers._matplotlib_renderer_3d_wires")
    renderer_gates = import_module("quantum_circuit_drawer.renderers._matplotlib_renderer_3d_gates")
    renderer_markers = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_markers"
    )

    assert callable(renderer_axes.prepare_axes_3d)
    assert callable(renderer_topology.draw_topology_planes_3d)
    assert callable(renderer_wires.draw_wires_3d)
    assert callable(renderer_gates.draw_gates_3d)
    assert callable(renderer_markers.draw_markers_3d)


def test_second_pass_operation_layout_split_modules_are_importable() -> None:
    layout_builder = import_module("quantum_circuit_drawer.layout._operation_layout_builder")
    layout_hover = import_module("quantum_circuit_drawer.layout._operation_layout_hover")
    layout_emitters = import_module("quantum_circuit_drawer.layout._operation_layout_emitters")
    layout_collections = import_module(
        "quantum_circuit_drawer.layout._operation_layout_collections"
    )

    assert callable(layout_builder.build_scene_collections_impl)
    assert callable(layout_hover.build_hover_data)
    assert callable(layout_emitters.layout_operation)
    assert callable(layout_collections.build_wire_and_label_collections)


def test_matplotlib_renderer_3d_render_still_uses_instance_prepare_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = build_simple_3d_scene()
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")
    prepare_axes_calls = 0
    original_prepare_axes = MatplotlibRenderer3D._prepare_axes

    def count_prepare_axes(
        renderer: MatplotlibRenderer3D,
        managed_axes: object,
        rendered_scene: object,
        *,
        fixed_view_state: object | None = None,
    ) -> None:
        nonlocal prepare_axes_calls
        prepare_axes_calls += 1
        original_prepare_axes(
            renderer,
            managed_axes,
            rendered_scene,
            fixed_view_state=fixed_view_state,
        )

    monkeypatch.setattr(MatplotlibRenderer3D, "_prepare_axes", count_prepare_axes)

    MatplotlibRenderer3D().render(scene, ax=axes)

    assert prepare_axes_calls == 1
    plt.close(figure)


def test_layout_engine_still_uses_operation_layout_matrix_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved_matrix_calls = 0
    matrix_dimension_calls = 0
    original_resolved_matrix = operation_layout_module.resolved_operation_matrix
    original_matrix_dimension = operation_layout_module.operation_matrix_dimension

    def count_resolved_matrix(operation: OperationIR) -> object | None:
        nonlocal resolved_matrix_calls
        resolved_matrix_calls += 1
        return original_resolved_matrix(operation)

    def count_matrix_dimension(operation: OperationIR) -> int | None:
        nonlocal matrix_dimension_calls
        matrix_dimension_calls += 1
        return original_matrix_dimension(operation)

    monkeypatch.setattr(operation_layout_module, "resolved_operation_matrix", count_resolved_matrix)
    monkeypatch.setattr(
        operation_layout_module, "operation_matrix_dimension", count_matrix_dimension
    )

    scene = LayoutEngine().compute(build_repeated_layout_ir(), DrawStyle())
    hover_items = [gate.hover_data for gate in scene.gates if gate.hover_data is not None]

    assert hover_items
    assert resolved_matrix_calls >= 1
    assert matrix_dimension_calls >= 1
