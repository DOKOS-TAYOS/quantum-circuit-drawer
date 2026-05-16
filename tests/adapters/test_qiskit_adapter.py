from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

pytestmark = [pytest.mark.optional, pytest.mark.integration]

qiskit = pytest.importorskip("qiskit")

from qiskit.circuit.classical import expr

from quantum_circuit_drawer.adapters.qiskit_adapter import QiskitAdapter
from quantum_circuit_drawer.drawing.pipeline import prepare_draw_pipeline
from quantum_circuit_drawer.exceptions import UnsupportedOperationError
from quantum_circuit_drawer.hover import HoverOptions
from quantum_circuit_drawer.ir.lowering import lower_semantic_circuit
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind
from quantum_circuit_drawer.ir.semantic import SemanticCircuitIR
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.style import DrawStyle
from tests.support import (
    OperationSignature,
    assert_axes_contains_circuit_artists,
    assert_classical_wire_bundles,
    assert_operation_signatures,
    assert_quantum_wire_labels,
    flatten_operations,
)
from tests.support import (
    draw_quantum_circuit_legacy as draw_quantum_circuit,
)


def flatten_semantic_operations(circuit: SemanticCircuitIR) -> list[object]:
    return [operation for layer in circuit.layers for operation in layer.operations]


def test_qiskit_adapter_matches_canonical_contract() -> None:
    circuit = qiskit.QuantumCircuit(2, 1)
    circuit.h(0)
    circuit.rz(0.5, 1)
    circuit.cx(0, 1)
    circuit.measure(1, 0)

    ir = QiskitAdapter().to_ir(circuit)
    measurement = flatten_operations(ir)[-1]

    assert ir.metadata["framework"] == "qiskit"
    assert_quantum_wire_labels(ir, ["q0", "q1"])
    assert_classical_wire_bundles(ir, [("c", 1)])
    assert_operation_signatures(
        ir,
        [
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.H,
                "H",
                (),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.RZ,
                "RZ",
                (0.5,),
                ("q1",),
            ),
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
    assert measurement.classical_target == "c0"
    assert measurement.metadata["classical_bit_label"] == "c[0]"


def test_qiskit_adapter_exposes_semantic_ir_for_standard_circuit() -> None:
    circuit = qiskit.QuantumCircuit(2, 1)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure(1, 0)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    lowered_ir = lower_semantic_circuit(semantic_ir)

    assert semantic_ir.metadata["framework"] == "qiskit"
    assert_operation_signatures(
        lowered_ir,
        [
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.H,
                "H",
                (),
                ("q0",),
            ),
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
    assert flatten_semantic_operations(semantic_ir)[0].provenance.framework == "qiskit"


def test_qiskit_adapter_converts_common_operations() -> None:
    circuit = qiskit.QuantumCircuit(2, 1)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.swap(0, 1)
    circuit.barrier()
    circuit.measure(1, 0)

    ir = QiskitAdapter().to_ir(circuit)

    names = [operation.name for layer in ir.layers for operation in layer.operations]
    kinds = [operation.kind for layer in ir.layers for operation in layer.operations]

    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].label == "c"
    assert ir.classical_wires[0].metadata["bundle_size"] == 1
    assert "H" in names
    assert "X" in names
    assert OperationKind.SWAP in kinds
    assert OperationKind.BARRIER in kinds
    assert OperationKind.MEASUREMENT in kinds


def test_qiskit_adapter_preserves_temporal_order_when_packing_layers() -> None:
    circuit = qiskit.QuantumCircuit(3, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cz(1, 2)
    circuit.swap(0, 2)
    circuit.barrier()
    circuit.measure(1, 0)
    circuit.measure(2, 1)

    ir = QiskitAdapter().to_ir(circuit)

    layer_kinds = [[operation.kind for operation in layer.operations] for layer in ir.layers]

    assert layer_kinds == [
        [OperationKind.GATE],
        [OperationKind.CONTROLLED_GATE],
        [OperationKind.CONTROLLED_GATE],
        [OperationKind.SWAP],
        [OperationKind.BARRIER],
        [OperationKind.MEASUREMENT],
        [OperationKind.MEASUREMENT],
    ]


def test_qiskit_adapter_groups_classical_bits_by_register() -> None:
    quantum = qiskit.QuantumRegister(3, "q")
    first = qiskit.ClassicalRegister(2, "alpha")
    second = qiskit.ClassicalRegister(3, "beta")
    circuit = qiskit.QuantumCircuit(quantum, first, second)
    circuit.measure(0, first[0])
    circuit.measure(1, second[1])

    ir = QiskitAdapter().to_ir(circuit)

    assert [(wire.label, wire.metadata["bundle_size"]) for wire in ir.classical_wires] == [
        ("alpha", 2),
        ("beta", 3),
    ]
    assert [
        operation.classical_target for layer in ir.layers for operation in layer.operations
    ] == [
        ir.classical_wires[0].id,
        ir.classical_wires[1].id,
    ]


def test_qiskit_adapter_preserves_named_quantum_register_labels() -> None:
    first = qiskit.QuantumRegister(2, name="qchannel(1)")
    second = qiskit.QuantumRegister(1, name="qchannel(2)")
    classical = qiskit.ClassicalRegister(3, name="classic")
    circuit = qiskit.QuantumCircuit(first, second, classical, name="Circuit")

    ir = QiskitAdapter().to_ir(circuit)

    assert_quantum_wire_labels(
        ir,
        [
            "qchannel(1)[0]",
            "qchannel(1)[1]",
            "qchannel(2)",
        ],
    )


def test_qiskit_adapter_keeps_individual_classical_bit_labels() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(2, "alpha")
    circuit = qiskit.QuantumCircuit(quantum, classical)
    circuit.measure(0, classical[0])
    circuit.measure(1, classical[1])

    ir = QiskitAdapter().to_ir(circuit)

    measurements = [operation for layer in ir.layers for operation in layer.operations]

    assert [measurement.metadata["classical_bit_label"] for measurement in measurements] == [
        "alpha[0]",
        "alpha[1]",
    ]


def test_qiskit_adapter_maps_canonical_gate_families() -> None:
    circuit = qiskit.QuantumCircuit(3)
    circuit.h(0)
    circuit.rz(0.5, 1)
    circuit.cx(0, 1)
    circuit.cz(1, 2)
    circuit.ccx(0, 1, 2)
    circuit.crz(0.25, 0, 2)

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]
    signatures = [
        (operation.kind, operation.canonical_family, len(operation.control_wires), operation.name)
        for operation in operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.H, 0, "H") in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.RZ, 0, "RZ") in signatures
    assert (OperationKind.CONTROLLED_GATE, CanonicalGateFamily.X, 1, "X") in signatures
    assert (OperationKind.CONTROLLED_GATE, CanonicalGateFamily.Z, 1, "Z") in signatures
    assert (OperationKind.CONTROLLED_GATE, CanonicalGateFamily.X, 2, "X") in signatures
    assert (OperationKind.CONTROLLED_GATE, CanonicalGateFamily.RZ, 1, "RZ") in signatures


