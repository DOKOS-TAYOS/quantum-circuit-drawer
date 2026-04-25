from __future__ import annotations

import builtins
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import matplotlib.pyplot as plt
import pytest

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    CircuitBuilder,
    HardwareTopology,
    draw_quantum_circuit,
)
from quantum_circuit_drawer.adapters.qiskit_adapter import QiskitAdapter
from quantum_circuit_drawer.drawing.pipeline import (
    PreparedDrawPipeline,
    _resolve_qasm_input,
    prepare_draw_pipeline,
)
from quantum_circuit_drawer.drawing.request import DrawRequest, build_draw_request
from quantum_circuit_drawer.exceptions import UnsupportedFrameworkError
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.operations import (
    CanonicalGateFamily,
    OperationIR,
    OperationKind,
)
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.scene_3d import ConnectionRenderStyle3D
from quantum_circuit_drawer.layout.topology_3d import build_topology
from quantum_circuit_drawer.renderers._matplotlib_figure import get_topology_menu_state
from tests.support import (
    OperationSignature,
    assert_classical_wire_bundles,
    assert_operation_signatures,
    assert_quantum_wire_labels,
    build_public_draw_config,
)


def _build_quantum_wires(count: int) -> tuple[WireIR, ...]:
    return tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(count)
    )


def _build_topology_ir(count: int) -> CircuitIR:
    return CircuitIR(
        quantum_wires=_build_quantum_wires(count),
        layers=(),
    )


def _build_controlled_three_qubit_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=_build_quantum_wires(3),
        layers=(
            LayerIR(
                operations=(
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        canonical_family=CanonicalGateFamily.X,
                        target_wires=("q2",),
                        control_wires=("q0",),
                    ),
                )
            ),
        ),
    )


def _prepare_3d_pipeline(
    circuit: object,
    *,
    framework: str | None = None,
    topology: str | HardwareTopology = "line",
    topology_menu: bool = False,
    direct: bool = True,
    topology_qubits: str = "used",
    topology_resize: str = "error",
) -> PreparedDrawPipeline:
    request = build_draw_request(
        circuit=circuit,
        framework=framework,
        show=False,
        view="3d",
        topology=topology,  # type: ignore[arg-type]
        topology_menu=topology_menu,
        direct=direct,
        topology_qubits=topology_qubits,  # type: ignore[arg-type]
        topology_resize=topology_resize,  # type: ignore[arg-type]
        hover=True,
    )
    return prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )


def _prepare_request(
    circuit: object,
    *,
    framework: str | None = None,
) -> DrawRequest:
    return build_draw_request(
        circuit=circuit,
        framework=framework,
        show=False,
    )


class _FakeQiskitCircuit:
    def __init__(self, source: tuple[str, str]) -> None:
        self.source = source

    @classmethod
    def from_qasm_str(cls, qasm_text: str) -> _FakeQiskitCircuit:
        return cls(("qasm2", qasm_text))


class _FakeQiskitMissingOptionalLibraryError(Exception):
    pass


def _install_fake_qiskit(
    monkeypatch: pytest.MonkeyPatch,
    *,
    qasm3_loads: object,
) -> None:
    fake_qiskit = ModuleType("qiskit")
    fake_qiskit.QuantumCircuit = _FakeQiskitCircuit
    fake_qiskit.circuit = SimpleNamespace(QuantumCircuit=_FakeQiskitCircuit)
    fake_qiskit.qasm3 = SimpleNamespace(loads=qasm3_loads)
    monkeypatch.setitem(sys.modules, "qiskit", fake_qiskit)


def test_public_package_exports_builder_and_hardware_topology() -> None:
    assert quantum_circuit_drawer.CircuitBuilder is CircuitBuilder
    assert quantum_circuit_drawer.HardwareTopology is HardwareTopology
    for export_name in (
        "FunctionalTopology",
        "PeriodicTopology1D",
        "PeriodicTopology2D",
        "line_topology",
        "grid_topology",
        "star_topology",
        "star_tree_topology",
        "honeycomb_topology",
    ):
        assert hasattr(quantum_circuit_drawer, export_name)


