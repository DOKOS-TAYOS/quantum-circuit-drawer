"""Managed fixed-page-window facade for 2D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ..layout.scene import LayoutScene
from ..renderers._matplotlib_page_projection import _ProjectedPage
from ..renderers.matplotlib_primitives import _GateTextCache
from ..renderers.matplotlib_renderer import MatplotlibRenderer
from ..typing import LayoutEngineLike
from .page_window_controls import _MAIN_AXES_BOUNDS, _attach_controls, _sync_inputs
from .page_window_render import _render_current_window
from .ui_palette import ManagedUiPalette, managed_ui_palette

if TYPE_CHECKING:
    from matplotlib.text import Text
    from matplotlib.widgets import Button, TextBox

    from ..ir.circuit import CircuitIR


@dataclass(slots=True)
class Managed2DPageWindowState:
    """Managed fixed-page-window state attached to one figure."""

    figure: Figure
    axes: Axes
    circuit: CircuitIR
    layout_engine: LayoutEngineLike
    renderer: MatplotlibRenderer
    scene: LayoutScene
    effective_page_width: float
    total_pages: int
    start_page: int
    visible_page_count: int
    page_cache: dict[int, _ProjectedPage] = field(default_factory=dict)
    text_fit_cache: _GateTextCache = field(default_factory=dict)
    page_box: TextBox | None = None
    visible_pages_box: TextBox | None = None
    visible_pages_decrement_button: Button | None = None
    visible_pages_increment_button: Button | None = None
    previous_page_button: Button | None = None
    next_page_button: Button | None = None
    page_axes: Axes | None = None
    visible_pages_axes: Axes | None = None
    visible_pages_decrement_axes: Axes | None = None
    visible_pages_increment_axes: Axes | None = None
    previous_page_button_axes: Axes | None = None
    next_page_button_axes: Axes | None = None
    page_suffix_text: Text | None = None
    visible_suffix_text: Text | None = None
    ui_palette: ManagedUiPalette | None = None
    is_syncing_inputs: bool = False


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
) -> Managed2DPageWindowState:
    """Attach fixed page-window controls and render the initial visible window."""

    total_pages = max(1, len(scene.pages))
    ui_palette = managed_ui_palette(scene.style.theme)
    state = Managed2DPageWindowState(
        figure=figure,
        axes=axes,
        circuit=circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        scene=scene,
        effective_page_width=effective_page_width,
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


def apply_page_window_axes_bounds(axes: Axes) -> None:
    """Pin page-window drawing axes above the control row."""

    axes.set_position(_MAIN_AXES_BOUNDS)
