"""Spacing heuristics used by the layout engine."""

from __future__ import annotations

from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..style import DrawStyle
from ..utils.formatting import format_gate_name, format_parameters

_COMPACT_RESULT_DISPLAY_LABELS = frozenset({"Prob", "ExpVal", "Counts"})
_COMPACT_RESULT_TERMINAL_KINDS = frozenset({"probs", "expval", "counts"})
_COMPACT_RESULT_WIDTH_FACTOR = 0.78


def estimate_text_width(text: str, font_size: float) -> float:
    """Estimate text width in layout units."""

    if not text:
        return 0.0
    return max(0.0, len(text) * font_size * 0.055)


def operation_label_parts(
    operation: OperationIR | MeasurementIR, style: DrawStyle
) -> tuple[str, str | None]:
    label = operation.label or operation.name
    subtitle_value = operation.metadata.get("display_subtitle")
    subtitle = str(subtitle_value) if isinstance(subtitle_value, str) else None
    if subtitle is None and style.show_params and operation.parameters:
        subtitle = format_parameters(operation.parameters)
    return label, subtitle


def uses_compact_parametric_width(
    operation: OperationIR | MeasurementIR,
    label: str,
    subtitle: str | None,
) -> bool:
    """Return whether a parametric gate should keep the standard compact width."""

    if subtitle is None:
        return False
    if operation.kind not in {OperationKind.GATE, OperationKind.CONTROLLED_GATE}:
        return False
    return len(label) <= 4 and len(subtitle) <= 8


def uses_compact_label_width(
    operation: OperationIR | MeasurementIR,
    label: str,
    subtitle: str | None,
) -> bool:
    """Return whether a short non-parametric gate should keep a square footprint."""

    if operation.metadata.get("compact_width") is True:
        return True
    if subtitle is not None:
        return False
    if operation.kind not in {OperationKind.GATE, OperationKind.CONTROLLED_GATE}:
        return False
    return len(label) <= 4


def uses_compact_result_width(
    operation: OperationIR | MeasurementIR,
    label: str,
    subtitle: str | None,
) -> bool:
    """Return whether a terminal result box should use a narrow footprint."""

    if subtitle is not None:
        return False
    if operation.kind is not OperationKind.GATE:
        return False
    if operation.metadata.get("compact_result_width") is True:
        return True
    terminal_kind = operation.metadata.get("pennylane_terminal_kind")
    if isinstance(terminal_kind, str) and terminal_kind in _COMPACT_RESULT_TERMINAL_KINDS:
        return True
    return format_gate_name(label) in _COMPACT_RESULT_DISPLAY_LABELS


def operation_width_from_parts(
    *,
    operation: OperationIR | MeasurementIR,
    style: DrawStyle,
    label: str,
    subtitle: str | None,
) -> float:
    """Estimate minimum width from precomputed label parts."""

    if operation.kind is OperationKind.BARRIER:
        return max(0.35, style.gate_width * 0.35)
    if operation.kind is OperationKind.SWAP:
        return style.gate_width

    if uses_compact_result_width(operation, label, subtitle):
        return max(0.45, style.gate_width * _COMPACT_RESULT_WIDTH_FACTOR)
    if uses_compact_parametric_width(operation, label, subtitle):
        return style.gate_width
    if uses_compact_label_width(operation, label, subtitle):
        return style.gate_width
    width = max(style.gate_width, estimate_text_width(label, style.font_size) + 0.25)
    if subtitle:
        width = max(width, estimate_text_width(subtitle, style.font_size * 0.8) + 0.25)
    return width