def test_hardware_topology_from_coupling_map_preserves_custom_coordinates() -> None:
    circuit = _build_topology_ir(3)
    topology = HardwareTopology.from_coupling_map(
        [(0, 1), (1, 2)],
        name="linear_demo",
        coordinates={
            0: (0.0, 0.0),
            1: (1.25, 0.5),
            2: (2.5, 0.0),
        },
    )

    built_topology = build_topology(topology, tuple(circuit.quantum_wires))

    assert built_topology.name == "linear_demo"
    assert built_topology.positions == {
        "q0": (0.0, 0.0),
        "q1": (1.25, 0.5),
        "q2": (2.5, 0.0),
    }
    assert built_topology.edges == (("q0", "q1"), ("q1", "q2"))


def test_builtin_topologies_accept_flexible_qubit_counts() -> None:
    for topology_name, wire_count in (
        ("grid", 5),
        ("star", 1),
        ("star_tree", 5),
        ("honeycomb", 7),
    ):
        built_topology = build_topology(topology_name, _build_quantum_wires(wire_count))

        assert len(built_topology.nodes) == wire_count

    assert len(quantum_circuit_drawer.line_topology(3).node_ids) == 3
    assert len(quantum_circuit_drawer.grid_topology(5).node_ids) == 5
    assert len(quantum_circuit_drawer.star_topology(1).node_ids) == 1
    assert len(quantum_circuit_drawer.star_tree_topology(5).node_ids) == 5
    assert len(quantum_circuit_drawer.honeycomb_topology(7).node_ids) == 7


def test_honeycomb_topology_uses_compact_hexagonal_chip_patch() -> None:
    seed_topology = quantum_circuit_drawer.honeycomb_topology(6)
    assert set(seed_topology.edges) == {
        (0, 1),
        (0, 5),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
    }

    topology = quantum_circuit_drawer.honeycomb_topology(7)
    assert topology.coordinates is not None
    degree_by_node = {node_id: 0 for node_id in topology.node_ids}
    for first, second in topology.edges:
        degree_by_node[first] += 1
        degree_by_node[second] += 1

    assert len(topology.edges) >= len(topology.node_ids)
    assert max(degree_by_node.values()) <= 3

    compact_topology = quantum_circuit_drawer.honeycomb_topology(10)
    assert compact_topology.coordinates is not None
    compact_width = max(position[0] for position in compact_topology.coordinates.values()) - min(
        position[0] for position in compact_topology.coordinates.values()
    )
    compact_height = max(position[1] for position in compact_topology.coordinates.values()) - min(
        position[1] for position in compact_topology.coordinates.values()
    )
    assert max(compact_width, compact_height) / min(compact_width, compact_height) <= 1.35
    assert len({position[1] for position in compact_topology.coordinates.values()}) >= 6

    larger_topology = quantum_circuit_drawer.honeycomb_topology(27)
    larger_degree_by_node = {node_id: 0 for node_id in larger_topology.node_ids}
    for first, second in larger_topology.edges:
        larger_degree_by_node[first] += 1
        larger_degree_by_node[second] += 1

    assert max(larger_degree_by_node.values()) == 3


def test_grid_topology_prefers_square_core_for_small_remainders() -> None:
    topology = quantum_circuit_drawer.grid_topology(10)

    assert sorted({position[0] for position in topology.coordinates.values()}) == [
        0.0,
        1.0,
        2.0,
    ]
    assert sorted({position[1] for position in topology.coordinates.values()}) == [
        -3.0,
        -2.0,
        -1.0,
        0.0,
    ]
    assert topology.coordinates[9] == (1.0, -3.0)
    assert (7, 9) in topology.edges
    assert (8, 9) not in topology.edges


