from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.artist import Artist
from matplotlib.backend_bases import MouseEvent
from matplotlib.collections import PathCollection
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from matplotlib.text import Annotation
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import (  # type: ignore[import-untyped]
    Line3DCollection,
    Poly3DCollection,
)

from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.classical_conditions import ClassicalConditionIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine_3d import LayoutEngine3D
from quantum_circuit_drawer.layout.scene_3d import (
    ConnectionRenderStyle3D,
    GateRenderStyle3D,
    MarkerStyle3D,
    Point3D,
    SceneConnection3D,
    SceneGate3D,
)
from quantum_circuit_drawer.layout.topology_3d import build_topology
from quantum_circuit_drawer.renderers.matplotlib_renderer_3d import (
    MatplotlibRenderer3D,
    _RenderContext3D,
)
from quantum_circuit_drawer.style import (
    DrawStyle,
    resolved_connection_line_width,
    resolved_topology_edge_line_width,
    resolved_wire_line_width,
)
from tests.support import (
    assert_axes_contains_circuit_artists,
    assert_figure_has_visible_content,
    assert_saved_image_has_visible_content,
    build_dense_rotation_ir,
    build_sample_ir,
    normalize_rendered_text,
)
from tests.support import (
    draw_quantum_circuit_legacy as draw_quantum_circuit,
)

pytestmark = pytest.mark.renderer

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

_BATCHED_TEXT_ARTIST_GID = "quantum-circuit-drawer-3d-batched-text"


def _rendered_content_size(figure: Figure) -> tuple[int, int]:
    figure.canvas.draw()
    image = np.asarray(figure.canvas.buffer_rgba())[:, :, :3]
    non_background_pixels = np.any(image != 0, axis=2)
    y_indices, x_indices = np.where(non_background_pixels)
    return (
        int(x_indices.max() - x_indices.min() + 1),
        int(y_indices.max() - y_indices.min() + 1),
    )


def _batched_text_artists(figure: Figure) -> list[PathCollection]:
    return [
        artist
        for artist in figure.artists
        if isinstance(artist, PathCollection) and artist.get_gid() == _BATCHED_TEXT_ARTIST_GID
    ]


def _normalized_axis_text_values(axes: Axes3D) -> set[str]:
    return {normalize_rendered_text(text.get_text()) for text in axes.texts}


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


def _dense_marker_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(6)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q5",),
                        control_wires=("q0",),
                    ),
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q4",),
                        control_wires=("q1",),
                    ),
                    OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=("q2", "q3")),
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


def _marker_and_measurement_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",)),
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    ),
                    OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=("q0", "q1")),
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q1",),
                        classical_target="c0",
                    ),
                ]
            )
        ],
    )


def _bundled_measurement_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[
            WireIR(
                id="c0",
                index=0,
                kind=WireKind.CLASSICAL,
                label="c",
                metadata={"bundle_size": 2},
            )
        ],
        layers=[
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                        metadata={"classical_bit_label": "c[0]"},
                    ),
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q1",),
                        classical_target="c0",
                        metadata={"classical_bit_label": "c[1]"},
                    ),
                ]
            )
        ],
    )


def _single_gate_ir(*, name: str = "H") -> CircuitIR:
    return CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name=name, target_wires=("q0",))]
            )
        ],
    )


def _multi_single_gate_ir(*, layers: int = 4) -> CircuitIR:
    return CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            )
            for _ in range(layers)
        ],
    )


def _multi_topological_control_ir(*, layers: int = 4) -> CircuitIR:
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
            for _ in range(layers)
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


def test_topology_3d_caches_neighbor_map_and_shortest_paths() -> None:
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(4)
    )

    topology = build_topology("line", quantum_wires)
    first_neighbor_map = topology.neighbor_map
    second_neighbor_map = topology.neighbor_map
    first_path = topology.shortest_path("q0", "q3")
    second_path = topology.shortest_path("q0", "q3")

    assert first_neighbor_map is second_neighbor_map
    assert first_path == ("q0", "q1", "q2", "q3")
    assert first_path is second_path


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


