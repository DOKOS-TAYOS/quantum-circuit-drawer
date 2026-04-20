"""Managed slider helpers for 2D and 3D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ._draw_managed_viewport import (
    axes_viewport_pixels,
    build_continuous_slider_scene,
)
from ._draw_pipeline import PreparedDrawPipeline, _compute_3d_scene
from ._managed_3d_view_state import (
    _MANAGED_3D_FIXED_VIEW_STATE_ATTR,
    capture_managed_3d_view_state,
)
from ._managed_ui_palette import ManagedUiPalette, managed_ui_palette
from .ir.circuit import CircuitIR
from .layout._layering import normalized_draw_circuit
from .layout._layout_scaffold import build_layout_paging_inputs, paged_scene_metrics_for_width
from .layout.scene import (
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneMeasurement,
    SceneSwap,
    SceneText,
    SceneWire,
)
from .layout.scene_3d import LayoutScene3D
from .renderers._matplotlib_figure import clear_hover_state, set_viewport_width
from .style import DrawStyle
from .typing import LayoutEngine3DLike, LayoutEngineLike

if TYPE_CHECKING:
    from matplotlib.widgets import Button, Slider, TextBox
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from .layout.topology_3d import TopologyName
    from .renderers.matplotlib_renderer import MatplotlibRenderer

_VIEWPORT_EPSILON = 1e-6

_MANAGED_2D_MAIN_AXES_BOUNDS = (0.02, 0.02, 0.96, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_HORIZONTAL_BOUNDS = (0.02, 0.18, 0.96, 0.8)
_MANAGED_2D_MAIN_AXES_WITH_VERTICAL_BOUNDS = (0.14, 0.02, 0.84, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_BOTH_BOUNDS = (0.14, 0.18, 0.84, 0.8)
_MANAGED_2D_MAIN_AXES_WITH_LEFT_CONTROLS_BOUNDS = (0.14, 0.02, 0.84, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_HORIZONTAL_AND_BOX_BOUNDS = (0.14, 0.18, 0.84, 0.8)
_MANAGED_2D_HORIZONTAL_SLIDER_HEIGHT = 0.06
_MANAGED_2D_HORIZONTAL_SLIDER_BOTTOM = 0.05
_MANAGED_2D_LEFT_CONTROL_LEFT = 0.04
_MANAGED_2D_LEFT_CONTROL_WIDTH = 0.09
_MANAGED_2D_VERTICAL_SLIDER_WIDTH = 0.021
_MANAGED_2D_VISIBLE_QUBITS_WIDTH = 0.055
_MANAGED_2D_VISIBLE_QUBITS_HEIGHT = 0.045
_MANAGED_2D_VISIBLE_QUBITS_BOTTOM = 0.05
_MANAGED_2D_VISIBLE_QUBITS_BOTTOM_WITH_HORIZONTAL = 0.12
_MANAGED_2D_VISIBLE_QUBITS_GAP = 0.02
_MANAGED_2D_VERTICAL_SLIDER_TOP_INSET = 0.035
_MANAGED_2D_VERTICAL_SLIDER_BOTTOM_INSET = 0.02
_MANAGED_2D_STEPPER_BUTTON_WIDTH = 0.024
_MANAGED_2D_STEPPER_BUTTON_GAP = 0.006
_DEFAULT_VISIBLE_QUBITS = 15

_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"
_MANAGED_3D_MAIN_AXES_BOUNDS = (0.0, 0.0, 1.0, 1.0)
_MANAGED_3D_MAIN_AXES_WITH_SLIDER_BOUNDS = (0.0, 0.14, 1.0, 0.86)
_MANAGED_3D_SLIDER_BOUNDS = (0.18, 0.05, 0.72, 0.06)
_MANAGED_3D_MENU_BOUNDS = (0.035, 0.06, 0.2, 0.24)
_MANAGED_3D_MENU_BOUNDS_WITH_SLIDER = (0.035, 0.18, 0.2, 0.24)


@dataclass(frozen=True, slots=True)
class Managed2DSliderLayout:
    """Resolved 2D slider layout and viewport geometry."""

    main_axes_bounds: tuple[float, float, float, float]
    horizontal_axes_bounds: tuple[float, float, float, float] | None
    vertical_axes_bounds: tuple[float, float, float, float] | None
    visible_qubits_axes_bounds: tuple[float, float, float, float] | None
    visible_qubits_decrement_axes_bounds: tuple[float, float, float, float] | None
    visible_qubits_increment_axes_bounds: tuple[float, float, float, float] | None
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
    circuit: CircuitIR
    layout_engine: LayoutEngineLike
    renderer: MatplotlibRenderer
    style: DrawStyle
    full_scene: LayoutScene
    scene: LayoutScene
    column_widths: tuple[float, ...]
    total_scene_width: float
    total_column_count: int
    horizontal_slider: Slider | None
    vertical_slider: Slider | None
    visible_qubits_box: TextBox | None
    visible_qubits_decrement_button: Button | None
    visible_qubits_increment_button: Button | None
    horizontal_axes: Axes | None
    vertical_axes: Axes | None
    visible_qubits_axes: Axes | None
    visible_qubits_decrement_axes: Axes | None
    visible_qubits_increment_axes: Axes | None
    start_column: int
    max_start_column: int
    start_row: int
    max_start_row: int
    viewport_width: float
    viewport_height: float
    viewport_aspect_ratio: float
    total_visible_rows: int
    visible_qubits: int
    allow_figure_resize: bool
    show_visible_qubits_box: bool
    layout: Managed2DSliderLayout | None = None
    horizontal_scene_cache: dict[int, LayoutScene] = field(default_factory=dict)
    window_scene_cache: dict[tuple[int, int], LayoutScene] = field(default_factory=dict)
    is_syncing_visible_qubits: bool = False

    def show_start_column(self, start_column: int) -> None:
        """Render the requested horizontal start column."""

        self.start_column = int(start_column)
        _apply_2d_slider_state(self)

    def show_start_row(self, start_row: int) -> None:
        """Render the requested vertical start row."""

        self.start_row = int(start_row)
        _apply_2d_slider_state(self)


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
    scene_cache: dict[int, LayoutScene3D] = field(default_factory=dict)
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
    circuit: CircuitIR | None = None,
    layout_engine: LayoutEngineLike | None = None,
    renderer: MatplotlibRenderer | None = None,
    normalized_style: DrawStyle | None = None,
) -> None:
    """Attach and wire sliders that redraw one discrete 2D window at a time."""

    if circuit is None or layout_engine is None or renderer is None:
        resolved_viewport_height = scene.height if viewport_height is None else viewport_height
        max_scroll_x = max(0.0, scene.width - viewport_width)
        max_scroll_y = max(0.0, scene.height - resolved_viewport_height)
        if max_scroll_x <= 0.0 and max_scroll_y <= 0.0:
            return
        raise ValueError(
            "discrete 2D page slider requires circuit, layout_engine, and renderer context"
        )

    resolved_layout = layout or prepare_page_slider_layout(axes, scene)
    resolved_viewport_width = (
        resolved_layout.viewport_width
        if resolved_layout.viewport_width > _VIEWPORT_EPSILON
        else viewport_width
    )
    resolved_viewport_height = (
        resolved_layout.viewport_height
        if resolved_layout.viewport_height > _VIEWPORT_EPSILON
        else (scene.height if viewport_height is None else viewport_height)
    )

    resolved_visible_row_count = max(
        _scene_visible_row_count(scene),
        1 if quantum_wire_count is None else quantum_wire_count,
    )
    resolved_visible_qubits = _clamp_visible_qubits(
        initial_visible_qubits,
        resolved_visible_row_count,
    )

    resolved_style = scene.style if normalized_style is None else normalized_style
    normalized_circuit = normalized_draw_circuit(circuit)
    paging_inputs = build_layout_paging_inputs(normalized_circuit, resolved_style)
    total_scene_width = paged_scene_metrics_for_width(
        paging_inputs,
        max_page_width=float("inf"),
    ).scene_width
    initial_viewport_height = _visible_qubits_viewport_height(
        scene,
        visible_qubits=resolved_visible_qubits,
    )
    initial_viewport_width = min(
        total_scene_width,
        initial_viewport_height
        * max(
            resolved_viewport_width / max(resolved_viewport_height, _VIEWPORT_EPSILON),
            _VIEWPORT_EPSILON,
        ),
    )
    if (
        total_scene_width - initial_viewport_width <= _VIEWPORT_EPSILON
        and resolved_visible_row_count <= resolved_visible_qubits
    ):
        clear_hover_state(axes)
        axes.clear()
        axes.set_position(resolved_layout.main_axes_bounds)
        setattr(axes, "_quantum_circuit_drawer_windowed_clip", False)
        set_viewport_width(figure, viewport_width=scene.width)
        renderer.render(scene, ax=axes)
        return

    state = Managed2DPageSliderState(
        figure=figure,
        axes=axes,
        circuit=normalized_circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        style=resolved_style,
        full_scene=scene,
        scene=scene,
        column_widths=tuple(paging_inputs.column_widths),
        total_scene_width=total_scene_width,
        total_column_count=len(normalized_circuit.layers),
        horizontal_slider=None,
        vertical_slider=None,
        visible_qubits_box=None,
        visible_qubits_decrement_button=None,
        visible_qubits_increment_button=None,
        horizontal_axes=None,
        vertical_axes=None,
        visible_qubits_axes=None,
        visible_qubits_decrement_axes=None,
        visible_qubits_increment_axes=None,
        start_column=0,
        max_start_column=0,
        start_row=0,
        max_start_row=0,
        viewport_width=initial_viewport_width,
        viewport_height=initial_viewport_height,
        viewport_aspect_ratio=(
            resolved_viewport_width / resolved_viewport_height
            if resolved_viewport_height > 0.0
            else 1.0
        ),
        total_visible_rows=resolved_visible_row_count,
        visible_qubits=resolved_visible_qubits,
        allow_figure_resize=allow_figure_resize,
        show_visible_qubits_box=resolved_visible_row_count > _DEFAULT_VISIBLE_QUBITS,
        layout=None,
    )
    set_page_slider(figure, state)
    _apply_2d_slider_state(state)
    _sync_visible_qubits_box(state, state.visible_qubits)


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
    max_start_column = max(0, state.total_column_count - 1)
    state.max_start_column = max_start_column if _has_horizontal_overflow(state) else 0
    state.max_start_row = max(0, state.total_visible_rows - state.visible_qubits)
    state.start_column = min(max(0, state.start_column), state.max_start_column)
    state.start_row = min(max(0, state.start_row), state.max_start_row)
    layout = _resolve_2d_slider_layout(
        state.axes,
        show_horizontal_slider=state.max_start_column > 0,
        show_vertical_slider=state.max_start_row > 0,
        show_visible_qubits_box=state.show_visible_qubits_box,
    )
    rebuild_controls = _needs_2d_control_rebuild(state, layout)
    if rebuild_controls:
        _remove_2d_controls(state)
    state.scene = _scene_for_current_window(state)
    clear_hover_state(state.axes)
    state.axes.clear()
    state.axes.set_position(layout.main_axes_bounds)
    setattr(state.axes, "_quantum_circuit_drawer_windowed_clip", True)
    set_viewport_width(state.figure, viewport_width=state.viewport_width)
    state.renderer.render(state.scene, ax=state.axes)
    set_slider_view(
        state.axes,
        state.scene,
        x_offset=0.0,
        viewport_width=state.viewport_width,
        y_offset=0.0,
        viewport_height=state.viewport_height,
    )
    if rebuild_controls:
        _attach_2d_controls(state, layout)
    state.layout = layout
    _sync_horizontal_slider(state)
    _sync_vertical_slider(state)
    _sync_visible_qubits_box(state, state.visible_qubits)
    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


def _attach_2d_controls(
    state: Managed2DPageSliderState,
    layout: Managed2DSliderLayout,
) -> None:
    from matplotlib.widgets import Button, Slider, TextBox

    theme = state.style.theme
    palette = managed_ui_palette(theme)

    if state.max_start_column > 0 and layout.horizontal_axes_bounds is not None:
        horizontal_axes = state.figure.add_axes(
            layout.horizontal_axes_bounds,
            facecolor=palette.surface_facecolor,
        )
        _style_control_axes(horizontal_axes, palette=palette)
        horizontal_slider = Slider(
            ax=horizontal_axes,
            label="",
            valmin=0.0,
            valmax=float(state.max_start_column),
            valinit=float(state.start_column),
            valstep=1.0,
            color=palette.slider_fill_color,
            track_color=palette.slider_track_color,
            handle_style={
                "facecolor": palette.accent_color,
                "edgecolor": palette.accent_edgecolor,
                "size": 16,
            },
        )
        _style_slider(horizontal_slider, palette=palette)
        horizontal_slider.on_changed(
            lambda value: state.show_start_column(int(round(float(value))))
        )
        state.horizontal_slider = horizontal_slider
        state.horizontal_axes = horizontal_axes

    if state.max_start_row > 0 and layout.vertical_axes_bounds is not None:
        vertical_axes = state.figure.add_axes(
            layout.vertical_axes_bounds,
            facecolor=palette.surface_facecolor,
        )
        _style_control_axes(vertical_axes, palette=palette)
        vertical_slider = Slider(
            ax=vertical_axes,
            label="",
            valmin=0.0,
            valmax=float(state.max_start_row),
            valinit=_vertical_slider_value_for_start_row(state, state.start_row),
            valstep=1.0,
            orientation="vertical",
            color=palette.slider_fill_color,
            track_color=palette.slider_track_color,
            handle_style={
                "facecolor": palette.accent_color,
                "edgecolor": palette.accent_edgecolor,
                "size": 12,
            },
        )
        _style_slider(vertical_slider, palette=palette)
        vertical_slider.on_changed(
            lambda value: state.show_start_row(_start_row_for_vertical_slider_value(state, value))
        )
        state.vertical_slider = vertical_slider
        state.vertical_axes = vertical_axes

    if state.show_visible_qubits_box and layout.visible_qubits_axes_bounds is not None:
        visible_qubits_axes = state.figure.add_axes(
            layout.visible_qubits_axes_bounds,
            facecolor=palette.surface_facecolor,
        )
        _style_control_axes(visible_qubits_axes, palette=palette)
        visible_qubits_box = TextBox(
            visible_qubits_axes,
            "",
            initial=str(state.visible_qubits),
            color=palette.surface_facecolor,
            hovercolor=palette.surface_hover_facecolor,
            textalignment="center",
        )
        _style_text_box(
            visible_qubits_box,
            text_color=palette.text_color,
            border_color=palette.surface_edgecolor,
            facecolor=palette.surface_facecolor,
        )
        visible_qubits_box.on_submit(lambda text: _handle_visible_qubits_submit(state, text))
        state.visible_qubits_box = visible_qubits_box
        state.visible_qubits_axes = visible_qubits_axes
        if layout.visible_qubits_increment_axes_bounds is not None:
            visible_qubits_increment_axes = state.figure.add_axes(
                layout.visible_qubits_increment_axes_bounds,
                facecolor=palette.surface_facecolor,
            )
            _style_control_axes(visible_qubits_increment_axes, palette=palette)
            visible_qubits_increment_button = Button(
                visible_qubits_increment_axes,
                "\u25b4",
                color=palette.surface_facecolor,
                hovercolor=palette.surface_hover_facecolor,
            )
            _style_stepper_button(visible_qubits_increment_button, palette=palette)
            visible_qubits_increment_button.on_clicked(
                lambda _: _set_visible_qubits(state, state.visible_qubits + 1)
            )
            state.visible_qubits_increment_button = visible_qubits_increment_button
            state.visible_qubits_increment_axes = visible_qubits_increment_axes
        if layout.visible_qubits_decrement_axes_bounds is not None:
            visible_qubits_decrement_axes = state.figure.add_axes(
                layout.visible_qubits_decrement_axes_bounds,
                facecolor=palette.surface_facecolor,
            )
            _style_control_axes(visible_qubits_decrement_axes, palette=palette)
            visible_qubits_decrement_button = Button(
                visible_qubits_decrement_axes,
                "\u25be",
                color=palette.surface_facecolor,
                hovercolor=palette.surface_hover_facecolor,
            )
            _style_stepper_button(visible_qubits_decrement_button, palette=palette)
            visible_qubits_decrement_button.on_clicked(
                lambda _: _set_visible_qubits(state, state.visible_qubits - 1)
            )
            state.visible_qubits_decrement_button = visible_qubits_decrement_button
            state.visible_qubits_decrement_axes = visible_qubits_decrement_axes


def _remove_2d_controls(state: Managed2DPageSliderState) -> None:
    for widget in (
        state.horizontal_slider,
        state.vertical_slider,
        state.visible_qubits_box,
        state.visible_qubits_decrement_button,
        state.visible_qubits_increment_button,
    ):
        if widget is not None and hasattr(widget, "disconnect_events"):
            widget.disconnect_events()

    for axes in (
        state.horizontal_axes,
        state.vertical_axes,
        state.visible_qubits_axes,
        state.visible_qubits_decrement_axes,
        state.visible_qubits_increment_axes,
    ):
        if axes is not None:
            axes.remove()

    state.horizontal_slider = None
    state.vertical_slider = None
    state.visible_qubits_box = None
    state.visible_qubits_decrement_button = None
    state.visible_qubits_increment_button = None
    state.horizontal_axes = None
    state.vertical_axes = None
    state.visible_qubits_axes = None
    state.visible_qubits_decrement_axes = None
    state.visible_qubits_increment_axes = None
    state.layout = None


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
        state.full_scene,
        visible_qubits=resolved_visible_qubits,
    )
    state.viewport_width = min(
        state.total_scene_width,
        state.viewport_height * max(state.viewport_aspect_ratio, _VIEWPORT_EPSILON),
    )
    if state.viewport_height > _VIEWPORT_EPSILON:
        state.viewport_aspect_ratio = state.viewport_width / state.viewport_height
    state.horizontal_scene_cache.clear()
    state.window_scene_cache.clear()
    state.layout = None
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


def _sync_horizontal_slider(state: Managed2DPageSliderState) -> None:
    if state.horizontal_slider is None:
        return
    _set_slider_value_silently(state.horizontal_slider, float(state.start_column))


def _sync_vertical_slider(state: Managed2DPageSliderState) -> None:
    if state.vertical_slider is None:
        return
    _set_slider_value_silently(
        state.vertical_slider,
        _vertical_slider_value_for_start_row(state, state.start_row),
    )


def _set_slider_value_silently(slider: Slider, value: float) -> None:
    if float(slider.val) == float(value):
        return

    previous_event_state = slider.eventson
    slider.eventson = False
    try:
        slider.set_val(float(value))
    finally:
        slider.eventson = previous_event_state


def _vertical_slider_value_for_start_row(
    state: Managed2DPageSliderState,
    start_row: int,
) -> float:
    return float(state.max_start_row - min(max(0, start_row), state.max_start_row))


def _start_row_for_vertical_slider_value(
    state: Managed2DPageSliderState,
    value: float,
) -> int:
    resolved_value = int(round(float(value)))
    return min(max(0, state.max_start_row - resolved_value), state.max_start_row)


def _visible_qubits_viewport_height(
    scene: LayoutScene,
    *,
    visible_qubits: int,
) -> float:
    resolved_visible_qubits = max(1, visible_qubits)
    wire_positions = sorted(wire.y for wire in scene.wires)
    if not wire_positions:
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


def _needs_2d_control_rebuild(
    state: Managed2DPageSliderState,
    layout: Managed2DSliderLayout,
) -> bool:
    if state.layout is None:
        return True

    if state.layout.horizontal_axes_bounds != layout.horizontal_axes_bounds:
        return True
    if state.layout.vertical_axes_bounds != layout.vertical_axes_bounds:
        return True
    if state.layout.visible_qubits_axes_bounds != layout.visible_qubits_axes_bounds:
        return True
    if (
        state.layout.visible_qubits_decrement_axes_bounds
        != layout.visible_qubits_decrement_axes_bounds
    ):
        return True
    if (
        state.layout.visible_qubits_increment_axes_bounds
        != layout.visible_qubits_increment_axes_bounds
    ):
        return True

    if (state.horizontal_slider is None) != (layout.horizontal_axes_bounds is None):
        return True
    if (state.vertical_slider is None) != (layout.vertical_axes_bounds is None):
        return True
    if (state.visible_qubits_box is None) != (layout.visible_qubits_axes_bounds is None):
        return True
    if (state.visible_qubits_decrement_button is None) != (
        layout.visible_qubits_decrement_axes_bounds is None
    ):
        return True
    if (state.visible_qubits_increment_button is None) != (
        layout.visible_qubits_increment_axes_bounds is None
    ):
        return True

    if state.horizontal_slider is not None and state.horizontal_slider.valmax != float(
        state.max_start_column
    ):
        return True
    if state.vertical_slider is not None and state.vertical_slider.valmax != float(
        state.max_start_row
    ):
        return True

    return False


def _has_horizontal_overflow(state: Managed2DPageSliderState) -> bool:
    return state.total_scene_width - state.viewport_width > _VIEWPORT_EPSILON


def _scene_for_current_window(state: Managed2DPageSliderState) -> LayoutScene:
    cache_key = (state.start_column, state.start_row)
    cached_scene = state.window_scene_cache.get(cache_key)
    if cached_scene is not None:
        return cached_scene

    horizontal_scene = _horizontal_scene_for_start_column(state, state.start_column)
    if state.max_start_row <= 0:
        state.window_scene_cache[cache_key] = horizontal_scene
        return horizontal_scene

    window_scene = _row_window_scene(
        horizontal_scene,
        start_row=state.start_row,
        visible_qubits=state.visible_qubits,
    )
    state.window_scene_cache[cache_key] = window_scene
    return window_scene


def _horizontal_scene_for_start_column(
    state: Managed2DPageSliderState,
    start_column: int,
) -> LayoutScene:
    cached_scene = state.horizontal_scene_cache.get(start_column)
    if cached_scene is not None:
        return cached_scene

    resolved_start_column = min(max(0, start_column), max(0, state.total_column_count - 1))
    end_column = _window_end_column(
        state.column_widths,
        state.style,
        start_column=resolved_start_column,
        max_scene_width=state.viewport_width,
    )
    window_scene = _width_budgeted_horizontal_scene(
        state,
        start_column=resolved_start_column,
        estimated_end_column=end_column,
    )
    window_scene.hover = state.full_scene.hover
    state.horizontal_scene_cache[resolved_start_column] = window_scene
    return window_scene


def _width_budgeted_horizontal_scene(
    state: Managed2DPageSliderState,
    *,
    start_column: int,
    estimated_end_column: int,
) -> LayoutScene:
    max_end_column = max(0, state.total_column_count - 1)
    resolved_end_column = min(max(start_column, estimated_end_column), max_end_column)
    window_scene = _continuous_horizontal_scene(
        state,
        start_column=start_column,
        end_column=resolved_end_column,
    )

    while (
        window_scene.width > state.viewport_width + _VIEWPORT_EPSILON
        and resolved_end_column > start_column
    ):
        resolved_end_column -= 1
        window_scene = _continuous_horizontal_scene(
            state,
            start_column=start_column,
            end_column=resolved_end_column,
        )

    candidate_end_column = resolved_end_column + 1
    while candidate_end_column <= max_end_column:
        candidate_scene = _continuous_horizontal_scene(
            state,
            start_column=start_column,
            end_column=candidate_end_column,
        )
        if candidate_scene.width > state.viewport_width + _VIEWPORT_EPSILON:
            break
        window_scene = candidate_scene
        candidate_end_column += 1

    return window_scene


def _continuous_horizontal_scene(
    state: Managed2DPageSliderState,
    *,
    start_column: int,
    end_column: int,
) -> LayoutScene:
    windowed_circuit = circuit_window(
        state.circuit,
        start_column=start_column,
        window_size=max(1, end_column - start_column + 1),
    )
    return build_continuous_slider_scene(
        windowed_circuit,
        state.layout_engine,
        state.style,
        hover_enabled=state.full_scene.hover.enabled,
    )


def _window_end_column(
    column_widths: tuple[float, ...],
    style: DrawStyle,
    *,
    start_column: int,
    max_scene_width: float,
) -> int:
    current_scene_width = style.margin_left + style.margin_right
    end_column = start_column
    for column in range(start_column, len(column_widths)):
        additional_width = column_widths[column]
        if column > start_column:
            additional_width += style.layer_spacing
        proposed_scene_width = current_scene_width + additional_width
        if column > start_column and proposed_scene_width > max_scene_width + _VIEWPORT_EPSILON:
            break
        current_scene_width = proposed_scene_width
        end_column = column
    return end_column


def _row_window_scene(
    scene: LayoutScene,
    *,
    start_row: int,
    visible_qubits: int,
) -> LayoutScene:
    visible_wires = tuple(scene.wires[start_row : start_row + visible_qubits])
    if not visible_wires:
        return scene

    first_wire_y = visible_wires[0].y
    last_wire_y = visible_wires[-1].y
    style = scene.style
    window_top = first_wire_y - style.margin_top
    window_bottom = last_wire_y + style.margin_bottom
    y_shift = style.margin_top - first_wire_y
    window_height = style.margin_top + style.margin_bottom + (last_wire_y - first_wire_y)
    visible_wire_ids = {wire.id for wire in visible_wires}

    return LayoutScene(
        width=scene.width,
        height=window_height,
        page_height=window_height,
        style=scene.style,
        wires=tuple(_shift_wire(wire, y_shift=y_shift) for wire in visible_wires),
        gates=tuple(
            _shift_gate(gate, y_shift=y_shift)
            for gate in scene.gates
            if _intersects_range(
                gate.y - (gate.height / 2.0),
                gate.y + (gate.height / 2.0),
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        gate_annotations=tuple(
            _shift_gate_annotation(annotation, y_shift=y_shift)
            for annotation in scene.gate_annotations
            if _intersects_range(
                annotation.y,
                annotation.y,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        controls=tuple(
            _shift_control(control, y_shift=y_shift)
            for control in scene.controls
            if _intersects_range(
                control.y,
                control.y,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        connections=tuple(
            _shift_connection(connection, y_shift=y_shift)
            for connection in scene.connections
            if _intersects_range(
                connection.y_start,
                connection.y_end,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        swaps=tuple(
            _shift_swap(swap, y_shift=y_shift)
            for swap in scene.swaps
            if _intersects_range(
                swap.y_top,
                swap.y_bottom,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        barriers=tuple(
            _shift_barrier(barrier, y_shift=y_shift)
            for barrier in scene.barriers
            if _intersects_range(
                barrier.y_top,
                barrier.y_bottom,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        measurements=tuple(
            _shift_measurement(measurement, y_shift=y_shift)
            for measurement in scene.measurements
            if _measurement_intersects_range(
                measurement,
                window_top=window_top,
                window_bottom=window_bottom,
            )
        ),
        texts=tuple(
            _shift_text(text, y_shift=y_shift)
            for text in scene.texts
            if getattr(text, "text", "")
            and _text_matches_visible_wire(text, scene, visible_wire_ids)
        ),
        pages=((replace(scene.pages[0], y_offset=0.0),) if scene.pages else ()),
        hover=scene.hover,
        wire_y_positions={
            wire_id: wire_y + y_shift
            for wire_id, wire_y in scene.wire_y_positions.items()
            if wire_id in visible_wire_ids
        },
        page_count_for_text_scale=1,
    )


def _intersects_range(
    start: float,
    end: float,
    *,
    window_top: float,
    window_bottom: float,
) -> bool:
    lower = min(start, end)
    upper = max(start, end)
    return upper >= window_top - _VIEWPORT_EPSILON and lower <= window_bottom + _VIEWPORT_EPSILON


def _measurement_intersects_range(
    measurement: SceneMeasurement,
    *,
    window_top: float,
    window_bottom: float,
) -> bool:
    measurement_top = measurement.quantum_y - (measurement.height / 2.0)
    measurement_bottom = measurement.quantum_y + (measurement.height / 2.0)
    lower = measurement_top
    upper = measurement_bottom
    if measurement.classical_y is not None:
        lower = min(lower, measurement.classical_y, measurement.connector_y)
        upper = max(upper, measurement.classical_y, measurement.connector_y)
    return upper >= window_top - _VIEWPORT_EPSILON and lower <= window_bottom + _VIEWPORT_EPSILON


def _text_matches_visible_wire(
    text: SceneText,
    scene: LayoutScene,
    visible_wire_ids: set[str],
) -> bool:
    for wire in scene.wires:
        if wire.id in visible_wire_ids and abs(wire.y - text.y) <= _VIEWPORT_EPSILON:
            return True
    return False


def _shift_wire(wire: SceneWire, *, y_shift: float) -> SceneWire:
    return replace(wire, y=wire.y + y_shift)


def _shift_gate(gate: SceneGate, *, y_shift: float) -> SceneGate:
    return replace(gate, y=gate.y + y_shift)


def _shift_gate_annotation(
    annotation: SceneGateAnnotation,
    *,
    y_shift: float,
) -> SceneGateAnnotation:
    return replace(annotation, y=annotation.y + y_shift)


def _shift_control(control: SceneControl, *, y_shift: float) -> SceneControl:
    return replace(control, y=control.y + y_shift)


def _shift_connection(connection: SceneConnection, *, y_shift: float) -> SceneConnection:
    return replace(
        connection,
        y_start=connection.y_start + y_shift,
        y_end=connection.y_end + y_shift,
    )


def _shift_swap(swap: SceneSwap, *, y_shift: float) -> SceneSwap:
    return replace(
        swap,
        y_top=swap.y_top + y_shift,
        y_bottom=swap.y_bottom + y_shift,
    )


def _shift_barrier(barrier: SceneBarrier, *, y_shift: float) -> SceneBarrier:
    return replace(
        barrier,
        y_top=barrier.y_top + y_shift,
        y_bottom=barrier.y_bottom + y_shift,
    )


def _shift_measurement(
    measurement: SceneMeasurement,
    *,
    y_shift: float,
) -> SceneMeasurement:
    return replace(
        measurement,
        quantum_y=measurement.quantum_y + y_shift,
        classical_y=(
            None if measurement.classical_y is None else measurement.classical_y + y_shift
        ),
        connector_y=measurement.connector_y + y_shift,
    )


def _shift_text(text: SceneText, *, y_shift: float) -> SceneText:
    return replace(text, y=text.y + y_shift)


def configure_3d_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    set_page_slider: Callable[[Figure, object], None],
) -> Managed3DPageSliderState | None:
    """Attach and wire a managed 3D slider that moves through circuit columns."""

    from ._draw_managed_page_window_3d import windowed_3d_page_ranges

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
    slider.on_changed(lambda value: state.show_start_column(int(round(float(value)))))
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
        visible_qubits_decrement_axes_bounds=(
            _visible_qubits_stepper_bounds(
                show_horizontal_slider=show_horizontal_slider,
                increasing=False,
            )
            if show_visible_qubits_box
            else None
        ),
        visible_qubits_increment_axes_bounds=(
            _visible_qubits_stepper_bounds(
                show_horizontal_slider=show_horizontal_slider,
                increasing=True,
            )
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
            box_bottom
            + box_height
            + _MANAGED_2D_VISIBLE_QUBITS_GAP
            + _MANAGED_2D_VERTICAL_SLIDER_BOTTOM_INSET,
        )
    slider_top = bottom + height - _MANAGED_2D_VERTICAL_SLIDER_TOP_INSET
    slider_height = max(_VIEWPORT_EPSILON, slider_top - slider_bottom)
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


def _visible_qubits_stepper_bounds(
    *,
    show_horizontal_slider: bool,
    increasing: bool,
) -> tuple[float, float, float, float]:
    box_left, box_bottom, box_width, box_height = _visible_qubits_box_bounds(
        show_horizontal_slider=show_horizontal_slider
    )
    button_height = (box_height - 0.004) / 2.0
    button_left = box_left + box_width + _MANAGED_2D_STEPPER_BUTTON_GAP
    button_bottom = box_bottom + box_height - button_height if increasing else box_bottom
    return (
        button_left,
        button_bottom,
        _MANAGED_2D_STEPPER_BUTTON_WIDTH,
        button_height,
    )


def _style_control_axes(axes: Axes, *, palette: ManagedUiPalette) -> None:
    axes.set_facecolor(palette.surface_facecolor)
    axes.tick_params(
        left=False,
        bottom=False,
        labelleft=False,
        labelbottom=False,
    )
    for spine in axes.spines.values():
        spine.set_visible(True)
        spine.set_color(palette.surface_edgecolor)
        spine.set_linewidth(1.0)


def _style_slider(slider: Slider, *, palette: ManagedUiPalette) -> None:
    from matplotlib.lines import Line2D

    _style_control_axes(slider.ax, palette=palette)
    slider.label.set_color(palette.secondary_text_color)
    slider.label.set_fontsize(10.0)
    slider.valtext.set_visible(False)
    if hasattr(slider, "track"):
        slider.track.set_alpha(1.0)
        slider.track.set_facecolor(palette.slider_track_color)
        slider.track.set_edgecolor("none")
    if hasattr(slider, "poly"):
        slider.poly.set_alpha(0.32)
        slider.poly.set_facecolor(palette.slider_fill_color)
        slider.poly.set_edgecolor("none")
    if hasattr(slider, "vline"):
        slider.vline.set_color(palette.accent_color)
        slider.vline.set_alpha(0.75)
        slider.vline.set_linewidth(2.2)
    handle = getattr(slider, "_handle", None)
    if isinstance(handle, Line2D):
        handle.set_markerfacecolor(palette.accent_color)
        handle.set_markeredgecolor(palette.accent_edgecolor)
        handle.set_markeredgewidth(1.2)


def _style_stepper_button(button: Button, *, palette: ManagedUiPalette) -> None:
    button.ax.set_facecolor(palette.surface_facecolor)
    button.color = palette.surface_facecolor
    button.hovercolor = palette.surface_hover_facecolor
    button.label.set_color(palette.text_color)
    button.label.set_fontsize(8.5)
    button.label.set_fontweight("bold")
    for spine in button.ax.spines.values():
        spine.set_color(palette.surface_edgecolor)
        spine.set_linewidth(1.0)


def _style_text_box(
    text_box: TextBox,
    *,
    text_color: str,
    border_color: str,
    facecolor: str,
) -> None:
    text_box.label.set_visible(False)
    text_box.ax.set_facecolor(facecolor)
    if hasattr(text_box, "text_disp"):
        text_box.text_disp.set_color(text_color)
        text_box.text_disp.set_fontsize(10.0)
    if hasattr(text_box, "cursor"):
        text_box.cursor.set_color(text_color)
        text_box.cursor.set_linewidth(1.5)
    text_box.ax.set_title("")
    text_box.ax.tick_params(
        left=False,
        bottom=False,
        labelleft=False,
        labelbottom=False,
    )
    for spine in text_box.ax.spines.values():
        spine.set_color(border_color)
        spine.set_linewidth(1.0)


def _figure_size_inches(figure: object) -> tuple[float, float]:
    if hasattr(figure, "get_size_inches"):
        size_inches = getattr(figure, "get_size_inches")()
        return float(size_inches[0]), float(size_inches[1])
    parent_figure = getattr(figure, "figure")
    size_inches = parent_figure.get_size_inches()
    return float(size_inches[0]), float(size_inches[1])
