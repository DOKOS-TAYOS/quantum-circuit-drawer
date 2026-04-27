"""Managed-figure rendering helpers for the public drawing API."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeGuard, cast

from ..drawing.pipeline import PreparedDrawPipeline
from ..style import DrawStyle
from ..typing import LayoutEngineLike, OutputPath
from ._render_pipeline import render_draw_pipeline_on_axes as _render_draw_pipeline_on_axes_impl
from ._render_pipeline import render_managed_draw_pipeline as _render_managed_draw_pipeline_impl
from .controls import apply_managed_3d_axes_bounds as _apply_managed_3d_axes_bounds_impl
from .page_window import configure_page_window as _configure_page_window_impl
from .slider_2d import configure_page_slider as _configure_page_slider_impl
from .slider_2d import page_slider_figsize as _page_slider_figsize_impl
from .slider_2d import prepare_page_slider_layout as _prepare_page_slider_layout_impl
from .slider_2d import set_slider_view as _set_slider_view_impl
from .slider_2d import slider_viewport_height as _slider_viewport_height_impl
from .slider_2d import slider_viewport_width as _slider_viewport_width_impl
from .slider_3d import configure_3d_page_slider as _configure_3d_page_slider_impl
from .viewport import axes_viewport_pixels as _axes_viewport_pixels_impl
from .viewport import axes_viewport_ratio as _axes_viewport_ratio_impl
from .viewport import build_continuous_slider_scene as _build_continuous_slider_scene_impl
from .viewport import compute_paged_scene as _compute_paged_scene_impl
from .viewport import page_window_adaptive_paged_scene as _page_window_adaptive_paged_scene_impl
from .viewport import scene_aspect_ratio as _scene_aspect_ratio_impl
from .viewport import viewport_adaptive_paged_scene as _viewport_adaptive_paged_scene_impl
from .viewport import viewport_scene_score as _viewport_scene_score_impl
from .zoom import configure_zoom_text_scaling as _configure_zoom_text_scaling_impl
from .zoom import current_text_scale as _current_text_scale_impl
from .zoom import current_view_size as _current_view_size_impl

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..ir.circuit import CircuitIR
    from ..ir.semantic import SemanticCircuitIR
    from ..layout.scene import LayoutScene
    from ..layout.scene_3d import LayoutScene3D
    from ..renderers.matplotlib_renderer import MatplotlibRenderer
    from .slider_2d import Managed2DSliderLayout

_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"

__all__ = [
    "_MANAGED_3D_VIEWPORT_BOUNDS_ATTR",
    "apply_managed_3d_axes_bounds",
    "axes_viewport_pixels",
    "axes_viewport_ratio",
    "build_continuous_slider_scene",
    "compute_paged_scene",
    "configure_3d_page_slider",
    "configure_page_slider",
    "configure_page_window",
    "configure_zoom_text_scaling",
    "current_text_scale",
    "current_view_size",
    "is_3d_axes",
    "is_3d_scene",
    "page_slider_figsize",
    "page_window_adaptive_paged_scene",
    "prepare_page_slider_layout",
    "render_draw_pipeline_on_axes",
    "render_managed_draw_pipeline",
    "scene_aspect_ratio",
    "set_slider_view",
    "slider_viewport_height",
    "slider_viewport_width",
    "viewport_adaptive_paged_scene",
    "viewport_scene_score",
]


def render_managed_draw_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    call_show: bool | None = None,
    figsize: tuple[float, float] | None,
    page_slider: bool,
    page_window: bool,
    respect_precomputed_scene: bool = False,
) -> tuple[Figure, Axes]:
    """Render a prepared pipeline on a managed figure."""

    return _render_managed_draw_pipeline_impl(
        pipeline,
        output=output,
        show=show,
        call_show=call_show,
        figsize=figsize,
        page_slider=page_slider,
        page_window=page_window,
        respect_precomputed_scene=respect_precomputed_scene,
    )


def render_draw_pipeline_on_axes(
    pipeline: PreparedDrawPipeline,
    *,
    axes: Axes,
    output: OutputPath | None,
    respect_precomputed_scene: bool = False,
) -> Axes:
    """Render a prepared pipeline on existing axes using one-shot 2D composition."""

    return _render_draw_pipeline_on_axes_impl(
        pipeline,
        axes=axes,
        output=output,
        respect_precomputed_scene=respect_precomputed_scene,
    )


def build_continuous_slider_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a continuous-width 2D scene for page-slider mode."""

    return _build_continuous_slider_scene_impl(
        circuit,
        layout_engine,
        style,
        hover_enabled=hover_enabled,
    )


def viewport_adaptive_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    axes: Axes,
    *,
    hover_enabled: bool = True,
    initial_scene: LayoutScene | None = None,
) -> tuple[LayoutScene, float]:
    """Return the paged scene whose aspect best matches the current axes viewport."""

    return _viewport_adaptive_paged_scene_impl(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
    )


def page_window_adaptive_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    axes: Axes,
    *,
    hover_enabled: bool = True,
    initial_scene: LayoutScene | None = None,
    visible_page_count: int = 1,
) -> tuple[LayoutScene, float]:
    """Return the paged scene that best matches the fixed page-window viewport."""

    return _page_window_adaptive_paged_scene_impl(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
        visible_page_count=visible_page_count,
    )


