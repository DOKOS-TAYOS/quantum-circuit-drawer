from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest

import quantum_circuit_drawer
import quantum_circuit_drawer.api as public_api
from quantum_circuit_drawer import (
    CircuitAnalysisResult,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    analyze_quantum_circuit,
)
from quantum_circuit_drawer.drawing.runtime import RuntimeContext
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind


def _analysis_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=(
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ),
        classical_wires=(WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0"),),
        layers=(
            LayerIR(
                operations=(
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",)),
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    ),
                )
            ),
            LayerIR(
                operations=(
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q1",),
                        classical_target="c0",
                    ),
                )
            ),
            LayerIR(
                operations=(
                    OperationIR(kind=OperationKind.BARRIER, name="barrier", target_wires=("q0",)),
                )
            ),
        ),
    )


def test_analyze_quantum_circuit_returns_public_summary_without_rendering(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    output_path = sandbox_tmp_path / "must_not_exist.png"
    show_calls: list[object] = []
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: show_calls.append((args, kwargs)))
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )

    result = analyze_quantum_circuit(
        _analysis_ir(),
        config=DrawConfig(
            side=DrawSideConfig(
                render=CircuitRenderOptions(
                    framework="ir",
                    mode=DrawMode.FULL,
                    view="2d",
                )
            ),
            output=OutputOptions(show=True, output_path=output_path),
        ),
    )

    assert isinstance(result, CircuitAnalysisResult)
    assert result.detected_framework == "ir"
    assert result.mode is DrawMode.FULL
    assert result.view == "2d"
    assert result.page_count == 1
    assert result.quantum_wire_count == 2
    assert result.classical_wire_count == 1
    assert result.total_wire_count == 3
    assert result.layer_count == 3
    assert result.operation_count == 4
    assert result.gate_count == 1
    assert result.controlled_gate_count == 1
    assert result.multi_qubit_operation_count == 1
    assert result.measurement_count == 1
    assert result.swap_count == 0
    assert result.barrier_count == 1
    assert result.warnings == ()
    assert show_calls == []
    assert not output_path.exists()


def test_analyze_quantum_circuit_to_dict_is_json_friendly() -> None:
    result = analyze_quantum_circuit(
        _analysis_ir(),
        config=DrawConfig(output=OutputOptions(show=False)),
    )

    payload = result.to_dict()

    assert payload["detected_framework"] == "ir"
    assert payload["mode"] == result.mode.value
    assert payload["view"] == "2d"
    assert payload["operation_count"] == 4
    assert isinstance(payload["diagnostics"], tuple)


def test_public_package_exports_analysis_api() -> None:
    assert quantum_circuit_drawer.analyze_quantum_circuit is analyze_quantum_circuit
    assert quantum_circuit_drawer.CircuitAnalysisResult is CircuitAnalysisResult
    assert public_api.analyze_quantum_circuit is not None
    assert public_api.CircuitAnalysisResult is CircuitAnalysisResult
