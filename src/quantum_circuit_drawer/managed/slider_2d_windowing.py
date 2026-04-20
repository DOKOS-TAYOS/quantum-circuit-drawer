"""Managed 2D slider scene windowing helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from ..layout.scene import (
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneMeasurement,
    SceneSwap,
    SceneText,
    SceneWire,
)
from ..style import DrawStyle
from .slider_3d import circuit_window
from .viewport import build_continuous_slider_scene

if TYPE_CHECKING:
    from .slider_2d import Managed2DPageSliderState

_VIEWPORT_EPSILON = 1e-6


def _scene_for_current_window(state: Managed2DPageSliderState) -> LayoutScene:
    cache_key = (state.start_column, state.start_row)
    cached_scene = state.window_scene_cache.get(cache_key)
    if cached_scene is not None:
        return cached_scene

    horizontal_scene = _horizontal_scene_for_start_column(state, state.start_column)
    if state.max_start_row <= 0:
        state.window_scene_cache[cache_key] = horizontal_scene
        return horizontal_scene

    window_scene = _row_window_scene(
        horizontal_scene,
        start_row=state.start_row,
        visible_qubits=state.visible_qubits,
    )
    state.window_scene_cache[cache_key] = window_scene
    return window_scene


def _horizontal_scene_for_start_column(
    state: Managed2DPageSliderState,
    start_column: int,
) -> LayoutScene:
    cached_scene = state.horizontal_scene_cache.get(start_column)
    if cached_scene is not None:
        return cached_scene

    resolved_start_column = min(max(0, start_column), max(0, state.total_column_count - 1))
    end_column = _window_end_column(
        state.column_widths,
        state.style,
        start_column=resolved_start_column,
        max_scene_width=state.viewport_width,
    )
    window_scene = _width_budgeted_horizontal_scene(
        state,
        start_column=resolved_start_column,
        estimated_end_column=end_column,
    )
    window_scene.hover = state.full_scene.hover
    state.horizontal_scene_cache[resolved_start_column] = window_scene
    return window_scene


def _width_budgeted_horizontal_scene(
    state: Managed2DPageSliderState,
    *,
    start_column: int,
    estimated_end_column: int,
) -> LayoutScene:
    max_end_column = max(0, state.total_column_count - 1)
    resolved_end_column = min(max(start_column, estimated_end_column), max_end_column)
    window_scene = _continuous_horizontal_scene(
        state,
        start_column=start_column,
        end_column=resolved_end_column,
    )

    while (
        window_scene.width > state.viewport_width + _VIEWPORT_EPSILON
        and resolved_end_column > start_column
    ):
        resolved_end_column -= 1
        window_scene = _continuous_horizontal_scene(
            state,
            start_column=start_column,
            end_column=resolved_end_column,
        )

    candidate_end_column = resolved_end_column + 1
    while candidate_end_column <= max_end_column:
        candidate_scene = _continuous_horizontal_scene(
            state,
            start_column=start_column,
            end_column=candidate_end_column,
        )
        if candidate_scene.width > state.viewport_width + _VIEWPORT_EPSILON:
            break
        window_scene = candidate_scene
        candidate_end_column += 1

    return window_scene


def _continuous_horizontal_scene(
    state: Managed2DPageSliderState,
    *,
    start_column: int,
    end_column: int,
) -> LayoutScene:
    windowed_circuit = circuit_window(
        state.circuit,
        start_column=start_column,
        window_size=max(1, end_column - start_column + 1),
    )
    return build_continuous_slider_scene(
        windowed_circuit,
        state.layout_engine,
        state.style,
        hover_enabled=state.full_scene.hover.enabled,
    )


def _window_end_column(
    column_widths: tuple[float, ...],
    style: DrawStyle,
    *,
    start_column: int,
    max_scene_width: float,
) -> int:
    current_scene_width = style.margin_left + style.margin_right
    end_column = start_column
    for column in range(start_column, len(column_widths)):
        additional_width = column_widths[column]
        if column > start_column:
            additional_width += style.layer_spacing
        proposed_scene_width = current_scene_width + additional_width
        if column > start_column and proposed_scene_width > max_scene_width + _VIEWPORT_EPSILON:
            break
        current_scene_width = proposed_scene_width
        end_column = column
    return end_column


def _row_window_scene(
    scene: LayoutScene,
    *,
    start_row: int,
    visible_qubits: int,
) -> LayoutScene:
    visible_wires = tuple(scene.wires[start_row : start_row + visible_qubits])
    if not visible_wires:
        return scene

    first_wire_y = visible_wires[0].y
    last_wire_y = visible_wires[-1].y
    style = scene.style
    window_top = first_wire_y - style.margin_top
    window_bottom = last_wire_y + style.margin_bottom
    y_shift = style.margin_top - first_wire_y
    window_height = style.margin_top + style.margin_bottom + (last_wire_y - first_wire_y)
    visible_wire_ids = {wire.id for wire in visible_wires}

    return LayoutScene(
        width=scene.width,
        height=window_height,
        page_height=window_height,
        style=scene.style,
        wires=tuple(_shift_wire(wire, y_shift=y_shift) for wire in visible_wires),
        gates=tuple(
            _shift_gate(gate, y_shift=y_shift)
            for gate in scene.gates
            if _intersects_range(
                gate.y - (gate.height / 2.0),
                gate.y + (gate.height / 2.0),
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        gate_annotations=tuple(
            _shift_gate_annotation(annotation, y_shift=y_shift)
            for annotation in scene.gate_annotations
            if _intersects_range(
                annotation.y,
                annotation.y,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        controls=tuple(
            _shift_control(control, y_shift=y_shift)
            for control in scene.controls
            if _intersects_range(
                control.y,
                control.y,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        connections=tuple(
            _shift_connection(connection, y_shift=y_shift)
            for connection in scene.connections
            if _intersects_range(
                connection.y_start,
                connection.y_end,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        swaps=tuple(
            _shift_swap(swap, y_shift=y_shift)
            for swap in scene.swaps
            if _intersects_range(
                swap.y_top,
                swap.y_bottom,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        barriers=tuple(
            _shift_barrier(barrier, y_shift=y_shift)
            for barrier in scene.barriers
            if _intersects_range(
                barrier.y_top,
                barrier.y_bottom,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        measurements=tuple(
            _shift_measurement(measurement, y_shift=y_shift)
            for measurement in scene.measurements
            if _measurement_intersects_range(
                measurement,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        texts=tuple(
            _shift_text(text, y_shift=y_shift)
            for text in scene.texts
            if getattr(text, "text", "")
            and _text_matches_visible_wire(text, scene, visible_wire_ids)
        ),
        pages=((replace(scene.pages[0], y_offset=0.0),) if scene.pages else ()),
        hover=scene.hover,
        wire_y_positions={
            wire_id: wire_y + y_shift
            for wire_id, wire_y in scene.wire_y_positions.items()
            if wire_id in visible_wire_ids
        },
        page_count_for_text_scale=1,
    )


def _intersects_range(
    start: float,
    end: float,
    *,
    window_top: float,
    window_bottom: float,
) -> bool:
    lower = min(start, end)
    upper = max(start, end)
    return upper >= window_top - _VIEWPORT_EPSILON and lower <= window_bottom + _VIEWPORT_EPSILON


def _measurement_intersects_range(
    measurement: SceneMeasurement,
    *,
    window_top: float,
    window_bottom: float,
) -> bool:
    measurement_top = measurement.quantum_y - (measurement.height / 2.0)
    measurement_bottom = measurement.quantum_y + (measurement.height / 2.0)
    lower = measurement_top
    upper = measurement_bottom
    if measurement.classical_y is not None:
        lower = min(lower, measurement.classical_y, measurement.connector_y)
        upper = max(upper, measurement.classical_y, measurement.connector_y)
    return upper >= window_top - _VIEWPORT_EPSILON and lower <= window_bottom + _VIEWPORT_EPSILON


def _text_matches_visible_wire(
    text: SceneText,
    scene: LayoutScene,
    visible_wire_ids: set[str],
) -> bool:
    for wire in scene.wires:
        if wire.id in visible_wire_ids and abs(wire.y - text.y) <= _VIEWPORT_EPSILON:
            return True
    return False


def _shift_wire(wire: SceneWire, *, y_shift: float) -> SceneWire:
    return replace(wire, y=wire.y + y_shift)


def _shift_gate(gate: SceneGate, *, y_shift: float) -> SceneGate:
    return replace(gate, y=gate.y + y_shift)


def _shift_gate_annotation(
    annotation: SceneGateAnnotation,
    *,
    y_shift: float,
) -> SceneGateAnnotation:
    return replace(annotation, y=annotation.y + y_shift)


def _shift_control(control: SceneControl, *, y_shift: float) -> SceneControl:
    return replace(control, y=control.y + y_shift)


def _shift_connection(connection: SceneConnection, *, y_shift: float) -> SceneConnection:
    return replace(
        connection,
        y_start=connection.y_start + y_shift,
        y_end=connection.y_end + y_shift,
    )


def _shift_swap(swap: SceneSwap, *, y_shift: float) -> SceneSwap:
    return replace(
        swap,
        y_top=swap.y_top + y_shift,
        y_bottom=swap.y_bottom + y_shift,
    )


def _shift_barrier(barrier: SceneBarrier, *, y_shift: float) -> SceneBarrier:
    return replace(
        barrier,
        y_top=barrier.y_top + y_shift,
        y_bottom=barrier.y_bottom + y_shift,
    )


def _shift_measurement(
    measurement: SceneMeasurement,
    *,
    y_shift: float,
) -> SceneMeasurement:
    return replace(
        measurement,
        quantum_y=measurement.quantum_y + y_shift,
        classical_y=(
            None if measurement.classical_y is None else measurement.classical_y + y_shift
        ),
        connector_y=measurement.connector_y + y_shift,
    )


def _shift_text(text: SceneText, *, y_shift: float) -> SceneText:
    return replace(text, y=text.y + y_shift)
