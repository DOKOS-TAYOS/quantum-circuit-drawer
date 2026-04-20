"""Managed slider facade for 2D and 3D rendering."""

from __future__ import annotations

from .controls import (
    apply_managed_3d_axes_bounds,
    managed_3d_axes_bounds,
    managed_3d_menu_bounds,
)
from .slider_2d import (
    _DEFAULT_VISIBLE_QUBITS,
    Managed2DPageSliderState,
    Managed2DSliderLayout,
    _visible_qubits_viewport_height,
    configure_page_slider,
    page_slider_figsize,
    prepare_page_slider_layout,
    set_slider_view,
    slider_viewport_height,
    slider_viewport_size,
    slider_viewport_width,
)
from .slider_2d_windowing import _horizontal_scene_for_start_column
from .slider_3d import (
    Managed3DPageSliderState,
    circuit_window,
    configure_3d_page_slider,
    page_slider_window_size,
)

__all__ = [
    "_DEFAULT_VISIBLE_QUBITS",
    "_horizontal_scene_for_start_column",
    "_visible_qubits_viewport_height",
    "Managed2DPageSliderState",
    "Managed2DSliderLayout",
    "Managed3DPageSliderState",
    "apply_managed_3d_axes_bounds",
    "circuit_window",
    "configure_3d_page_slider",
    "configure_page_slider",
    "managed_3d_axes_bounds",
    "managed_3d_menu_bounds",
    "page_slider_figsize",
    "page_slider_window_size",
    "prepare_page_slider_layout",
    "set_slider_view",
    "slider_viewport_height",
    "slider_viewport_size",
    "slider_viewport_width",
]
