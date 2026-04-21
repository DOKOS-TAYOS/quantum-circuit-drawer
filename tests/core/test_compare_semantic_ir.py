from __future__ import annotations

import importlib

import matplotlib.pyplot as plt
import pytest

from quantum_circuit_drawer import DrawConfig, compare_circuits
from quantum_circuit_drawer.adapters import register_adapter
from quantum_circuit_drawer.adapters.base import BaseAdapter
from quantum_circuit_drawer.adapters.registry import AdapterRegistry
from quantum_circuit_drawer.circuit_compare import CircuitCompareConfig
from quantum_circuit_drawer.ir import (
    CircuitIR,
    LayerIR,
    OperationIR,
    OperationKind,
    WireIR,
    WireKind,
)
from quantum_circuit_drawer.ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
    SemanticProvenanceIR,
)
from tests.support import assert_figure_has_visible_content


class _SemanticCompareCircuit:
    pass


class _SemanticCompareAdapter(BaseAdapter):
    framework_name = "semantic_compare_demo"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return isinstance(circuit, _SemanticCompareCircuit)

    def to_ir(
        self,
        circuit: object,
        options: dict[str, object] | None = None,
    ) -> CircuitIR:
        del circuit, options
        raise AssertionError("legacy to_ir() should not be used when semantic IR is available")

    def to_semantic_ir(
        self,
        circuit: object,
        options: dict[str, object] | None = None,
    ) -> SemanticCircuitIR:
        del circuit, options
        return SemanticCircuitIR(
            quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
            layers=[
                SemanticLayerIR(
                    operations=[
                        SemanticOperationIR(
                            kind=OperationKind.GATE,
                            name="H",
                            target_wires=("q0",),
                            annotations=("native: demo_semantic_gate",),
                            provenance=SemanticProvenanceIR(
                                framework="semantic_compare_demo",
                                native_name="demo_semantic_gate",
                                grouping="step[0]",
                            ),
                        )
                    ]
                )
            ],
            metadata={"framework": self.framework_name},
        )


def test_compare_circuits_uses_semantic_signatures_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    monkeypatch.setattr(registry_module, "registry", registry)
    register_adapter(_SemanticCompareAdapter)

    plain_ir = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            )
        ],
        metadata={"framework": "ir"},
    )

    result = compare_circuits(
        _SemanticCompareCircuit(),
        plain_ir,
        left_config=DrawConfig(framework="semantic_compare_demo", show=False),
        right_config=DrawConfig(show=False),
        config=CircuitCompareConfig(show=False, highlight_differences=False),
    )

    assert result.metrics.differing_layer_count == 1
    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)
