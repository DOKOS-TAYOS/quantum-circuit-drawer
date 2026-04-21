from __future__ import annotations

from quantum_circuit_drawer.ir import OperationKind, WireIR, WireKind
from quantum_circuit_drawer.ir.lowering import lower_semantic_circuit
from quantum_circuit_drawer.ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
    SemanticProvenanceIR,
)
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.style import DrawStyle


def test_layout_engine_exposes_semantic_annotations_and_hover_details() -> None:
    semantic_circuit = SemanticCircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            SemanticLayerIR(
                operations=[
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="QFT",
                        target_wires=("q0",),
                        annotations=("moment[0]",),
                        hover_details=(
                            "native: CircuitOperation",
                            "decomposed from: QFT",
                        ),
                        provenance=SemanticProvenanceIR(
                            framework="pennylane",
                            native_name="QFT",
                            grouping="moment[0]",
                            decomposition_origin="QFT",
                        ),
                    )
                ]
            )
        ],
        metadata={"framework": "pennylane"},
    )

    scene = LayoutEngine().compute(lower_semantic_circuit(semantic_circuit), DrawStyle())

    assert [annotation.text for annotation in scene.gate_annotations] == ["moment[0]"]
    hover_data = next(gate.hover_data for gate in scene.gates if gate.hover_data is not None)
    assert hover_data.details == (
        "native: CircuitOperation",
        "decomposed from: QFT",
    )
