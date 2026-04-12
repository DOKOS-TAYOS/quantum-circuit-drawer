"""3D scene models for topology-aware circuit rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..ir.operations import OperationKind
from ..ir.wires import WireKind
from ..style import DrawStyle
from .topology_3d import Topology3D


class GateRenderStyle3D(StrEnum):
    """Canonical render styles for 3D gates."""

    BOX = "box"
    X_TARGET = "x_target"
    MEASUREMENT = "measurement"


class MarkerStyle3D(StrEnum):
    """Marker styles used by the 3D renderer."""

    CONTROL = "control"
    SWAP = "swap"
    TOPOLOGY_NODE = "topology_node"


class ConnectionRenderStyle3D(StrEnum):
    """Canonical line styles used by the 3D renderer."""

    STANDARD = "standard"
    CONTROL = "control"
    TOPOLOGY_EDGE = "topology_edge"


@dataclass(frozen=True, slots=True)
class Point3D:
    """Simple typed 3D point."""

    x: float
    y: float
    z: float


@dataclass(slots=True)
class SceneWire3D:
    id: str
    label: str
    kind: WireKind
    start: Point3D
    end: Point3D
    double_line: bool = False
    hover_text: str | None = None


@dataclass(slots=True)
class SceneConnection3D:
    column: int
    points: tuple[Point3D, ...]
    is_classical: bool = False
    double_line: bool = False
    render_style: ConnectionRenderStyle3D = ConnectionRenderStyle3D.STANDARD
    arrow_at_end: bool = False
    label: str | None = None
    hover_text: str | None = None


@dataclass(slots=True)
class SceneTopologyPlane3D:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z: float
    color: str
    alpha: float


@dataclass(slots=True)
class SceneGate3D:
    column: int
    center: Point3D
    size_x: float
    size_y: float
    size_z: float
    label: str
    subtitle: str | None
    kind: OperationKind
    render_style: GateRenderStyle3D = GateRenderStyle3D.BOX
    hover_text: str | None = None
    target_positions: tuple[Point3D, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class SceneMarker3D:
    column: int
    center: Point3D
    style: MarkerStyle3D
    size: float


@dataclass(slots=True)
class SceneText3D:
    position: Point3D
    text: str
    ha: str = "center"
    va: str = "center"
    font_size: float | None = None


@dataclass(slots=True)
class LayoutScene3D:
    width: float
    height: float
    depth: float
    style: DrawStyle
    topology: Topology3D
    wires: tuple[SceneWire3D, ...]
    gates: tuple[SceneGate3D, ...]
    markers: tuple[SceneMarker3D, ...]
    connections: tuple[SceneConnection3D, ...]
    topology_planes: tuple[SceneTopologyPlane3D, ...]
    texts: tuple[SceneText3D, ...]
    hover_enabled: bool
    quantum_wire_positions: dict[str, Point3D]
    classical_wire_positions: dict[str, Point3D]
    classical_plane_y: float
