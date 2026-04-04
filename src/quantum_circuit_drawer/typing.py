"""Shared typing helpers."""

from __future__ import annotations

from os import PathLike
from typing import TYPE_CHECKING, Protocol, TypeAlias

from matplotlib.axes import Axes
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .style import DrawStyle

Metadata: TypeAlias = dict[str, object]
OutputPath: TypeAlias = str | PathLike[str]
RenderResult: TypeAlias = tuple[Figure, Axes] | Axes


class LayoutEngineLike(Protocol):
    """Protocol for layout engines accepted by the public API."""

    def compute(self, circuit: CircuitIR, style: DrawStyle) -> LayoutScene:
        """Compute a drawable scene from a circuit IR and validated style."""