def test_static_topology_can_render_used_or_all_nodes_when_circuit_is_smaller() -> None:
    topology = HardwareTopology(
        node_ids=(0, 1, 2, 3),
        edges=((0, 1), (1, 2), (2, 3)),
        coordinates={
            0: (0.0, 0.0),
            1: (1.0, 0.0),
            2: (2.0, 0.0),
            3: (3.0, 0.0),
        },
        name="line4",
    )

    used_topology = build_topology(topology, _build_quantum_wires(2))
    full_topology = build_topology(topology, _build_quantum_wires(2), topology_qubits="all")

    assert [node.wire_id for node in used_topology.nodes] == ["q0", "q1"]
    assert used_topology.edges == (("q0", "q1"),)
    assert [node.label for node in full_topology.nodes] == ["q0", "q1", "2", "3"]
    assert [node.wire_id for node in full_topology.nodes[:2]] == ["q0", "q1"]
    assert len(full_topology.nodes) == 4
    assert full_topology.edges == (
        ("q0", "q1"),
        ("q1", "topology_line4_2"),
        ("topology_line4_2", "topology_line4_3"),
    )


def test_static_topology_rejects_larger_circuit_even_with_fit_policy() -> None:
    topology = HardwareTopology.from_coupling_map([(0, 1), (1, 2)], name="line3")

    with pytest.raises(ValueError, match="static topology 'line3' has 3 nodes but circuit uses 4"):
        build_topology(
            topology,
            _build_quantum_wires(4),
            topology_resize="fit",
        )


def test_functional_topology_resizes_only_when_requested() -> None:
    topology = quantum_circuit_drawer.FunctionalTopology(
        quantum_circuit_drawer.line_topology,
        qubit_count=2,
        name="dynamic_line",
    )

    with pytest.raises(ValueError, match="topology 'dynamic_line' has 2 nodes but circuit uses 3"):
        build_topology(topology, _build_quantum_wires(3))

    built_topology = build_topology(
        topology,
        _build_quantum_wires(3),
        topology_resize="fit",
    )

    assert [node.wire_id for node in built_topology.nodes] == ["q0", "q1", "q2"]


def test_periodic_1d_topology_auto_expands_to_fit_required_qubits() -> None:
    cell = HardwareTopology(node_ids=("x",), edges=(), coordinates={"x": (0.0, 0.0)})
    topology = quantum_circuit_drawer.PeriodicTopology1D(
        initial_cell=cell,
        periodic_cell=cell,
        final_cell=cell,
        bridge_edges=(("x", "x"),),
        repeat_count=1,
        name="chain",
    )

    built_topology = build_topology(
        topology,
        _build_quantum_wires(5),
        topology_resize="fit",
    )

    assert [node.wire_id for node in built_topology.nodes] == ["q0", "q1", "q2", "q3", "q4"]
    assert len(built_topology.edges) == 4


def test_periodic_2d_topology_auto_expands_balanced_grid_to_fit_required_qubits() -> None:
    cell = HardwareTopology(node_ids=("x",), edges=(), coordinates={"x": (0.0, 0.0)})
    topology = quantum_circuit_drawer.PeriodicTopology2D(
        top_left_cell=cell,
        top_edge_cell=cell,
        top_right_cell=cell,
        left_edge_cell=cell,
        center_cell=cell,
        right_edge_cell=cell,
        bottom_left_cell=cell,
        bottom_edge_cell=cell,
        bottom_right_cell=cell,
        horizontal_bridge_edges=(("x", "x"),),
        vertical_bridge_edges=(("x", "x"),),
        rows=1,
        columns=1,
        name="patch",
    )

    built_topology = build_topology(
        topology,
        _build_quantum_wires(12),
        topology_qubits="all",
        topology_resize="fit",
    )

    assert len(built_topology.nodes) == 16
    assert len({node.x for node in built_topology.nodes}) == 4
    assert len({node.y for node in built_topology.nodes}) == 4


