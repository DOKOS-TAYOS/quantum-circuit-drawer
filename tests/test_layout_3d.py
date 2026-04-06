from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.colors import to_hex
from matplotlib.text import Annotation
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # type: ignore[import-untyped]

from quantum_circuit_drawer import draw_quantum_circuit
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine_3d import LayoutEngine3D
from quantum_circuit_drawer.layout.scene_3d import ConnectionRenderStyle3D, MarkerStyle3D
from quantum_circuit_drawer.layout.topology_3d import build_topology
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_sample_ir


def _line_control_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(4)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q3",),
                        control_wires=("q0",),
                    )
                ]
            )
        ],
    )


def _five_wire_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(5)
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            )
        ],
    )


def _grid_controlled_z_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(4)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="Z",
                        target_wires=("q3",),
                        control_wires=("q0",),
                        canonical_family=CanonicalGateFamily.Z,
                    )
                ]
            )
        ],
    )


def test_build_topology_grid_prefers_more_columns_when_near_square() -> None:
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(6)
    )

    topology = build_topology("grid", quantum_wires)
    x_values = sorted({node.x for node in topology.nodes})
    y_values = sorted({node.y for node in topology.nodes})

    assert len(x_values) == 3
    assert len(y_values) == 2


def test_build_topology_honeycomb_accepts_only_reference_53_qubits() -> None:
    valid_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(53)
    )

    topology = build_topology("honeycomb", valid_wires)

    assert len(topology.nodes) == 53
    with pytest.raises(ValueError, match="topology 'honeycomb' does not support 52 quantum wires"):
        build_topology("honeycomb", valid_wires[:-1])


def test_layout_engine_3d_keeps_quantum_wires_fixed_in_xy_and_extends_in_z() -> None:
    scene = LayoutEngine3D().compute(
        build_sample_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )

    quantum_wires = [wire for wire in scene.wires if wire.kind is WireKind.QUANTUM]

    assert quantum_wires
    assert all(wire.start.x == wire.end.x and wire.start.y == wire.end.y for wire in quantum_wires)
    assert all(wire.end.z > wire.start.z for wire in quantum_wires)


def test_layout_engine_3d_routes_non_direct_controls_along_topology_path() -> None:
    scene = LayoutEngine3D().compute(
        _line_control_ir(),
        DrawStyle(),
        topology_name="line",
        direct=False,
        hover_enabled=True,
    )

    connection = next(
        connection
        for connection in scene.connections
        if connection.render_style is ConnectionRenderStyle3D.CONTROL
    )

    assert len(connection.points) == 4
    assert connection.hover_text == "2 intermediate qubits"


def test_layout_engine_3d_places_classical_wires_below_quantum_plane() -> None:
    scene = LayoutEngine3D().compute(
        build_sample_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )

    min_quantum_y = min(point.y for point in scene.quantum_wire_positions.values())

    assert scene.classical_wire_positions
    assert all(point.y < min_quantum_y for point in scene.classical_wire_positions.values())


def test_layout_engine_3d_adds_topology_graph_edges_and_start_nodes() -> None:
    scene = LayoutEngine3D().compute(
        _line_control_ir(),
        DrawStyle(),
        topology_name="line",
        direct=False,
        hover_enabled=False,
    )

    topology_edges = [
        connection
        for connection in scene.connections
        if connection.render_style is ConnectionRenderStyle3D.TOPOLOGY_EDGE
    ]
    topology_nodes = [
        marker for marker in scene.markers if marker.style is MarkerStyle3D.TOPOLOGY_NODE
    ]
    base_layer_z = next(iter(scene.quantum_wire_positions.values())).z

    assert len(topology_edges) == len(scene.topology.edges)
    assert len(topology_nodes) == len(scene.quantum_wire_positions)
    assert all(
        all(point.z == base_layer_z for point in connection.points) for connection in topology_edges
    )
    assert {marker.center for marker in topology_nodes} == set(
        scene.quantum_wire_positions.values()
    )


def test_draw_quantum_circuit_hides_gate_and_wire_labels_when_hover_is_interactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        hover=True,
    )

    labels = {text.get_text() for text in axes.texts}

    assert axes.figure is figure
    assert "q0" not in labels
    assert "q1" not in labels
    assert "H" not in labels
    assert "M" not in labels