def test_layout_engine_3d_keeps_classical_conditions_for_controlled_x() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[
            WireIR(
                id="c0",
                index=0,
                kind=WireKind.CLASSICAL,
                label="c",
                metadata={"bundle_size": 1},
            )
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                        classical_conditions=(
                            ClassicalConditionIR(wire_ids=("c0",), expression="if c[0]=1"),
                        ),
                    )
                ]
            )
        ],
    )

    scene = LayoutEngine3D().compute(
        circuit,
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )

    classical_connections = [
        connection for connection in scene.connections if connection.is_classical
    ]

    assert len(classical_connections) == 1
    assert classical_connections[0].double_line is True
    assert classical_connections[0].label == "if c[0]=1"


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


def test_layout_engine_3d_adds_translucent_topology_plane_at_circuit_start() -> None:
    scene = LayoutEngine3D().compute(
        _line_control_ir(),
        DrawStyle(),
        topology_name="line",
        direct=False,
        hover_enabled=False,
    )
    topology_z = next(iter(scene.quantum_wire_positions.values())).z

    assert len(scene.topology_planes) == 1
    plane = scene.topology_planes[0]
    assert plane.z == topology_z
    assert plane.color == "#7c3aed"
    assert 0.08 <= plane.alpha <= 0.14
    assert plane.x_min < min(point.x for point in scene.quantum_wire_positions.values())
    assert plane.x_max > max(point.x for point in scene.quantum_wire_positions.values())


def test_layout_engine_3d_uses_smaller_swap_x_larger_controls_and_cubic_single_gates() -> None:
    style = DrawStyle()
    scene = LayoutEngine3D().compute(
        _marker_and_measurement_ir(),
        style,
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )

    swap_markers = [marker for marker in scene.markers if marker.style is MarkerStyle3D.SWAP]
    control_markers = [marker for marker in scene.markers if marker.style is MarkerStyle3D.CONTROL]
    single_qubit_gate = next(gate for gate in scene.gates if gate.label == "H")
    measurement_gate = next(
        gate for gate in scene.gates if gate.render_style is GateRenderStyle3D.MEASUREMENT
    )

    assert swap_markers
    assert control_markers
    assert max(marker.size for marker in swap_markers) < single_qubit_gate.size_x * 0.32
    assert min(marker.size for marker in control_markers) > style.control_radius * 6.5
    assert single_qubit_gate.size_x == single_qubit_gate.size_y == single_qubit_gate.size_z
    assert measurement_gate.size_x == measurement_gate.size_y == measurement_gate.size_z


def test_layout_engine_3d_uses_compact_column_spacing() -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=4),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    gate_depths = [gate.center.z for gate in scene.gates]
    spacing = [right - left for left, right in zip(gate_depths, gate_depths[1:], strict=False)]
    gate_depth = scene.gates[0].size_z

    assert spacing
    assert spacing == pytest.approx([spacing[0], spacing[0], spacing[0]])
    assert spacing[0] > gate_depth
    assert spacing[0] - gate_depth >= 0.1


def test_layout_engine_3d_marks_measurement_connection_with_arrow_to_classical_register() -> None:
    scene = LayoutEngine3D().compute(
        _marker_and_measurement_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )

    measurement_connection = next(
        connection
        for connection in scene.connections
        if connection.is_classical and connection.label == "c0"
    )
    classical_point = scene.classical_wire_positions["c0"]

    assert measurement_connection.arrow_at_end is True
    assert measurement_connection.points[-1].x == classical_point.x
    assert measurement_connection.points[-1].y == classical_point.y


def test_layout_engine_3d_prefers_specific_classical_bit_labels_for_measurements() -> None:
    scene = LayoutEngine3D().compute(
        _bundled_measurement_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )

    classical_labels = [
        connection.label for connection in scene.connections if connection.is_classical
    ]

    assert classical_labels == ["c[0]", "c[1]"]