def test_full_topology_render_adds_inactive_quantum_wires_with_physical_labels() -> None:
    topology = HardwareTopology(
        node_ids=(0, 1, 2),
        edges=((0, 1), (1, 2)),
        coordinates={0: (0.0, 0.0), 1: (1.0, 0.0), 2: (2.0, 0.0)},
        name="line3",
    )

    pipeline = _prepare_3d_pipeline(
        _build_topology_ir(2),
        topology=topology,
        topology_qubits="all",
    )

    assert [wire.label for wire in pipeline.paged_scene.wires if wire.kind is WireKind.QUANTUM] == [
        "q0",
        "q1",
        "2",
    ]


def test_hardware_topology_autolayout_is_deterministic() -> None:
    circuit = _build_topology_ir(4)
    topology = HardwareTopology.from_graph(
        {
            "n0": ("n1", "n2"),
            "n1": ("n0", "n3"),
            "n2": ("n0", "n3"),
            "n3": ("n1", "n2"),
        },
        name="diamond",
    )

    first = build_topology(topology, tuple(circuit.quantum_wires))
    second = build_topology(topology, tuple(circuit.quantum_wires))

    assert first.positions == second.positions
    assert len({position for position in first.positions.values()}) == 4


def test_prepare_draw_pipeline_routes_indirect_connections_on_custom_topology() -> None:
    topology = HardwareTopology.from_coupling_map(
        [(0, 1), (1, 2)],
        name="line3",
        coordinates={
            0: (0.0, 0.0),
            1: (1.0, 0.0),
            2: (2.0, 0.0),
        },
    )

    pipeline = _prepare_3d_pipeline(
        _build_controlled_three_qubit_ir(),
        topology=topology,
        direct=False,
    )
    control_connections = [
        connection
        for connection in pipeline.paged_scene.connections
        if connection.render_style is ConnectionRenderStyle3D.CONTROL
    ]

    assert len(control_connections) == 1
    assert [point.x for point in control_connections[0].points] == [0.0, 1.0, 2.0]


def test_draw_quantum_circuit_disables_topology_menu_for_custom_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topology = HardwareTopology.from_coupling_map(
        [(0, 1)],
        name="custom_pair",
        coordinates={0: (0.0, 0.0), 1: (1.0, 0.0)},
    )
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    result = draw_quantum_circuit(
        _build_topology_ir(2),
        config=build_public_draw_config(
            view="3d",
            topology=topology,
            topology_menu=True,
            hover=True,
            show=False,
        ),
    )

    assert get_topology_menu_state(result.primary_figure) is None
    assert any(
        diagnostic.code == "topology_menu_disabled_custom_topology"
        for diagnostic in result.diagnostics
    )

    plt.close(result.primary_figure)


def test_circuit_builder_builds_packed_ir_with_named_and_indexed_wires() -> None:
    circuit = (
        CircuitBuilder(["ancilla", "data"], ["readout0", "readout1"], name="demo")
        .h("ancilla")
        .x(1)
        .cx("ancilla", "data")
        .reset("data")
        .barrier(0, 1)
        .measure_all()
        .build()
    )

    assert circuit.name == "demo"
    assert_quantum_wire_labels(circuit, ["ancilla", "data"])
    assert_classical_wire_bundles(circuit, [("readout0", 1), ("readout1", 1)])
    assert len(circuit.layers) == 5
    assert [operation.name for operation in circuit.layers[0].operations] == ["H", "X"]
    assert_operation_signatures(
        circuit,
        [
            OperationSignature(OperationKind.GATE, CanonicalGateFamily.H, "H", (), ("q0",)),
            OperationSignature(OperationKind.GATE, CanonicalGateFamily.X, "X", (), ("q1",)),
            OperationSignature(
                OperationKind.CONTROLLED_GATE,
                CanonicalGateFamily.X,
                "X",
                (),
                ("q1",),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.RESET,
                "RESET",
                (),
                ("q1",),
            ),
            OperationSignature(
                OperationKind.BARRIER,
                CanonicalGateFamily.CUSTOM,
                "BARRIER",
                (),
                ("q0", "q1"),
            ),
            OperationSignature(
                OperationKind.MEASUREMENT,
                CanonicalGateFamily.CUSTOM,
                "M",
                (),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.MEASUREMENT,
                CanonicalGateFamily.CUSTOM,
                "M",
                (),
                ("q1",),
            ),
        ],
    )


