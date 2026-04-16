"""Internal scaffold helpers for 2D scene construction."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR
from ..style import DrawStyle
from ._layering import normalize_draw_layers
from ._operation_text import build_operation_text_metrics
from .scene import ScenePage
from .spacing import estimate_text_width, operation_width_from_parts


@dataclass(frozen=True, slots=True)
class _OperationMetrics:
    width: float
    label: str
    display_label: str
    subtitle: str | None


@dataclass(frozen=True, slots=True)
class _LayoutScaffold:
    draw_style: DrawStyle
    normalized_layers: tuple[LayerIR, ...]
    operation_metrics: dict[int, _OperationMetrics]
    wire_positions: dict[str, float]
    column_widths: tuple[float, ...]
    x_centers: tuple[float, ...]
    pages: tuple[ScenePage, ...]
    page_height: float
    scene_width: float
    scene_height: float


class _OperationWidthResolver(Protocol):
    def __call__(
        self,
        *,
        operation: OperationIR | MeasurementIR,
        style: DrawStyle,
        label: str,
        subtitle: str | None,
    ) -> float: ...


def build_layout_scaffold(
    circuit: CircuitIR,
    style: DrawStyle,
    *,
    operation_width_resolver: _OperationWidthResolver = operation_width_from_parts,
) -> _LayoutScaffold:
    """Build the shared 2D layout scaffold used by later scene assembly."""

    draw_style = _resolve_scene_style(circuit, style)
    normalized_layers = normalize_draw_layers(circuit)
    operation_metrics, column_widths = _build_operation_metrics_and_column_widths(
        normalized_layers,
        draw_style,
        operation_width_resolver=operation_width_resolver,
    )
    wire_positions = _build_wire_positions(circuit, draw_style)
    x_centers = tuple(_build_column_centers(column_widths, draw_style))
    page_height = max(wire_positions.values()) + draw_style.margin_bottom
    pages = _build_pages(column_widths, x_centers, page_height, draw_style)
    scene_width = max(
        (draw_style.margin_left + page.content_width + draw_style.margin_right for page in pages),
        default=_scene_width(column_widths, draw_style),
    )
    scene_height = page_height + ((len(pages) - 1) * (page_height + draw_style.page_vertical_gap))
    return _LayoutScaffold(
        draw_style=draw_style,
        normalized_layers=normalized_layers,
        operation_metrics=operation_metrics,
        wire_positions=wire_positions,
        column_widths=column_widths,
        x_centers=x_centers,
        pages=pages,
        page_height=page_height,
        scene_width=scene_width,
        scene_height=scene_height,
    )


def bundle_size(wire: WireIR) -> int:
    """Return the bundled classical wire size stored in metadata."""

    stored_size = wire.metadata.get("bundle_size", 1)
    return int(stored_size) if isinstance(stored_size, int | float | str) else 1


def _resolve_scene_style(circuit: CircuitIR, style: DrawStyle) -> DrawStyle:
    left_margin = style.margin_left
    if style.show_wire_labels:
        widest_label = max(
            (
                estimate_text_width(wire.label or wire.id, style.font_size * 0.82)
                for wire in circuit.all_wires
            ),
            default=0.0,
        )
        left_margin = max(left_margin, widest_label + style.label_margin + 0.12)
    return replace(style, margin_left=left_margin, margin_right=max(0.22, style.margin_right))


def _build_operation_metrics_and_column_widths(
    layers: Sequence[LayerIR],
    style: DrawStyle,
    *,
    operation_width_resolver: _OperationWidthResolver,
) -> tuple[dict[int, _OperationMetrics], tuple[float, ...]]:
    text_metrics = build_operation_text_metrics(layers, style)
    metrics: dict[int, _OperationMetrics] = {}
    cached_widths: dict[tuple[OperationKind, str, str | None], float] = {}
    column_widths: list[float] = []
    for layer in layers:
        if not layer.operations:
            column_widths.append(style.gate_width)
            continue
        column_width = style.gate_width
        for operation in layer.operations:
            operation_text = text_metrics[id(operation)]
            width_key = (
                operation.kind,
                operation_text.label,
                operation_text.subtitle,
            )
            width = cached_widths.get(width_key)
            if width is None:
                width = operation_width_resolver(
                    operation=operation,
                    style=style,
                    label=operation_text.label,
                    subtitle=operation_text.subtitle,
                )
                cached_widths[width_key] = width
            metrics[id(operation)] = _OperationMetrics(
                width=width,
                label=operation_text.label,
                display_label=operation_text.display_label,
                subtitle=operation_text.subtitle,
            )
            if width > column_width:
                column_width = width
        column_widths.append(column_width)
    return metrics, tuple(column_widths)


def _build_wire_positions(circuit: CircuitIR, style: DrawStyle) -> dict[str, float]:
    positions: dict[str, float] = {}
    current_y = style.margin_top
    for wire in circuit.quantum_wires:
        positions[wire.id] = current_y
        current_y += style.wire_spacing
    if circuit.classical_wires:
        current_y += style.classical_wire_gap
        for wire in circuit.classical_wires:
            positions[wire.id] = current_y
            current_y += style.wire_spacing
    return positions


def _build_column_centers(widths: Sequence[float], style: DrawStyle) -> list[float]:
    centers: list[float] = []
    current_x = style.margin_left
    for width in widths:
        centers.append(current_x + width / 2)
        current_x += width + style.layer_spacing
    return centers


def _scene_width(widths: Sequence[float], style: DrawStyle) -> float:
    if not widths:
        return style.margin_left + style.margin_right + style.gate_width
    total_columns = sum(widths)
    total_spacing = style.layer_spacing * max(0, len(widths) - 1)
    return style.margin_left + total_columns + total_spacing + style.margin_right


def _build_pages(
    widths: Sequence[float],
    x_centers: Sequence[float],
    page_height: float,
    style: DrawStyle,
) -> tuple[ScenePage, ...]:
    if not widths:
        return (
            ScenePage(
                index=0,
                start_column=0,
                end_column=0,
                content_x_start=style.margin_left,
                content_x_end=style.margin_left + style.gate_width,
                content_width=style.gate_width,
                y_offset=0.0,
            ),
        )

    pages: list[ScenePage] = []
    start_column = 0
    current_width = 0.0
    for column, width in enumerate(widths):
        proposed_width = (
            width if current_width == 0.0 else current_width + style.layer_spacing + width
        )
        if current_width > 0.0 and proposed_width > style.max_page_width:
            pages.append(
                _make_page(
                    index=len(pages),
                    start_column=start_column,
                    end_column=column - 1,
                    widths=widths,
                    x_centers=x_centers,
                    page_height=page_height,
                    style=style,
                )
            )
            start_column = column
            current_width = width
        else:
            current_width = proposed_width

    pages.append(
        _make_page(
            index=len(pages),
            start_column=start_column,
            end_column=len(widths) - 1,
            widths=widths,
            x_centers=x_centers,
            page_height=page_height,
            style=style,
        )
    )
    return tuple(pages)


def _make_page(
    *,
    index: int,
    start_column: int,
    end_column: int,
    widths: Sequence[float],
    x_centers: Sequence[float],
    page_height: float,
    style: DrawStyle,
) -> ScenePage:
    content_x_start = x_centers[start_column] - (widths[start_column] / 2)
    content_x_end = x_centers[end_column] + (widths[end_column] / 2)
    return ScenePage(
        index=index,
        start_column=start_column,
        end_column=end_column,
        content_x_start=content_x_start,
        content_x_end=content_x_end,
        content_width=content_x_end - content_x_start,
        y_offset=index * (page_height + style.page_vertical_gap),
    )
