"""Managed Matplotlib rendering internals."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .drawing import render_draw_pipeline_on_axes, render_managed_draw_pipeline

__all__ = [
    "render_draw_pipeline_on_axes",
    "render_managed_draw_pipeline",
]


def __getattr__(name: str) -> object:
    if name in {"render_draw_pipeline_on_axes", "render_managed_draw_pipeline"}:
        from .drawing import render_draw_pipeline_on_axes, render_managed_draw_pipeline

        return {
            "render_draw_pipeline_on_axes": render_draw_pipeline_on_axes,
            "render_managed_draw_pipeline": render_managed_draw_pipeline,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