def test_qiskit_adapter_decodes_open_control_state_into_control_values() -> None:
    circuit = qiskit.QuantumCircuit(2)
    circuit.append(qiskit.circuit.library.XGate().control(1, ctrl_state=0), [0, 1])

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.kind is OperationKind.CONTROLLED_GATE
    assert operation.control_wires == ("q0",)
    assert operation.control_values == ((0,),)


def test_qiskit_adapter_decodes_mixed_multi_control_state_big_endian() -> None:
    circuit = qiskit.QuantumCircuit(3)
    circuit.append(qiskit.circuit.library.XGate().control(2, ctrl_state=1), [0, 1, 2])

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.kind is OperationKind.CONTROLLED_GATE
    assert operation.control_wires == ("q0", "q1")
    assert operation.control_values == ((0,), (1,))


def test_qiskit_adapter_maps_additional_canonical_gate_families() -> None:
    circuit = qiskit.QuantumCircuit(2)
    circuit.sdg(0)
    circuit.tdg(1)
    circuit.sx(0)
    circuit.p(0.25, 1)
    circuit.u(0.1, 0.2, 0.3, 0)
    circuit.iswap(0, 1)

    ir = QiskitAdapter().to_ir(circuit)
    signatures = [
        (operation.kind, operation.canonical_family, operation.name, tuple(operation.parameters))
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.SDG, "Sdg", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.TDG, "Tdg", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.SX, "SX", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.P, "P", (0.25,)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.U, "U", (0.1, 0.2, 0.3)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.ISWAP, "iSWAP", ()) in signatures


def test_qiskit_adapter_attaches_framework_matrices_when_available() -> None:
    circuit = qiskit.QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    h_matrix = np.asarray(operations[0].metadata["matrix"])
    cx_matrix = np.asarray(operations[1].metadata["matrix"])

    assert h_matrix.shape == (2, 2)
    assert cx_matrix.shape == (4, 4)
    assert np.allclose(h_matrix, np.asarray(circuit.data[0].operation.to_matrix()))
    assert np.allclose(cx_matrix, np.asarray(circuit.data[1].operation.to_matrix()))


def test_qiskit_adapter_skips_framework_matrices_when_explicit_matrices_are_disabled() -> None:
    circuit = qiskit.QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    ir = QiskitAdapter().to_ir(circuit, options={"explicit_matrices": False})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert "matrix" not in operations[0].metadata
    assert "matrix" not in operations[1].metadata


def test_qiskit_adapter_converts_bit_if_test_into_classically_conditioned_operation() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)):
        circuit.x(1)

    ir = QiskitAdapter().to_ir(circuit)
    conditioned_operation = next(operation for layer in ir.layers for operation in layer.operations)

    assert conditioned_operation.name == "X"
    assert conditioned_operation.classical_conditions[0].wire_ids == ("c0",)
    assert conditioned_operation.classical_conditions[0].expression == "if c[0]=1"