def test_matplotlib_renderer_3d_compensates_single_gate_projection_to_look_square() -> None:
    scene = LayoutEngine3D().compute(
        _single_gate_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")
    renderer = MatplotlibRenderer3D()

    renderer.render(scene, ax=axes)

    gate = scene.gates[0]
    compensated_gate = renderer._display_compensated_gate(axes, gate)
    scale_x, scale_y, scale_z = renderer._projected_axis_scales(axes, gate.center)
    display_sizes = (
        compensated_gate.size_x * scale_x,
        compensated_gate.size_y * scale_y,
        compensated_gate.size_z * scale_z,
    )

    assert max(display_sizes) / min(display_sizes) < 1.15


def test_matplotlib_renderer_3d_batched_projection_matches_scalar_projection() -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=4),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")
    renderer = MatplotlibRenderer3D()

    renderer.render(scene, ax=axes)

    assert hasattr(renderer, "_projected_display_points")

    context = renderer._create_render_context(axes)
    point_array = np.array(
        [
            [scene.wires[0].start.x, scene.wires[0].start.y, scene.wires[0].start.z],
            [scene.wires[0].end.x, scene.wires[0].end.y, scene.wires[0].end.z],
            [scene.gates[0].center.x, scene.gates[0].center.y, scene.gates[0].center.z],
        ],
        dtype=float,
    )

    batched_points = renderer._projected_display_points(
        axes,
        point_array,
        render_context=context,
    )
    scalar_points = np.array(
        [
            renderer._projected_display_points(
                axes,
                np.array([(float(point[0]), float(point[1]), float(point[2]))], dtype=float),
                render_context=context,
            )[0]
            for point in point_array
        ],
        dtype=float,
    )

    assert np.allclose(batched_points, scalar_points)
    plt.close(figure)


def test_matplotlib_renderer_3d_batches_box_gates_when_hover_is_disabled() -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=6),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")

    MatplotlibRenderer3D().render(scene, ax=axes)

    gate_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, Poly3DCollection)
        and len(collection.get_facecolors()) > 0
        and to_hex(collection.get_facecolors()[0], keep_alpha=False)
        == to_hex(DrawStyle().theme.gate_facecolor, keep_alpha=False)
    ]

    assert len(scene.gates) == 6
    assert len(gate_collections) == 1
    plt.close(figure)


def test_matplotlib_renderer_3d_keeps_separate_gate_artists_when_hover_is_enabled() -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=6),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=True,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")

    MatplotlibRenderer3D().render(scene, ax=axes)

    gate_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, Poly3DCollection)
        and len(collection.get_facecolors()) > 0
        and to_hex(collection.get_facecolors()[0], keep_alpha=False)
        == to_hex(DrawStyle().theme.gate_facecolor, keep_alpha=False)
    ]

    assert len(gate_collections) == len(scene.gates)
    plt.close(figure)


def test_matplotlib_renderer_3d_batches_connections_when_hover_is_disabled() -> None:
    scene = LayoutEngine3D().compute(
        _multi_topological_control_ir(layers=4),
        DrawStyle(),
        topology_name="line",
        direct=False,
        hover_enabled=False,
    )
    connection_only_scene = replace(
        scene,
        gates=(),
        markers=(),
        texts=(),
        topology_planes=(),
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")

    MatplotlibRenderer3D().render(connection_only_scene, ax=axes)

    line_collections = [
        collection for collection in axes.collections if isinstance(collection, Line3DCollection)
    ]

    assert len(scene.connections) > 2
    assert len(line_collections) <= 2
    plt.close(figure)


def test_matplotlib_renderer_3d_batches_measurement_symbols_in_no_hover_mode() -> None:
    scene = LayoutEngine3D().compute(
        _bundled_measurement_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")

    MatplotlibRenderer3D().render(scene, ax=axes)

    measurement_symbol_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, Line3DCollection)
        and len(collection.get_colors()) > 0
        and to_hex(collection.get_colors()[0], keep_alpha=False)
        == to_hex(DrawStyle().theme.measurement_color, keep_alpha=False)
    ]

    assert len(measurement_symbol_collections) >= 1
    plt.close(figure)


