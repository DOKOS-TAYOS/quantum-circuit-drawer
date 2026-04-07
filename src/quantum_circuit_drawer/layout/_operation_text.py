"""Shared operation text preparation for layout engines."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..ir.circuit import LayerIR
from ..style import DrawStyle
from ..utils.formatting import format_gate_name
from .spacing import operation_label_parts


@dataclass(frozen=True, slots=True)
class OperationTextMetrics:
    """Normalized text information for an operation."""

    label: str
    display_label: str
    subtitle: str | None


def build_operation_text_metrics(
    layers: Sequence[LayerIR],
    style: DrawStyle,
) -> dict[int, OperationTextMetrics]:
    """Build reusable text metrics keyed by operation identity."""

    metrics: dict[int, OperationTextMetrics] = {}
    for layer in layers:
        for operation in layer.operations:
            label, subtitle = operation_label_parts(operation, style)
            metrics[id(operation)] = OperationTextMetrics(
                label=label,
                display_label=format_gate_name(label),
                subtitle=subtitle,
            )
    return metrics
