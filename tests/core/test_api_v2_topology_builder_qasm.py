from __future__ import annotations

import builtins

import matplotlib.pyplot as plt
import pytest

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    CircuitBuilder,
    HardwareTopology,
    draw_quantum_circuit,
)
from quantum_circuit_drawer.adapters.qiskit_adapter import QiskitAdapter
from quantum_circuit_drawer.drawing.pipeline import PreparedDrawPipeline, prepare_draw_pipeline
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
) -> PreparedDrawPipeline:
    request = build_draw_request(
        circuit=circuit,
        framework=framework,
        show=False,
        view="3d",
        topology=topology,  # type: ignore[arg-type]
        topology_menu=topology_menu,
        direct=direct,
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


def test_public_package_exports_builder_and_hardware_topology() -> None:
    assert quantum_circuit_drawer.CircuitBuilder is CircuitBuilder
    assert quantum_circuit_drawer.HardwareTopology is HardwareTopology


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
