"""Display-axes lifecycle and rerender helpers for managed 3D page windows."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ..renderers._matplotlib_figure import clear_hover_state
from ..renderers.matplotlib_renderer_3d import _MANAGED_3D_VIEWPORT_BOUNDS_ATTR
from .view_state_3d import (
    _MANAGED_3D_FIXED_VIEW_STATE_ATTR,
    Managed3DFixedViewState,
    capture_managed_3d_view_state,
)

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from ..layout.scene_3d import LayoutScene3D
    from .page_window_3d import Managed3DPageWindowState

_DISPLAY_AREA_LEFT = 0.02
_DISPLAY_AREA_BOTTOM = 0.18
_DISPLAY_AREA_WIDTH = 0.96
_DISPLAY_AREA_HEIGHT = 0.8
_DISPLAY_AXES_VERTICAL_GAP = 0.02


def _render_current_window(state: Managed3DPageWindowState) -> None:
    state.figure.patch.set_facecolor(state.current_scene.style.theme.figure_facecolor)
    fixed_view_state = _capture_shared_view_state(state)
    display_axes = _ensure_display_axes(
        state,
        fixed_view_state=fixed_view_state,
    )
    for axes, page_scene in zip(display_axes, _visible_page_scenes(state), strict=True):
        clear_hover_state(axes)
        axes.clear()
        bounds = cast(
            "tuple[float, float, float, float]",
            getattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR),
        )
        axes.set_position(bounds)
        if fixed_view_state is not None:
            setattr(axes, _MANAGED_3D_FIXED_VIEW_STATE_ATTR, fixed_view_state)
        state.pipeline.renderer.render(page_scene, ax=axes)

    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


def _capture_shared_view_state(
    state: Managed3DPageWindowState,
) -> Managed3DFixedViewState | None:
    if not state.display_axes:
        return None
    return capture_managed_3d_view_state(state.display_axes[0])


def _ensure_display_axes(
    state: Managed3DPageWindowState,
    *,
    fixed_view_state: Managed3DFixedViewState | None,
) -> tuple[Axes3D, ...]:
    target_bounds = _display_axes_bounds(state.visible_page_count)
    current_axes = list(state.display_axes or (state.base_axes,))

    while len(current_axes) < state.visible_page_count:
        current_axes.append(
            cast(
                "Axes3D",
                state.figure.add_axes((0.0, 0.0, 1.0, 1.0), projection="3d"),
            )
        )

    for axes in current_axes[state.visible_page_count :]:
        clear_hover_state(axes)
        _disconnect_removed_3d_axes_callbacks(axes)
        axes.remove()

    display_axes = tuple(current_axes[: state.visible_page_count])
    for axes, bounds in zip(display_axes, target_bounds, strict=True):
        axes.set_position(bounds)
        setattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, bounds)
        if fixed_view_state is not None:
            setattr(axes, _MANAGED_3D_FIXED_VIEW_STATE_ATTR, fixed_view_state)

    state.display_axes = display_axes
    return display_axes


def _disconnect_removed_3d_axes_callbacks(axes: Axes3D) -> None:
    canvas = getattr(axes.figure, "canvas", None)
    callbacks = getattr(canvas, "callbacks", None)
    registry = getattr(callbacks, "callbacks", None)
    if canvas is None or callbacks is None or not isinstance(registry, dict):
        return

    for signal_name in ("motion_notify_event", "button_press_event", "button_release_event"):
        signal_callbacks = registry.get(signal_name, {})
        for callback_id, callback_proxy in tuple(signal_callbacks.items()):
            callback = callback_proxy()
            if callback is None:
                continue
            if getattr(callback, "__self__", None) is axes:
                callbacks.disconnect(callback_id)


def _visible_page_scenes(state: Managed3DPageWindowState) -> tuple[LayoutScene3D, ...]:
    end_page = state.start_page + state.visible_page_count
    return state.page_scenes[state.start_page : end_page]


def _display_axes_bounds(
    visible_page_count: int,
) -> tuple[tuple[float, float, float, float], ...]:
    if visible_page_count <= 1:
        return (
            (_DISPLAY_AREA_LEFT, _DISPLAY_AREA_BOTTOM, _DISPLAY_AREA_WIDTH, _DISPLAY_AREA_HEIGHT),
        )

    total_gap = _DISPLAY_AXES_VERTICAL_GAP * (visible_page_count - 1)
    axes_height = (_DISPLAY_AREA_HEIGHT - total_gap) / float(visible_page_count)
    bounds: list[tuple[float, float, float, float]] = []
    for window_index in range(visible_page_count):
        bottom = _DISPLAY_AREA_BOTTOM + (
            (visible_page_count - window_index - 1) * (axes_height + _DISPLAY_AXES_VERTICAL_GAP)
        )
        bounds.append((_DISPLAY_AREA_LEFT, bottom, _DISPLAY_AREA_WIDTH, axes_height))
    return tuple(bounds)
