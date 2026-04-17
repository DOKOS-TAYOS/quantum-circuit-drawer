"""Shared type aliases and public protocol definitions."""

from __future__ import annotations

from os import PathLike
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D
    from .layout.topology_3d import TopologyName
    from .style import DrawStyle
else:
    Axes = Any
    Figure = Any

Metadata: TypeAlias = dict[str, object]
OutputPath: TypeAlias = str | PathLike[str]
RenderResult: TypeAlias = tuple[Figure, Axes] | Axes


class LayoutEngineLike(Protocol):
    """Protocol for custom 2D layout engines accepted by the public API."""

    def compute(self, circuit: CircuitIR, style: DrawStyle) -> LayoutScene:
        """Compute a 2D drawable scene from circuit IR and validated style."""


class _NormalizedLayoutEngineLike(Protocol):
    """Private protocol for built-in layout engines with normalized-style fast paths."""

    def _compute_with_normalized_style(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        hover_enabled: bool = True,
    ) -> LayoutScene:
        """Compute a 2D drawable scene from already-normalized style."""


class LayoutEngine3DLike(Protocol):
    """Protocol for custom 3D layout engines accepted by the public API."""

    def compute(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        topology_name: TopologyName,
        direct: bool,
        hover_enabled: bool,
    ) -> LayoutScene3D:
        """Compute a 3D drawable scene from circuit IR and validated style."""


class _NormalizedLayoutEngine3DLike(Protocol):
    """Private protocol for built-in 3D layout engines with normalized-style fast paths."""

    def _compute_with_normalized_style(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        topology_name: TopologyName,
        direct: bool,
        hover_enabled: bool,
    ) -> LayoutScene3D:
        """Compute a 3D drawable scene from already-normalized style."""
