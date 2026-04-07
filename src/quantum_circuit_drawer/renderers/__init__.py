"""Lazy renderer exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseRenderer
    from .matplotlib_renderer import MatplotlibRenderer
    from .matplotlib_renderer_3d import MatplotlibRenderer3D

__all__ = ["BaseRenderer", "MatplotlibRenderer", "MatplotlibRenderer3D"]


def __getattr__(name: str) -> object:
    if name == "BaseRenderer":
        from .base import BaseRenderer

        return BaseRenderer
    if name == "MatplotlibRenderer":
        from .matplotlib_renderer import MatplotlibRenderer

        return MatplotlibRenderer
    if name == "MatplotlibRenderer3D":
        from .matplotlib_renderer_3d import MatplotlibRenderer3D

        return MatplotlibRenderer3D
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