def test_qiskit_adapter_converts_register_if_test_into_classically_conditioned_operation() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical, 3)):
        circuit.z(1)

    ir = QiskitAdapter().to_ir(circuit)
    conditioned_operation = next(operation for layer in ir.layers for operation in layer.operations)

    assert conditioned_operation.name == "Z"
    assert conditioned_operation.classical_conditions[0].wire_ids == ("c0",)
    assert conditioned_operation.classical_conditions[0].expression == "if c=3"


def test_qiskit_adapter_converts_modern_bit_if_test_into_classically_conditioned_operation() -> (
    None
):
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test(expr.equal(classical[0], True)):
        circuit.x(0)

    ir = QiskitAdapter().to_ir(circuit)
    conditioned_operation = next(operation for layer in ir.layers for operation in layer.operations)

    assert conditioned_operation.name == "X"
    assert conditioned_operation.classical_conditions[0].wire_ids == ("c0",)
    assert conditioned_operation.classical_conditions[0].expression == "if c[0]=1"


def test_qiskit_adapter_converts_modern_compound_if_test_into_classically_conditioned_operation() -> (
    None
):
    quantum = qiskit.QuantumRegister(1, "q")
    first = qiskit.ClassicalRegister(1, "alpha")
    second = qiskit.ClassicalRegister(1, "beta")
    circuit = qiskit.QuantumCircuit(quantum, first, second)

    with circuit.if_test(
        expr.logic_and(
            expr.equal(first[0], True),
            expr.equal(second[0], False),
        )
    ):
        circuit.x(0)

    ir = QiskitAdapter().to_ir(circuit)
    conditioned_operation = next(operation for layer in ir.layers for operation in layer.operations)

    assert conditioned_operation.classical_conditions[0].wire_ids == ("c0", "c1")
    assert conditioned_operation.classical_conditions[0].expression == (
        "if (alpha[0]=1) && (beta[0]=0)"
    )


def test_qiskit_adapter_expands_multi_operation_if_block() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)):
        circuit.x(1)
        circuit.z(1)

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["X", "Z"]
    assert [operation.classical_conditions[0].expression for operation in operations] == [
        "if c[0]=1",
        "if c[0]=1",
    ]


def test_qiskit_adapter_expands_if_else_branches_with_group_metadata() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)) as else_:
        circuit.x(0)
    with else_:
        circuit.z(0)

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["X", "Z"]
    assert [operation.metadata["control_flow_group"]["label"] for operation in operations] == [
        "IF",
        "ELSE",
    ]
    assert operations[0].metadata["control_flow_group"]["conditions"][0].expression == ("if c[0]=1")
    assert operations[1].metadata["control_flow_group"]["conditions"] == ()
    assert operations[0].metadata["suppress_classical_condition_connections"] is True


def test_qiskit_adapter_falls_back_to_compact_if_when_simple_if_condition_is_not_normalizable() -> (
    None
):
    class UnsupportedCondition:
        def __str__(self) -> str:
            return "UnsupportedCondition()"

    operation = SimpleNamespace(
        blocks=(
            SimpleNamespace(
                qubits=("inner-q0",),
                clbits=(),
                data=((SimpleNamespace(name="x", params=()), ("inner-q0",), ()),),
            ),
        ),
        condition=UnsupportedCondition(),
    )

    converted = QiskitAdapter()._convert_if_else(
        operation=operation,
        qubits=("outer-q0",),
        clbits=(),
        qubit_ids={"outer-q0": "q0"},
        classical_targets={},
        register_targets={},
        composite_mode="expand",
        explicit_matrices=False,
    )

    assert len(converted) == 1
    assert converted[0].name == "IF"
    assert converted[0].classical_conditions == ()
    assert converted[0].hover_details == (
        "control flow: if_else",
        "condition: UnsupportedCondition()",
        "branches: true only",
        "block ops: true=1",
    )
    assert converted[0].provenance.native_name == "if_else"
    assert converted[0].metadata["qiskit_control_flow"] == "if_else"


def test_qiskit_adapter_expands_if_else_as_semantic_control_flow_groups() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)) as else_:
        circuit.x(0)
    with else_:
        circuit.z(0)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operations = flatten_semantic_operations(semantic_ir)
    lowered_operations = flatten_operations(lower_semantic_circuit(semantic_ir))

    assert [operation.name for operation in operations] == ["X", "Z"]
    assert [operation.provenance.composite_label for operation in operations] == ["IF", "ELSE"]
    assert operations[0].classical_conditions[0].expression == "if c[0]=1"
    assert operations[1].classical_conditions == ()
    assert operations[0].metadata["control_flow_group"]["details"] == (
        "control flow: if_else",
        "condition: if c[0]=1",
        "branches: true, false",
        "block ops: true=1, false=1",
    )
    assert operations[1].metadata["control_flow_group"]["details"] == (
        "control flow: if_else",
        "condition: if c[0]=1",
        "branches: true, false",
        "block ops: true=1, false=1",
    )
    assert lowered_operations[0].metadata["semantic_provenance"]["native_kind"] == "gate"
    assert (
        lowered_operations[0].metadata["semantic_provenance"]["decomposition_origin"] == "if_else"
    )


