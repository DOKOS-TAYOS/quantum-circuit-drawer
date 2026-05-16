from __future__ import annotations

from quantum_circuit_drawer.ir import (
    CircuitIR,
    ClassicalConditionIR,
    LayerIR,
    OperationIR,
    OperationKind,
    WireIR,
    WireKind,
)
from quantum_circuit_drawer.ir.lowering import (
    lower_semantic_circuit,
    semantic_circuit_from_circuit_ir,
)
from quantum_circuit_drawer.ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
    SemanticProvenanceIR,
    pack_semantic_operations,
    semantic_operation_signature,
)


def test_lower_semantic_circuit_preserves_native_metadata_for_rendering() -> None:
    semantic_circuit = SemanticCircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            SemanticLayerIR(
                operations=[
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                        annotations=("moment[0]", "native: PhasedXPowGate"),
                        hover_details=(
                            "group: moment[0]",
                            "decomposed from: CircuitOperation",
                        ),
                        provenance=SemanticProvenanceIR(
                            framework="cirq",
                            native_name="PhasedXPowGate",
                            native_kind="operation",
                            grouping="moment[0]",
                            decomposition_origin="CircuitOperation",
                        ),
                    )
                ],
                metadata={"native_group": "moment[0]"},
            )
        ],
        metadata={"framework": "cirq"},
    )

    lowered = lower_semantic_circuit(semantic_circuit)
    lowered_operation = lowered.layers[0].operations[0]

    assert lowered.metadata["framework"] == "cirq"
    assert lowered.layers[0].metadata["native_group"] == "moment[0]"
    assert lowered_operation.metadata["native_annotations"] == (
        "moment[0]",
        "native: PhasedXPowGate",
    )
    assert lowered_operation.metadata["hover_details"] == (
        "group: moment[0]",
        "decomposed from: CircuitOperation",
    )
    assert lowered_operation.metadata["semantic_provenance"] == {
        "framework": "cirq",
        "native_name": "PhasedXPowGate",
        "native_kind": "operation",
        "grouping": "moment[0]",
        "decomposition_origin": "CircuitOperation",
        "composite_label": None,
        "location": (),
    }


def test_semantic_circuit_from_plain_circuit_ir_keeps_legacy_contract_intact() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            )
        ],
        metadata={"framework": "ir"},
    )

    semantic_circuit = semantic_circuit_from_circuit_ir(circuit)
    semantic_operation = semantic_circuit.layers[0].operations[0]

    assert semantic_circuit.metadata["framework"] == "ir"
    assert semantic_operation.name == "H"
    assert semantic_operation.annotations == ()
    assert semantic_operation.hover_details == ()
    assert semantic_operation.provenance.framework == "ir"
    assert semantic_operation.provenance.native_name is None


def test_semantic_circuit_from_circuit_ir_preserves_lowered_semantic_provenance() -> None:
    semantic_circuit = SemanticCircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            SemanticLayerIR(
                operations=[
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="QFT",
                        target_wires=("q0",),
                        hover_details=("decomposed from: QFT",),
                        provenance=SemanticProvenanceIR(
                            framework="pennylane",
                            native_name="QFT",
                            native_kind="composite",
                            decomposition_origin="QFT",
                            composite_label="QFT",
                            location=(3, 1),
                        ),
                    )
                ]
            )
        ],
        metadata={"framework": "pennylane"},
    )

    lowered = lower_semantic_circuit(semantic_circuit)
    round_tripped = semantic_circuit_from_circuit_ir(lowered)
    semantic_operation = round_tripped.layers[0].operations[0]

    assert semantic_operation.provenance.framework == "pennylane"
    assert semantic_operation.provenance.native_name == "QFT"
    assert semantic_operation.provenance.native_kind == "composite"
    assert semantic_operation.provenance.decomposition_origin == "QFT"
    assert semantic_operation.provenance.composite_label == "QFT"
    assert semantic_operation.provenance.location == (3, 1)


def test_lower_semantic_circuit_preserves_control_values_for_rendering() -> None:
    semantic_circuit = SemanticCircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            SemanticLayerIR(
                operations=[
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                        control_values=((0,),),
                    )
                ]
            )
        ],
    )

    lowered = lower_semantic_circuit(semantic_circuit)
    lowered_operation = lowered.layers[0].operations[0]

    assert lowered_operation.control_values == ((0,),)


def test_semantic_operation_signature_distinguishes_control_states() -> None:
    wire_indices = {"q0": 0, "q1": 1}
    open_control = SemanticOperationIR(
        kind=OperationKind.CONTROLLED_GATE,
        name="X",
        target_wires=("q1",),
        control_wires=("q0",),
        control_values=((0,),),
    )
    closed_control = SemanticOperationIR(
        kind=OperationKind.CONTROLLED_GATE,
        name="X",
        target_wires=("q1",),
        control_wires=("q0",),
        control_values=((1,),),
    )

    assert semantic_operation_signature(open_control, wire_indices) != semantic_operation_signature(
        closed_control, wire_indices
    )


def test_pack_semantic_operations_compacts_control_flow_body_with_classical_dependency() -> None:
    condition = ClassicalConditionIR(wire_ids=("c0",), expression="c[0]=1")
    group_metadata = {
        "id": "op:while",
        "label": "WHILE",
        "wire_dependencies": ("c0",),
        "conditions": (condition,),
    }
    operations = [
        SemanticOperationIR(
            kind=OperationKind.MEASUREMENT,
            name="M_BEFORE",
            target_wires=("q3",),
            classical_target="c0",
        ),
        *(
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name=f"H{index}",
                target_wires=(wire_id,),
                metadata={
                    "control_flow_group": group_metadata,
                    "occupied_wire_dependencies": ("c0",),
                },
            )
            for index, wire_id in enumerate(("q0", "q1", "q2"))
        ),
        SemanticOperationIR(
            kind=OperationKind.MEASUREMENT,
            name="M_AFTER",
            target_wires=("q4",),
            classical_target="c0",
        ),
    ]

    packed_layers = pack_semantic_operations(operations)

    assert [[operation.name for operation in layer.operations] for layer in packed_layers] == [
        ["M_BEFORE"],
        ["H0", "H1", "H2"],
        ["M_AFTER"],
    ]


def test_pack_semantic_operations_reserves_control_flow_span_from_external_gates() -> None:
    group_metadata = {
        "id": "op:while",
        "label": "WHILE",
        "wire_dependencies": ("c0",),
    }
    operations = [
        SemanticOperationIR(kind=OperationKind.GATE, name="X_OUTSIDE", target_wires=("q1",)),
        SemanticOperationIR(
            kind=OperationKind.GATE,
            name="H0",
            target_wires=("q0",),
            metadata={
                "control_flow_group": group_metadata,
                "occupied_wire_dependencies": ("c0",),
            },
        ),
        SemanticOperationIR(
            kind=OperationKind.GATE,
            name="H2",
            target_wires=("q2",),
            metadata={
                "control_flow_group": group_metadata,
                "occupied_wire_dependencies": ("c0",),
            },
        ),
    ]

    packed_layers = pack_semantic_operations(
        operations,
        wire_order={"q0": 0, "q1": 1, "q2": 2, "c0": 3},
    )

    assert [[operation.name for operation in layer.operations] for layer in packed_layers] == [
        ["X_OUTSIDE"],
        ["H0", "H2"],
    ]
