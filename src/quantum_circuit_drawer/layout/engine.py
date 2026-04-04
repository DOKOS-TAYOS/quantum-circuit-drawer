"""Layout engine that converts IR into a neutral drawing scene."""

from __future__ import annotations

from collections.abc import Sequence

from ..exceptions import LayoutError
from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR
from ..style import DrawStyle, normalize_style
from ..utils.formatting import format_gate_name
from .routing import vertical_span
from .scene import (
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneMeasurement,
    ScenePage,
    SceneSwap,
    SceneText,
    SceneWire,
)
from .spacing import operation_label_parts, operation_width


class LayoutEngine:
    """Compute a backend-neutral scene from CircuitIR."""

    def compute(self, circuit: CircuitIR, style: DrawStyle) -> LayoutScene:
        if not circuit.quantum_wires:
            raise LayoutError("circuit must contain at least one quantum wire")

        draw_style = normalize_style(style)
        wire_map = circuit.wire_map
        normalized_layers = self._normalize_layers(circuit)
        wire_positions = self._build_wire_positions(circuit, draw_style)
        column_widths = self._build_column_widths(normalized_layers, draw_style)
        x_centers = self._build_column_centers(column_widths, draw_style)
        page_height = max(wire_positions.values()) + draw_style.margin_bottom
        pages = self._build_pages(column_widths, x_centers, page_height, draw_style)
        scene_width = max(
            (
                draw_style.margin_left + page.content_width + draw_style.margin_right
                for page in pages
            ),
            default=self._scene_width(column_widths, draw_style),
        )
        scene_height = page_height + (
            (len(pages) - 1) * (page_height + draw_style.page_vertical_gap)
        )

        wires = tuple(
            SceneWire(
                id=wire.id,
                label=wire.label or wire.id,
                kind=wire.kind,
                y=wire_positions[wire.id],
                x_start=draw_style.margin_left,
                x_end=draw_style.margin_left
                + (pages[0].content_width if pages else draw_style.gate_width),
                bundle_size=int(wire.metadata.get("bundle_size", 1)),
            )
            for wire in circuit.all_wires
        )
        texts = list(self._wire_labels(circuit, wire_positions, draw_style))
        gates: list[SceneGate] = []
        controls: list[SceneControl] = []
        connections: list[SceneConnection] = []
        swaps: list[SceneSwap] = []
        barriers: list[SceneBarrier] = []
        measurements: list[SceneMeasurement] = []

        for column, layer in enumerate(normalized_layers):
            x = x_centers[column]
            for operation in layer.operations:
                self._layout_operation(
                    operation=operation,
                    column=column,
                    x=x,
                    style=draw_style,
                    wire_map=wire_map,
                    wire_positions=wire_positions,
                    gates=gates,
                    controls=controls,
                    connections=connections,
                    swaps=swaps,
                    barriers=barriers,
                    measurements=measurements,
                )

        return LayoutScene(
            width=scene_width,
            height=scene_height,
            page_height=page_height,
            style=draw_style,
            wires=wires,
            gates=tuple(gates),
            controls=tuple(controls),
            connections=tuple(connections),
            swaps=tuple(swaps),
            barriers=tuple(barriers),
            measurements=tuple(measurements),
            texts=tuple(texts),
            pages=pages,
            wire_y_positions=wire_positions,
        )

    def _normalize_layers(self, circuit: CircuitIR) -> tuple[LayerIR, ...]:
        wire_order = {wire.id: index for index, wire in enumerate(circuit.all_wires)}
        normalized_layers: list[LayerIR] = []
        for layer in circuit.layers:
            drawable_layers: list[list[OperationIR | MeasurementIR]] = []
            latest_layer_by_slot: dict[int, int] = {}
            for operation in layer.operations:
                span_slots = self._operation_draw_span_slots(operation, wire_order)
                target_layer = (
                    max((latest_layer_by_slot.get(slot, -1) for slot in span_slots), default=-1) + 1
                )
                while len(drawable_layers) <= target_layer:
                    drawable_layers.append([])
                drawable_layers[target_layer].append(operation)
                for slot in span_slots:
                    latest_layer_by_slot[slot] = target_layer
            normalized_layers.extend(
                LayerIR(operations=tuple(drawable_layer)) for drawable_layer in drawable_layers
            )
        return tuple(normalized_layers)

    def _operation_draw_span_slots(
        self,
        operation: OperationIR | MeasurementIR,
        wire_order: dict[str, int],
    ) -> tuple[int, ...]:
        involved_wires = list(operation.control_wires) + list(operation.target_wires)
        if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
            involved_wires.append(operation.classical_target)

        slot_indexes = sorted(
            wire_order[wire_id] for wire_id in involved_wires if wire_id in wire_order
        )
        if not slot_indexes:
            return ()

        return tuple(range(slot_indexes[0], slot_indexes[-1] + 1))

    def _build_wire_positions(self, circuit: CircuitIR, style: DrawStyle) -> dict[str, float]:
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

    def _build_column_widths(self, layers: Sequence[LayerIR], style: DrawStyle) -> list[float]:
        widths: list[float] = []
        for layer in layers:
            if not layer.operations:
                widths.append(style.gate_width)
                continue
            widths.append(max(operation_width(operation, style) for operation in layer.operations))
        return widths

    def _build_column_centers(self, widths: Sequence[float], style: DrawStyle) -> list[float]:
        centers: list[float] = []
        current_x = style.margin_left
        for width in widths:
            centers.append(current_x + width / 2)
            current_x += width + style.layer_spacing
        return centers

    def _scene_width(self, widths: Sequence[float], style: DrawStyle) -> float:
        if not widths:
            return style.margin_left + style.margin_right + style.gate_width
        total_columns = sum(widths)
        total_spacing = style.layer_spacing * max(0, len(widths) - 1)
        return style.margin_left + total_columns + total_spacing + style.margin_right

    def _build_pages(
        self,
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
                    self._make_page(
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
            self._make_page(
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
        self,
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

    def _wire_labels(
        self, circuit: CircuitIR, wire_positions: dict[str, float], style: DrawStyle
    ) -> tuple[SceneText, ...]:
        if not style.show_wire_labels:
            return ()
        labels = [
            SceneText(
                x=style.margin_left - style.label_margin,
                y=wire_positions[wire.id],
                text=wire.label or wire.id,
                ha="right",
                font_size=style.font_size,
            )
            for wire in circuit.all_wires
        ]
        return tuple(labels)

    def _layout_operation(
        self,
        *,
        operation: OperationIR,
        column: int,
        x: float,
        style: DrawStyle,
        wire_map: dict[str, WireIR],
        wire_positions: dict[str, float],
        gates: list[SceneGate],
        controls: list[SceneControl],
        connections: list[SceneConnection],
        swaps: list[SceneSwap],
        barriers: list[SceneBarrier],
        measurements: list[SceneMeasurement],
    ) -> None:
        if isinstance(operation, MeasurementIR) or operation.kind is OperationKind.MEASUREMENT:
            quantum_y = wire_positions[operation.target_wires[0]]
            classical_y = (
                wire_positions.get(operation.classical_target)
                if isinstance(operation, MeasurementIR)
                else None
            )
            classical_label = None
            if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
                classical_wire = wire_map.get(operation.classical_target)
                classical_label = (
                    str(operation.metadata.get("classical_bit_label"))
                    if operation.metadata.get("classical_bit_label") is not None
                    else getattr(classical_wire, "label", None) or operation.classical_target
                )
            measurement_width = max(style.gate_width, operation_width(operation, style))
            connector_x = x + measurement_width * 0.24
            connector_y = quantum_y + style.gate_height * 0.18
            measurements.append(
                SceneMeasurement(
                    column=column,
                    x=x,
                    quantum_y=quantum_y,
                    classical_y=classical_y,
                    width=measurement_width,
                    height=style.gate_height,
                    label=operation.label or "M",
                    connector_x=connector_x,
                    connector_y=connector_y,
                )
            )
            if classical_y is not None:
                connections.append(
                    SceneConnection(
                        column=column,
                        x=connector_x,
                        y_start=connector_y,
                        y_end=classical_y,
                        is_classical=True,
                        linestyle="dashed",
                        arrow_at_end=True,
                        label=classical_label,
                    )
                )
            return

        if operation.kind is OperationKind.BARRIER:
            y_top, y_bottom = vertical_span(wire_positions, operation.target_wires)
            barriers.append(
                SceneBarrier(column=column, x=x, y_top=y_top - 0.3, y_bottom=y_bottom + 0.3)
            )
            return

        if operation.kind is OperationKind.SWAP:
            y_top, y_bottom = vertical_span(wire_positions, operation.target_wires)
            connections.append(SceneConnection(column=column, x=x, y_start=y_top, y_end=y_bottom))
            swaps.append(
                SceneSwap(
                    column=column,
                    x=x,
                    y_top=y_top,
                    y_bottom=y_bottom,
                    marker_size=style.swap_marker_size,
                )
            )
            return

        if operation.kind is OperationKind.CONTROLLED_GATE:
            label, subtitle = operation_label_parts(operation, style)
            y_top, y_bottom = vertical_span(wire_positions, operation.target_wires)
            gate_height = max(style.gate_height, (y_bottom - y_top) + style.gate_height)
            gates.append(
                SceneGate(
                    column=column,
                    x=x,
                    y=(y_top + y_bottom) / 2,
                    width=max(style.gate_width, operation_width(operation, style)),
                    height=gate_height,
                    label=format_gate_name(label),
                    subtitle=subtitle,
                    kind=operation.kind,
                )
            )
            control_ids = operation.control_wires
            for control_id in control_ids:
                controls.append(SceneControl(column=column, x=x, y=wire_positions[control_id]))
            span_top, span_bottom = vertical_span(
                wire_positions, (*control_ids, *operation.target_wires)
            )
            connections.append(
                SceneConnection(column=column, x=x, y_start=span_top, y_end=span_bottom)
            )
            return

        label, subtitle = operation_label_parts(operation, style)
        y_top, y_bottom = vertical_span(wire_positions, operation.target_wires)
        gates.append(
            SceneGate(
                column=column,
                x=x,
                y=(y_top + y_bottom) / 2,
                width=max(style.gate_width, operation_width(operation, style)),
                height=max(style.gate_height, (y_bottom - y_top) + style.gate_height),
                label=format_gate_name(label),
                subtitle=subtitle,
                kind=operation.kind,
            )
        )