def test_qiskit_adapter_expands_if_else_with_modern_condition_as_semantic_control_flow_group() -> (
    None
):
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test(
        expr.logic_or(
            expr.equal(classical[0], True),
            expr.equal(classical[1], False),
        )
    ) as else_:
        circuit.x(0)
    with else_:
        circuit.z(0)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operations = flatten_semantic_operations(semantic_ir)

    assert [operation.name for operation in operations] == ["X", "Z"]
    assert operations[0].classical_conditions[0].expression == "if (c[0]=1) || (c[1]=0)"
    assert operations[0].metadata["control_flow_group"]["details"] == (
        "control flow: if_else",
        "condition: if (c[0]=1) || (c[1]=0)",
        "branches: true, false",
        "block ops: true=1, false=1",
    )


def test_qiskit_adapter_lowered_semantic_if_else_matches_direct_ir() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test(
        expr.logic_or(
            expr.equal(classical[0], True),
            expr.equal(classical[1], False),
        )
    ):
        circuit.x(0)

    adapter = QiskitAdapter()
    semantic_ir = adapter.to_semantic_ir(circuit)
    lowered_from_semantic = lower_semantic_circuit(semantic_ir)
    direct_ir = adapter.to_ir(circuit)

    lowered_operations = flatten_operations(lowered_from_semantic)
    direct_operations = flatten_operations(direct_ir)

    assert [
        (
            operation.kind,
            operation.name,
            operation.target_wires,
            tuple(condition.expression for condition in operation.classical_conditions),
        )
        for operation in lowered_operations
    ] == [
        (
            operation.kind,
            operation.name,
            operation.target_wires,
            tuple(condition.expression for condition in operation.classical_conditions),
        )
        for operation in direct_operations
    ]


def test_qiskit_adapter_expands_switch_case_branches_with_group_metadata() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.switch(classical[0]) as case:
        with case(0):
            circuit.x(0)
        with case(1):
            circuit.z(0)
        with case(case.DEFAULT):
            circuit.h(0)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operations = flatten_semantic_operations(semantic_ir)

    assert [operation.name for operation in operations] == ["X", "Z", "H"]
    assert [operation.provenance.composite_label for operation in operations] == [
        "case 0",
        "case 1",
        "case default",
    ]
    assert [operation.metadata["control_flow_group"]["label"] for operation in operations] == [
        "case 0",
        "case 1",
        "case default",
    ]
    assert operations[0].metadata["control_flow_group"]["conditions"][0].expression == (
        "switch on c[0]"
    )
    assert operations[0].metadata["control_flow_group"]["details"] == (
        "control flow: switch_case",
        "target: c[0]",
        "case: 0",
        "case ops: 1",
    )


def test_qiskit_adapter_expands_switch_case_multi_value_case_label() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.switch(classical) as case:
        with case(0, 1):
            circuit.x(0)
        with case(case.DEFAULT):
            circuit.h(0)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operations = flatten_semantic_operations(semantic_ir)

    assert [operation.metadata["control_flow_group"]["label"] for operation in operations] == [
        "case 0, 1",
        "case default",
    ]


def test_draw_qiskit_switch_case_shows_target_and_cases_in_static_output() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.switch(classical[0]) as case:
        with case(0):
            circuit.x(0)
        with case(case.DEFAULT):
            circuit.h(0)

    figure, axes = draw_quantum_circuit(circuit, framework="qiskit", show=False)

    assert_axes_contains_circuit_artists(
        axes,
        expected_texts={"case 0", "case default", "switch on c[0]", "X", "H"},
    )
    figure.clear()


def test_qiskit_adapter_expands_for_loop_and_keeps_control_flow_hover_metadata() -> None:
    circuit = qiskit.QuantumCircuit(1)
    body = qiskit.QuantumCircuit(1)
    body.x(0)
    circuit.for_loop(range(3), None, body, circuit.qubits, ())

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.name == "X"
    assert operation.kind is OperationKind.GATE
    assert operation.classical_conditions == ()
    assert operation.provenance.composite_label == "FOR"
    assert operation.metadata["control_flow_group"]["details"] == (
        "control flow: for_loop",
        "iteration: range(0, 3)",
        "body ops: 1",
    )


def test_qiskit_adapter_expands_while_loop_and_keeps_control_flow_hover_metadata() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)
    body = qiskit.QuantumCircuit(1, 1)
    body.x(0)
    circuit.while_loop((classical[0], 1), body, quantum, classical)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.name == "X"
    assert operation.classical_conditions == ()
    assert operation.provenance.composite_label == "WHILE"
    assert operation.metadata["control_flow_group"]["details"] == (
        "control flow: while_loop",
        "condition: if c[0]=1",
        "body ops: 1",
    )


