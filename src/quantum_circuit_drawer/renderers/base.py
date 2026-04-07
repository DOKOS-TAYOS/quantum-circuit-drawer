"""Renderer interfaces used by the drawing pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod

from matplotlib.axes import Axes

from ..layout.scene import LayoutScene
from ..layout.scene_3d import LayoutScene3D
from ..typing import OutputPath, RenderResult


class BaseRenderer(ABC):
    """Backend renderer contract for 2D and 3D layout scenes."""

    backend_name: str

    @abstractmethod
    def render(
        self,
        scene: LayoutScene | LayoutScene3D,
        *,
        ax: Axes | None = None,
        output: OutputPath | None = None,
    ) -> RenderResult:
        """Render a layout scene to a managed figure or caller-owned axes.

        Implementations return ``(figure, axes)`` when they create the figure
        themselves, or the same axes object when rendering into ``ax``.
        """