def test_matplotlib_renderer_3d_offscreen_render_compensates_box_gates_once_per_gate() -> None:
    class _CountingRenderer(MatplotlibRenderer3D):
        def __init__(self) -> None:
            super().__init__()
            self.compensation_calls = 0

        def _display_compensated_gate(
            self,
            axes: Axes3D,
            gate: SceneGate3D,
            render_context: _RenderContext3D | None = None,
        ) -> SceneGate3D:
            self.compensation_calls += 1
            return super()._display_compensated_gate(
                axes,
                gate,
                render_context=render_context,
            )

    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=6),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    renderer = _CountingRenderer()

    result = renderer.render(scene)

    assert isinstance(result, tuple)
    figure, _ = result

    assert renderer.compensation_calls == len(scene.gates)
    plt.close(figure)


def test_matplotlib_renderer_3d_caller_managed_render_keeps_standard_box_gate_compensation_path() -> (
    None
):
    class _CountingRenderer(MatplotlibRenderer3D):
        def __init__(self) -> None:
            super().__init__()
            self.compensation_calls = 0

        def _display_compensated_gate(
            self,
            axes: Axes3D,
            gate: SceneGate3D,
            render_context: _RenderContext3D | None = None,
        ) -> SceneGate3D:
            self.compensation_calls += 1
            return super()._display_compensated_gate(
                axes,
                gate,
                render_context=render_context,
            )

    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=6),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")
    renderer = _CountingRenderer()

    renderer.render(scene, ax=axes)

    assert renderer.compensation_calls == len(scene.gates) * 2
    plt.close(figure)


def test_matplotlib_renderer_3d_offscreen_render_reuses_x_target_geometry_between_fit_and_draw() -> (
    None
):
    class _CountingRenderer(MatplotlibRenderer3D):
        def __init__(self) -> None:
            super().__init__()
            self.ring_point_calls = 0
            self.ring_segment_calls = 0

        def _x_target_ring_points(
            self,
            gate: SceneGate3D,
            radius: float,
            render_context: _RenderContext3D,
        ) -> np.ndarray:
            self.ring_point_calls += 1
            return super()._x_target_ring_points(gate, radius, render_context)

        def _segments_for_ring_points(
            self,
            points: np.ndarray,
        ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
            self.ring_segment_calls += 1
            return super()._segments_for_ring_points(points)

    scene = LayoutEngine3D().compute(
        _multi_topological_control_ir(layers=4),
        DrawStyle(),
        topology_name="line",
        direct=False,
        hover_enabled=False,
    )
    x_target_count = sum(
        1 for gate in scene.gates if gate.render_style is GateRenderStyle3D.X_TARGET
    )
    renderer = _CountingRenderer()

    result = renderer.render(scene)

    assert isinstance(result, tuple)
    figure, _ = result

    assert renderer.ring_point_calls == x_target_count
    assert renderer.ring_segment_calls == x_target_count
    plt.close(figure)


def test_matplotlib_renderer_3d_hover_render_keeps_standard_x_target_geometry_path() -> None:
    class _CountingRenderer(MatplotlibRenderer3D):
        def __init__(self) -> None:
            super().__init__()
            self.ring_point_calls = 0
            self.ring_segment_calls = 0

        def _x_target_ring_points(
            self,
            gate: SceneGate3D,
            radius: float,
            render_context: _RenderContext3D,
        ) -> np.ndarray:
            self.ring_point_calls += 1
            return super()._x_target_ring_points(gate, radius, render_context)

        def _segments_for_ring_points(
            self,
            points: np.ndarray,
        ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
            self.ring_segment_calls += 1
            return super()._segments_for_ring_points(points)

    scene = LayoutEngine3D().compute(
        _multi_topological_control_ir(layers=4),
        DrawStyle(),
        topology_name="line",
        direct=False,
        hover_enabled=True,
    )
    x_target_count = sum(
        1 for gate in scene.gates if gate.render_style is GateRenderStyle3D.X_TARGET
    )
    renderer = _CountingRenderer()

    result = renderer.render(scene)

    assert isinstance(result, tuple)
    figure, _ = result

    assert renderer.ring_point_calls == x_target_count * 2
    assert renderer.ring_segment_calls == 0
    plt.close(figure)


def test_matplotlib_renderer_3d_batches_offscreen_texts_for_managed_non_hover_render() -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=6),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )

    result = MatplotlibRenderer3D().render(scene)

    assert isinstance(result, tuple)
    figure, axes = result

    assert len(scene.texts) == 7
    assert len(_batched_text_artists(figure)) == 2
    assert len(axes.texts) == 0
    plt.close(figure)


