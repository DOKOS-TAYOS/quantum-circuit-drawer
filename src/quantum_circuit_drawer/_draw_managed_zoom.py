"""Zoom-aware text scaling helpers for managed 2D rendering."""

from __future__ import annotations

import math
from collections.abc import Callable

from matplotlib.axes import Axes
from matplotlib.backend_bases import Event
from matplotlib.text import Annotation

from .layout.scene import LayoutScene


def configure_zoom_text_scaling(axes: Axes, *, scene: LayoutScene) -> None:
    """Attach zoom-responsive text scaling to the provided 2D axes."""

    from .renderers._matplotlib_figure import (
        TextScalingState,
        get_base_font_size,
        get_gate_text_metadata,
        get_text_scaling_state,
        set_base_font_size,
        set_text_scaling_state,
    )
    from .renderers.matplotlib_primitives import (
        _build_gate_text_fitting_context,
        _fit_gate_text_font_size_with_context,
        _multiline_text_line_spacing,
    )

    base_view_width, base_view_height = current_view_size(axes)
    if base_view_width <= 0.0 or base_view_height <= 0.0:
        return
    if not axes.texts:
        return
    base_gate_text_context = _build_gate_text_fitting_context(axes, scene)

    state = get_text_scaling_state(axes)
    if state is None:
        for text_artist in axes.texts:
            set_base_font_size(
                text_artist,
                _coerce_font_size(text_artist.get_fontsize(), default=scene.style.font_size),
            )
        state = TextScalingState(
            base_view_width=base_view_width,
            base_view_height=base_view_height,
            scene=scene,
            base_points_per_layout_unit=base_gate_text_context.points_per_layout_unit,
            last_points_per_layout_unit=base_gate_text_context.points_per_layout_unit,
        )
        set_text_scaling_state(axes, state)
        canvas = axes.figure.canvas

        def apply_text_scale(*, request_redraw: bool) -> None:
            current_state = get_text_scaling_state(axes)
            if current_state is None or current_state is not state or state.is_updating:
                return

            scale_factor = current_text_scale(axes, state)
            gate_text_context = _build_gate_text_fitting_context(axes, current_state.scene)
            points_per_layout_unit = gate_text_context.points_per_layout_unit
            text_fit_cache: dict[tuple[object, float, float], float] = {}

            if math.isclose(
                scale_factor,
                state.last_scale_factor,
                rel_tol=1e-6,
                abs_tol=1e-6,
            ) and math.isclose(
                points_per_layout_unit,
                state.last_points_per_layout_unit,
                rel_tol=1e-6,
                abs_tol=1e-6,
            ):
                return

            state.is_updating = True
            try:
                for text_artist in axes.texts:
                    gate_text_metadata = get_gate_text_metadata(text_artist)
                    if gate_text_metadata is None:
                        if isinstance(text_artist, Annotation):
                            continue
                        base_font_size = get_base_font_size(
                            text_artist,
                            default=_coerce_font_size(
                                text_artist.get_fontsize(),
                                default=scene.style.font_size,
                            ),
                        )
                        _apply_text_artist_scale(
                            text_artist,
                            font_size=base_font_size * scale_factor,
                            multiline_line_spacing=_multiline_text_line_spacing,
                        )
                        continue
                    base_font_size = get_base_font_size(
                        text_artist,
                        default=_coerce_font_size(
                            text_artist.get_fontsize(),
                            default=scene.style.font_size,
                        ),
                    )
                    _apply_text_artist_scale(
                        text_artist,
                        font_size=_fit_gate_text_font_size_with_context(
                            context=gate_text_context,
                            width=gate_text_metadata.gate_width,
                            height=gate_text_metadata.gate_height,
                            text=text_artist.get_text(),
                            default_font_size=base_font_size,
                            height_fraction=gate_text_metadata.height_fraction,
                            max_font_size=base_font_size * scale_factor,
                            cache=text_fit_cache,
                        ),
                        multiline_line_spacing=_multiline_text_line_spacing,
                    )
                state.last_scale_factor = scale_factor
                state.last_points_per_layout_unit = points_per_layout_unit
                state.update_queued = False
            finally:
                state.is_updating = False

            if request_redraw and canvas is not None:
                canvas.draw_idle()

        def update_text_scale_on_limits_change(_axes: Axes) -> None:
            apply_text_scale(request_redraw=canvas is not None)

        if canvas is not None:

            def redraw_text_scale(_event: Event) -> None:
                apply_text_scale(request_redraw=False)

            state.draw_callback_id = canvas.mpl_connect("draw_event", redraw_text_scale)

        state.xlim_callback_id = axes.callbacks.connect(
            "xlim_changed",
            update_text_scale_on_limits_change,
        )
        state.ylim_callback_id = axes.callbacks.connect(
            "ylim_changed",
            update_text_scale_on_limits_change,
        )
        return

    for text_artist in axes.texts:
        if not hasattr(text_artist, "_quantum_circuit_drawer_base_font_size"):
            set_base_font_size(
                text_artist,
                _coerce_font_size(text_artist.get_fontsize(), default=scene.style.font_size),
            )
    state.base_view_width = base_view_width
    state.base_view_height = base_view_height
    state.scene = scene
    state.base_points_per_layout_unit = base_gate_text_context.points_per_layout_unit
    state.last_scale_factor = 1.0
    state.last_points_per_layout_unit = base_gate_text_context.points_per_layout_unit
    state.update_queued = False


def current_view_size(axes: Axes) -> tuple[float, float]:
    """Return the current visible data window for the axes."""

    x_limits = axes.get_xlim()
    y_limits = axes.get_ylim()
    return abs(x_limits[1] - x_limits[0]), abs(y_limits[1] - y_limits[0])


def current_text_scale(axes: Axes, state: object) -> float:
    """Return the current zoom scale factor for 2D text."""

    from .renderers._matplotlib_figure import TextScalingState

    if not isinstance(state, TextScalingState):
        return 1.0

    current_view_width, current_view_height = current_view_size(axes)
    if current_view_width <= 0.0 or current_view_height <= 0.0:
        return 1.0

    scale_x = state.base_view_width / current_view_width
    scale_y = state.base_view_height / current_view_height
    return max(scale_x, scale_y)


def _coerce_font_size(font_size: float | str, *, default: float) -> float:
    if isinstance(font_size, int | float):
        return float(font_size)
    return default


def _apply_text_artist_scale(
    text_artist: object,
    *,
    font_size: float,
    multiline_line_spacing: Callable[[float], float],
) -> None:
    text_artist.set_fontsize(font_size)
    if "\n" not in text_artist.get_text() or not hasattr(text_artist, "set_linespacing"):
        return
    text_artist.set_linespacing(multiline_line_spacing(font_size))
