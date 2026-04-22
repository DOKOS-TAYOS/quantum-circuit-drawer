"""MyQLM adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from ..diagnostics import RenderDiagnostic
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.semantic import SemanticCircuitIR, SemanticOperationIR, pack_semantic_operations
from ..ir.wires import WireIR, WireKind
from ._helpers import (
    build_classical_register,
    extract_dependency_types,
    resolve_composite_mode,
    sequential_bit_labels,
)
from ._myqlm_conversion import MyQLMConversionContext, convert_operation
from ._myqlm_resolver import (
    _MyQLMCircuitLike,
    declared_classical_count,
    declared_quantum_count,
    unsupported_policy_from_options,
    used_classical_count,
    used_qubit_count,
)
from .base import BaseAdapter


class MyQLMAdapter(BaseAdapter):
    """Convert ``qat.core.Circuit`` objects into semantic IR and ``CircuitIR``."""

    framework_name = "myqlm"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        circuit_types = extract_dependency_types("qat", ("core.Circuit",))
        return bool(circuit_types) and isinstance(circuit, circuit_types)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        semantic_ir = self.to_semantic_ir(circuit, options=options)
        assert semantic_ir is not None
        return lower_semantic_circuit(semantic_ir)

    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR:
        if not self.can_handle(circuit):
            raise TypeError("MyQLMAdapter received a non-MyQLM circuit")

        typed_circuit = cast(_MyQLMCircuitLike, circuit)
        composite_mode = resolve_composite_mode(options)
        quantum_count = max(
            declared_quantum_count(typed_circuit),
            used_qubit_count(circuit),
        )
        classical_count = max(
            declared_classical_count(typed_circuit),
            used_classical_count(circuit),
        )
        qubit_wire_ids = {index: f"q{index}" for index in range(quantum_count)}
        quantum_wires = [
            WireIR(
                id=qubit_wire_ids[index],
                index=index,
                kind=WireKind.QUANTUM,
                label=f"q{index}",
            )
            for index in range(quantum_count)
        ]
        classical_wires, classical_bit_targets = build_classical_register(
            sequential_bit_labels(classical_count)
        )
        classical_targets = {index: target for index, target in enumerate(classical_bit_targets)}
        diagnostics: list[RenderDiagnostic] = []
        conversion_context = MyQLMConversionContext(
            framework_name=self.framework_name,
            gate_definitions=typed_circuit.gateDic,
            qubit_wire_ids=qubit_wire_ids,
            classical_targets=classical_targets,
            composite_mode=composite_mode,
            unsupported_policy=unsupported_policy_from_options(options),
            diagnostics=diagnostics,
        )
        semantic_operations: list[SemanticOperationIR] = []

        for operation_index, operation in enumerate(typed_circuit.ops):
            semantic_operations.extend(
                convert_operation(
                    conversion_context,
                    operation,
                    location=(operation_index,),
                    decomposition_origin=None,
                    composite_label=None,
                )
            )

        resolved_diagnostics = tuple(diagnostics)
        return SemanticCircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=pack_semantic_operations(semantic_operations),
            name=typed_circuit.name,
            metadata={
                "framework": self.framework_name,
                "diagnostics": resolved_diagnostics,
            },
            diagnostics=resolved_diagnostics,
        )