def test_matplotlib_renderer_3d_keeps_standard_text_artists_for_caller_managed_axes() -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=6),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")

    MatplotlibRenderer3D().render(scene, ax=axes)

    assert _batched_text_artists(figure) == []
    assert len(axes.texts) == len(scene.texts)
    plt.close(figure)


def test_matplotlib_renderer_3d_does_not_batch_texts_when_hover_is_enabled() -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=6),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=True,
    )

    result = MatplotlibRenderer3D().render(scene)

    assert isinstance(result, tuple)
    figure, axes = result

    assert _batched_text_artists(figure) == []
    assert any(isinstance(text, Annotation) for text in axes.texts)
    plt.close(figure)


def test_matplotlib_renderer_3d_cleans_batched_text_overlays_before_rerender() -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=6),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )

    result = MatplotlibRenderer3D().render(scene)

    assert isinstance(result, tuple)
    figure, axes = result
    axes.clear()

    MatplotlibRenderer3D().render(scene, ax=axes)

    assert len(_batched_text_artists(figure)) == 2
    plt.close(figure)


def test_draw_quantum_circuit_3d_uses_most_of_shorter_figsize_dimension() -> None:
    wide_figure, _ = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        figsize=(12.0, 3.0),
        show=False,
    )
    tall_figure, _ = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        figsize=(3.0, 12.0),
        show=False,
    )

    wide_content_size = max(_rendered_content_size(wide_figure))
    tall_content_size = max(_rendered_content_size(tall_figure))
    wide_short_dimension = min(wide_figure.canvas.get_width_height())
    tall_short_dimension = min(tall_figure.canvas.get_width_height())

    assert wide_content_size / wide_short_dimension > 0.75
    assert tall_content_size / tall_short_dimension > 0.75
    plt.close(wide_figure)
    plt.close(tall_figure)


def test_draw_quantum_circuit_3d_fills_managed_figure_without_overflow() -> None:
    wide_figure, wide_axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        figsize=(12.0, 3.0),
        show=False,
    )
    tall_figure, tall_axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        figsize=(3.0, 12.0),
        show=False,
    )
    wide_figure.canvas.draw()
    tall_figure.canvas.draw()

    wide_canvas_width, wide_canvas_height = wide_figure.canvas.get_width_height()
    tall_canvas_width, tall_canvas_height = tall_figure.canvas.get_width_height()

    assert wide_axes.bbox.x0 >= 0.0
    assert wide_axes.bbox.y0 >= 0.0
    assert wide_axes.bbox.x1 <= wide_canvas_width
    assert wide_axes.bbox.y1 <= wide_canvas_height
    assert (
        min(
            wide_axes.bbox.width / wide_canvas_width,
            wide_axes.bbox.height / wide_canvas_height,
        )
        > 0.95
    )
    assert tall_axes.bbox.x0 >= 0.0
    assert tall_axes.bbox.y0 >= 0.0
    assert tall_axes.bbox.x1 <= tall_canvas_width
    assert tall_axes.bbox.y1 <= tall_canvas_height
    assert (
        min(
            tall_axes.bbox.width / tall_canvas_width,
            tall_axes.bbox.height / tall_canvas_height,
        )
        > 0.95
    )
    plt.close(wide_figure)
    plt.close(tall_figure)


