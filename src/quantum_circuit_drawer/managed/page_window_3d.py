"""Managed fixed-page-window helpers for 3D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ..layout.topology_3d import TopologyName
from .page_window_3d_controls import (
    _attach_controls,
    _clamp_visible_page_count,
    _sync_inputs,
)
from .page_window_3d_ranges import (
    _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO,
    _projected_scene_aspect_ratio,
    windowed_3d_page_ranges,
    windowed_3d_page_scenes,
)
from .page_window_3d_render import _render_current_window
from .ui_palette import ManagedUiPalette, managed_ui_palette
from .viewport import _figure_size_inches

if TYPE_CHECKING:
    from matplotlib.text import Text
    from matplotlib.widgets import Button, TextBox
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from ..drawing.pipeline import PreparedDrawPipeline
    from ..layout.scene_3d import LayoutScene3D

__all__ = [
    "_MIN_3D_PAGE_PROJECTED_ASPECT_RATIO",
    "_projected_scene_aspect_ratio",
    "Managed3DPageWindowState",
    "configure_3d_page_window",
    "windowed_3d_page_ranges",
    "windowed_3d_page_scenes",
]


@dataclass(slots=True)
class Managed3DPageWindowState:
    """Managed fixed-page-window state attached to one 3D figure."""

    figure: Figure
    base_axes: Axes3D
    pipeline: PreparedDrawPipeline
    page_scenes: tuple[LayoutScene3D, ...]
    total_pages: int
    start_page: int
    visible_page_count: int
    display_axes: tuple[Axes3D, ...] = ()
    page_box: TextBox | None = None
    visible_pages_box: TextBox | None = None
    visible_pages_decrement_button: Button | None = None
    visible_pages_increment_button: Button | None = None
    previous_page_button: Button | None = None
    next_page_button: Button | None = None
    previous_page_button_axes: Axes | None = None
    page_axes: Axes | None = None
    next_page_button_axes: Axes | None = None
    visible_pages_axes: Axes | None = None
    visible_pages_decrement_axes: Axes | None = None
    visible_pages_increment_axes: Axes | None = None
    page_suffix_text: Text | None = None
    visible_suffix_text: Text | None = None
    ui_palette: ManagedUiPalette | None = None
    is_syncing_inputs: bool = False

    @property
    def current_scene(self) -> LayoutScene3D:
        """Return the first scene currently shown in the window."""

        return self.page_scenes[self.start_page]

    def select_topology(self, topology: TopologyName) -> None:
        """Switch topology while preserving the current window state."""

        updated_draw_options = replace(self.pipeline.draw_options, topology=topology)
        updated_pipeline = replace(self.pipeline, draw_options=updated_draw_options)
        updated_page_scenes = windowed_3d_page_scenes(
            updated_pipeline,
            figure_size=_figure_size_inches(self.figure),
        )
        self.pipeline = replace(updated_pipeline, paged_scene=updated_page_scenes[0])
        self.page_scenes = updated_page_scenes
        self.total_pages = len(self.page_scenes)
        self.start_page = min(self.start_page, self.total_pages - 1)
        self.visible_page_count = _clamp_visible_page_count(
            self.visible_page_count,
            total_pages=self.total_pages,
            start_page=self.start_page,
        )
        _render_current_window(self)
        _sync_inputs(self)


def configure_3d_page_window(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    page_scenes: tuple[LayoutScene3D, ...],
    set_page_window: Callable[[Figure, object], None],
) -> Managed3DPageWindowState:
    """Attach fixed page-window controls and render the initial 3D window."""

    base_axes = cast("Axes3D", axes)
    total_pages = max(1, len(page_scenes))
    ui_palette = managed_ui_palette(page_scenes[0].style.theme)
    state = Managed3DPageWindowState(
        figure=figure,
        base_axes=base_axes,
        pipeline=pipeline,
        page_scenes=page_scenes,
        total_pages=total_pages,
        start_page=0,
        visible_page_count=1,
        ui_palette=ui_palette,
    )
    set_page_window(figure, state)
    _attach_controls(state)
    _render_current_window(state)
    _sync_inputs(state)
    return state
