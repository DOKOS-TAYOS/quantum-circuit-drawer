"""Operation metrics helpers for the 3D layout engine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..ir.circuit import LayerIR
from ..style import DrawStyle
from ._operation_text import build_operation_text_metrics


@dataclass(frozen=True, slots=True)
class _OperationMetrics3D:
    label: str
    display_label: str
    subtitle: str | None


def build_operation_metrics_3d(
    layers: Sequence[LayerIR],
    style: DrawStyle,
) -> dict[int, _OperationMetrics3D]:
    """Build the text metrics cache used by 3D gate layout."""

    text_metrics = build_operation_text_metrics(layers, style)
    metrics: dict[int, _OperationMetrics3D] = {}
    for layer in layers:
        for operation in layer.operations:
            operation_text = text_metrics[id(operation)]
            metrics[id(operation)] = _OperationMetrics3D(
                label=operation_text.label,
                display_label=operation_text.display_label,
                subtitle=operation_text.subtitle,
            )
    return metrics