def test_qiskit_adapter_normalizes_modern_while_loop_conditions() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)
    body = qiskit.QuantumCircuit(1, 2)
    body.x(0)
    circuit.while_loop(
        expr.logic_not(
            expr.logic_and(
                expr.equal(classical[0], True),
                expr.equal(classical[1], False),
            )
        ),
        body,
        quantum,
        classical,
    )

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.name == "X"
    assert operation.classical_conditions == ()
    assert operation.provenance.composite_label == "WHILE"
    assert operation.metadata["control_flow_group"]["details"] == (
        "control flow: while_loop",
        "condition: if !((c[0]=1) && (c[1]=0))",
        "body ops: 1",
    )


def test_qiskit_adapter_keeps_native_while_loop_hover_when_condition_is_not_normalizable() -> None:
    class UnsupportedCondition:
        def __str__(self) -> str:
            return "UnsupportedCondition()"

    operation = SimpleNamespace(
        condition=UnsupportedCondition(),
        params=(),
    )

    classical_conditions, condition_details = QiskitAdapter()._compact_control_flow_conditions(
        name="while_loop",
        operation=operation,
        classical_targets={},
        register_targets={},
    )
    hover_details = QiskitAdapter()._control_flow_hover_details(
        name="while_loop",
        operation=operation,
        condition_details=condition_details,
    )

    assert classical_conditions == ()
    assert hover_details == (
        "control flow: while_loop",
        "condition: UnsupportedCondition()",
        "body ops: 0",
    )


def test_qiskit_adapter_formats_logic_not_conditions_directly() -> None:
    classical = qiskit.ClassicalRegister(1, "c")
    condition = QiskitAdapter()._condition_from_qiskit(
        expr.logic_not(expr.equal(classical[0], True)),
        classical_targets={classical[0]: ("c0", "c[0]")},
        register_targets={classical: ("c0", "c")},
    )

    assert condition.wire_ids == ("c0",)
    assert condition.expression == "if !(c[0]=1)"


def test_qiskit_adapter_formats_expressive_switch_targets_directly() -> None:
    classical = qiskit.ClassicalRegister(1, "c")
    condition, target_text = QiskitAdapter()._switch_target_from_qiskit(
        expr.bit_not(classical[0]),
        classical_targets={classical[0]: ("c0", "c[0]")},
        register_targets={classical: ("c0", "c")},
    )

    assert condition.wire_ids == ("c0",)
    assert condition.expression == "switch on ~c[0]"
    assert target_text == "~c[0]"


def test_prepare_draw_pipeline_keeps_qiskit_control_flow_hover_details() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)) as else_:
        circuit.x(0)
    with else_:
        circuit.z(0)

    pipeline = prepare_draw_pipeline(
        circuit=circuit,
        framework="qiskit",
        style=None,
        layout=None,
        options={"hover": HoverOptions()},
    )
    hover_details = next(
        highlight.hover_data.details
        for highlight in pipeline.paged_scene.group_highlights
        if highlight.hover_data is not None and highlight.hover_data.name == "if"
    )

    assert hover_details == (
        "control flow: if_else",
        "condition: if c[0]=1",
        "branches: true, false",
        "block ops: true=1, false=1",
    )


def test_draw_quantum_circuit_renders_qiskit_control_flow_labels() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)) as else_:
        circuit.x(0)
    with else_:
        circuit.z(0)
    with circuit.switch(classical[0]) as case:
        with case(0):
            circuit.x(0)
        with case(case.DEFAULT):
            circuit.h(0)
    for_body = qiskit.QuantumCircuit(1)
    for_body.x(0)
    circuit.for_loop(range(2), None, for_body, quantum, ())
    while_body = qiskit.QuantumCircuit(1, 1)
    while_body.x(0)
    circuit.while_loop((classical[0], 1), while_body, quantum, classical)

    figure, axes = draw_quantum_circuit(circuit, framework="qiskit", show=False)

    assert_axes_contains_circuit_artists(
        axes,
        expected_texts={
            "if",
            "else",
            "case 0",
            "case default",
            "for x2",
            "while",
            "if c[0]=1",
        },
    )
    figure.clear()


def test_qiskit_adapter_expands_for_and_while_with_group_metadata_by_default() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)
    for_body = qiskit.QuantumCircuit(1)
    for_body.x(0)
    while_body = qiskit.QuantumCircuit(1, 1)
    while_body.h(0)

    circuit.for_loop(range(2), None, for_body, quantum, ())
    circuit.while_loop((classical[0], 1), while_body, quantum, classical)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operations = flatten_semantic_operations(semantic_ir)

    assert [operation.name for operation in operations] == ["X", "H"]
    assert [operation.provenance.composite_label for operation in operations] == [
        "FOR",
        "WHILE",
    ]
    assert [operation.provenance.location for operation in operations] == [(0, 0), (1, 0)]
    assert operations[0].metadata["control_flow_group"]["label"] == "FOR x2"
    assert operations[1].metadata["control_flow_group"]["label"] == "WHILE"
    assert "control flow: for_loop" in operations[0].metadata["control_flow_group"]["details"]
    assert "control flow: while_loop" in operations[1].metadata["control_flow_group"]["details"]


