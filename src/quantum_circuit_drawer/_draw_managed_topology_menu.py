"""Managed-figure topology selector for interactive 3D renders."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.text import Text
from matplotlib.widgets import Button

from ._draw_pipeline import PreparedDrawPipeline, _compute_3d_scene
from .layout.topology_3d import TopologyName, build_topology
from .renderers._matplotlib_figure import (
    clear_hover_state,
    set_topology_menu_state,
)
from .typing import LayoutEngine3DLike

if TYPE_CHECKING:
    from matplotlib.figure import Figure, SubFigure

    from .layout.scene_3d import LayoutScene3D

_ALL_TOPOLOGIES: tuple[TopologyName, ...] = (
    "line",
    "grid",
    "star",
    "star_tree",
    "honeycomb",
)
_ACTIVE_BUTTON_COLOR = "#1d4ed8"
_ACTIVE_BORDER_COLOR = "#bfdbfe"
_ACTIVE_TEXT_COLOR = "#ffffff"
_ENABLED_BUTTON_COLOR = "#111827"
_ENABLED_BORDER_COLOR = "#6b7280"
_ENABLED_TEXT_COLOR = "#f3f4f6"
_DISABLED_BUTTON_COLOR = "#0f172a"
_DISABLED_BORDER_COLOR = "#1f2937"
_DISABLED_TEXT_COLOR = "#64748b"
_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"
_MENU_MAIN_AXES_BOUNDS = (0.0, 0.0, 0.8, 1.0)
_MENU_TITLE_POSITION = (0.88, 0.92)
_MENU_BUTTON_LEFT = 0.82
_MENU_BUTTON_WIDTH = 0.15
_MENU_BUTTON_HEIGHT = 0.075
_MENU_BUTTON_GAP = 0.018
_MENU_BUTTON_START_BOTTOM = 0.79


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
    buttons: dict[TopologyName, Button] = field(default_factory=dict)
    button_axes: dict[TopologyName, Axes] = field(default_factory=dict)
    title_artist: Text | None = None

    def is_enabled(self, topology: TopologyName) -> bool:
        """Return whether the requested topology is available for this circuit."""

        return topology in self.valid_topologies

    def select_topology(self, topology: TopologyName) -> None:
        """Switch to a new valid topology and redraw the managed 3D axes."""

        if not self.is_enabled(topology) or topology == self.active_topology:
            _refresh_button_styles(self)
            canvas = getattr(self.figure, "canvas", None)
            if canvas is not None:
                canvas.draw_idle()
            return

        updated_pipeline = _pipeline_for_topology(self.pipeline, topology)
        updated_scene = cast("LayoutScene3D", updated_pipeline.paged_scene)
        self.pipeline = updated_pipeline
        self.scene = updated_scene
        self.active_topology = topology

        clear_hover_state(self.axes)
        self.axes.clear()
        self.axes.set_position(_MENU_MAIN_AXES_BOUNDS)
        setattr(self.axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, _MENU_MAIN_AXES_BOUNDS)
        self.pipeline.renderer.render(updated_scene, ax=self.axes)
        _refresh_button_styles(self)

        canvas = getattr(self.figure, "canvas", None)
        if canvas is not None:
            canvas.draw_idle()

    def remove(self) -> None:
        """Remove topology-menu artists from the figure."""

        if self.title_artist is not None:
            self.title_artist.remove()
            self.title_artist = None

        for button_axes in self.button_axes.values():
            button_axes.remove()
        self.button_axes.clear()
        self.buttons.clear()


def attach_topology_menu(
    *,
    figure: Figure | SubFigure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
) -> TopologyMenuState:
    """Attach a topology selector to an interactive managed 3D figure."""

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
        scene=cast("LayoutScene3D", pipeline.paged_scene),
        active_topology=active_topology,
        valid_topologies=valid_topologies,
    )
    axes.set_position(_MENU_MAIN_AXES_BOUNDS)
    setattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, _MENU_MAIN_AXES_BOUNDS)
    state.title_artist = figure.text(
        _MENU_TITLE_POSITION[0],
        _MENU_TITLE_POSITION[1],
        "Topology",
        ha="center",
        va="center",
        color=_ENABLED_TEXT_COLOR,
        fontsize=10.0,
        weight="bold",
    )

    for index, topology_name in enumerate(_ALL_TOPOLOGIES):
        button_bottom = _MENU_BUTTON_START_BOTTOM - (
            index * (_MENU_BUTTON_HEIGHT + _MENU_BUTTON_GAP)
        )
        button_axes = figure.add_axes(
            (
                _MENU_BUTTON_LEFT,
                button_bottom,
                _MENU_BUTTON_WIDTH,
                _MENU_BUTTON_HEIGHT,
            )
        )
        button = Button(button_axes, topology_name)
        button.on_clicked(lambda _event, selected=topology_name: state.select_topology(selected))
        state.button_axes[topology_name] = button_axes
        state.buttons[topology_name] = button

    _refresh_button_styles(state)
    set_topology_menu_state(figure, state)
    return state


def _refresh_button_styles(state: TopologyMenuState) -> None:
    for topology_name, button in state.buttons.items():
        enabled = state.is_enabled(topology_name)
        active = enabled and topology_name == state.active_topology
        if active:
            facecolor = _ACTIVE_BUTTON_COLOR
            border_color = _ACTIVE_BORDER_COLOR
            text_color = _ACTIVE_TEXT_COLOR
            hovercolor = _ACTIVE_BUTTON_COLOR
        elif enabled:
            facecolor = _ENABLED_BUTTON_COLOR
            border_color = _ENABLED_BORDER_COLOR
            text_color = _ENABLED_TEXT_COLOR
            hovercolor = "#1f2937"
        else:
            facecolor = _DISABLED_BUTTON_COLOR
            border_color = _DISABLED_BORDER_COLOR
            text_color = _DISABLED_TEXT_COLOR
            hovercolor = _DISABLED_BUTTON_COLOR

        button.color = facecolor
        button.hovercolor = hovercolor
        button.ax.set_facecolor(facecolor)
        button.label.set_color(text_color)
        button.label.set_fontsize(9.0)
        for spine in button.ax.spines.values():
            spine.set_visible(True)
            spine.set_edgecolor(border_color)
            spine.set_linewidth(1.4 if active else 1.0)
        button.ax.set_xticks([])
        button.ax.set_yticks([])


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