def test_matplotlib_renderer_3d_keeps_gate_compensation_consistent_across_figsize_shapes() -> None:
    class _RecordingRenderer(MatplotlibRenderer3D):
        def __init__(self) -> None:
            super().__init__()
            self.compensated_sizes: list[tuple[float, float, float]] = []

        def _display_compensated_gate(
            self,
            axes: Axes3D,
            gate: SceneGate3D,
            render_context: _RenderContext3D | None = None,
        ) -> SceneGate3D:
            result = super()._display_compensated_gate(
                axes,
                gate,
                render_context=render_context,
            )
            self.compensated_sizes.append((result.size_x, result.size_y, result.size_z))
            return result

    scene = LayoutEngine3D().compute(
        _single_gate_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    compensated_sizes_by_figsize: dict[tuple[int, int], tuple[float, float, float]] = {}

    for figsize in ((12, 3), (3, 12)):
        figure = plt.figure(figsize=figsize)
        axes = figure.add_subplot(111, projection="3d")
        renderer = _RecordingRenderer()

        renderer.render(scene, ax=axes)

        compensated_sizes_by_figsize[figsize] = renderer.compensated_sizes[0]
        plt.close(figure)

    assert compensated_sizes_by_figsize[(12, 3)] == pytest.approx(
        compensated_sizes_by_figsize[(3, 12)],
        rel=0.02,
    )


def test_matplotlib_renderer_3d_renders_double_line_classical_connections_as_parallel_segments() -> (
    None
):
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[
            WireIR(
                id="c0",
                index=0,
                kind=WireKind.CLASSICAL,
                label="c",
                metadata={"bundle_size": 1},
            )
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                        classical_conditions=(
                            ClassicalConditionIR(wire_ids=("c0",), expression="if c[0]=1"),
                        ),
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine3D().compute(
        circuit,
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")

    MatplotlibRenderer3D().render(scene, ax=axes)

    parallel_segments = [
        cast(
            tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
            collection._segments3d,
        )
        for collection in axes.collections
        if isinstance(collection, Line3DCollection) and len(collection._segments3d) == 2
    ]

    assert any(
        segments[0][0][1:] == segments[1][0][1:]
        and segments[0][1][1:] == segments[1][1][1:]
        and segments[1][0][0] - segments[0][0][0] == pytest.approx(0.1)
        and segments[1][1][0] - segments[0][1][0] == pytest.approx(0.1)
        for segments in parallel_segments
    )
    plt.close(figure)


def test_matplotlib_renderer_3d_draws_swap_markers_as_diagonal_crosses_in_hover_mode() -> None:
    scene = LayoutEngine3D().compute(
        _dense_marker_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=True,
    )
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")

    MatplotlibRenderer3D().render(scene, ax=axes)

    diagonal_crosses = [
        cast(
            tuple[tuple[tuple[float, float, float], tuple[float, float, float]], ...],
            collection._segments3d,
        )
        for collection in axes.collections
        if isinstance(collection, Line3DCollection)
        and len(collection._segments3d) == 2
        and all(
            segment[0][0] != segment[1][0] and segment[0][1] != segment[1][1]
            for segment in collection._segments3d
        )
    ]

    assert diagonal_crosses
    plt.close(figure)


def test_matplotlib_renderer_3d_skips_degenerate_connections_without_adding_segments() -> None:
    scene = LayoutEngine3D().compute(
        _single_gate_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    degenerate_scene = replace(
        scene,
        connections=scene.connections
        + (
            SceneConnection3D(
                column=99,
                points=(Point3D(x=0.0, y=0.0, z=scene.gates[0].center.z),),
                render_style=ConnectionRenderStyle3D.STANDARD,
            ),
        ),
    )
    base_figure = plt.figure()
    base_axes = base_figure.add_subplot(111, projection="3d")
    degenerate_figure = plt.figure()
    degenerate_axes = degenerate_figure.add_subplot(111, projection="3d")
    renderer = MatplotlibRenderer3D()

    renderer.render(scene, ax=base_axes)
    renderer.render(degenerate_scene, ax=degenerate_axes)

    base_line_collections = [
        collection
        for collection in base_axes.collections
        if isinstance(collection, Line3DCollection)
    ]
    degenerate_line_collections = [
        collection
        for collection in degenerate_axes.collections
        if isinstance(collection, Line3DCollection)
    ]

    assert len(degenerate_line_collections) == len(base_line_collections)
    plt.close(base_figure)
    plt.close(degenerate_figure)


def test_matplotlib_renderer_3d_hides_hover_annotation_when_pointer_leaves_axes() -> None:
    scene = LayoutEngine3D().compute(
        _single_gate_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=True,
    )
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")

    MatplotlibRenderer3D().render(scene, ax=axes)

    annotation = next(text for text in axes.texts if isinstance(text, Annotation))
    annotation.set_visible(True)
    figure.canvas.draw()
    figure.canvas.callbacks.process(
        "motion_notify_event",
        MouseEvent("motion_notify_event", figure.canvas, 0.0, 0.0),
    )

    assert annotation.get_visible() is False
    plt.close(figure)


def test_matplotlib_renderer_3d_prioritizes_gate_hover_targets_over_wire_hover_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine3D().compute(
        _single_gate_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=True,
    )
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")
    captured_hover_texts: list[str] = []
    original_attach_hover = MatplotlibRenderer3D._attach_hover

    def capture_hover_targets(
        renderer: MatplotlibRenderer3D,
        managed_axes: Axes3D,
        rendered_scene: object,
        hover_targets: list[tuple[object, str]],
    ) -> None:
        captured_hover_texts.extend(text for _, text in hover_targets)
        original_attach_hover(
            renderer,
            managed_axes,
            rendered_scene,
            cast("list[tuple[Artist, str]]", hover_targets),
        )

    monkeypatch.setattr(MatplotlibRenderer3D, "_attach_hover", capture_hover_targets)

    MatplotlibRenderer3D().render(scene, ax=axes)

    gate_hover_texts = [gate.hover_text for gate in scene.gates if gate.hover_text]
    wire_hover_texts = [wire.hover_text for wire in scene.wires if wire.hover_text]

    assert gate_hover_texts
    assert wire_hover_texts
    assert min(captured_hover_texts.index(text) for text in gate_hover_texts) < min(
        captured_hover_texts.index(text) for text in wire_hover_texts
    )
    plt.close(figure)


def test_matplotlib_renderer_3d_batches_noninteractive_marker_scatters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine3D().compute(
        _dense_marker_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")
    renderer = MatplotlibRenderer3D()
    scatter_calls = 0
    original_scatter = axes.scatter

    def counting_scatter(*args: object, **kwargs: object) -> object:
        nonlocal scatter_calls
        scatter_calls += 1
        return original_scatter(*args, **kwargs)

    monkeypatch.setattr(axes, "scatter", counting_scatter)

    renderer.render(scene, ax=axes)

    assert scatter_calls == 2


def test_matplotlib_renderer_3d_uses_batched_projection_when_fitting_scene(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine3D().compute(
        _dense_marker_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")
    renderer = MatplotlibRenderer3D()

    renderer._prepare_axes(axes, scene)
    renderer._synchronize_axes_geometry(axes)

    assert hasattr(renderer, "_projected_display_points")

    batched_projection_calls = 0
    original_projected_display_points = renderer._projected_display_points

    def counting_projected_display_points(*args: object, **kwargs: object) -> np.ndarray:
        nonlocal batched_projection_calls
        batched_projection_calls += 1
        return original_projected_display_points(*args, **kwargs)

    monkeypatch.setattr(renderer, "_projected_display_points", counting_projected_display_points)

    renderer._fit_scene_to_shorter_canvas_dimension(axes, scene)

    assert batched_projection_calls >= 1
    plt.close(figure)


def test_matplotlib_renderer_3d_batches_noninteractive_x_target_rings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine3D().compute(
        _dense_marker_ir(),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")
    renderer = MatplotlibRenderer3D()
    plot_calls = 0
    original_plot = axes.plot

    def counting_plot(*args: object, **kwargs: object) -> list[object]:
        nonlocal plot_calls
        plot_calls += 1
        return original_plot(*args, **kwargs)

    monkeypatch.setattr(axes, "plot", counting_plot)

    renderer.render(scene, ax=axes)

    assert plot_calls <= len(scene.wires) + 1


def test_matplotlib_renderer_3d_reuses_projection_matrix_for_gate_compensation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine3D().compute(
        _multi_single_gate_ir(layers=4),
        DrawStyle(),
        topology_name="line",
        direct=True,
        hover_enabled=False,
    )
    figure = plt.figure(figsize=(12, 3))
    axes = figure.add_subplot(111, projection="3d")
    renderer = MatplotlibRenderer3D()
    get_proj_calls = 0
    original_get_proj = axes.get_proj

    def counting_get_proj() -> object:
        nonlocal get_proj_calls
        get_proj_calls += 1
        return original_get_proj()

    monkeypatch.setattr(axes, "get_proj", counting_get_proj)

    renderer.render(scene, ax=axes)

    assert get_proj_calls <= 2


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


def test_draw_quantum_circuit_3d_uses_mathtext_for_visible_labels_by_default() -> None:
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=1, wire_count=1),
        view="3d",
        topology="line",
        ax=axes,
        show=False,
    )

    assert r"$\mathrm{0}$" in {text.get_text() for text in axes.texts}
    assert r"$\mathrm{RX}$" + "\n" + r"$0.5$" in {text.get_text() for text in axes.texts}


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
    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        hover=True,
        show=False,
    )

    labels = {text.get_text() for text in axes.texts}

    assert ("q0" in labels and "q1" in labels and "H" in labels) or _batched_text_artists(figure)


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

    assert_figure_has_visible_content(figure)
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

    assert_figure_has_visible_content(figure)
    assert_saved_image_has_visible_content(output)


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
    theme = DrawStyle().theme
    expected_wire_color = to_hex(theme.wire_color, keep_alpha=False)
    expected_control_color = to_hex(theme.control_connection_color, keep_alpha=False)
    expected_topology_color = to_hex(theme.topology_edge_color, keep_alpha=False)
    wire_widths = [
        line.get_linewidth()
        for line in axes.lines
        if to_hex(line.get_color(), keep_alpha=False) == expected_wire_color
    ]
    control_widths = [
        collection.get_linewidths()[0]
        for color, collection in line_collection_colors.items()
        if color == expected_control_color
    ]
    topology_widths = [
        collection.get_linewidths()[0]
        for color, collection in line_collection_colors.items()
        if color == expected_topology_color
    ]

    assert expected_wire_color in wire_colors
    assert expected_control_color in line_collection_colors
    assert expected_topology_color in line_collection_colors
    assert wire_widths
    assert control_widths
    assert topology_widths
    assert wire_widths == pytest.approx([resolved_wire_line_width(DrawStyle())] * len(wire_widths))
    assert control_widths == pytest.approx([resolved_connection_line_width(DrawStyle())])
    assert topology_widths == pytest.approx([resolved_topology_edge_line_width(DrawStyle())])


def test_draw_quantum_circuit_renders_topology_plane_gate_borders_measurement_symbol_and_arrow() -> (
    None
):
    _, axes = draw_quantum_circuit(
        _marker_and_measurement_ir(),
        view="3d",
        topology="line",
        show=False,
    )

    gate_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, Poly3DCollection) and len(collection.get_facecolors()) > 0
    ]
    plane_collections = [
        collection
        for collection in gate_collections
        if to_hex(collection.get_facecolors()[0], keep_alpha=False) == "#7c3aed"
    ]
    measurement_symbol_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, Line3DCollection)
        and len(collection.get_colors()) > 0
        and to_hex(collection.get_colors()[0], keep_alpha=False)
        == to_hex(DrawStyle().theme.measurement_color, keep_alpha=False)
    ]
    classical_arrow_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, Line3DCollection)
        and len(collection.get_colors()) > 0
        and to_hex(collection.get_colors()[0], keep_alpha=False)
        == to_hex(DrawStyle().theme.classical_wire_color, keep_alpha=False)
    ]

    assert plane_collections
    assert any(
        collection.get_alpha() is not None and collection.get_alpha() >= 0.08
        for collection in plane_collections
    )
    assert any(
        collection.get_linewidths()[0] < DrawStyle().line_width for collection in gate_collections
    )
    assert measurement_symbol_collections
    assert not any(text.get_text() == "M" for text in axes.texts)
    assert any(
        len(getattr(collection, "_segments3d", collection.get_segments())) >= 2
        for collection in classical_arrow_collections
    )


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

    assert axes.name == "3d"
    assert_axes_contains_circuit_artists(axes, min_line_like_artists=2, min_patches=0)
    assert_figure_has_visible_content(figure)
    assert_saved_image_has_visible_content(output)
