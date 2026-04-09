"""Shared operation text preparation for layout engines."""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from dataclasses import dataclass

from ..ir.circuit import LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR
from ..style import DrawStyle
from ..utils.formatting import format_gate_name
from .spacing import operation_label_parts


@dataclass(frozen=True, slots=True)
class OperationTextMetrics:
    """Normalized text information for an operation."""

    label: str
    display_label: str
    subtitle: str | None


def _cache_token(value: object) -> object:
    return value if isinstance(value, Hashable) else repr(value)


def _operation_text_cache_key(
    operation: OperationIR | MeasurementIR,
    style: DrawStyle,
) -> tuple[object, ...]:
    return (
        operation.label or operation.name,
        tuple(_cache_token(value) for value in operation.parameters) if style.show_params else (),
        style.show_params,
    )


def build_operation_text_metrics(
    layers: Sequence[LayerIR],
    style: DrawStyle,
) -> dict[int, OperationTextMetrics]:
    """Build reusable text metrics keyed by operation identity."""

    metrics: dict[int, OperationTextMetrics] = {}
    cached_metrics: dict[tuple[object, ...], OperationTextMetrics] = {}
    for layer in layers:
        for operation in layer.operations:
            cache_key = _operation_text_cache_key(operation, style)
            operation_metrics = cached_metrics.get(cache_key)
            if operation_metrics is None:
                label, subtitle = operation_label_parts(operation, style)
                operation_metrics = OperationTextMetrics(
                    label=label,
                    display_label=format_gate_name(label),
                    subtitle=subtitle,
                )
                cached_metrics[cache_key] = operation_metrics
            metrics[id(operation)] = operation_metrics
    return metrics
