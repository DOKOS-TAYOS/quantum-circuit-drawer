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


def test_qiskit_adapter_keeps_if_else_as_compact_composite() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)) as else_:
        circuit.x(0)
    with else_:
        circuit.z(0)

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) == 1
    assert operations[0].name == "IF/ELSE"


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


def test_qiskit_adapter_keeps_if_else_as_compact_semantic_control_flow() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)) as else_:
        circuit.x(0)
    with else_:
        circuit.z(0)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operation = flatten_semantic_operations(semantic_ir)[0]
    lowered_operation = flatten_operations(lower_semantic_circuit(semantic_ir))[0]

    assert operation.name == "IF/ELSE"
    assert operation.kind is OperationKind.GATE
    assert operation.classical_conditions[0].expression == "if c[0]=1"
    assert operation.hover_details == (
        "control flow: if_else",
        "condition: if c[0]=1",
        "branches: true, false",
        "block ops: true=1, false=1",
    )
    assert operation.provenance.native_name == "if_else"
    assert lowered_operation.metadata["semantic_provenance"]["native_kind"] == "control_flow"
    assert lowered_operation.metadata["hover_details"] == operation.hover_details


def test_qiskit_adapter_keeps_if_else_with_modern_condition_as_compact_semantic_control_flow() -> (
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
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.name == "IF/ELSE"
    assert operation.classical_conditions[0].expression == "if (c[0]=1) || (c[1]=0)"
    assert operation.hover_details == (
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


def test_qiskit_adapter_keeps_switch_case_as_compact_semantic_control_flow() -> None:
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
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.name == "SWITCH"
    assert operation.kind is OperationKind.GATE
    assert operation.classical_conditions[0].expression == "switch on c[0]"
    assert operation.hover_details == (
        "control flow: switch_case",
        "target: c[0]",
        "cases: 0, 1, default",
        "case count: 3",
    )


def test_qiskit_adapter_keeps_for_loop_as_compact_semantic_control_flow() -> None:
    circuit = qiskit.QuantumCircuit(1)
    body = qiskit.QuantumCircuit(1)
    body.x(0)
    circuit.for_loop(range(3), None, body, circuit.qubits, ())

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.name == "FOR"
    assert operation.kind is OperationKind.GATE
    assert operation.classical_conditions == ()
    assert operation.hover_details == (
        "control flow: for_loop",
        "iteration: range(0, 3)",
        "body ops: 1",
    )


def test_qiskit_adapter_keeps_while_loop_as_compact_semantic_control_flow() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)
    body = qiskit.QuantumCircuit(1, 1)
    body.x(0)
    circuit.while_loop((classical[0], 1), body, quantum, classical)

    semantic_ir = QiskitAdapter().to_semantic_ir(circuit)
    operation = flatten_semantic_operations(semantic_ir)[0]

    assert operation.name == "WHILE"
    assert operation.classical_conditions[0].expression == "if c[0]=1"
    assert operation.hover_details == (
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

    assert operation.name == "WHILE"
    assert operation.classical_conditions[0].wire_ids == ("c0",)
    assert operation.classical_conditions[0].expression == "if !((c[0]=1) && (c[1]=0))"
    assert operation.hover_details == (
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
        gate.hover_data.details
        for gate in pipeline.paged_scene.gates
        if gate.hover_data is not None and gate.hover_data.name == "if/else"
    )

    assert hover_details == (
        "control flow: if_else",
        "condition: if c[0]=1",
        "branches: true, false",
        "block ops: true=1, false=1",
    )


def test_draw_quantum_circuit_renders_qiskit_compact_control_flow_boxes() -> None:
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
        expected_texts={"if/else", "switch", "for", "while"},
    )
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
