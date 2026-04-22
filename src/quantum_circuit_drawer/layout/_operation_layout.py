"""Internal helpers for mapping IR operations into 2D scene primitives."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..ir.circuit import CircuitIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR
from ..ir.wires import WireIR
from ..utils import matrix_support as _matrix_support_module
from ._layout_scaffold import _LayoutScaffold, _OperationMetrics
from ._operation_layout_builder import build_scene_collections_impl
from ._operation_layout_collections import wire_labels
from ._operation_layout_emitters import (
    append_classical_condition_connections,
    append_gate_annotations,
    layout_barrier,
    layout_controlled_gate,
    layout_controlled_x,
    layout_controlled_z,
    layout_gate,
    layout_measurement,
    layout_operation,
    layout_swap,
    uses_canonical_controlled_x_target,
    uses_canonical_controlled_z,
)
from ._operation_layout_hover import (
    build_hover_data,
    cache_token,
    hover_matrix_and_dimension,
    hover_matrix_cache_key,
    hover_name,
    maybe_hover_data,
)
from .scene import (
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneHoverData,
    SceneMeasurement,
    SceneSwap,
    SceneText,
    SceneWire,
)

resolved_operation_matrix = _matrix_support_module.resolved_operation_matrix
operation_matrix_dimension = _matrix_support_module.operation_matrix_dimension


@dataclass(frozen=True, slots=True)
class _SceneCollections:
    wires: tuple[SceneWire, ...]
    texts: tuple[SceneText, ...]
    gates: tuple[SceneGate, ...]
    gate_annotations: tuple[SceneGateAnnotation, ...]
    controls: tuple[SceneControl, ...]
    connections: tuple[SceneConnection, ...]
    swaps: tuple[SceneSwap, ...]
    barriers: tuple[SceneBarrier, ...]
    measurements: tuple[SceneMeasurement, ...]


@dataclass(slots=True)
class _OperationSceneBuilder:
    circuit: CircuitIR
    scaffold: _LayoutScaffold
    hover_enabled: bool = True
    resolved_operation_matrix_fn: Callable[[OperationIR], object | None] = resolved_operation_matrix
    operation_matrix_dimension_fn: Callable[[OperationIR], int | None] = operation_matrix_dimension
    wire_map: dict[str, WireIR] = field(init=False)
    gates: list[SceneGate] = field(default_factory=list, init=False)
    gate_annotations: list[SceneGateAnnotation] = field(default_factory=list, init=False)
    controls: list[SceneControl] = field(default_factory=list, init=False)
    connections: list[SceneConnection] = field(default_factory=list, init=False)
    swaps: list[SceneSwap] = field(default_factory=list, init=False)
    barriers: list[SceneBarrier] = field(default_factory=list, init=False)
    measurements: list[SceneMeasurement] = field(default_factory=list, init=False)
    hover_matrix_cache: dict[tuple[object, ...], tuple[object | None, int | None]] = field(
        default_factory=dict,
        init=False,
    )
    scene_collections_type: type[_SceneCollections] = field(default=_SceneCollections, init=False)

    def __post_init__(self) -> None:
        self.wire_map = self.circuit.wire_map

    def build(self) -> _SceneCollections:
        return build_scene_collections_impl(self)

    def _wire_labels(self) -> tuple[SceneText, ...]:
        return wire_labels(self)

    def _hover_data(
        self,
        *,
        operation: OperationIR,
        column: int,
        name: str,
        gate_x: float,
        gate_y: float,
        gate_width: float,
        gate_height: float,
    ) -> SceneHoverData:
        return build_hover_data(
            self,
            operation=operation,
            column=column,
            name=name,
            gate_x=gate_x,
            gate_y=gate_y,
            gate_width=gate_width,
            gate_height=gate_height,
        )

    def _hover_matrix_and_dimension(
        self,
        operation: OperationIR,
    ) -> tuple[object | None, int | None]:
        return hover_matrix_and_dimension(self, operation)

    def _hover_matrix_cache_key(self, operation: OperationIR) -> tuple[object, ...]:
        return hover_matrix_cache_key(self, operation)

    def _cache_token(self, value: object) -> object:
        return cache_token(self, value)

    def _maybe_hover_data(
        self,
        *,
        operation: OperationIR,
        column: int,
        name: str,
        gate_x: float,
        gate_y: float,
        gate_width: float,
        gate_height: float,
    ) -> SceneHoverData | None:
        return maybe_hover_data(
            self,
            operation=operation,
            column=column,
            name=name,
            gate_x=gate_x,
            gate_y=gate_y,
            gate_width=gate_width,
            gate_height=gate_height,
        )

    def _hover_name(self, operation: OperationIR | MeasurementIR, display_name: str) -> str:
        return hover_name(self, operation, display_name)

    def _layout_operation(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
    ) -> None:
        layout_operation(self, operation=operation, metrics=metrics, column=column, x=x)

    def _append_classical_condition_connections(
        self,
        *,
        operation: OperationIR,
        column: int,
        x: float,
        anchor_center_y: float,
        anchor_half_extent: float,
    ) -> None:
        append_classical_condition_connections(
            self,
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=anchor_center_y,
            anchor_half_extent=anchor_half_extent,
        )

    def _layout_measurement(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
    ) -> None:
        layout_measurement(self, operation=operation, metrics=metrics, column=column, x=x)

    def _layout_barrier(self, *, operation: OperationIR, column: int, x: float) -> None:
        layout_barrier(self, operation=operation, column=column, x=x)

    def _layout_swap(self, *, operation: OperationIR, column: int, x: float) -> None:
        layout_swap(self, operation=operation, column=column, x=x)

    def _layout_controlled_gate(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
    ) -> None:
        layout_controlled_gate(self, operation=operation, metrics=metrics, column=column, x=x)

    def _layout_controlled_z(self, *, operation: OperationIR, column: int, x: float) -> None:
        layout_controlled_z(self, operation=operation, column=column, x=x)

    def _layout_controlled_x(self, *, operation: OperationIR, column: int, x: float) -> None:
        layout_controlled_x(self, operation=operation, column=column, x=x)

    def _layout_gate(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
    ) -> None:
        layout_gate(self, operation=operation, metrics=metrics, column=column, x=x)

    def _uses_canonical_controlled_x_target(self, operation: OperationIR) -> bool:
        return uses_canonical_controlled_x_target(self, operation)

    def _uses_canonical_controlled_z(self, operation: OperationIR) -> bool:
        return uses_canonical_controlled_z(self, operation)

    def _append_gate_annotations(
        self,
        *,
        column: int,
        x: float,
        width: float,
        target_wires: tuple[str, ...],
        operation_id: str | None = None,
    ) -> None:
        append_gate_annotations(
            self,
            column=column,
            x=x,
            width=width,
            target_wires=target_wires,
            operation_id=operation_id,
        )


def build_scene_collections(
    circuit: CircuitIR,
    scaffold: _LayoutScaffold,
    *,
    hover_enabled: bool = True,
) -> _SceneCollections:
    """Build all scene primitives using the shared scaffold."""

    return _OperationSceneBuilder(
        circuit=circuit,
        scaffold=scaffold,
        hover_enabled=hover_enabled,
        resolved_operation_matrix_fn=resolved_operation_matrix,
        operation_matrix_dimension_fn=operation_matrix_dimension,
    ).build()
