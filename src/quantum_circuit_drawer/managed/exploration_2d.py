"""Shared exploration-state helpers for managed interactive 2D rendering."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TypeVar

from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent

from .._compat import StrEnum
from ..drawing.pages import _items_for_page
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.operations import OperationKind
from ..ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
    SemanticProvenanceIR,
    semantic_operation_id,
    semantic_operation_id_from_location,
)
from ..ir.wires import WireIR, WireKind
from ..layout.scene import (
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneGroupHighlight,
    SceneMeasurement,
    SceneSwap,
    SceneVisualState,
    SceneWireFoldMarker,
)
from ..layout.scene_3d import (
    LayoutScene3D,
    SceneConnection3D,
    SceneGate3D,
    SceneMarker3D,
    SceneText3D,
)
from ..renderers._matplotlib_page_projection import page_x_offset, page_y_offset

_CLICK_CONNECTION_HALF_WIDTH = 0.1
_ANCILLA_NAME_HINTS = ("ancilla", "anc", "work")
_COLLAPSED_LABEL_NUMBER_PATTERN = re.compile(
    r"(?<![\w.])[-+]?(?:\d+\.\d+|\d+\.|\.\d+)(?:[eE][-+]?\d+)?"
)
_SceneOperationVisualItem = TypeVar(
    "_SceneOperationVisualItem",
    SceneGate,
    SceneGateAnnotation,
    SceneControl,
    SceneConnection,
    SceneSwap,
    SceneBarrier,
    SceneMeasurement,
)
_SceneOperationVisualItem3D = TypeVar(
    "_SceneOperationVisualItem3D",
    SceneGate3D,
    SceneConnection3D,
    SceneMarker3D,
    SceneText3D,
)


class WireFilterMode(StrEnum):
    """Wire visibility mode for managed 2D exploration."""

    ALL = "all"
    ACTIVE = "active"


@dataclass(frozen=True, slots=True)
class ExplorationBlock:
    """Top-level semantic block that can be collapsed or expanded."""

    block_id: str
    label: str
    top_level_location: tuple[int, ...]
    operation_ids: tuple[str, ...]
    wire_ids: tuple[str, ...]
    operation_count: int
    original_collapsed_operation: SemanticOperationIR | None = None


@dataclass(frozen=True, slots=True)
class ExplorationHiddenWireRange:
    """Contiguous hidden wires between two visible wires."""

    before_wire_id: str
    after_wire_id: str
    hidden_wire_ids: tuple[str, ...]

    @property
    def hidden_wire_count(self) -> int:
        return len(self.hidden_wire_ids)


@dataclass(frozen=True, slots=True)
class ExplorationCatalog:
    """Static semantic exploration metadata shared by slider and page-window modes."""

    current_semantic_ir: SemanticCircuitIR
    expanded_semantic_ir: SemanticCircuitIR
    blocks: dict[str, ExplorationBlock]
    block_id_by_operation_id: dict[str, str]
    initial_collapsed_block_ids: frozenset[str]


@dataclass(slots=True)
class Managed2DExplorationState:
    """Mutable exploration state shared by the 2D managed views."""

    catalog: ExplorationCatalog
    collapsed_block_ids: set[str]
    wire_filter_mode: WireFilterMode = WireFilterMode.ALL
    show_ancillas: bool = True
    selected_operation_id: str | None = None
    transformed_semantic_ir: SemanticCircuitIR | None = None
    hidden_wire_ranges: tuple[ExplorationHiddenWireRange, ...] = ()


@dataclass(frozen=True, slots=True)
class TransformedExplorationCircuit:
    """Semantic circuit after collapse and wire-filter transforms."""

    semantic_ir: SemanticCircuitIR
    circuit_ir: CircuitIR
    hidden_wire_ranges: tuple[ExplorationHiddenWireRange, ...]


@dataclass(frozen=True, slots=True)
class ExplorationSelectionScope:
    """Selection-derived emphasis state for one transformed semantic circuit."""

    selected_operation_id: str | None
    related_operation_ids: tuple[str, ...]
    selected_wire_ids: tuple[str, ...]

    @property
    def emphasized_operation_ids(self) -> tuple[str, ...]:
        if self.selected_operation_id is None:
            return ()
        return tuple(dict.fromkeys((self.selected_operation_id, *self.related_operation_ids)))


@dataclass(frozen=True, slots=True)
class ExplorationBlockAction:
    """Context-sensitive block action available for the current selection."""

    action: str
    block_id: str
    label: str


@dataclass(frozen=True, slots=True)
class ExplorationControlAvailability:
    """Resolved visibility for managed exploration controls."""

    show_wire_filter: bool
    show_ancilla_toggle: bool
    show_block_toggle: bool


@dataclass(frozen=True, slots=True)
class SceneClickTarget:
    """Clickable scene-space hit target for operation selection."""

    operation_id: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def area(self) -> float:
        return max(0.0, self.x_max - self.x_min) * max(0.0, self.y_max - self.y_min)


@dataclass(frozen=True, slots=True)
class _TopLevelOperationGroup:
    operations: tuple[SemanticOperationIR, ...]
    barrier_wire_ids: tuple[str, ...] = ()


def build_exploration_catalog(
    current_semantic_ir: SemanticCircuitIR,
    expanded_semantic_ir: SemanticCircuitIR,
) -> ExplorationCatalog:
    """Build the shared semantic catalog used by managed 2D exploration."""

    blocks: dict[str, ExplorationBlock] = {}
    block_id_by_operation_id: dict[str, str] = {}
    grouped_operations = _operations_by_top_level_location(expanded_semantic_ir)
    wire_order = {wire.id: index for index, wire in enumerate(expanded_semantic_ir.all_wires)}
    current_operations_by_id = {
        semantic_operation_id(operation): operation
        for operation in _flatten_operations(current_semantic_ir)
    }

    for top_level_location, operations in grouped_operations:
        label = _collapse_label(operations)
        if label is None or len(operations) <= 1:
            continue

        block_id = semantic_operation_id_from_location(top_level_location)
        wire_ids = tuple(
            sorted(
                {wire_id for operation in operations for wire_id in operation.occupied_wire_ids},
                key=lambda wire_id: wire_order.get(wire_id, len(wire_order)),
            )
        )
        operation_ids = tuple(semantic_operation_id(operation) for operation in operations)
        blocks[block_id] = ExplorationBlock(
            block_id=block_id,
            label=label,
            top_level_location=top_level_location,
            operation_ids=operation_ids,
            wire_ids=wire_ids,
            operation_count=len(operations),
            original_collapsed_operation=current_operations_by_id.get(block_id),
        )
        block_id_by_operation_id[block_id] = block_id
        for operation_id in operation_ids:
            block_id_by_operation_id[operation_id] = block_id

    return ExplorationCatalog(
        current_semantic_ir=current_semantic_ir,
        expanded_semantic_ir=expanded_semantic_ir,
        blocks=blocks,
        block_id_by_operation_id=block_id_by_operation_id,
        initial_collapsed_block_ids=_initial_collapsed_block_ids(
            current_semantic_ir=current_semantic_ir,
            blocks=blocks,
        ),
    )


def managed_exploration_state(
    current_semantic_ir: SemanticCircuitIR,
    expanded_semantic_ir: SemanticCircuitIR,
) -> Managed2DExplorationState:
    """Build the shared mutable exploration state for one managed 2D figure."""

    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)
    return Managed2DExplorationState(
        catalog=catalog,
        collapsed_block_ids=set(catalog.initial_collapsed_block_ids),
    )


def transform_semantic_circuit(
    catalog: ExplorationCatalog,
    *,
    collapsed_block_ids: set[str] | frozenset[str],
    wire_filter_mode: WireFilterMode,
    show_ancillas: bool,
) -> TransformedExplorationCircuit:
    """Apply collapse and wire-visibility transforms to the expanded semantic source."""

    collapsed_circuit = _collapsed_semantic_circuit(
        catalog,
        collapsed_block_ids=collapsed_block_ids,
    )

    visible_wire_ids = _visible_wire_ids(
        collapsed_circuit,
        wire_filter_mode=wire_filter_mode,
        show_ancillas=show_ancillas,
    )
    filtered_layers = tuple(
        SemanticLayerIR(operations=visible_operations, metadata=dict(layer.metadata))
        for layer in collapsed_circuit.layers
        if (
            visible_operations := tuple(
                operation
                for operation in layer.operations
                if set(operation.occupied_wire_ids).issubset(visible_wire_ids)
            )
        )
    )
    filtered_circuit = SemanticCircuitIR(
        quantum_wires=tuple(
            wire for wire in collapsed_circuit.quantum_wires if wire.id in visible_wire_ids
        ),
        classical_wires=tuple(
            wire for wire in collapsed_circuit.classical_wires if wire.id in visible_wire_ids
        ),
        layers=filtered_layers,
        name=collapsed_circuit.name,
        metadata=dict(collapsed_circuit.metadata),
        diagnostics=tuple(collapsed_circuit.diagnostics),
    )
    return TransformedExplorationCircuit(
        semantic_ir=filtered_circuit,
        circuit_ir=lower_semantic_circuit(filtered_circuit),
        hidden_wire_ranges=_hidden_wire_ranges(
            all_wires=collapsed_circuit.all_wires,
            visible_wire_ids=visible_wire_ids,
        ),
    )


def exploration_control_availability(
    catalog: ExplorationCatalog,
    *,
    collapsed_block_ids: set[str] | frozenset[str],
    wire_filter_mode: WireFilterMode,
    show_ancillas: bool,
    selected_operation_id: str | None,
) -> ExplorationControlAvailability:
    """Return which managed exploration controls can currently change the view."""

    collapsed_circuit = _collapsed_semantic_circuit(
        catalog,
        collapsed_block_ids=collapsed_block_ids,
    )
    all_visible_wire_ids = _visible_wire_ids(
        collapsed_circuit,
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=show_ancillas,
    )
    active_visible_wire_ids = _visible_wire_ids(
        collapsed_circuit,
        wire_filter_mode=WireFilterMode.ACTIVE,
        show_ancillas=show_ancillas,
    )
    ancillas_shown_wire_ids = _visible_wire_ids(
        collapsed_circuit,
        wire_filter_mode=wire_filter_mode,
        show_ancillas=True,
    )
    ancillas_hidden_wire_ids = _visible_wire_ids(
        collapsed_circuit,
        wire_filter_mode=wire_filter_mode,
        show_ancillas=False,
    )
    return ExplorationControlAvailability(
        show_wire_filter=all_visible_wire_ids != active_visible_wire_ids,
        show_ancilla_toggle=ancillas_shown_wire_ids != ancillas_hidden_wire_ids,
        show_block_toggle=selected_block_action(
            catalog,
            selected_operation_id=selected_operation_id,
            collapsed_block_ids=collapsed_block_ids,
        )
        is not None,
    )


def selection_scope(
    circuit: SemanticCircuitIR,
    *,
    selected_operation_id: str | None,
) -> ExplorationSelectionScope:
    """Compute related operations and wires for the current selection."""

    if selected_operation_id is None:
        return ExplorationSelectionScope(
            selected_operation_id=None,
            related_operation_ids=(),
            selected_wire_ids=(),
        )

    operations = _flatten_operations(circuit)
    operation_ids = [semantic_operation_id(operation) for operation in operations]
    try:
        selected_index = operation_ids.index(selected_operation_id)
    except ValueError:
        return ExplorationSelectionScope(
            selected_operation_id=None,
            related_operation_ids=(),
            selected_wire_ids=(),
        )

    selected_operation = operations[selected_index]
    selected_wire_ids = tuple(dict.fromkeys(selected_operation.occupied_wire_ids))
    selected_wire_set = set(selected_wire_ids)

    related_operation_ids: list[str] = []
    previous_operation = _neighbor_operation(
        operations,
        start_index=selected_index - 1,
        step=-1,
        wire_ids=selected_wire_set,
    )
    if previous_operation is not None:
        related_operation_ids.append(semantic_operation_id(previous_operation))

    next_operation = _neighbor_operation(
        operations,
        start_index=selected_index + 1,
        step=1,
        wire_ids=selected_wire_set,
    )
    if next_operation is not None:
        related_operation_ids.append(semantic_operation_id(next_operation))

    return ExplorationSelectionScope(
        selected_operation_id=selected_operation_id,
        related_operation_ids=tuple(related_operation_ids),
        selected_wire_ids=selected_wire_ids,
    )


def selected_block_action(
    catalog: ExplorationCatalog,
    *,
    selected_operation_id: str | None,
    collapsed_block_ids: set[str] | frozenset[str],
) -> ExplorationBlockAction | None:
    """Return the contextual block action available for the current selection."""

    if selected_operation_id is None:
        return None

    block_id = catalog.block_id_by_operation_id.get(selected_operation_id)
    if block_id is None:
        return None

    block = catalog.blocks.get(block_id)
    if block is None:
        return None

    if block_id in collapsed_block_ids:
        return ExplorationBlockAction(
            action="expand",
            block_id=block_id,
            label=f"Expand {block.label}",
        )
    return ExplorationBlockAction(
        action="collapse",
        block_id=block_id,
        label=f"Collapse {block.label}",
    )


def next_selected_operation_id_for_block_action(
    catalog: ExplorationCatalog,
    action: ExplorationBlockAction,
) -> str:
    """Return the operation selection that should remain active after a block action."""

    if action.action == "expand":
        block = catalog.blocks[action.block_id]
        return block.operation_ids[0]
    return action.block_id


def apply_scene_visual_state(
    scene: LayoutScene,
    circuit: SemanticCircuitIR,
    *,
    selected_operation_id: str | None,
) -> LayoutScene:
    """Return a scene copy with contextual emphasis applied to visible elements."""

    scope = selection_scope(circuit, selected_operation_id=selected_operation_id)
    grouped_operation_ids = _expanded_group_operation_ids(circuit)
    if scope.selected_operation_id is None:
        return replace(
            scene,
            group_highlights=_group_highlights_for_operation_ids(
                scene,
                grouped_operation_ids=grouped_operation_ids,
            ),
        )

    emphasized_operation_ids = set(scope.emphasized_operation_ids)
    selected_wire_ids = set(scope.selected_wire_ids)
    operation_ids = {semantic_operation_id(operation) for operation in _flatten_operations(circuit)}
    return replace(
        scene,
        wires=tuple(
            replace(
                wire,
                visual_state=(
                    SceneVisualState.HIGHLIGHTED
                    if wire.id in selected_wire_ids
                    else SceneVisualState.DIMMED
                ),
            )
            for wire in scene.wires
        ),
        gates=tuple(
            _with_operation_visual_state(
                gate,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for gate in scene.gates
        ),
        gate_annotations=tuple(
            _with_operation_visual_state(
                annotation,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for annotation in scene.gate_annotations
        ),
        controls=tuple(
            _with_operation_visual_state(
                control,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for control in scene.controls
        ),
        connections=tuple(
            _with_operation_visual_state(
                connection,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for connection in scene.connections
        ),
        swaps=tuple(
            _with_operation_visual_state(
                swap,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for swap in scene.swaps
        ),
        barriers=tuple(
            _with_operation_visual_state(
                barrier,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for barrier in scene.barriers
        ),
        measurements=tuple(
            _with_operation_visual_state(
                measurement,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for measurement in scene.measurements
        ),
        texts=tuple(
            replace(
                text,
                visual_state=(
                    SceneVisualState.HIGHLIGHTED
                    if text.wire_id in selected_wire_ids
                    else SceneVisualState.DIMMED
                    if text.wire_id is not None
                    else text.visual_state
                ),
            )
            for text in scene.texts
        ),
        group_highlights=_group_highlights_for_operation_ids(
            scene,
            grouped_operation_ids=grouped_operation_ids,
        ),
    )


def append_wire_fold_markers(
    scene: LayoutScene,
    hidden_wire_ranges: Sequence[ExplorationHiddenWireRange],
) -> LayoutScene:
    """Return a scene copy with hidden-wire markers inserted between visible wire groups."""

    if not hidden_wire_ranges:
        return replace(scene, wire_fold_markers=())

    markers: list[SceneWireFoldMarker] = []
    for hidden_range in hidden_wire_ranges:
        before_y = scene.wire_y_positions.get(hidden_range.before_wire_id)
        after_y = scene.wire_y_positions.get(hidden_range.after_wire_id)
        if before_y is None or after_y is None:
            continue
        markers.append(
            SceneWireFoldMarker(
                x=scene.style.margin_left + min(0.4, scene.style.gate_width * 0.45),
                y=(before_y + after_y) / 2.0,
                hidden_wire_count=hidden_range.hidden_wire_count,
                text=_hidden_wire_marker_text(hidden_range.hidden_wire_count),
            )
        )

    return replace(scene, wire_fold_markers=tuple(markers))


def apply_scene_visual_state_3d(
    scene: LayoutScene3D,
    circuit: SemanticCircuitIR,
    *,
    selected_operation_id: str | None,
) -> LayoutScene3D:
    """Return a 3D scene copy with contextual emphasis applied."""

    scope = selection_scope(circuit, selected_operation_id=selected_operation_id)
    grouped_operation_ids = _expanded_group_operation_ids(circuit)
    if scope.selected_operation_id is None:
        return replace(
            scene,
            wires=tuple(
                replace(wire, visual_state=SceneVisualState.DEFAULT) for wire in scene.wires
            ),
            gates=tuple(
                replace(
                    gate,
                    visual_state=SceneVisualState.DEFAULT,
                    group_highlighted=gate.operation_id in grouped_operation_ids,
                )
                for gate in scene.gates
            ),
            markers=tuple(
                replace(marker, visual_state=SceneVisualState.DEFAULT) for marker in scene.markers
            ),
            connections=tuple(
                replace(connection, visual_state=SceneVisualState.DEFAULT)
                for connection in scene.connections
            ),
            texts=tuple(
                replace(text, visual_state=SceneVisualState.DEFAULT) for text in scene.texts
            ),
        )

    selected_wire_ids = set(scope.selected_wire_ids)
    emphasized_operation_ids = set(scope.emphasized_operation_ids)
    operation_ids = {semantic_operation_id(operation) for operation in _flatten_operations(circuit)}
    return replace(
        scene,
        wires=tuple(
            replace(
                wire,
                visual_state=(
                    SceneVisualState.HIGHLIGHTED
                    if wire.id in selected_wire_ids
                    else SceneVisualState.DIMMED
                    if scope.selected_operation_id is not None
                    else SceneVisualState.DEFAULT
                ),
            )
            for wire in scene.wires
        ),
        gates=tuple(
            replace(
                _with_operation_visual_state_3d(
                    gate,
                    selected_operation_id=scope.selected_operation_id,
                    emphasized_operation_ids=emphasized_operation_ids,
                    operation_ids=operation_ids,
                ),
                group_highlighted=gate.operation_id in grouped_operation_ids,
            )
            for gate in scene.gates
        ),
        markers=tuple(
            _with_operation_visual_state_3d(
                marker,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for marker in scene.markers
        ),
        connections=tuple(
            _with_operation_visual_state_3d(
                connection,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
            )
            for connection in scene.connections
        ),
        texts=tuple(
            _with_text_visual_state_3d(
                text,
                selected_operation_id=scope.selected_operation_id,
                emphasized_operation_ids=emphasized_operation_ids,
                operation_ids=operation_ids,
                selected_wire_ids=selected_wire_ids,
            )
            for text in scene.texts
        ),
    )


def scene_click_targets(scene: LayoutScene) -> tuple[SceneClickTarget, ...]:
    """Build clickable operation hit-boxes for the currently rendered scene."""

    targets: list[SceneClickTarget] = []
    for page in scene.pages:
        x_offset = page_x_offset(page, scene)
        y_offset = page_y_offset(page)
        for gate in _items_for_page(scene.gates, page=page):
            if gate.operation_id is None:
                continue
            targets.append(
                SceneClickTarget(
                    operation_id=gate.operation_id,
                    x_min=gate.x + x_offset - (gate.width / 2.0),
                    x_max=gate.x + x_offset + (gate.width / 2.0),
                    y_min=gate.y + y_offset - (gate.height / 2.0),
                    y_max=gate.y + y_offset + (gate.height / 2.0),
                )
            )
        for measurement in _items_for_page(scene.measurements, page=page):
            if measurement.operation_id is None:
                continue
            targets.append(
                SceneClickTarget(
                    operation_id=measurement.operation_id,
                    x_min=measurement.x + x_offset - (measurement.width / 2.0),
                    x_max=measurement.x + x_offset + (measurement.width / 2.0),
                    y_min=measurement.quantum_y + y_offset - (measurement.height / 2.0),
                    y_max=measurement.quantum_y + y_offset + (measurement.height / 2.0),
                )
            )
        for control in _items_for_page(scene.controls, page=page):
            if control.operation_id is None:
                continue
            radius = scene.style.control_radius
            targets.append(
                SceneClickTarget(
                    operation_id=control.operation_id,
                    x_min=control.x + x_offset - radius,
                    x_max=control.x + x_offset + radius,
                    y_min=control.y + y_offset - radius,
                    y_max=control.y + y_offset + radius,
                )
            )
        for swap in _items_for_page(scene.swaps, page=page):
            if swap.operation_id is None:
                continue
            targets.append(
                SceneClickTarget(
                    operation_id=swap.operation_id,
                    x_min=swap.x + x_offset - swap.marker_size,
                    x_max=swap.x + x_offset + swap.marker_size,
                    y_min=swap.y_top + y_offset - swap.marker_size,
                    y_max=swap.y_bottom + y_offset + swap.marker_size,
                )
            )
        for connection in _items_for_page(scene.connections, page=page):
            if connection.operation_id is None:
                continue
            targets.append(
                SceneClickTarget(
                    operation_id=connection.operation_id,
                    x_min=connection.x + x_offset - _CLICK_CONNECTION_HALF_WIDTH,
                    x_max=connection.x + x_offset + _CLICK_CONNECTION_HALF_WIDTH,
                    y_min=min(connection.y_start, connection.y_end) + y_offset,
                    y_max=max(connection.y_start, connection.y_end) + y_offset,
                )
            )
    return tuple(targets)


def clicked_operation_id(
    axes: Axes,
    scene: LayoutScene,
    event: MouseEvent,
) -> str | None:
    """Resolve the selected operation id for one click inside the main axes."""

    if event.inaxes is not axes or event.xdata is None or event.ydata is None:
        return None

    x_value = float(event.xdata)
    y_value = float(event.ydata)
    matching_targets = [
        target
        for target in scene_click_targets(scene)
        if target.x_min <= x_value <= target.x_max and target.y_min <= y_value <= target.y_max
    ]
    if not matching_targets:
        return None
    return min(matching_targets, key=lambda target: target.area).operation_id


def toggle_wire_filter_mode(mode: WireFilterMode) -> WireFilterMode:
    """Return the alternate wire-filter mode."""

    if mode is WireFilterMode.ALL:
        return WireFilterMode.ACTIVE
    return WireFilterMode.ALL


def _collapse_top_level_blocks(
    expanded_semantic_ir: SemanticCircuitIR,
    *,
    blocks: dict[str, ExplorationBlock],
    collapsed_block_ids: set[str] | frozenset[str],
) -> tuple[_TopLevelOperationGroup, ...]:
    wire_order = {wire.id: index for index, wire in enumerate(expanded_semantic_ir.all_wires)}
    grouped_operations = {
        semantic_operation_id_from_location(top_level_location): operations
        for top_level_location, operations in _operations_by_top_level_location(
            expanded_semantic_ir
        )
    }
    terminal_barrier_wire_ids = tuple(wire.id for wire in expanded_semantic_ir.all_wires)
    operation_groups: list[_TopLevelOperationGroup] = []
    for top_level_location, operations in _top_level_operation_groups(expanded_semantic_ir):
        block_id = semantic_operation_id_from_location(top_level_location)
        block = blocks.get(block_id)
        if block is None or block_id not in collapsed_block_ids:
            barrier_wire_ids: tuple[str, ...] = ()
            if block is not None:
                barrier_wire_ids = block.wire_ids
            elif any(_is_terminal_output_operation(operation) for operation in operations):
                barrier_wire_ids = terminal_barrier_wire_ids
            operation_groups.append(
                _TopLevelOperationGroup(
                    operations=operations,
                    barrier_wire_ids=barrier_wire_ids,
                )
            )
            continue

        operation_groups.append(
            _TopLevelOperationGroup(
                operations=(
                    _collapsed_block_operation(
                        block,
                        operations=grouped_operations[block_id],
                        wire_order=wire_order,
                    ),
                ),
                barrier_wire_ids=block.wire_ids,
            )
        )
    return tuple(operation_groups)


def _pack_top_level_operation_groups(
    circuit: SemanticCircuitIR,
    operation_groups: Sequence[_TopLevelOperationGroup],
) -> tuple[SemanticLayerIR, ...]:
    wire_order = {wire.id: index for index, wire in enumerate(circuit.all_wires)}
    layer_operations: list[list[SemanticOperationIR]] = []
    latest_layer_by_slot: dict[int, int] = {}
    for operation_group in operation_groups:
        group_slots = _wire_span_slots(operation_group.barrier_wire_ids, wire_order)
        group_floor = max(
            (latest_layer_by_slot.get(slot, -1) for slot in group_slots),
            default=-1,
        )
        group_layers: list[int] = []
        for operation in operation_group.operations:
            span_slots = _semantic_operation_draw_span_slots(operation, wire_order)
            operation_floor = max(
                (latest_layer_by_slot.get(slot, -1) for slot in span_slots),
                default=-1,
            )
            target_layer = max(group_floor, operation_floor) + 1
            while len(layer_operations) <= target_layer:
                layer_operations.append([])
            layer_operations[target_layer].append(operation)
            group_layers.append(target_layer)
            for slot in span_slots:
                latest_layer_by_slot[slot] = target_layer

        if group_slots and group_layers:
            group_end = max(group_layers)
            for slot in group_slots:
                latest_layer_by_slot[slot] = max(
                    latest_layer_by_slot.get(slot, -1),
                    group_end,
                )

    return tuple(
        SemanticLayerIR(operations=tuple(operations))
        for operations in layer_operations
        if operations
    )


def _semantic_operation_draw_span_slots(
    operation: SemanticOperationIR,
    wire_order: dict[str, int],
) -> tuple[int, ...]:
    wire_ids: list[str] = []
    wire_ids.extend(operation.control_wires)
    wire_ids.extend(operation.target_wires)
    for condition in operation.classical_conditions:
        wire_ids.extend(condition.wire_ids)
    if operation.classical_target is not None:
        wire_ids.append(operation.classical_target)
    return _wire_span_slots(tuple(wire_ids), wire_order)


def _wire_span_slots(
    wire_ids: Sequence[str],
    wire_order: dict[str, int],
) -> tuple[int, ...]:
    slots = [wire_order[wire_id] for wire_id in wire_ids if wire_id in wire_order]
    if not slots:
        return ()
    return tuple(range(min(slots), max(slots) + 1))


def _collapsed_semantic_circuit(
    catalog: ExplorationCatalog,
    *,
    collapsed_block_ids: set[str] | frozenset[str],
) -> SemanticCircuitIR:
    collapsed_operation_groups = _collapse_top_level_blocks(
        catalog.expanded_semantic_ir,
        blocks=catalog.blocks,
        collapsed_block_ids=collapsed_block_ids,
    )
    collapsed_layers = _pack_top_level_operation_groups(
        catalog.expanded_semantic_ir,
        collapsed_operation_groups,
    )
    return SemanticCircuitIR(
        quantum_wires=catalog.expanded_semantic_ir.quantum_wires,
        classical_wires=catalog.expanded_semantic_ir.classical_wires,
        layers=collapsed_layers,
        name=catalog.expanded_semantic_ir.name,
        metadata=dict(catalog.expanded_semantic_ir.metadata),
        diagnostics=tuple(catalog.expanded_semantic_ir.diagnostics),
    )


def _collapsed_block_operation(
    block: ExplorationBlock,
    *,
    operations: Sequence[SemanticOperationIR],
    wire_order: dict[str, int],
) -> SemanticOperationIR:
    if block.original_collapsed_operation is not None:
        return block.original_collapsed_operation

    first_operation = operations[0]
    visible_label = _rounded_collapsed_block_label(block.label)
    target_wires = tuple(
        sorted(block.wire_ids, key=lambda wire_id: wire_order.get(wire_id, len(wire_order)))
    )
    return SemanticOperationIR(
        kind=OperationKind.GATE,
        name=block.label,
        label=visible_label,
        target_wires=target_wires,
        hover_details=(
            f"collapsed block: {block.label}",
            f"operations: {block.operation_count}",
        ),
        provenance=SemanticProvenanceIR(
            framework=first_operation.provenance.framework,
            native_name=block.label,
            native_kind="composite",
            composite_label=block.label,
            location=block.top_level_location,
        ),
        metadata={
            "collapsed_block": True,
            "compact_width": True,
            "suppress_target_annotations": True,
        },
    )


def _rounded_collapsed_block_label(label: str) -> str:
    return _COLLAPSED_LABEL_NUMBER_PATTERN.sub(_rounded_numeric_label_match, label)


def _rounded_numeric_label_match(match: re.Match[str]) -> str:
    value = float(match.group(0))
    if not math.isfinite(value):
        return match.group(0)
    rounded = f"{value:.3f}".rstrip("0").rstrip(".")
    if rounded == "-0":
        return "0"
    return rounded


def _visible_wire_ids(
    circuit: SemanticCircuitIR,
    *,
    wire_filter_mode: WireFilterMode,
    show_ancillas: bool,
) -> set[str]:
    used_wire_ids = {
        wire_id
        for operation in _flatten_operations(circuit)
        for wire_id in operation.occupied_wire_ids
    }
    visible_wire_ids = {
        wire.id
        for wire in circuit.all_wires
        if wire_filter_mode is WireFilterMode.ALL or wire.id in used_wire_ids
    }
    if show_ancillas:
        return visible_wire_ids

    filtered_wire_ids = {
        wire_id for wire_id in visible_wire_ids if not _is_ancilla_wire(circuit.wire_map[wire_id])
    }
    if filtered_wire_ids:
        return filtered_wire_ids
    return visible_wire_ids


def _is_ancilla_wire(wire: WireIR) -> bool:
    if wire.kind is not WireKind.QUANTUM:
        return False
    label = (wire.label or wire.id).strip().lower()
    return any(hint in label for hint in _ANCILLA_NAME_HINTS)


def _hidden_wire_ranges(
    *,
    all_wires: Sequence[WireIR],
    visible_wire_ids: set[str],
) -> tuple[ExplorationHiddenWireRange, ...]:
    ordered_visible_indexes = [
        index for index, wire in enumerate(all_wires) if wire.id in visible_wire_ids
    ]
    ranges: list[ExplorationHiddenWireRange] = []
    for left_index, right_index in zip(
        ordered_visible_indexes, ordered_visible_indexes[1:], strict=False
    ):
        if right_index - left_index <= 1:
            continue
        hidden_wire_ids = tuple(wire.id for wire in all_wires[left_index + 1 : right_index])
        if not hidden_wire_ids:
            continue
        ranges.append(
            ExplorationHiddenWireRange(
                before_wire_id=all_wires[left_index].id,
                after_wire_id=all_wires[right_index].id,
                hidden_wire_ids=hidden_wire_ids,
            )
        )
    return tuple(ranges)


def _group_highlight_operation_ids(
    circuit: SemanticCircuitIR,
    *,
    selected_operation_id: str | None,
) -> frozenset[str]:
    if selected_operation_id is None:
        return frozenset()

    operations = _flatten_operations(circuit)
    selected_operation = next(
        (
            operation
            for operation in operations
            if semantic_operation_id(operation) == selected_operation_id
        ),
        None,
    )
    if selected_operation is None:
        return frozenset()

    selected_group_key = _decomposition_group_key(selected_operation)
    if selected_group_key is None:
        return frozenset()

    return frozenset(
        semantic_operation_id(operation)
        for operation in operations
        if _decomposition_group_key(operation) == selected_group_key
    )


def _expanded_group_operation_ids(
    circuit: SemanticCircuitIR,
) -> frozenset[str]:
    operation_ids: set[str] = set()
    for operation in _flatten_operations(circuit):
        if _decomposition_group_key(operation) is None:
            continue
        operation_ids.add(semantic_operation_id(operation))
    return frozenset(operation_ids)


def _decomposition_group_key(
    operation: SemanticOperationIR,
) -> tuple[int, str] | None:
    if operation.metadata.get("collapsed_block") is True:
        return None
    location = operation.provenance.location
    composite_label = (
        operation.provenance.composite_label or operation.provenance.decomposition_origin
    )
    if location is None or len(location) < 2 or composite_label is None:
        return None
    return int(location[0]), composite_label


def _group_highlights_for_operation_ids(
    scene: LayoutScene,
    *,
    grouped_operation_ids: frozenset[str],
) -> tuple[SceneGroupHighlight, ...]:
    if not grouped_operation_ids:
        return ()

    bounds_by_operation_id: dict[str, list[float]] = {}
    connection_half_width = max(0.06, scene.style.control_radius * 0.6)

    for gate in scene.gates:
        _extend_group_bounds(
            bounds_by_operation_id,
            operation_id=gate.operation_id,
            grouped_operation_ids=grouped_operation_ids,
            column=gate.column,
            x_min=gate.x - (gate.width / 2.0),
            x_max=gate.x + (gate.width / 2.0),
            y_min=gate.y - (gate.height / 2.0),
            y_max=gate.y + (gate.height / 2.0),
        )
    for measurement in scene.measurements:
        _extend_group_bounds(
            bounds_by_operation_id,
            operation_id=measurement.operation_id,
            grouped_operation_ids=grouped_operation_ids,
            column=measurement.column,
            x_min=measurement.x - (measurement.width / 2.0),
            x_max=measurement.x + (measurement.width / 2.0),
            y_min=measurement.quantum_y - (measurement.height / 2.0),
            y_max=measurement.quantum_y + (measurement.height / 2.0),
        )
    for control in scene.controls:
        _extend_group_bounds(
            bounds_by_operation_id,
            operation_id=control.operation_id,
            grouped_operation_ids=grouped_operation_ids,
            column=control.column,
            x_min=control.x - scene.style.control_radius,
            x_max=control.x + scene.style.control_radius,
            y_min=control.y - scene.style.control_radius,
            y_max=control.y + scene.style.control_radius,
        )
    for swap in scene.swaps:
        _extend_group_bounds(
            bounds_by_operation_id,
            operation_id=swap.operation_id,
            grouped_operation_ids=grouped_operation_ids,
            column=swap.column,
            x_min=swap.x - swap.marker_size,
            x_max=swap.x + swap.marker_size,
            y_min=swap.y_top - swap.marker_size,
            y_max=swap.y_bottom + swap.marker_size,
        )
    for connection in scene.connections:
        _extend_group_bounds(
            bounds_by_operation_id,
            operation_id=connection.operation_id,
            grouped_operation_ids=grouped_operation_ids,
            column=connection.column,
            x_min=connection.x - connection_half_width,
            x_max=connection.x + connection_half_width,
            y_min=min(connection.y_start, connection.y_end),
            y_max=max(connection.y_start, connection.y_end),
        )

    x_padding = max(0.06, scene.style.gate_width * 0.08)
    y_padding = max(0.08, scene.style.gate_height * 0.1)
    highlights: list[SceneGroupHighlight] = []
    for bounds in bounds_by_operation_id.values():
        column, x_min, x_max, y_min, y_max = bounds
        highlights.append(
            SceneGroupHighlight(
                column=int(column),
                x=(x_min + x_max) / 2.0,
                y=(y_min + y_max) / 2.0,
                width=(x_max - x_min) + (x_padding * 2.0),
                height=(y_max - y_min) + (y_padding * 2.0),
                visual_state=SceneVisualState.HIGHLIGHTED,
            )
        )
    return tuple(sorted(highlights, key=lambda highlight: (highlight.column, highlight.x)))


def _extend_group_bounds(
    bounds_by_operation_id: dict[str, list[float]],
    *,
    operation_id: str | None,
    grouped_operation_ids: frozenset[str],
    column: int,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    if operation_id is None or operation_id not in grouped_operation_ids:
        return

    bounds = bounds_by_operation_id.get(operation_id)
    if bounds is None:
        bounds_by_operation_id[operation_id] = [
            float(column),
            float(x_min),
            float(x_max),
            float(y_min),
            float(y_max),
        ]
        return

    bounds[1] = min(bounds[1], float(x_min))
    bounds[2] = max(bounds[2], float(x_max))
    bounds[3] = min(bounds[3], float(y_min))
    bounds[4] = max(bounds[4], float(y_max))


def _initial_collapsed_block_ids(
    *,
    current_semantic_ir: SemanticCircuitIR,
    blocks: dict[str, ExplorationBlock],
) -> frozenset[str]:
    collapsed_ids = {
        semantic_operation_id(operation)
        for operation in _flatten_operations(current_semantic_ir)
        if semantic_operation_id(operation) in blocks
    }
    return frozenset(collapsed_ids)


def _operations_by_top_level_location(
    circuit: SemanticCircuitIR,
) -> tuple[tuple[tuple[int, ...], tuple[SemanticOperationIR, ...]], ...]:
    grouped_operations: dict[tuple[int, ...], list[tuple[int, SemanticOperationIR]]] = {}
    for encounter_index, operation in enumerate(_flatten_operations(circuit)):
        grouped_operations.setdefault(_top_level_location(operation), []).append(
            (encounter_index, operation)
        )

    ordered_locations = sorted(
        grouped_operations,
        key=lambda location: _top_level_location_sort_key(
            location,
            grouped_operations[location],
        ),
    )
    return tuple(
        (
            location,
            tuple(
                operation
                for _, operation in sorted(
                    grouped_operations[location],
                    key=_grouped_operation_sort_key,
                )
            ),
        )
        for location in ordered_locations
    )


def _top_level_operation_groups(
    circuit: SemanticCircuitIR,
) -> tuple[tuple[tuple[int, ...], tuple[SemanticOperationIR, ...]], ...]:
    grouped_operations: dict[
        tuple[tuple[int, tuple[int, ...]], tuple[int, ...]],
        list[tuple[int, SemanticOperationIR]],
    ] = {}
    for encounter_index, operation in enumerate(_flatten_operations(circuit)):
        top_level_location = _top_level_location(operation)
        order_key = _operation_top_level_order_key(operation, encounter_index)
        grouped_operations.setdefault((order_key, top_level_location), []).append(
            (encounter_index, operation)
        )

    return tuple(
        (
            top_level_location,
            tuple(
                operation for _, operation in sorted(operations, key=_grouped_operation_sort_key)
            ),
        )
        for _, top_level_location, operations in (
            (*group_key, grouped_operations[group_key]) for group_key in sorted(grouped_operations)
        )
    )


def _top_level_location(operation: SemanticOperationIR) -> tuple[int, ...]:
    if not operation.provenance.location:
        return ()
    return (operation.provenance.location[0],)


def _top_level_location_sort_key(
    location: tuple[int, ...],
    operations: Sequence[tuple[int, SemanticOperationIR]],
) -> tuple[int, tuple[int, ...]]:
    return _top_level_location_order_key(location, operations[0][0])


def _operation_top_level_order_key(
    operation: SemanticOperationIR,
    encounter_index: int,
) -> tuple[int, tuple[int, ...]]:
    if _is_terminal_output_operation(operation):
        location = operation.provenance.location or (encounter_index,)
        return (2, location)
    return _top_level_location_order_key(_top_level_location(operation), encounter_index)


def _top_level_location_order_key(
    location: tuple[int, ...],
    fallback_index: int,
) -> tuple[int, tuple[int, ...]]:
    if location:
        return (0, location)
    return (1, (fallback_index,))


def _grouped_operation_sort_key(
    entry: tuple[int, SemanticOperationIR],
) -> tuple[int, tuple[int, ...]]:
    encounter_index, operation = entry
    if operation.provenance.location:
        return (0, operation.provenance.location)
    return (1, (encounter_index,))


def _is_terminal_output_operation(operation: SemanticOperationIR) -> bool:
    if operation.metadata.get("pennylane_terminal_kind") in {"probs", "expval", "counts"}:
        return True
    return operation.provenance.native_kind in {"probs", "expval", "counts"}


def _collapse_label(operations: Sequence[SemanticOperationIR]) -> str | None:
    if not operations:
        return None
    if not any(len(operation.provenance.location) > 1 for operation in operations):
        return None
    for operation in operations:
        for candidate in (
            operation.provenance.composite_label,
            operation.provenance.decomposition_origin,
            operation.provenance.native_name,
        ):
            if candidate:
                return candidate
    return None


def _flatten_operations(circuit: SemanticCircuitIR) -> tuple[SemanticOperationIR, ...]:
    return tuple(operation for layer in circuit.layers for operation in layer.operations)


def _neighbor_operation(
    operations: Sequence[SemanticOperationIR],
    *,
    start_index: int,
    step: int,
    wire_ids: set[str],
) -> SemanticOperationIR | None:
    index = start_index
    while 0 <= index < len(operations):
        operation = operations[index]
        if wire_ids.intersection(operation.occupied_wire_ids):
            return operation
        index += step
    return None


def _with_operation_visual_state(
    item: _SceneOperationVisualItem,
    *,
    selected_operation_id: str | None,
    emphasized_operation_ids: set[str],
    operation_ids: set[str],
) -> _SceneOperationVisualItem:
    operation_id = getattr(item, "operation_id", None)
    if operation_id is None or operation_id not in operation_ids:
        return item
    if operation_id in emphasized_operation_ids:
        if operation_id == selected_operation_id:
            state = SceneVisualState.HIGHLIGHTED
        else:
            state = SceneVisualState.RELATED
    else:
        state = SceneVisualState.DIMMED
    return replace(item, visual_state=state)


def _with_operation_visual_state_3d(
    item: _SceneOperationVisualItem3D,
    *,
    selected_operation_id: str | None,
    emphasized_operation_ids: set[str],
    operation_ids: set[str],
) -> _SceneOperationVisualItem3D:
    operation_id = getattr(item, "operation_id", None)
    if operation_id is None or operation_id not in operation_ids:
        default_state = (
            SceneVisualState.DIMMED
            if selected_operation_id is not None and getattr(item, "column", -1) >= 0
            else SceneVisualState.DEFAULT
        )
        return replace(item, visual_state=default_state)
    if operation_id in emphasized_operation_ids:
        if operation_id == selected_operation_id:
            state = SceneVisualState.HIGHLIGHTED
        else:
            state = SceneVisualState.RELATED
    else:
        state = SceneVisualState.DIMMED
    return replace(item, visual_state=state)


def _with_text_visual_state_3d(
    text: SceneText3D,
    *,
    selected_operation_id: str | None,
    emphasized_operation_ids: set[str],
    operation_ids: set[str],
    selected_wire_ids: set[str],
) -> SceneText3D:
    if text.operation_id is not None:
        return _with_operation_visual_state_3d(
            text,
            selected_operation_id=selected_operation_id,
            emphasized_operation_ids=emphasized_operation_ids,
            operation_ids=operation_ids,
        )
    if text.wire_id is not None and selected_operation_id is not None:
        return replace(
            text,
            visual_state=(
                SceneVisualState.HIGHLIGHTED
                if text.wire_id in selected_wire_ids
                else SceneVisualState.DIMMED
            ),
        )
    return replace(text, visual_state=SceneVisualState.DEFAULT)


def _hidden_wire_marker_text(hidden_wire_count: int) -> str:
    noun = "wire" if hidden_wire_count == 1 else "wires"
    return f"... {hidden_wire_count} hidden {noun} ..."
