"""Managed slider helpers for 2D and 3D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ._draw_managed_viewport import axes_viewport_pixels
from ._draw_pipeline import PreparedDrawPipeline, _compute_3d_scene
from .ir.circuit import CircuitIR
from .layout._layout_scaffold import build_layout_paging_inputs, paged_scene_metrics_for_width
from .layout.scene import LayoutScene
from .layout.scene_3d import LayoutScene3D
from .renderers._matplotlib_figure import clear_hover_state, set_viewport_width
from .typing import LayoutEngine3DLike

if TYPE_CHECKING:
    from matplotlib.widgets import Slider, TextBox

    from .layout.topology_3d import TopologyName

_VIEWPORT_EPSILON = 1e-6

_MANAGED_2D_MAIN_AXES_BOUNDS = (0.02, 0.02, 0.96, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_HORIZONTAL_BOUNDS = (0.02, 0.18, 0.96, 0.8)
_MANAGED_2D_MAIN_AXES_WITH_VERTICAL_BOUNDS = (0.12, 0.02, 0.86, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_BOTH_BOUNDS = (0.12, 0.18, 0.86, 0.8)
_MANAGED_2D_MAIN_AXES_WITH_LEFT_CONTROLS_BOUNDS = (0.12, 0.02, 0.86, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_HORIZONTAL_AND_BOX_BOUNDS = (0.12, 0.18, 0.86, 0.8)
_MANAGED_2D_HORIZONTAL_SLIDER_HEIGHT = 0.055
_MANAGED_2D_HORIZONTAL_SLIDER_BOTTOM = 0.045
_MANAGED_2D_LEFT_CONTROL_LEFT = 0.04
_MANAGED_2D_LEFT_CONTROL_WIDTH = 0.055
_MANAGED_2D_VERTICAL_SLIDER_WIDTH = 0.021
_MANAGED_2D_VISIBLE_QUBITS_WIDTH = 0.055
_MANAGED_2D_VISIBLE_QUBITS_HEIGHT = 0.045
_MANAGED_2D_VISIBLE_QUBITS_BOTTOM = 0.045
_MANAGED_2D_VISIBLE_QUBITS_BOTTOM_WITH_HORIZONTAL = 0.115
_MANAGED_2D_VISIBLE_QUBITS_GAP = 0.02
_DEFAULT_VISIBLE_QUBITS = 15

_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"
_MANAGED_3D_MAIN_AXES_BOUNDS = (0.0, 0.0, 1.0, 1.0)
_MANAGED_3D_MAIN_AXES_WITH_SLIDER_BOUNDS = (0.0, 0.14, 1.0, 0.86)
_MANAGED_3D_SLIDER_BOUNDS = (0.18, 0.045, 0.72, 0.055)
_MANAGED_3D_MENU_BOUNDS = (0.035, 0.06, 0.2, 0.24)
_MANAGED_3D_MENU_BOUNDS_WITH_SLIDER = (0.035, 0.18, 0.2, 0.24)


@dataclass(frozen=True, slots=True)
class Managed2DSliderLayout:
    """Resolved 2D slider layout and viewport geometry."""

    main_axes_bounds: tuple[float, float, float, float]
    horizontal_axes_bounds: tuple[float, float, float, float] | None
    vertical_axes_bounds: tuple[float, float, float, float] | None
    visible_qubits_axes_bounds: tuple[float, float, float, float] | None
    viewport_width: float
    viewport_height: float

    @property
    def show_horizontal_slider(self) -> bool:
        return self.horizontal_axes_bounds is not None

    @property
    def show_vertical_slider(self) -> bool:
        return self.vertical_axes_bounds is not None

    @property
    def show_visible_qubits_box(self) -> bool:
        return self.visible_qubits_axes_bounds is not None


@dataclass(slots=True)
class Managed2DPageSliderState:
    """Typed 2D managed-slider state attached to the figure metadata."""

    figure: Figure
    axes: Axes
    scene: LayoutScene
    horizontal_slider: Slider | None
    vertical_slider: Slider | None
    visible_qubits_box: TextBox | None
    horizontal_axes: Axes | None
    vertical_axes: Axes | None
    visible_qubits_axes: Axes | None
    x_offset: float
    y_offset: float
    viewport_width: float
    viewport_height: float
    viewport_aspect_ratio: float
    total_visible_rows: int
    visible_qubits: int
    allow_figure_resize: bool
    show_visible_qubits_box: bool
    is_syncing_visible_qubits: bool = False


@dataclass(slots=True)
class Managed3DPageSliderState:
    """Typed 3D managed-slider state attached to the figure metadata."""

    figure: Figure
    axes: Axes
    pipeline: PreparedDrawPipeline
    current_scene: LayoutScene3D
    horizontal_slider: Slider | None
    horizontal_axes: Axes | None
    start_column: int
    window_size: int
    max_start_column: int
    scene_cache: dict[int, LayoutScene3D] = field(default_factory=dict)
    vertical_slider: Slider | None = None
    vertical_axes: Axes | None = None

    def show_start_column(self, start_column: int) -> None:
        """Render the requested 3D column window on the managed axes."""

        resolved_start_column = min(max(0, start_column), self.max_start_column)
        scene = self._scene_for_start_column(resolved_start_column)
        self.start_column = resolved_start_column
        self.current_scene = scene

        clear_hover_state(self.axes)
        self.axes.clear()
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


def prepare_page_slider_layout(axes: Axes, scene: LayoutScene) -> Managed2DSliderLayout:
    """Resolve the 2D slider viewport and control placement for one axes."""

    candidate_layouts: list[tuple[int, float, Managed2DSliderLayout]] = []
    for show_horizontal_slider, show_vertical_slider in (
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ):
        layout = _resolve_2d_slider_layout(
            axes,
            show_horizontal_slider=show_horizontal_slider,
            show_vertical_slider=show_vertical_slider,
            show_visible_qubits_box=False,
        )
        viewport_width, viewport_height = slider_viewport_size(axes, scene)
        needs_horizontal_slider = scene.width - viewport_width > _VIEWPORT_EPSILON
        needs_vertical_slider = scene.height - viewport_height > _VIEWPORT_EPSILON
        if not show_horizontal_slider and needs_horizontal_slider:
            continue
        if not show_vertical_slider and needs_vertical_slider:
            continue
        layout = replace(layout, viewport_width=viewport_width, viewport_height=viewport_height)
        slider_count = int(show_horizontal_slider) + int(show_vertical_slider)
        visible_area = viewport_width * viewport_height
        candidate_layouts.append((slider_count, -visible_area, layout))

    if not candidate_layouts:
        layout = _resolve_2d_slider_layout(
            axes,
            show_horizontal_slider=True,
            show_vertical_slider=True,
            show_visible_qubits_box=False,
        )
        viewport_width, viewport_height = slider_viewport_size(axes, scene)
        return replace(
            layout,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )

    _, _, selected_layout = min(candidate_layouts)
    return selected_layout


def configure_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    scene: LayoutScene,
    viewport_width: float,
    set_page_slider: Callable[[Figure, object], None],
    viewport_height: float | None = None,
    layout: Managed2DSliderLayout | None = None,
    quantum_wire_count: int | None = None,
    allow_figure_resize: bool = True,
    initial_visible_qubits: int = _DEFAULT_VISIBLE_QUBITS,
) -> None:
    """Attach and wire sliders that scroll the rendered 2D circuit."""

    resolved_layout = layout or prepare_page_slider_layout(axes, scene)
    resolved_viewport_width = (
        resolved_layout.viewport_width if layout is not None else viewport_width
    )
    resolved_viewport_height = (
        resolved_layout.viewport_height
        if layout is not None
        else (scene.height if viewport_height is None else viewport_height)
    )
    max_scroll_x = max(0.0, scene.width - resolved_viewport_width)
    max_scroll_y = max(0.0, scene.height - resolved_viewport_height)
    if max_scroll_x <= 0.0 and max_scroll_y <= 0.0:
        return

    resolved_visible_row_count = max(
        _scene_visible_row_count(scene),
        1 if quantum_wire_count is None else quantum_wire_count,
    )
    state = Managed2DPageSliderState(
        figure=figure,
        axes=axes,
        scene=scene,
        horizontal_slider=None,
        vertical_slider=None,
        visible_qubits_box=None,
        horizontal_axes=None,
        vertical_axes=None,
        visible_qubits_axes=None,
        x_offset=0.0,
        y_offset=0.0,
        viewport_width=resolved_viewport_width,
        viewport_height=resolved_viewport_height,
        viewport_aspect_ratio=(
            resolved_viewport_width / resolved_viewport_height
            if resolved_viewport_height > 0.0
            else 1.0
        ),
        total_visible_rows=resolved_visible_row_count,
        visible_qubits=_clamp_visible_qubits(
            initial_visible_qubits,
            resolved_visible_row_count,
        ),
        allow_figure_resize=allow_figure_resize,
        show_visible_qubits_box=(
            max_scroll_y > 0.0 and resolved_visible_row_count > _DEFAULT_VISIBLE_QUBITS
        ),
    )
    set_page_slider(figure, state)
    if state.show_visible_qubits_box:
        _set_visible_qubits(state, state.visible_qubits)
        return
    _apply_2d_slider_state(state)


def page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    """Return a readable managed figure size for page-slider mode."""

    width = max(4.8, viewport_width * 0.98)
    height = max(2.0, scene_height * 0.68) + 1.0
    return width, height


def slider_viewport_size(axes: Axes, scene: LayoutScene) -> tuple[float, float]:
    """Estimate the visible 2D viewport using equal X/Y scaling."""

    axes_width_pixels, axes_height_pixels = axes_viewport_pixels(axes)
    if axes_width_pixels <= 0.0 or axes_height_pixels <= 0.0:
        return scene.width, scene.height
    axes_ratio = axes_width_pixels / axes_height_pixels
    full_height_viewport_width = min(scene.width, scene.height * axes_ratio)
    uncapped_figure_width, uncapped_figure_height = page_slider_figsize(
        full_height_viewport_width,
        scene.height,
    )
    figure_width_inches, figure_height_inches = _figure_size_inches(axes.figure)
    compact_scale = min(
        1.0,
        figure_width_inches / uncapped_figure_width if uncapped_figure_width > 0.0 else 1.0,
        figure_height_inches / uncapped_figure_height if uncapped_figure_height > 0.0 else 1.0,
    )
    viewport_height = min(scene.height, scene.height * compact_scale)
    viewport_width = viewport_height * axes_ratio
    if viewport_width > scene.width:
        viewport_width = scene.width
        viewport_height = min(scene.height, viewport_width / axes_ratio)
    return viewport_width, viewport_height


def slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene width for the current slider viewport."""

    return slider_viewport_size(axes, scene)[0]


