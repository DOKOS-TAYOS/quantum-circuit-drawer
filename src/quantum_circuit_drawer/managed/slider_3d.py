"""Managed 3D slider state and orchestration helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ..drawing.pipeline import PreparedDrawPipeline, _compute_3d_scene
from ..ir.circuit import CircuitIR
from ..layout._layering import normalized_draw_circuit
from ..layout._layout_scaffold import build_layout_paging_inputs, paged_scene_metrics_for_width
from ..layout.scene_3d import LayoutScene3D
from ..renderers._matplotlib_figure import clear_hover_state
from ..style import DrawStyle
from ..typing import LayoutEngine3DLike
from .controls import (
    _style_control_axes,
    _style_slider,
    apply_managed_3d_axes_bounds,
    managed_3d_axes_bounds,
)
from .ui_palette import managed_ui_palette
from .view_state_3d import (
    _MANAGED_3D_FIXED_VIEW_STATE_ATTR,
    capture_managed_3d_view_state,
)
from .viewport import _figure_size_inches

if TYPE_CHECKING:
    from matplotlib.widgets import Slider
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from ..layout.topology_3d import TopologyName

_MANAGED_3D_SLIDER_BOUNDS = (0.18, 0.05, 0.72, 0.06)


@dataclass(slots=True)
class Managed3DPageSliderState:
    """Typed 3D managed-slider state attached to the figure metadata."""

    figure: Figure
    axes: Axes3D
    pipeline: PreparedDrawPipeline
    current_scene: LayoutScene3D
    horizontal_slider: Slider | None
    horizontal_axes: Axes | None
    start_column: int
    window_size: int
    max_start_column: int
    scene_cache: dict[int, LayoutScene3D]
    vertical_slider: Slider | None = None
    vertical_axes: Axes | None = None

    def show_start_column(self, start_column: int) -> None:
        """Render the requested 3D column window on the managed axes."""

        resolved_start_column = min(max(0, start_column), self.max_start_column)
        scene = self._scene_for_start_column(resolved_start_column)
        self.start_column = resolved_start_column
        self.current_scene = scene

        fixed_view_state = capture_managed_3d_view_state(self.axes)
        clear_hover_state(self.axes)
        self.axes.clear()
        setattr(self.axes, _MANAGED_3D_FIXED_VIEW_STATE_ATTR, fixed_view_state)
        apply_managed_3d_axes_bounds(self.axes, has_page_slider=self.horizontal_slider is not None)
        self.pipeline.renderer.render(scene, ax=self.axes)

        canvas = getattr(self.figure, "canvas", None)
        if canvas is not None:
            canvas.draw_idle()

    def select_topology(self, topology: TopologyName) -> None:
        """Switch topology while keeping the current column window."""

        updated_draw_options = replace(self.pipeline.draw_options, topology=topology)
        self.pipeline = replace(self.pipeline, draw_options=updated_draw_options)
        self.scene_cache.clear()
        self.show_start_column(self.start_column)

    def _scene_for_start_column(self, start_column: int) -> LayoutScene3D:
        cached_scene = self.scene_cache.get(start_column)
        if cached_scene is not None:
            return cached_scene

        windowed_circuit = circuit_window(
            self.pipeline.ir,
            start_column=start_column,
            window_size=self.window_size,
        )
        scene = _compute_3d_scene(
            cast("LayoutEngine3DLike", self.pipeline.layout_engine),
            windowed_circuit,
            self.pipeline.normalized_style,
            topology_name=self.pipeline.draw_options.topology,
            direct=self.pipeline.draw_options.direct,
            hover_enabled=self.pipeline.draw_options.hover.enabled,
        )
        self.scene_cache[start_column] = scene
        return scene


def configure_3d_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    set_page_slider: Callable[[Figure, object], None],
) -> Managed3DPageSliderState | None:
    """Attach and wire a managed 3D slider that moves through circuit columns."""

    from .page_window_3d_ranges import windowed_3d_page_ranges

    normalized_pipeline = replace(pipeline, ir=normalized_draw_circuit(pipeline.ir))
    total_columns = len(normalized_pipeline.ir.layers)
    page_ranges = windowed_3d_page_ranges(
        pipeline,
        figure_size=_figure_size_inches(figure),
        axes_bounds=managed_3d_axes_bounds(has_page_slider=True),
    )
    first_page_start, first_page_end = page_ranges[0]
    window_size = max(1, first_page_end - first_page_start + 1)
    max_start_column = max(0, total_columns - window_size)
    if max_start_column <= 0:
        return None

    from matplotlib.widgets import Slider

    axes_3d = cast("Axes3D", axes)
    apply_managed_3d_axes_bounds(axes, has_page_slider=True)
    slider_axes = figure.add_axes(_MANAGED_3D_SLIDER_BOUNDS)
    palette = managed_ui_palette(cast("LayoutScene3D", pipeline.paged_scene).style.theme)
    _style_control_axes(slider_axes, palette=palette)
    state = Managed3DPageSliderState(
        figure=figure,
        axes=axes_3d,
        pipeline=normalized_pipeline,
        current_scene=cast("LayoutScene3D", pipeline.paged_scene),
        horizontal_slider=None,
        horizontal_axes=slider_axes,
        start_column=0,
        window_size=window_size,
        max_start_column=max_start_column,
        scene_cache={},
    )
    initial_scene = state._scene_for_start_column(0)
    state.current_scene = initial_scene

    slider = Slider(
        ax=slider_axes,
        label="",
        valmin=0.0,
        valmax=float(max_start_column),
        valinit=0.0,
        valstep=1.0,
        color=palette.slider_fill_color,
        track_color=palette.slider_track_color,
        handle_style={
            "facecolor": palette.accent_color,
            "edgecolor": palette.accent_edgecolor,
            "size": 16,
        },
    )
    _style_slider(slider, palette=palette)
    slider.on_changed(lambda value: state.show_start_column(round(float(value))))
    state.horizontal_slider = slider
    set_page_slider(figure, state)
    return state


def page_slider_window_size(circuit: CircuitIR, style: DrawStyle) -> int:
    """Return the number of columns that fit in the first 2D page budget."""

    normalized_circuit = normalized_draw_circuit(circuit)
    paging_inputs = build_layout_paging_inputs(normalized_circuit, style)
    metrics = paged_scene_metrics_for_width(
        paging_inputs,
        max_page_width=float(getattr(style, "max_page_width")),
    )
    if not metrics.pages:
        return max(1, len(normalized_circuit.layers))
    first_page = metrics.pages[0]
    return max(1, first_page.end_column - first_page.start_column + 1)


def circuit_window(
    circuit: CircuitIR,
    *,
    start_column: int,
    window_size: int,
) -> CircuitIR:
    """Return a new circuit containing only one contiguous layer window."""

    end_column = min(len(circuit.layers), start_column + window_size)
    return CircuitIR(
        quantum_wires=circuit.quantum_wires,
        classical_wires=circuit.classical_wires,
        layers=tuple(circuit.layers[start_column:end_column]),
        name=circuit.name,
        metadata=dict(circuit.metadata),
    )
