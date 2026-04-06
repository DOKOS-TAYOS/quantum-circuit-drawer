"""Renderer interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from matplotlib.axes import Axes

from ..layout.scene import LayoutScene
from ..layout.scene_3d import LayoutScene3D
from ..typing import OutputPath, RenderResult


class BaseRenderer(ABC):
    """Backend renderer contract."""

    backend_name: str

    @abstractmethod
    def render(
        self,
        scene: LayoutScene | LayoutScene3D,
        *,
        ax: Axes | None = None,
        output: OutputPath | None = None,
    ) -> RenderResult:
        """Render a layout scene."""