def slider_viewport_height(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene height for the current slider viewport."""

    return slider_viewport_size(axes, scene)[1]


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

    resolved_viewport_height = scene.height if viewport_height is None else viewport_height
    max_x_offset = max(0.0, scene.width - viewport_width)
    max_y_offset = max(0.0, scene.height - resolved_viewport_height)
    resolved_x_offset = min(max(0.0, x_offset), max_x_offset)
    resolved_y_offset = min(max(0.0, y_offset), max_y_offset)
    axes.set_xlim(resolved_x_offset, resolved_x_offset + viewport_width)
    axes.set_ylim(resolved_y_offset + resolved_viewport_height, resolved_y_offset)


def _apply_2d_slider_state(state: Managed2DPageSliderState) -> None:
    max_scroll_x = max(0.0, state.scene.width - state.viewport_width)
    max_scroll_y = max(0.0, state.scene.height - state.viewport_height)
    state.x_offset = min(max(0.0, state.x_offset), max_scroll_x)
    state.y_offset = min(max(0.0, state.y_offset), max_scroll_y)
    layout = _resolve_2d_slider_layout(
        state.axes,
        show_horizontal_slider=max_scroll_x > 0.0,
        show_vertical_slider=max_scroll_y > 0.0,
        show_visible_qubits_box=state.show_visible_qubits_box,
    )
    _remove_2d_controls(state)
    set_viewport_width(state.figure, viewport_width=state.viewport_width)
    set_slider_view(
        state.axes,
        state.scene,
        x_offset=state.x_offset,
        y_offset=state.y_offset,
        viewport_width=state.viewport_width,
        viewport_height=state.viewport_height,
    )
    _attach_2d_controls(state, layout)
    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


def _attach_2d_controls(
    state: Managed2DPageSliderState,
    layout: Managed2DSliderLayout,
) -> None:
    from matplotlib.widgets import Slider, TextBox

    scene = state.scene
    theme = scene.style.theme
    max_scroll_x = max(0.0, scene.width - state.viewport_width)
    max_scroll_y = max(0.0, scene.height - state.viewport_height)

    if max_scroll_x > 0.0 and layout.horizontal_axes_bounds is not None:
        horizontal_axes = state.figure.add_axes(
            layout.horizontal_axes_bounds,
            facecolor=theme.axes_facecolor,
        )
        horizontal_slider = Slider(
            ax=horizontal_axes,
            label="Scroll",
            valmin=0.0,
            valmax=max_scroll_x,
            valinit=state.x_offset,
            color=theme.gate_edgecolor,
            track_color=theme.classical_wire_color,
            handle_style={
                "facecolor": theme.accent_color,
                "edgecolor": theme.text_color,
                "size": 16,
            },
        )
        _style_slider(horizontal_slider, text_color=theme.text_color)
        horizontal_slider.on_changed(lambda value: _update_scroll(state, x_offset=float(value)))
        state.horizontal_slider = horizontal_slider
        state.horizontal_axes = horizontal_axes

    if max_scroll_y > 0.0 and layout.vertical_axes_bounds is not None:
        vertical_axes = state.figure.add_axes(
            layout.vertical_axes_bounds,
            facecolor=theme.axes_facecolor,
        )
        vertical_slider = Slider(
            ax=vertical_axes,
            label="Scroll",
            valmin=0.0,
            valmax=max_scroll_y,
            valinit=state.y_offset,
            valstep=max_scroll_y / max(1, int(round(max_scroll_y / 0.1))),
            orientation="vertical",
            color=theme.gate_edgecolor,
            track_color=theme.classical_wire_color,
            handle_style={
                "facecolor": theme.accent_color,
                "edgecolor": theme.text_color,
                "size": 12,
            },
        )
        _style_slider(vertical_slider, text_color=theme.text_color)
        vertical_slider.on_changed(lambda value: _update_scroll(state, y_offset=float(value)))
        state.vertical_slider = vertical_slider
        state.vertical_axes = vertical_axes

    if state.show_visible_qubits_box and layout.visible_qubits_axes_bounds is not None:
        visible_qubits_axes = state.figure.add_axes(
            layout.visible_qubits_axes_bounds,
            facecolor=theme.axes_facecolor,
        )
        visible_qubits_box = TextBox(
            visible_qubits_axes,
            "",
            initial=str(state.visible_qubits),
            color=theme.axes_facecolor,
            hovercolor=theme.figure_facecolor,
            textalignment="center",
        )
        _style_text_box(visible_qubits_box, text_color=theme.text_color)
        visible_qubits_box.on_submit(lambda text: _handle_visible_qubits_submit(state, text))
        state.visible_qubits_box = visible_qubits_box
        state.visible_qubits_axes = visible_qubits_axes


def _remove_2d_controls(state: Managed2DPageSliderState) -> None:
    for widget in (
        state.horizontal_slider,
        state.vertical_slider,
        state.visible_qubits_box,
    ):
        if widget is not None and hasattr(widget, "disconnect_events"):
            widget.disconnect_events()

    for axes in (
        state.horizontal_axes,
        state.vertical_axes,
        state.visible_qubits_axes,
    ):
        if axes is not None:
            axes.remove()

    state.horizontal_slider = None
    state.vertical_slider = None
    state.visible_qubits_box = None
    state.horizontal_axes = None
    state.vertical_axes = None
    state.visible_qubits_axes = None


def _update_scroll(
    state: Managed2DPageSliderState,
    *,
    x_offset: float | None = None,
    y_offset: float | None = None,
) -> None:
    if x_offset is not None:
        state.x_offset = float(x_offset)
    if y_offset is not None:
        state.y_offset = float(y_offset)
    set_slider_view(
        state.axes,
        state.scene,
        x_offset=state.x_offset,
        y_offset=state.y_offset,
        viewport_width=state.viewport_width,
        viewport_height=state.viewport_height,
    )
    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


def _handle_visible_qubits_submit(
    state: Managed2DPageSliderState,
    text: str,
) -> None:
    if state.is_syncing_visible_qubits:
        return

    try:
        requested_visible_qubits = int(text.strip())
    except ValueError:
        _sync_visible_qubits_box(state, state.visible_qubits)
        return

    _set_visible_qubits(state, requested_visible_qubits)


def _set_visible_qubits(
    state: Managed2DPageSliderState,
    requested_visible_qubits: int,
) -> None:
    resolved_visible_qubits = _clamp_visible_qubits(
        requested_visible_qubits,
        state.total_visible_rows,
    )
    state.visible_qubits = resolved_visible_qubits
    state.viewport_height = _visible_qubits_viewport_height(
        state.scene,
        visible_qubits=resolved_visible_qubits,
    )
    state.viewport_width = min(
        state.scene.width,
        state.viewport_height * max(state.viewport_aspect_ratio, _VIEWPORT_EPSILON),
    )
    if state.viewport_height > _VIEWPORT_EPSILON:
        state.viewport_aspect_ratio = state.viewport_width / state.viewport_height
    if state.allow_figure_resize:
        figure_width, figure_height = page_slider_figsize(
            state.viewport_width,
            state.viewport_height,
        )
        state.figure.set_size_inches(figure_width, figure_height, forward=True)
    _apply_2d_slider_state(state)
    _sync_visible_qubits_box(state, resolved_visible_qubits)


def _sync_visible_qubits_box(
    state: Managed2DPageSliderState,
    visible_qubits: int,
) -> None:
    if state.visible_qubits_box is None:
        return

    state.is_syncing_visible_qubits = True
    try:
        state.visible_qubits_box.set_val(str(visible_qubits))
    finally:
        state.is_syncing_visible_qubits = False


def _visible_qubits_viewport_height(
    scene: LayoutScene,
    *,
    visible_qubits: int,
) -> float:
    resolved_visible_qubits = max(1, visible_qubits)
    wire_positions = sorted(wire.y for wire in scene.wires)
    if not wire_positions or resolved_visible_qubits >= len(wire_positions):
        return scene.height

    largest_window_span = max(
        wire_positions[index + resolved_visible_qubits - 1] - wire_positions[index]
        for index in range(len(wire_positions) - resolved_visible_qubits + 1)
    )
    style = scene.style
    return min(scene.height, style.margin_top + style.margin_bottom + largest_window_span)


def _clamp_visible_qubits(
    visible_qubits: int,
    total_visible_rows: int | None,
) -> int:
    resolved_total_visible_rows = max(1, 1 if total_visible_rows is None else total_visible_rows)
    return min(max(1, visible_qubits), resolved_total_visible_rows)


def _scene_visible_row_count(scene: LayoutScene) -> int:
    return max(1, len(scene.wires))


def configure_3d_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    set_page_slider: Callable[[Figure, object], None],
) -> Managed3DPageSliderState | None:
    """Attach and wire a managed 3D slider that moves through circuit columns."""

    total_columns = len(pipeline.ir.layers)
    window_size = page_slider_window_size(pipeline.ir, pipeline.normalized_style)
    max_start_column = max(0, total_columns - window_size)
    if max_start_column <= 0:
        return None

    from matplotlib.widgets import Slider

    apply_managed_3d_axes_bounds(axes, has_page_slider=True)
    slider_axes = figure.add_axes(_MANAGED_3D_SLIDER_BOUNDS)
    state = Managed3DPageSliderState(
        figure=figure,
        axes=axes,
        pipeline=pipeline,
        current_scene=cast("LayoutScene3D", pipeline.paged_scene),
        horizontal_slider=None,
        horizontal_axes=slider_axes,
        start_column=0,
        window_size=window_size,
        max_start_column=max_start_column,
    )
    initial_scene = state._scene_for_start_column(0)
    state.current_scene = initial_scene

    slider = Slider(
        ax=slider_axes,
        label="Columns",
        valmin=0.0,
        valmax=float(max_start_column),
        valinit=0.0,
        valstep=1.0,
        color=initial_scene.style.theme.gate_edgecolor,
        track_color=initial_scene.style.theme.classical_wire_color,
        handle_style={
            "facecolor": initial_scene.style.theme.accent_color,
            "edgecolor": initial_scene.style.theme.text_color,
            "size": 16,
        },
    )
    _style_slider(slider, text_color=initial_scene.style.theme.text_color)
    slider.on_changed(lambda value: state.show_start_column(int(round(float(value)))))
    state.horizontal_slider = slider
    set_page_slider(figure, state)
    return state


def page_slider_window_size(circuit: CircuitIR, style: object) -> int:
    """Return the number of columns that fit in the first 2D page budget."""

    paging_inputs = build_layout_paging_inputs(circuit, cast("object", style))
    metrics = paged_scene_metrics_for_width(
        paging_inputs,
        max_page_width=float(getattr(style, "max_page_width")),
    )
    if not metrics.pages:
        return max(1, len(circuit.layers))
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


def managed_3d_axes_bounds(*, has_page_slider: bool) -> tuple[float, float, float, float]:
    """Return the managed 3D axes bounds for the active control layout."""

    if has_page_slider:
        return _MANAGED_3D_MAIN_AXES_WITH_SLIDER_BOUNDS
    return _MANAGED_3D_MAIN_AXES_BOUNDS


def managed_3d_menu_bounds(*, has_page_slider: bool) -> tuple[float, float, float, float]:
    """Return the managed 3D topology-menu bounds for the active control layout."""

    if has_page_slider:
        return _MANAGED_3D_MENU_BOUNDS_WITH_SLIDER
    return _MANAGED_3D_MENU_BOUNDS


def apply_managed_3d_axes_bounds(
    axes: Axes,
    *,
    has_page_slider: bool,
) -> tuple[float, float, float, float]:
    """Apply the managed 3D main-axes bounds and store the viewport metadata."""

    bounds = managed_3d_axes_bounds(has_page_slider=has_page_slider)
    axes.set_position(bounds)
    setattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, bounds)
    return bounds


def _apply_2d_main_axes_bounds(
    axes: Axes,
    *,
    show_horizontal_slider: bool,
    show_vertical_slider: bool,
    show_visible_qubits_box: bool,
) -> tuple[float, float, float, float]:
    show_left_controls = show_vertical_slider or show_visible_qubits_box
    if show_horizontal_slider and show_visible_qubits_box:
        bounds = _MANAGED_2D_MAIN_AXES_WITH_HORIZONTAL_AND_BOX_BOUNDS
    elif show_horizontal_slider and show_vertical_slider:
        bounds = _MANAGED_2D_MAIN_AXES_WITH_BOTH_BOUNDS
    elif show_horizontal_slider:
        bounds = _MANAGED_2D_MAIN_AXES_WITH_HORIZONTAL_BOUNDS
    elif show_vertical_slider:
        bounds = _MANAGED_2D_MAIN_AXES_WITH_VERTICAL_BOUNDS
    elif show_left_controls:
        bounds = _MANAGED_2D_MAIN_AXES_WITH_LEFT_CONTROLS_BOUNDS
    else:
        bounds = _MANAGED_2D_MAIN_AXES_BOUNDS
    axes.set_position(bounds)
    return bounds


def _resolve_2d_slider_layout(
    axes: Axes,
    *,
    show_horizontal_slider: bool,
    show_vertical_slider: bool,
    show_visible_qubits_box: bool,
) -> Managed2DSliderLayout:
    main_axes_bounds = _apply_2d_main_axes_bounds(
        axes,
        show_horizontal_slider=show_horizontal_slider,
        show_vertical_slider=show_vertical_slider,
        show_visible_qubits_box=show_visible_qubits_box,
    )
    return Managed2DSliderLayout(
        main_axes_bounds=main_axes_bounds,
        horizontal_axes_bounds=(
            _horizontal_slider_bounds(main_axes_bounds) if show_horizontal_slider else None
        ),
        vertical_axes_bounds=(
            _vertical_slider_bounds(
                main_axes_bounds,
                show_horizontal_slider=show_horizontal_slider,
                show_visible_qubits_box=show_visible_qubits_box,
            )
            if show_vertical_slider
            else None
        ),
        visible_qubits_axes_bounds=(
            _visible_qubits_box_bounds(show_horizontal_slider=show_horizontal_slider)
            if show_visible_qubits_box
            else None
        ),
        viewport_width=0.0,
        viewport_height=0.0,
    )


def _horizontal_slider_bounds(
    main_axes_bounds: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    left, _, width, _ = main_axes_bounds
    return (
        max(0.08, left),
        _MANAGED_2D_HORIZONTAL_SLIDER_BOTTOM,
        min(width, 0.88 - max(0.08, left) + 0.08),
        _MANAGED_2D_HORIZONTAL_SLIDER_HEIGHT,
    )


def _vertical_slider_bounds(
    main_axes_bounds: tuple[float, float, float, float],
    *,
    show_horizontal_slider: bool,
    show_visible_qubits_box: bool,
) -> tuple[float, float, float, float]:
    _, bottom, _, height = main_axes_bounds
    slider_bottom = bottom
    if show_visible_qubits_box:
        _, box_bottom, _, box_height = _visible_qubits_box_bounds(
            show_horizontal_slider=show_horizontal_slider
        )
        slider_bottom = max(
            slider_bottom,
            box_bottom + box_height + _MANAGED_2D_VISIBLE_QUBITS_GAP,
        )
    slider_height = max(_VIEWPORT_EPSILON, bottom + height - slider_bottom)
    slider_left = _MANAGED_2D_LEFT_CONTROL_LEFT + (
        (_MANAGED_2D_LEFT_CONTROL_WIDTH - _MANAGED_2D_VERTICAL_SLIDER_WIDTH) / 2.0
    )
    return (
        slider_left,
        slider_bottom,
        _MANAGED_2D_VERTICAL_SLIDER_WIDTH,
        slider_height,
    )


def _visible_qubits_box_bounds(
    *,
    show_horizontal_slider: bool,
) -> tuple[float, float, float, float]:
    bottom = (
        _MANAGED_2D_VISIBLE_QUBITS_BOTTOM_WITH_HORIZONTAL
        if show_horizontal_slider
        else _MANAGED_2D_VISIBLE_QUBITS_BOTTOM
    )
    return (
        _MANAGED_2D_LEFT_CONTROL_LEFT,
        bottom,
        _MANAGED_2D_VISIBLE_QUBITS_WIDTH,
        _MANAGED_2D_VISIBLE_QUBITS_HEIGHT,
    )


def _style_slider(slider: Slider, *, text_color: str) -> None:
    slider.label.set_color(text_color)
    slider.valtext.set_visible(False)
    if hasattr(slider, "track"):
        slider.track.set_alpha(0.45)
    if hasattr(slider, "poly"):
        slider.poly.set_alpha(0.75)
    if hasattr(slider, "vline"):
        slider.vline.set_linewidth(3.0)


def _style_text_box(text_box: TextBox, *, text_color: str) -> None:
    text_box.label.set_visible(False)
    if hasattr(text_box, "text_disp"):
        text_box.text_disp.set_color(text_color)
        text_box.text_disp.set_fontsize(9.5)
    if hasattr(text_box, "cursor"):
        text_box.cursor.set_color(text_color)
        text_box.cursor.set_linewidth(1.6)
    text_box.ax.set_title("")
    text_box.ax.tick_params(
        left=False,
        bottom=False,
        labelleft=False,
        labelbottom=False,
    )
    for spine in text_box.ax.spines.values():
        spine.set_color(text_color)


def _figure_size_inches(figure: object) -> tuple[float, float]:
    if hasattr(figure, "get_size_inches"):
        size_inches = getattr(figure, "get_size_inches")()
        return float(size_inches[0]), float(size_inches[1])
    parent_figure = getattr(figure, "figure")
    size_inches = parent_figure.get_size_inches()
    return float(size_inches[0]), float(size_inches[1])
