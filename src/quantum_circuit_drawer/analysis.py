"""Public non-rendering circuit analysis API."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from ._logging import (
    duration_ms,
    emit_render_diagnostics,
    log_event,
    logged_api_call,
    push_log_context,
)
from .config import DrawConfig, DrawMode, OutputOptions
from .diagnostics import DiagnosticSeverity, RenderDiagnostic
from .ir.circuit import CircuitIR
from .ir.operations import OperationIR, OperationKind

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CircuitAnalysisResult:
    """Summary returned by ``analyze_quantum_circuit`` without rendering figures."""

    detected_framework: str | None
    mode: DrawMode
    view: str
    page_count: int
    quantum_wire_count: int
    classical_wire_count: int
    total_wire_count: int
    layer_count: int
    operation_count: int
    gate_count: int
    controlled_gate_count: int
    multi_qubit_operation_count: int
    measurement_count: int
    swap_count: int
    barrier_count: int
    diagnostics: tuple[RenderDiagnostic, ...] = ()

    @property
    def warnings(self) -> tuple[RenderDiagnostic, ...]:
        """Return only warning-level diagnostics for quick inspection."""

        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity is DiagnosticSeverity.WARNING
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly summary without Matplotlib objects."""

        return {
            "detected_framework": self.detected_framework,
            "mode": self.mode.value,
            "view": self.view,
            "page_count": self.page_count,
            "quantum_wire_count": self.quantum_wire_count,
            "classical_wire_count": self.classical_wire_count,
            "total_wire_count": self.total_wire_count,
            "layer_count": self.layer_count,
            "operation_count": self.operation_count,
            "gate_count": self.gate_count,
            "controlled_gate_count": self.controlled_gate_count,
            "multi_qubit_operation_count": self.multi_qubit_operation_count,
            "measurement_count": self.measurement_count,
            "swap_count": self.swap_count,
            "barrier_count": self.barrier_count,
            "diagnostics": tuple(
                _diagnostic_to_dict(diagnostic) for diagnostic in self.diagnostics
            ),
        }


def analyze_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
) -> CircuitAnalysisResult:
    """Analyze a supported circuit without rendering or saving figures."""

    from .drawing.preparation import prepare_draw_call

    with logged_api_call(logger, api="analyze_quantum_circuit") as started_at:
        prepared = prepare_draw_call(
            circuit,
            config=_without_rendered_output(config),
            ax=None,
        )
        pipeline = prepared.pipeline
        ir = pipeline.ir
        operation_counts = _operation_counts(ir)
        with push_log_context(
            view=prepared.resolved_config.config.view,
            mode=prepared.resolved_config.mode.value,
            framework=pipeline.detected_framework,
            backend=prepared.resolved_config.config.backend,
        ):
            result = CircuitAnalysisResult(
                detected_framework=pipeline.detected_framework,
                mode=prepared.resolved_config.mode,
                view=prepared.resolved_config.config.view,
                page_count=_analysis_page_count(pipeline.paged_scene),
                quantum_wire_count=ir.quantum_wire_count,
                classical_wire_count=ir.classical_wire_count,
                total_wire_count=ir.total_wire_count,
                layer_count=len(ir.layers),
                operation_count=operation_counts.operation_count,
                gate_count=operation_counts.gate_count,
                controlled_gate_count=operation_counts.controlled_gate_count,
                multi_qubit_operation_count=operation_counts.multi_qubit_operation_count,
                measurement_count=operation_counts.measurement_count,
                swap_count=operation_counts.swap_count,
                barrier_count=operation_counts.barrier_count,
                diagnostics=prepared.diagnostics,
            )
            emit_render_diagnostics(logger, result.diagnostics)
            log_event(
                logger,
                logging.INFO,
                "api.completed",
                "Completed analyze_quantum_circuit.",
                duration_ms=duration_ms(started_at),
                page_count=result.page_count,
                detected_framework=result.detected_framework,
                operation_count=result.operation_count,
                layer_count=result.layer_count,
                diagnostic_count=len(result.diagnostics),
            )
            return result


@dataclass(frozen=True, slots=True)
class _OperationCounts:
    operation_count: int
    gate_count: int
    controlled_gate_count: int
    multi_qubit_operation_count: int
    measurement_count: int
    swap_count: int
    barrier_count: int


def _without_rendered_output(config: DrawConfig | None) -> DrawConfig:
    if config is None:
        return DrawConfig(output=OutputOptions(show=False))
    return replace(
        config,
        output=replace(
            config.output,
            show=False,
            output_path=None,
        ),
    )


def _analysis_page_count(scene: object) -> int:
    pages = getattr(scene, "pages", None)
    if isinstance(pages, tuple | list):
        return max(1, len(pages))
    return 1


def _operation_counts(ir: CircuitIR) -> _OperationCounts:
    operation_count = 0
    gate_count = 0
    controlled_gate_count = 0
    multi_qubit_operation_count = 0
    measurement_count = 0
    swap_count = 0
    barrier_count = 0
    for layer in ir.layers:
        for operation in layer.operations:
            operation_count += 1
            if operation.kind is OperationKind.GATE:
                gate_count += 1
            elif operation.kind is OperationKind.CONTROLLED_GATE:
                controlled_gate_count += 1
            elif operation.kind is OperationKind.MEASUREMENT:
                measurement_count += 1
            elif operation.kind is OperationKind.SWAP:
                swap_count += 1
            elif operation.kind is OperationKind.BARRIER:
                barrier_count += 1
            if _is_multi_qubit_operation(operation):
                multi_qubit_operation_count += 1
    return _OperationCounts(
        operation_count=operation_count,
        gate_count=gate_count,
        controlled_gate_count=controlled_gate_count,
        multi_qubit_operation_count=multi_qubit_operation_count,
        measurement_count=measurement_count,
        swap_count=swap_count,
        barrier_count=barrier_count,
    )


def _is_multi_qubit_operation(operation: OperationIR) -> bool:
    quantum_wire_ids = tuple(dict.fromkeys((*operation.control_wires, *operation.target_wires)))
    return len(quantum_wire_ids) > 1


def _diagnostic_to_dict(diagnostic: RenderDiagnostic) -> dict[str, str]:
    return {
        "code": diagnostic.code,
        "message": diagnostic.message,
        "severity": diagnostic.severity.value,
    }


__all__ = ["CircuitAnalysisResult", "analyze_quantum_circuit"]
