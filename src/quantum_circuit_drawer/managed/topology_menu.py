"""Managed-figure topology selector for interactive 3D renders."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.widgets import RadioButtons

from ..drawing.pipeline import PreparedDrawPipeline, _compute_3d_scene
from ..layout.topology_3d import TopologyName, build_topology
from ..renderers._matplotlib_figure import (
    clear_hover_state,
    get_page_slider,
    get_page_window,
    set_topology_menu_state,
)
from ..typing import LayoutEngine3DLike
from .controls import apply_managed_3d_axes_bounds, managed_3d_menu_bounds
from .page_window_3d import Managed3DPageWindowState
from .slider_3d import Managed3DPageSliderState
from .ui_palette import ManagedUiPalette, managed_ui_palette

if TYPE_CHECKING:
    from matplotlib.figure import Figure, SubFigure

    from ..layout.scene_3d import LayoutScene3D

_ALL_TOPOLOGIES: tuple[TopologyName, ...] = (
    "line",
    "grid",
    "star",
    "star_tree",
    "honeycomb",
)
_MENU_LABEL_FONT_SIZE = 10.0
_MENU_RADIO_MARKER_SIZE = 72.0
_PAGE_WINDOW_MENU_BOUNDS = (0.77, 0.24, 0.17, 0.29)


@dataclass(slots=True)
class TopologyMenuState:
    """Interactive topology-menu state attached to one managed figure."""

    figure: Figure | SubFigure
    axes: Axes
    pipeline: PreparedDrawPipeline
    scene: LayoutScene3D
    active_topology: TopologyName
    valid_topologies: tuple[TopologyName, ...]
    topologies: tuple[TopologyName, ...] = _ALL_TOPOLOGIES
    ui_palette: ManagedUiPalette | None = None
    menu_axes: Axes | None = None
    radio: RadioButtons | None = None

    def is_enabled(self, topology: TopologyName) -> bool:
        """Return whether the requested topology is available for this circuit."""

        return topology in self.valid_topologies

    def select_topology(self, topology: TopologyName) -> None:
        """Switch to a new valid topology and redraw the managed 3D axes."""

        if not self.is_enabled(topology) or topology == self.active_topology:
            _set_radio_selection(self, self.active_topology)
            _refresh_radio_styles(self)
            canvas = getattr(self.figure, "canvas", None)
            if canvas is not None:
                canvas.draw_idle()
            return

        page_slider_state = get_page_slider(self.figure)
        page_window_state = get_page_window(self.figure)
        if isinstance(page_slider_state, Managed3DPageSliderState):
            page_slider_state.select_topology(topology)
            self.pipeline = page_slider_state.pipeline
            self.scene = page_slider_state.current_scene
            self.active_topology = topology
        elif isinstance(page_window_state, Managed3DPageWindowState):
            page_window_state.select_topology(topology)
            self.pipeline = page_window_state.pipeline
            self.scene = page_window_state.current_scene
            self.axes = page_window_state.display_axes[0]
            self.active_topology = topology
        else:
            updated_pipeline = _pipeline_for_topology(self.pipeline, topology)
            updated_scene = cast("LayoutScene3D", updated_pipeline.paged_scene)
            self.pipeline = updated_pipeline
            self.scene = updated_scene
            self.active_topology = topology

            clear_hover_state(self.axes)
            self.axes.clear()
            apply_managed_3d_axes_bounds(self.axes, has_page_slider=False)
            self.pipeline.renderer.render(updated_scene, ax=self.axes)
        _set_radio_selection(self, topology)
        _refresh_radio_styles(self)

        canvas = getattr(self.figure, "canvas", None)
        if canvas is not None:
            canvas.draw_idle()

    def remove(self) -> None:
        """Remove topology-menu artists from the figure."""

        if self.radio is not None:
            self.radio.disconnect_events()
            self.radio = None

        if self.menu_axes is not None:
            self.menu_axes.remove()
            self.menu_axes = None


def attach_topology_menu(
    *,
    figure: Figure | SubFigure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
) -> TopologyMenuState:
    """Attach a topology selector to an interactive managed 3D figure."""

    page_slider_state = get_page_slider(figure)
    page_window_state = get_page_window(figure)
    scene = (
        page_slider_state.current_scene
        if isinstance(page_slider_state, Managed3DPageSliderState)
        else (
            page_window_state.current_scene
            if isinstance(page_window_state, Managed3DPageWindowState)
            else cast("LayoutScene3D", pipeline.paged_scene)
        )
    )
    valid_topologies = tuple(
        topology_name
        for topology_name in _ALL_TOPOLOGIES
        if _supports_topology(topology_name, tuple(pipeline.ir.quantum_wires))
    )
    active_topology = cast("TopologyName", pipeline.draw_options.topology)
    state = TopologyMenuState(
        figure=figure,
        axes=axes,
        pipeline=pipeline,
        scene=scene,
        active_topology=active_topology,
        valid_topologies=valid_topologies,
        ui_palette=managed_ui_palette(scene.style.theme),
    )
    if not isinstance(page_window_state, Managed3DPageWindowState):
        apply_managed_3d_axes_bounds(
            axes,
            has_page_slider=isinstance(page_slider_state, Managed3DPageSliderState),
        )
    state.menu_axes = figure.add_axes(
        _PAGE_WINDOW_MENU_BOUNDS
        if isinstance(page_window_state, Managed3DPageWindowState)
        else managed_3d_menu_bounds(
            has_page_slider=isinstance(page_slider_state, Managed3DPageSliderState)
        )
    )
    assert state.ui_palette is not None
    _configure_menu_axes(state.menu_axes, palette=state.ui_palette)
    state.radio = RadioButtons(
        state.menu_axes,
        _ALL_TOPOLOGIES,
        active=_ALL_TOPOLOGIES.index(active_topology),
        activecolor=state.ui_palette.accent_color,
        useblit=False,
    )
    state.radio.on_clicked(lambda selected: state.select_topology(cast("TopologyName", selected)))
    _refresh_radio_styles(state)
    set_topology_menu_state(figure, state)
    return state


def _configure_menu_axes(menu_axes: Axes, *, palette: ManagedUiPalette) -> None:
    menu_axes.set_facecolor(palette.surface_facecolor)
    menu_axes.set_xticks([])
    menu_axes.set_yticks([])
    menu_axes.set_navigate(False)
    for spine in menu_axes.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor(palette.surface_edgecolor)
        spine.set_linewidth(1.0)


def _refresh_radio_styles(state: TopologyMenuState) -> None:
    if state.radio is None or state.ui_palette is None:
        return

    label_colors: list[str] = []
    font_weights: list[str] = []
    face_colors: list[str] = []
    edge_colors: list[str] = []
    line_widths: list[float] = []

    for topology_name in state.topologies:
        enabled = state.is_enabled(topology_name)
        active = enabled and topology_name == state.active_topology
        if active:
            label_colors.append(state.ui_palette.text_color)
            font_weights.append("bold")
            face_colors.append(state.ui_palette.accent_color)
            edge_colors.append(state.ui_palette.surface_edgecolor_active)
            line_widths.append(1.8)
        elif enabled:
            label_colors.append(state.ui_palette.text_color)
            font_weights.append("normal")
            face_colors.append("none")
            edge_colors.append(state.ui_palette.surface_edgecolor)
            line_widths.append(1.4)
        else:
            label_colors.append(state.ui_palette.disabled_text_color)
            font_weights.append("normal")
            face_colors.append("none")
            edge_colors.append(state.ui_palette.surface_edgecolor_disabled)
            line_widths.append(1.2)

    state.radio.set_label_props(
        {
            "color": label_colors,
            "fontsize": [_MENU_LABEL_FONT_SIZE] * len(label_colors),
            "fontweight": font_weights,
        }
    )
    state.radio.set_radio_props(
        {
            "s": [_MENU_RADIO_MARKER_SIZE] * len(edge_colors),
            "facecolor": face_colors,
            "edgecolor": edge_colors,
            "linewidth": line_widths,
        }
    )


def _set_radio_selection(state: TopologyMenuState, topology: TopologyName) -> None:
    if state.radio is None:
        return

    eventson = state.radio.eventson
    state.radio.eventson = False
    state.radio.set_active(state.topologies.index(topology))
    state.radio.eventson = eventson


def _pipeline_for_topology(
    pipeline: PreparedDrawPipeline,
    topology: TopologyName,
) -> PreparedDrawPipeline:
    draw_options = replace(pipeline.draw_options, topology=topology)
    scene = _compute_3d_scene(
        cast("LayoutEngine3DLike", pipeline.layout_engine),
        pipeline.ir,
        pipeline.normalized_style,
        topology_name=topology,
        direct=draw_options.direct,
        hover_enabled=draw_options.hover.enabled,
        topology_qubits=draw_options.topology_qubits,
        topology_resize=draw_options.topology_resize,
    )
    return replace(
        pipeline,
        paged_scene=scene,
        draw_options=draw_options,
    )


def _supports_topology(
    topology: TopologyName,
    quantum_wires: tuple[object, ...],
) -> bool:
    try:
        build_topology(topology, cast("tuple", quantum_wires))
    except ValueError:
        return False
    return True


__all__ = [
    "Axes",
    "LayoutEngine3DLike",
    "Managed3DPageSliderState",
    "Managed3DPageWindowState",
    "ManagedUiPalette",
    "PreparedDrawPipeline",
    "RadioButtons",
    "TYPE_CHECKING",
    "TopologyMenuState",
    "TopologyName",
    "_ALL_TOPOLOGIES",
    "_MENU_LABEL_FONT_SIZE",
    "_MENU_RADIO_MARKER_SIZE",
    "_PAGE_WINDOW_MENU_BOUNDS",
    "_compute_3d_scene",
    "_configure_menu_axes",
    "_pipeline_for_topology",
    "_refresh_radio_styles",
    "_set_radio_selection",
    "_supports_topology",
    "annotations",
    "apply_managed_3d_axes_bounds",
    "attach_topology_menu",
    "build_topology",
    "cast",
    "clear_hover_state",
    "dataclass",
    "get_page_slider",
    "get_page_window",
    "managed_3d_menu_bounds",
    "managed_ui_palette",
    "replace",
    "set_topology_menu_state",
]