def test_circuit_builder_supports_generic_gate_swap_and_measure() -> None:
    circuit = (
        CircuitBuilder(2, 2)
        .gate("RZ", 0, params=(0.5,))
        .swap(0, 1)
        .measure(0, 0)
        .measure(1, 1)
        .build()
    )

    assert_quantum_wire_labels(circuit, ["q0", "q1"])
    assert_classical_wire_bundles(circuit, [("c0", 1), ("c1", 1)])
    assert_operation_signatures(
        circuit,
        [
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.RZ,
                "RZ",
                (0.5,),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.SWAP,
                CanonicalGateFamily.CUSTOM,
                "SWAP",
                (),
                ("q0", "q1"),
            ),
            OperationSignature(
                OperationKind.MEASUREMENT,
                CanonicalGateFamily.CUSTOM,
                "M",
                (),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.MEASUREMENT,
                CanonicalGateFamily.CUSTOM,
                "M",
                (),
                ("q1",),
            ),
        ],
    )


@pytest.mark.optional
@pytest.mark.integration
def test_prepare_draw_pipeline_accepts_openqasm_strings() -> None:
    qiskit = pytest.importorskip("qiskit")
    qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[2];
        creg c[1];
        h q[0];
        cx q[0],q[1];
        measure q[1] -> c[0];
    """

    request = _prepare_request(qasm)
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )
    expected_ir = QiskitAdapter().to_ir(qiskit.QuantumCircuit.from_qasm_str(qasm))

    assert_quantum_wire_labels(pipeline.ir, ["q0", "q1"])
    assert_classical_wire_bundles(pipeline.ir, [("c", 1)])
    assert_operation_signatures(
        pipeline.ir,
        [
            OperationSignature(OperationKind.GATE, CanonicalGateFamily.H, "H", (), ("q0",)),
            OperationSignature(
                OperationKind.CONTROLLED_GATE,
                CanonicalGateFamily.X,
                "X",
                (),
                ("q1",),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.MEASUREMENT,
                CanonicalGateFamily.CUSTOM,
                "M",
                (),
                ("q1",),
            ),
        ],
    )
    assert_operation_signatures(
        pipeline.ir,
        [
            OperationSignature(
                operation.kind,
                operation.canonical_family,
                operation.name,
                tuple(operation.parameters),
                tuple(operation.target_wires),
                tuple(operation.control_wires),
            )
            for layer in expected_ir.layers
            for operation in layer.operations
        ],
    )


def test_resolve_qasm_input_accepts_openqasm3_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    qasm = "OPENQASM 3.0; qubit[1] q;"
    loaded_texts: list[str] = []

    def fake_loads(qasm_text: str) -> _FakeQiskitCircuit:
        loaded_texts.append(qasm_text)
        return _FakeQiskitCircuit(("qasm3", qasm_text))

    _install_fake_qiskit(monkeypatch, qasm3_loads=fake_loads)

    circuit, framework = _resolve_qasm_input(qasm, None)

    assert framework == "qiskit"
    assert isinstance(circuit, _FakeQiskitCircuit)
    assert circuit.source == ("qasm3", qasm)
    assert loaded_texts == [qasm]


def test_resolve_qasm_input_accepts_openqasm3_path(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    qasm_path = sandbox_tmp_path / "bell.qasm3"
    qasm_path.write_text("OPENQASM 3.0; qubit[1] q;", encoding="utf-8")

    def fake_loads(qasm_text: str) -> _FakeQiskitCircuit:
        return _FakeQiskitCircuit(("qasm3", qasm_text))

    _install_fake_qiskit(monkeypatch, qasm3_loads=fake_loads)

    circuit, framework = _resolve_qasm_input(qasm_path, None)

    assert framework == "qiskit"
    assert isinstance(circuit, _FakeQiskitCircuit)
    assert circuit.source == ("qasm3", "OPENQASM 3.0; qubit[1] q;")


def test_resolve_qasm_input_accepts_explicit_qasm_framework_for_openqasm3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    qasm = "OPENQASM 3.0; qubit[1] q;"

    def fake_loads(qasm_text: str) -> _FakeQiskitCircuit:
        return _FakeQiskitCircuit(("qasm3", qasm_text))

    _install_fake_qiskit(monkeypatch, qasm3_loads=fake_loads)

    circuit, framework = _resolve_qasm_input(qasm, "qasm")

    assert framework == "qiskit"
    assert isinstance(circuit, _FakeQiskitCircuit)
    assert circuit.source == ("qasm3", qasm)


@pytest.mark.optional
@pytest.mark.integration
def test_prepare_draw_pipeline_accepts_openqasm3_strings() -> None:
    qiskit = pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_qasm3_import")
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        bit[1] c;
        h q[0];
        cx q[0], q[1];
        c[0] = measure q[1];
    """

    request = _prepare_request(qasm)
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )
    expected_ir = QiskitAdapter().to_ir(qiskit.qasm3.loads(qasm))

    assert_quantum_wire_labels(pipeline.ir, ["q0", "q1"])
    assert_classical_wire_bundles(pipeline.ir, [("c", 1)])
    assert_operation_signatures(
        pipeline.ir,
        [
            OperationSignature(OperationKind.GATE, CanonicalGateFamily.H, "H", (), ("q0",)),
            OperationSignature(
                OperationKind.CONTROLLED_GATE,
                CanonicalGateFamily.X,
                "X",
                (),
                ("q1",),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.MEASUREMENT,
                CanonicalGateFamily.CUSTOM,
                "M",
                (),
                ("q1",),
            ),
        ],
    )
    assert_operation_signatures(
        pipeline.ir,
        [
            OperationSignature(
                operation.kind,
                operation.canonical_family,
                operation.name,
                tuple(operation.parameters),
                tuple(operation.target_wires),
                tuple(operation.control_wires),
            )
            for layer in expected_ir.layers
            for operation in layer.operations
        ],
    )