def test_layout_engine_draws_qiskit_for_and_while_body_groups_with_hover_data() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)
    for_body = qiskit.QuantumCircuit(1)
    for_body.x(0)
    while_body = qiskit.QuantumCircuit(1, 1)
    while_body.h(0)

    circuit.for_loop(range(2), None, for_body, quantum, ())
    circuit.while_loop((classical[0], 1), while_body, quantum, classical)

    ir = QiskitAdapter().to_ir(circuit)
    scene = LayoutEngine().compute(ir, DrawStyle())

    assert [gate.label for gate in scene.gates] == ["X", "H"]
    assert [highlight.label for highlight in scene.group_highlights] == ["FOR x2", "WHILE"]
    assert all(highlight.hover_data is not None for highlight in scene.group_highlights)
    assert scene.group_highlights[0].hover_data is not None
    assert scene.group_highlights[0].hover_data.name == "for"
    assert "control flow: for_loop" in scene.group_highlights[0].hover_data.details
    assert scene.group_highlights[1].hover_data is not None
    assert scene.group_highlights[1].hover_data.name == "while"
    assert "control flow: while_loop" in scene.group_highlights[1].hover_data.details


def test_layout_engine_compacts_independent_gates_inside_qiskit_while_group() -> None:
    quantum = qiskit.QuantumRegister(3, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)
    circuit.measure(0, 0)

    with circuit.while_loop((classical[0], 1)):
        circuit.h([0, 1, 2])

    ir = QiskitAdapter().to_ir(circuit)
    scene = LayoutEngine().compute(ir, DrawStyle())

    while_highlight = next(
        highlight for highlight in scene.group_highlights if highlight.label == "WHILE"
    )
    x_min = while_highlight.x - (while_highlight.width / 2.0)
    x_max = while_highlight.x + (while_highlight.width / 2.0)
    y_min = while_highlight.y - (while_highlight.height / 2.0)
    y_max = while_highlight.y + (while_highlight.height / 2.0)
    while_h_gates = [
        gate
        for gate in scene.gates
        if gate.label == "H" and x_min <= gate.x <= x_max and y_min <= gate.y <= y_max
    ]

    assert len(while_h_gates) == 3
    assert {gate.column for gate in while_h_gates} == {1}


def test_layout_engine_draws_qiskit_control_flow_group_conditions_and_for_iterations() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)) as else_:
        circuit.x(0)
    with else_:
        circuit.z(1)
    for_body = qiskit.QuantumCircuit(2)
    for_body.h(0)
    circuit.for_loop(range(3), None, for_body, quantum, ())
    while_body = qiskit.QuantumCircuit(2, 1)
    while_body.h(1)
    circuit.while_loop((classical[0], 1), while_body, quantum, classical)

    ir = QiskitAdapter().to_ir(circuit)
    scene = LayoutEngine().compute(ir, DrawStyle())

    assert [highlight.label for highlight in scene.group_highlights] == [
        "IF",
        "ELSE",
        "FOR x3",
        "WHILE",
    ]
    classical_connections = [
        connection
        for connection in scene.connections
        if connection.is_classical and connection.label == "if c[0]=1"
    ]
    assert len(classical_connections) == 2
    for connection in classical_connections:
        assert connection.double_line is True
        assert connection.arrow_at_end is True
        assert connection.y_start == scene.wire_y_positions["c0"]
        assert connection.y_end < scene.wire_y_positions["c0"]
    for highlight in scene.group_highlights:
        assert highlight.y + (highlight.height / 2.0) < scene.wire_y_positions["c0"]


def test_qiskit_initialize_uses_state_preparation_label_and_small_state_vector_subtitle() -> None:
    circuit = qiskit.QuantumCircuit(2)
    circuit.initialize([1, 0, 0, 0], [0, 1])

    ir = QiskitAdapter().to_ir(circuit)
    operation = flatten_operations(ir)[0]
    scene = LayoutEngine().compute(ir, DrawStyle())

    assert operation.name == "StatePreparation"
    assert operation.label == "StatePreparation"
    assert operation.metadata["display_subtitle"] == "[1, 0,\n0, 0]"
    assert operation.metadata["subtitle_font_scale"] == pytest.approx(0.46)
    assert scene.gates[0].label == "StatePreparation"
    assert scene.gates[0].subtitle == "[1, 0,\n0, 0]"
    assert scene.gates[0].subtitle_font_scale == pytest.approx(0.46)
    assert scene.gates[0].width > scene.style.gate_width
    assert scene.gates[0].width < scene.style.gate_width * 4.5


def test_qiskit_initialize_keeps_one_qubit_state_vector_subtitle_on_one_line() -> None:
    circuit = qiskit.QuantumCircuit(1)
    circuit.initialize([0.8, 0.6], [0])

    ir = QiskitAdapter().to_ir(circuit)
    operation = flatten_operations(ir)[0]
    scene = LayoutEngine().compute(ir, DrawStyle())

    assert operation.metadata["display_subtitle"] == "[0.8, 0.6]"
    assert scene.gates[0].subtitle == "[0.8, 0.6]"
    assert scene.gates[0].width < scene.style.gate_width * 3.5


