"""Backend-neutral layout scene models."""

from __future__ import annotations

from dataclasses import dataclass, field

from .._compat import StrEnum
from ..hover import HoverOptions
from ..ir.operations import OperationKind
from ..ir.wires import WireKind
from ..style import DrawStyle


class GateRenderStyle(StrEnum):
    """Canonical visual styles for scene gates."""

    BOX = "box"
    X_TARGET = "x_target"


class SceneVisualState(StrEnum):
    """Visual emphasis state applied to interactive 2D scene elements."""

    DEFAULT = "default"
    HIGHLIGHTED = "highlighted"
    RELATED = "related"
    DIMMED = "dimmed"


@dataclass(frozen=True, slots=True)
class SceneHoverData:
    """Interactive hover payload shared across the artists of one operation."""

    key: str
    name: str
    qubit_labels: tuple[str, ...]
    other_wire_labels: tuple[str, ...]
    matrix: object | None
    matrix_dimension: int | None
    gate_x: float
    gate_y: float
    gate_width: float
    gate_height: float
    details: tuple[str, ...] = ()


@dataclass(slots=True)
class SceneWire:
    id: str
    label: str
    kind: WireKind
    y: float
    x_start: float
    x_end: float
    bundle_size: int = 1
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneGate:
    column: int
    x: float
    y: float
    width: float
    height: float
    label: str
    subtitle: str | None
    kind: OperationKind
    render_style: GateRenderStyle = GateRenderStyle.BOX
    hover_data: SceneHoverData | None = None
    operation_id: str | None = None
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneGateAnnotation:
    column: int
    x: float
    y: float
    text: str
    font_size: float
    operation_id: str | None = None
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneControl:
    column: int
    x: float
    y: float
    state: int = 1
    hover_data: SceneHoverData | None = None
    operation_id: str | None = None
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneConnection:
    column: int
    x: float
    y_start: float
    y_end: float
    is_classical: bool = False
    double_line: bool = False
    linestyle: str = "solid"
    arrow_at_end: bool = False
    label: str | None = None
    hover_data: SceneHoverData | None = None
    operation_id: str | None = None
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneSwap:
    column: int
    x: float
    y_top: float
    y_bottom: float
    marker_size: float
    hover_data: SceneHoverData | None = None
    operation_id: str | None = None
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneBarrier:
    column: int
    x: float
    y_top: float
    y_bottom: float
    operation_id: str | None = None
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneMeasurement:
    column: int
    x: float
    quantum_y: float
    classical_y: float | None
    width: float
    height: float
    label: str
    connector_x: float
    connector_y: float
    hover_data: SceneHoverData | None = None
    operation_id: str | None = None
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneText:
    x: float
    y: float
    text: str
    ha: str = "center"
    va: str = "center"
    font_size: float | None = None
    wire_id: str | None = None
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class SceneWireFoldMarker:
    x: float
    y: float
    hidden_wire_count: int
    text: str
    visual_state: SceneVisualState = SceneVisualState.DEFAULT


@dataclass(slots=True)
class ScenePage:
    index: int
    start_column: int
    end_column: int
    content_x_start: float
    content_x_end: float
    content_width: float
    y_offset: float


@dataclass(slots=True)
class LayoutScene:
    width: float
    height: float
    page_height: float
    style: DrawStyle
    wires: tuple[SceneWire, ...]
    gates: tuple[SceneGate, ...]
    gate_annotations: tuple[SceneGateAnnotation, ...]
    controls: tuple[SceneControl, ...]
    connections: tuple[SceneConnection, ...]
    swaps: tuple[SceneSwap, ...]
    barriers: tuple[SceneBarrier, ...]
    measurements: tuple[SceneMeasurement, ...]
    texts: tuple[SceneText, ...]
    wire_fold_markers: tuple[SceneWireFoldMarker, ...]
    pages: tuple[ScenePage, ...]
    hover: HoverOptions = field(default_factory=lambda: HoverOptions(enabled=False))
    wire_y_positions: dict[str, float] = field(default_factory=dict)
    page_count_for_text_scale: int | None = None