def test_draw_quantum_circuit_interactive_hover_draws_without_annotation_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        hover=True,
    )

    annotation = next(text for text in axes.texts if isinstance(text, Annotation))
    annotation.set_visible(True)
    figure.canvas.draw()


def test_draw_quantum_circuit_interactive_hover_stays_above_scene_artists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    _, axes = draw_quantum_circuit(
        _line_control_ir(),
        view="3d",
        topology="line",
        direct=False,
        hover=True,
    )

    annotation = next(text for text in axes.texts if isinstance(text, Annotation))
    max_scene_zorder = max(
        (
            *(line.get_zorder() for line in axes.lines),
            *(collection.get_zorder() for collection in axes.collections),
        ),
        default=0.0,
    )

    assert annotation.get_zorder() > max_scene_zorder


def test_draw_quantum_circuit_falls_back_to_visible_labels_for_noninteractive_hover() -> None:
    _, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        hover=True,
        show=False,
    )

    labels = {text.get_text() for text in axes.texts}

    assert "q0" in labels
    assert "q1" in labels
    assert "H" in labels


def test_draw_quantum_circuit_projects_time_axis_horizontally_by_default() -> None:
    scene = LayoutEngine3D().compute(
        _five_wire_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure, axes = draw_quantum_circuit(
        _five_wire_ir(),
        view="3d",
        topology="line",
        show=False,
    )
    wire = next(wire for wire in scene.wires if wire.kind is WireKind.QUANTUM)

    start_projection = proj3d.proj_transform(
        wire.start.x, wire.start.y, wire.start.z, axes.get_proj()
    )
    end_projection = proj3d.proj_transform(wire.end.x, wire.end.y, wire.end.z, axes.get_proj())
    start_display = axes.transData.transform((start_projection[0], start_projection[1]))
    end_display = axes.transData.transform((end_projection[0], end_projection[1]))
    delta_x = abs(end_display[0] - start_display[0])
    delta_y = abs(end_display[1] - start_display[1])

    assert figure is not None
    assert delta_x > delta_y


def test_draw_quantum_circuit_saves_non_empty_3d_output(sandbox_tmp_path: Path) -> None:
    output = sandbox_tmp_path / "circuit-3d.png"

    figure, _ = draw_quantum_circuit(
        _five_wire_ir(),
        view="3d",
        topology="line",
        output=output,
        show=False,
    )

    assert figure is not None
    assert output.exists()
    assert output.stat().st_size > 0


def test_draw_quantum_circuit_uses_distinct_quantum_control_and_topology_line_styles() -> None:
    _, axes = draw_quantum_circuit(
        _line_control_ir(),
        view="3d",
        topology="line",
        direct=False,
        show=False,
    )

    line_collection_colors = {
        to_hex(collection.get_colors()[0], keep_alpha=False): collection
        for collection in axes.collections
        if isinstance(collection, Line3DCollection) and len(collection.get_colors()) > 0
    }
    wire_colors = {to_hex(line.get_color(), keep_alpha=False) for line in axes.lines}
    wire_widths = [
        line.get_linewidth() for line in axes.lines if to_hex(line.get_color()) == "#ffffff"
    ]
    control_widths = [
        collection.get_linewidths()[0]
        for color, collection in line_collection_colors.items()
        if color == "#22c55e"
    ]
    topology_widths = [
        collection.get_linewidths()[0]
        for color, collection in line_collection_colors.items()
        if color == "#facc15"
    ]

    assert "#ffffff" in wire_colors
    assert "#22c55e" in line_collection_colors
    assert "#facc15" in line_collection_colors
    assert wire_widths
    assert control_widths
    assert topology_widths
    assert min(control_widths) > max(wire_widths)
    assert max(topology_widths) < min(control_widths)


def test_draw_quantum_circuit_renders_topological_controlled_z_in_3d_grid(
    sandbox_tmp_path: Path,
) -> None:
    output = sandbox_tmp_path / "controlled-z-grid-3d.png"

    figure, axes = draw_quantum_circuit(
        _grid_controlled_z_ir(),
        view="3d",
        topology="grid",
        direct=False,
        output=output,
        show=False,
    )

    assert figure is not None
    assert axes.name == "3d"
    assert output.exists()
    assert output.stat().st_size > 0