def test_qiskit_initialize_omits_large_state_vector_subtitle() -> None:
    circuit = qiskit.QuantumCircuit(6)
    circuit.initialize([1, *([0] * 63)], range(6))

    ir = QiskitAdapter().to_ir(circuit)
    operation = flatten_operations(ir)[0]
    scene = LayoutEngine().compute(ir, DrawStyle())

    assert "display_subtitle" not in operation.metadata
    assert operation.metadata["suppress_params"] is True
    assert scene.gates[0].label == "StatePreparation"
    assert scene.gates[0].subtitle is None
    assert scene.gates[0].width < scene.style.gate_width * 4.5


def test_draw_qiskit_initialize_uses_smaller_font_for_state_vector_subtitle() -> None:
    circuit = qiskit.QuantumCircuit(2)
    circuit.initialize([1, 0, 0, 0], [0, 1])

    figure, axes = draw_quantum_circuit(circuit, framework="qiskit", show=False)

    label_text = next(text for text in axes.texts if text.get_text() == "StatePreparation")
    subtitle_text = next(text for text in axes.texts if text.get_text() == "[1, 0,\n0, 0]")

    assert subtitle_text.get_fontsize() < label_text.get_fontsize() * 0.7
    figure.clear()


def test_qiskit_adapter_keeps_composite_instruction_compact_by_default() -> None:
    subcircuit = qiskit.QuantumCircuit(2, name="my_sub")
    subcircuit.h(0)
    subcircuit.cx(0, 1)

    circuit = qiskit.QuantumCircuit(2)
    circuit.append(subcircuit.to_instruction(), [0, 1])

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) == 1
    assert operations[0].name == "my_sub"
    assert operations[0].target_wires == ("q0", "q1")


def test_qiskit_adapter_expands_composite_instruction_when_requested() -> None:
    subcircuit = qiskit.QuantumCircuit(2, name="my_sub")
    subcircuit.h(0)
    subcircuit.cx(0, 1)

    circuit = qiskit.QuantumCircuit(2)
    circuit.append(subcircuit.to_instruction(), [0, 1])

    ir = QiskitAdapter().to_ir(circuit, options={"composite_mode": "expand"})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["H", "X"]


def test_qiskit_adapter_expands_fundamental_rzz_instruction_when_requested() -> None:
    circuit = qiskit.QuantumCircuit(2)
    circuit.rzz(0.7, 0, 1)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit, options={"composite_mode": "expand"})
    operations = flatten_semantic_operations(semantic_ir)

    assert [operation.name for operation in operations] == ["X", "RZ", "X"]
    assert [operation.kind for operation in operations] == [
        OperationKind.CONTROLLED_GATE,
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
    ]
    assert [operation.provenance.decomposition_origin for operation in operations] == [
        "rzz",
        "rzz",
        "rzz",
    ]
    assert [operation.provenance.location for operation in operations] == [(0, 0), (0, 1), (0, 2)]


def test_qiskit_adapter_propagates_composite_provenance_when_expanding_instruction() -> None:
    subcircuit = qiskit.QuantumCircuit(2, name="my_sub")
    subcircuit.h(0)
    subcircuit.cx(0, 1)

    circuit = qiskit.QuantumCircuit(2)
    circuit.append(subcircuit.to_instruction(), [0, 1])

    semantic_ir = QiskitAdapter().to_semantic_ir(
        circuit,
        options={"composite_mode": "expand", "explicit_matrices": False},
    )
    operations = flatten_semantic_operations(semantic_ir)

    assert [operation.name for operation in operations] == ["H", "X"]
    assert [operation.provenance.decomposition_origin for operation in operations] == [
        "my_sub",
        "my_sub",
    ]
    assert [operation.provenance.composite_label for operation in operations] == [
        "my_sub",
        "my_sub",
    ]
    assert [operation.provenance.location for operation in operations] == [(0, 0), (0, 1)]


