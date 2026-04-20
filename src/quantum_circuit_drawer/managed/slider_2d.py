"""Focused namespace for managed 2D slider types and helpers."""

from __future__ import annotations

from .slider import (
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

__all__ = [
    "_DEFAULT_VISIBLE_QUBITS",
    "_visible_qubits_viewport_height",
    "Managed2DPageSliderState",
    "Managed2DSliderLayout",
    "configure_page_slider",
    "page_slider_figsize",
    "prepare_page_slider_layout",
    "set_slider_view",
    "slider_viewport_height",
    "slider_viewport_size",
    "slider_viewport_width",
]
