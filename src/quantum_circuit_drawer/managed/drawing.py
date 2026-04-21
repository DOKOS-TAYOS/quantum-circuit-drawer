"""Compatibility facade for managed drawing helpers."""

from __future__ import annotations

from . import page_window as _page_window
from . import rendering as _rendering
from . import slider_2d as _slider_2d
from . import slider_2d_windowing as _slider_2d_windowing
from . import slider_3d as _slider_3d
from . import viewport as _viewport
from . import zoom as _zoom
from .controls import apply_managed_3d_axes_bounds, managed_3d_axes_bounds, managed_3d_menu_bounds
from .rendering import render_draw_pipeline_on_axes, render_managed_draw_pipeline
from .viewport import page_window_adaptive_paged_scene
from .zoom import configure_zoom_text_scaling

_SOURCE_MODULES = (
    _rendering,
    _viewport,
    _slider_2d,
    _slider_2d_windowing,
    _slider_3d,
    _page_window,
    _zoom,
)

__all__ = [
    "apply_managed_3d_axes_bounds",
    "configure_zoom_text_scaling",
    "managed_3d_axes_bounds",
    "managed_3d_menu_bounds",
    "page_window_adaptive_paged_scene",
    "render_draw_pipeline_on_axes",
    "render_managed_draw_pipeline",
]

for _source_module in _SOURCE_MODULES:
    for _name in dir(_source_module):
        if _name.startswith("__"):
            continue
        globals()[_name] = getattr(_source_module, _name)
        if _name not in __all__:
            __all__.append(_name)

__all__.sort()