def test_qiskit_adapter_supports_additional_common_operations() -> None:
    circuit = qiskit.QuantumCircuit(4)
    circuit.id(0)
    circuit.reset(1)
    circuit.delay(12, 2, unit="ns")
    circuit.cy(0, 1)
    circuit.ch(1, 2)
    circuit.cp(0.125, 0, 3)
    circuit.cu(0.1, 0.2, 0.3, 0.4, 1, 2)
    circuit.rxx(0.5, 0, 1)
    circuit.ryy(0.6, 1, 2)
    circuit.rzz(0.7, 2, 3)
    circuit.rzx(0.8, 0, 2)
    circuit.ecr(1, 3)
    circuit.cswap(0, 1, 2)

    ir = QiskitAdapter().to_ir(circuit)
    signatures = [
        (
            operation.kind,
            operation.canonical_family,
            operation.name,
            tuple(operation.parameters),
            tuple(operation.target_wires),
            tuple(operation.control_wires),
        )
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.I, "I", (), ("q0",), ()) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RESET,
        "RESET",
        (),
        ("q1",),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.DELAY,
        "DELAY",
        (12,),
        ("q2",),
        (),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.Y,
        "Y",
        (),
        ("q1",),
        ("q0",),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.H,
        "H",
        (),
        ("q2",),
        ("q1",),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.P,
        "P",
        (0.125,),
        ("q3",),
        ("q0",),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.U,
        "U",
        (0.1, 0.2, 0.3, 0.4),
        ("q2",),
        ("q1",),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RXX,
        "RXX",
        (0.5,),
        ("q0", "q1"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RYY,
        "RYY",
        (0.6,),
        ("q1", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RZZ,
        "RZZ",
        (0.7,),
        ("q2", "q3"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RZX,
        "RZX",
        (0.8,),
        ("q0", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.ECR,
        "ECR",
        (),
        ("q1", "q3"),
        (),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.CUSTOM,
        "SWAP",
        (),
        ("q1", "q2"),
        ("q0",),
    ) in signatures


def test_qiskit_adapter_raises_for_measure_without_classical_target() -> None:
    class _MeasureOperation:
        name = "measure"
        params: tuple[object, ...] = ()

    qubit = object()
    adapter = QiskitAdapter()

    with pytest.raises(
        UnsupportedOperationError,
        match=r"instruction 'measure' has no classical target",
    ):
        adapter._convert_instruction(
            (_MeasureOperation(), (qubit,), ()),
            {qubit: "q0"},
            {},
            {},
            composite_mode="compact",
        )


def test_qiskit_adapter_raises_for_misaligned_if_else_true_block_qubits() -> None:
    outer_qubits = ("outer-q0",)
    outer_clbits = ("outer-c0",)
    operation = SimpleNamespace(
        blocks=(SimpleNamespace(qubits=("inner-q0", "inner-q1"), clbits=("inner-c0",), data=()),),
        condition=("outer-c0", 1),
    )

    with pytest.raises(
        UnsupportedOperationError, match="if_else true_block qubit mapping mismatch"
    ):
        QiskitAdapter()._convert_if_else(
            operation=operation,
            qubits=outer_qubits,
            clbits=outer_clbits,
            qubit_ids={"outer-q0": "q0"},
            classical_targets={"outer-c0": ("c0", "c[0]")},
            register_targets={},
            composite_mode="expand",
        )


def test_qiskit_adapter_raises_for_misaligned_if_else_true_block_clbits() -> None:
    outer_qubits = ("outer-q0",)
    outer_clbits = ("outer-c0",)
    operation = SimpleNamespace(
        blocks=(SimpleNamespace(qubits=("inner-q0",), clbits=("inner-c0", "inner-c1"), data=()),),
        condition=("outer-c0", 1),
    )

    with pytest.raises(
        UnsupportedOperationError, match="if_else true_block clbit mapping mismatch"
    ):
        QiskitAdapter()._convert_if_else(
            operation=operation,
            qubits=outer_qubits,
            clbits=outer_clbits,
            qubit_ids={"outer-q0": "q0"},
            classical_targets={"outer-c0": ("c0", "c[0]")},
            register_targets={},
            composite_mode="expand",
        )


def test_qiskit_adapter_raises_for_misaligned_composite_definition_qubits() -> None:
    operation = SimpleNamespace(
        definition=SimpleNamespace(
            qubits=("inner-q0", "inner-q1"),
            clbits=(),
            data=(),
        )
    )

    with pytest.raises(
        UnsupportedOperationError,
        match="composite definition qubit mapping mismatch",
    ):
        QiskitAdapter()._expand_definition(
            operation=operation,
            qubits=("outer-q0",),
            clbits=(),
            qubit_ids={"outer-q0": "q0"},
            classical_targets={},
            composite_mode="expand",
        )


def test_qiskit_adapter_raises_for_misaligned_composite_definition_clbits() -> None:
    operation = SimpleNamespace(
        definition=SimpleNamespace(
            qubits=("inner-q0",),
            clbits=("inner-c0", "inner-c1"),
            data=(),
        )
    )

    with pytest.raises(
        UnsupportedOperationError,
        match="composite definition clbit mapping mismatch",
    ):
        QiskitAdapter()._expand_definition(
            operation=operation,
            qubits=("outer-q0",),
            clbits=("outer-c0",),
            qubit_ids={"outer-q0": "q0"},
            classical_targets={"outer-c0": ("c0", "c[0]")},
            composite_mode="expand",
        )


def test_qiskit_adapter_rejects_measure_without_quantum_target() -> None:
    adapter = QiskitAdapter()
    malformed_instruction = SimpleNamespace(name="measure", params=())

    with pytest.raises(
        UnsupportedOperationError,
        match="Qiskit instruction 'measure' has no quantum target",
    ):
        adapter._convert_instruction(
            (malformed_instruction, (), ("cbit",)),
            {},
            {"cbit": ("c0", "c[0]")},
            {},
            composite_mode="compact",
        )