@pytest.mark.optional
@pytest.mark.integration
def test_prepare_draw_pipeline_accepts_explicit_qasm_framework() -> None:
    pytest.importorskip("qiskit")
    qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        x q[0];
    """

    request = _prepare_request(qasm, framework="qasm")
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )

    assert_operation_signatures(
        pipeline.ir,
        [
            OperationSignature(OperationKind.GATE, CanonicalGateFamily.X, "X", (), ("q0",)),
        ],
    )


@pytest.mark.optional
@pytest.mark.integration
def test_prepare_draw_pipeline_accepts_openqasm_path(sandbox_tmp_path: Path) -> None:
    pytest.importorskip("qiskit")
    qasm_path = sandbox_tmp_path / "bell.qasm"
    qasm_path.write_text(
        """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[2];
        creg c[1];
        h q[0];
        cx q[0],q[1];
        measure q[1] -> c[0];
        """,
        encoding="utf-8",
    )

    request = _prepare_request(qasm_path)
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )

    assert_quantum_wire_labels(pipeline.ir, ["q0", "q1"])
    assert_classical_wire_bundles(pipeline.ir, [("c", 1)])
    assert_operation_signatures(
        pipeline.ir,
        [
            OperationSignature(OperationKind.GATE, CanonicalGateFamily.H, "H", (), ("q0",)),
            OperationSignature(
                OperationKind.CONTROLLED_GATE,
                CanonicalGateFamily.X,
                "X",
                (),
                ("q1",),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.MEASUREMENT,
                CanonicalGateFamily.CUSTOM,
                "M",
                (),
                ("q1",),
            ),
        ],
    )


@pytest.mark.optional
@pytest.mark.integration
def test_prepare_draw_pipeline_accepts_openqasm_string_path_with_explicit_framework(
    sandbox_tmp_path: Path,
) -> None:
    pytest.importorskip("qiskit")
    qasm_path = sandbox_tmp_path / "x_gate.qasm"
    qasm_path.write_text(
        """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        x q[0];
        """,
        encoding="utf-8",
    )

    request = _prepare_request(str(qasm_path), framework="qasm")
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )

    assert_operation_signatures(
        pipeline.ir,
        [
            OperationSignature(OperationKind.GATE, CanonicalGateFamily.X, "X", (), ("q0",)),
        ],
    )


def test_draw_quantum_circuit_qasm_path_reports_missing_file(sandbox_tmp_path: Path) -> None:
    missing_path = sandbox_tmp_path / "missing.qasm"

    with pytest.raises(UnsupportedFrameworkError, match="OpenQASM file does not exist"):
        draw_quantum_circuit(missing_path, config=build_public_draw_config(show=False))


def test_draw_quantum_circuit_qasm_path_requires_openqasm_header(
    sandbox_tmp_path: Path,
) -> None:
    qasm_path = sandbox_tmp_path / "invalid.qasm"
    qasm_path.write_text("qreg q[1];", encoding="utf-8")

    with pytest.raises(UnsupportedFrameworkError, match="must start with 'OPENQASM'"):
        draw_quantum_circuit(qasm_path, config=build_public_draw_config(show=False))


def test_draw_quantum_circuit_explicit_qasm_requires_text_or_qasm_path(
    sandbox_tmp_path: Path,
) -> None:
    text_path = sandbox_tmp_path / "circuit.txt"
    text_path.write_text("OPENQASM 2.0;", encoding="utf-8")

    with pytest.raises(UnsupportedFrameworkError, match=r"\.qasm or \.qasm3 extension"):
        draw_quantum_circuit(
            text_path,
            config=build_public_draw_config(framework="qasm", show=False),
        )


def test_draw_quantum_circuit_qasm3_requires_importer_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    qasm = "OPENQASM 3.0; qubit[1] q;"

    def fake_loads(qasm_text: str) -> _FakeQiskitCircuit:
        raise _FakeQiskitMissingOptionalLibraryError(
            "The 'qiskit_qasm3_import' library is required"
        )

    _install_fake_qiskit(monkeypatch, qasm3_loads=fake_loads)

    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"OpenQASM 3 input requires .*qiskit-qasm3-import.*qasm3",
    ):
        draw_quantum_circuit(qasm, config=build_public_draw_config(show=False))


def test_draw_quantum_circuit_rejects_unsupported_openqasm_version() -> None:
    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"unsupported OpenQASM version '4\.0'",
    ):
        draw_quantum_circuit("OPENQASM 4.0;", config=build_public_draw_config(show=False))


def test_draw_quantum_circuit_qasm_requires_qiskit_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__
    qasm = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[1];'

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "qiskit" or name.startswith("qiskit."):
            raise ModuleNotFoundError(name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(UnsupportedFrameworkError, match=r"OpenQASM input requires .*qiskit"):
        draw_quantum_circuit(qasm, config=build_public_draw_config(show=False))


def test_draw_quantum_circuit_does_not_autodetect_arbitrary_strings_as_qasm() -> None:
    with pytest.raises(UnsupportedFrameworkError, match="string inputs are only supported"):
        draw_quantum_circuit("hello quantum world", config=build_public_draw_config(show=False))