def compute_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a paged 2D scene using the provided normalized style."""

    return _compute_paged_scene_impl(
        circuit,
        layout_engine,
        style,
        hover_enabled=hover_enabled,
    )


def axes_viewport_ratio(axes: Axes) -> float:
    """Return the current visible axes aspect ratio in pixels."""

    return _axes_viewport_ratio_impl(axes)


def axes_viewport_pixels(axes: Axes) -> tuple[float, float]:
    """Return the current axes viewport size in pixels."""

    return _axes_viewport_pixels_impl(axes)


def scene_aspect_ratio(scene: LayoutScene) -> float:
    """Return the width-to-height ratio of a 2D scene."""

    return _scene_aspect_ratio_impl(scene)


def viewport_scene_score(scene: LayoutScene, viewport_ratio: float) -> float:
    """Return how closely the scene aspect matches the viewport aspect."""

    return _viewport_scene_score_impl(scene, viewport_ratio)


def configure_zoom_text_scaling(axes: Axes, *, scene: LayoutScene) -> None:
    """Attach zoom-responsive text scaling to the provided 2D axes."""

    _configure_zoom_text_scaling_impl(axes, scene=scene)


def current_view_size(axes: Axes) -> tuple[float, float]:
    """Return the current visible data window for the axes."""

    return _current_view_size_impl(axes)


def current_text_scale(axes: Axes, state: object) -> float:
    """Return the current zoom scale factor for 2D text."""

    return _current_text_scale_impl(axes, state)


def configure_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    scene: LayoutScene,
    viewport_width: float,
    set_page_slider: Callable[[Figure, object], None],
    viewport_height: float | None = None,
    layout: object | None = None,
    quantum_wire_count: int | None = None,
    allow_figure_resize: bool = True,
    circuit: CircuitIR | None = None,
    layout_engine: LayoutEngineLike | None = None,
    renderer: MatplotlibRenderer | None = None,
    normalized_style: DrawStyle | None = None,
    semantic_ir: object | None = None,
    expanded_semantic_ir: object | None = None,
    keyboard_shortcuts_enabled: bool = True,
    double_click_toggle_enabled: bool = True,
) -> None:
    """Attach and wire a slider that redraws discrete 2D circuit windows."""

    _configure_page_slider_impl(
        figure=figure,
        axes=axes,
        scene=scene,
        viewport_width=viewport_width,
        set_page_slider=set_page_slider,
        viewport_height=viewport_height,
        layout=cast("Managed2DSliderLayout | None", layout),
        quantum_wire_count=quantum_wire_count,
        allow_figure_resize=allow_figure_resize,
        circuit=circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        normalized_style=normalized_style,
        semantic_ir=cast("SemanticCircuitIR | None", semantic_ir),
        expanded_semantic_ir=cast("SemanticCircuitIR | None", expanded_semantic_ir),
        keyboard_shortcuts_enabled=keyboard_shortcuts_enabled,
        double_click_toggle_enabled=double_click_toggle_enabled,
    )


def configure_page_window(
    *,
    figure: Figure,
    axes: Axes,
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    renderer: MatplotlibRenderer,
    scene: LayoutScene,
    effective_page_width: float,
    set_page_window: Callable[[Figure, object], None],
    semantic_ir: object | None = None,
    expanded_semantic_ir: object | None = None,
    keyboard_shortcuts_enabled: bool = True,
    double_click_toggle_enabled: bool = True,
) -> object:
    """Attach fixed page-window controls for one managed 2D figure."""

    return _configure_page_window_impl(
        figure=figure,
        axes=axes,
        circuit=circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        scene=scene,
        effective_page_width=effective_page_width,
        set_page_window=set_page_window,
        semantic_ir=cast("SemanticCircuitIR | None", semantic_ir),
        expanded_semantic_ir=cast("SemanticCircuitIR | None", expanded_semantic_ir),
        keyboard_shortcuts_enabled=keyboard_shortcuts_enabled,
        double_click_toggle_enabled=double_click_toggle_enabled,
    )


def page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    """Return a readable managed figure size for page-slider mode."""

    return _page_slider_figsize_impl(viewport_width, scene_height)


def slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene width for the current axes aspect ratio."""

    return _slider_viewport_width_impl(axes, scene)


def slider_viewport_height(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene height for the current axes aspect ratio."""

    return _slider_viewport_height_impl(axes, scene)


def set_slider_view(
    axes: Axes,
    scene: LayoutScene,
    *,
    x_offset: float,
    viewport_width: float,
    y_offset: float = 0.0,
    viewport_height: float | None = None,
) -> None:
    """Set the 2D axes limits used for the slider viewport."""

    _set_slider_view_impl(
        axes,
        scene,
        x_offset=x_offset,
        y_offset=y_offset,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )


def configure_3d_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    set_page_slider: Callable[[Figure, object], None],
    keyboard_shortcuts_enabled: bool = True,
    double_click_toggle_enabled: bool = True,
) -> object | None:
    """Attach and wire a 3D page slider that moves through circuit columns."""

    return _configure_3d_page_slider_impl(
        figure=figure,
        axes=axes,
        pipeline=pipeline,
        set_page_slider=set_page_slider,
        keyboard_shortcuts_enabled=keyboard_shortcuts_enabled,
        double_click_toggle_enabled=double_click_toggle_enabled,
    )


def prepare_page_slider_layout(axes: Axes, scene: LayoutScene) -> object:
    """Resolve the 2D slider layout and viewport before rendering."""

    return _prepare_page_slider_layout_impl(axes, scene)


def apply_managed_3d_axes_bounds(
    axes: Axes,
    *,
    has_page_slider: bool,
) -> tuple[float, float, float, float]:
    """Apply managed 3D viewport bounds for the active control layout."""

    return _apply_managed_3d_axes_bounds_impl(axes, has_page_slider=has_page_slider)


def is_3d_axes(ax: Axes) -> bool:
    """Return whether the provided axes is a Matplotlib 3D axes."""

    return getattr(ax, "name", "") == "3d"


def is_3d_scene(scene: LayoutScene | LayoutScene3D) -> TypeGuard[LayoutScene3D]:
    """Return whether a prepared scene is a 3D scene."""

    return hasattr(scene, "depth")
