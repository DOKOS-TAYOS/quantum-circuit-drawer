"""Shared managed control layout and styling helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

from .ui_palette import ManagedUiPalette

if TYPE_CHECKING:
    from matplotlib.widgets import Button, Slider, TextBox

    from .slider_2d import Managed2DSliderLayout

_VIEWPORT_EPSILON = 1e-6

_MANAGED_2D_MAIN_AXES_BOUNDS = (0.02, 0.02, 0.96, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_HORIZONTAL_BOUNDS = (0.02, 0.18, 0.96, 0.8)
_MANAGED_2D_MAIN_AXES_WITH_VERTICAL_BOUNDS = (0.14, 0.02, 0.84, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_BOTH_BOUNDS = (0.14, 0.18, 0.84, 0.8)
_MANAGED_2D_MAIN_AXES_WITH_LEFT_CONTROLS_BOUNDS = (0.14, 0.02, 0.84, 0.96)
_MANAGED_2D_MAIN_AXES_WITH_HORIZONTAL_AND_BOX_BOUNDS = (0.14, 0.18, 0.84, 0.8)
_MANAGED_2D_HORIZONTAL_SLIDER_HEIGHT = 0.04
_MANAGED_2D_HORIZONTAL_SLIDER_BOTTOM = 0.125
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

_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"
_MANAGED_3D_MAIN_AXES_BOUNDS = (0.0, 0.0, 1.0, 1.0)
_MANAGED_3D_MAIN_AXES_WITH_SLIDER_BOUNDS = (0.0, 0.14, 1.0, 0.86)
_MANAGED_3D_MENU_BOUNDS = (0.85, 0.035, 0.12, 0.21)
_MANAGED_3D_MENU_BOUNDS_WITH_SLIDER = (0.85, 0.155, 0.12, 0.21)
_CONTROL_LABEL_WIDTH_PADDING_FRACTION = 0.18
_CONTROL_LABEL_HEIGHT_PADDING_FRACTION = 0.24
_CONTROL_LABEL_DEFAULT_HEIGHT_SCALE = 0.52
_CONTROL_MIN_FONT_SIZE = 1.0
_RADIO_LABEL_SIDE_PADDING_POINTS = 10.0
_BUTTON_LABEL_OPTIONS_ATTR = "_quantum_circuit_drawer_button_label_options"


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
    """Apply the managed 3D main-axes bounds and store viewport metadata."""

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
    from .slider_2d import Managed2DSliderLayout

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
    button.label.set_fontweight("bold")
    for spine in button.ax.spines.values():
        spine.set_color(palette.surface_edgecolor)
        spine.set_linewidth(1.0)
    _fit_button_label_font_size(button)


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


def _fit_button_label_font_size(
    button: Button,
    *,
    text: str | None = None,
    possible_labels: tuple[str, ...] | None = None,
    fontweight: str = "bold",
) -> float:
    label_text = button.label.get_text() if text is None else text
    if possible_labels is not None:
        setattr(button, _BUTTON_LABEL_OPTIONS_ATTR, possible_labels)
    label_options = cast(
        "tuple[str, ...] | None",
        getattr(button, _BUTTON_LABEL_OPTIONS_ATTR, None),
    ) or (label_text,)
    button.label.set_text(label_text)
    width_points, height_points = _axes_size_points(button.ax)
    resolved_font_size = min(
        _fit_control_label_font_size(
            candidate_label,
            width_points=width_points,
            height_points=height_points,
            fontweight=fontweight,
        )
        for candidate_label in label_options
    )
    button.label.set_fontsize(resolved_font_size)
    button.label.set_fontweight(fontweight)
    return resolved_font_size


def _fit_radio_label_font_size(
    menu_axes: Axes,
    *,
    labels: tuple[str, ...] | list[str],
    marker_diameter_points: float,
    max_font_size: float | None = None,
) -> float:
    width_points, height_points = _axes_size_points(menu_axes)
    row_height_points = height_points / max(1, len(labels))
    available_width_points = max(
        _VIEWPORT_EPSILON,
        width_points - marker_diameter_points - _RADIO_LABEL_SIDE_PADDING_POINTS,
    )
    resolved_font_size = min(
        _fit_control_label_font_size(
            label,
            width_points=available_width_points,
            height_points=row_height_points,
            fontweight="normal",
        )
        for label in labels
    )
    if max_font_size is not None:
        return min(resolved_font_size, max_font_size)
    return resolved_font_size


def _radio_marker_size_points_squared(
    menu_axes: Axes,
    *,
    item_count: int,
) -> float:
    _, height_points = _axes_size_points(menu_axes)
    row_height_points = height_points / max(1, item_count)
    marker_diameter_points = max(6.0, min(11.0, row_height_points * 0.42))
    return marker_diameter_points * marker_diameter_points


def _radio_marker_diameter_points(
    menu_axes: Axes,
    *,
    item_count: int,
) -> float:
    return _radio_marker_size_points_squared(menu_axes, item_count=item_count) ** 0.5


def _fit_control_label_font_size(
    text: str,
    *,
    width_points: float,
    height_points: float,
    fontweight: str,
) -> float:
    available_width_points = max(
        _VIEWPORT_EPSILON,
        width_points * (1.0 - _CONTROL_LABEL_WIDTH_PADDING_FRACTION),
    )
    available_height_points = max(
        _VIEWPORT_EPSILON,
        height_points * (1.0 - _CONTROL_LABEL_HEIGHT_PADDING_FRACTION),
    )
    unit_width_points, unit_height_points = _text_size_at_unit_font(
        text,
        fontweight=fontweight,
    )
    preferred_font_size = max(
        _CONTROL_MIN_FONT_SIZE,
        height_points * _CONTROL_LABEL_DEFAULT_HEIGHT_SCALE,
    )
    fitted_width_font_size = (
        available_width_points / unit_width_points
        if unit_width_points > _VIEWPORT_EPSILON
        else preferred_font_size
    )
    fitted_height_font_size = (
        available_height_points / unit_height_points
        if unit_height_points > _VIEWPORT_EPSILON
        else preferred_font_size
    )
    return max(
        _CONTROL_MIN_FONT_SIZE,
        min(preferred_font_size, fitted_width_font_size, fitted_height_font_size),
    )


def _text_size_at_unit_font(
    text: str,
    *,
    fontweight: str,
) -> tuple[float, float]:
    lines = text.splitlines() or [" "]
    font_properties = FontProperties(size=1.0, weight=fontweight)
    max_width_points = 0.0
    total_height_points = 0.0
    for line_index, line in enumerate(lines):
        if line.strip():
            line_bounds = TextPath(
                (0.0, 0.0),
                line,
                size=1.0,
                prop=font_properties,
            ).get_extents()
            max_width_points = max(max_width_points, line_bounds.width)
            total_height_points += line_bounds.height
        else:
            total_height_points += 1.0
        if line_index < (len(lines) - 1):
            total_height_points += 0.28
    return max_width_points, total_height_points


def _axes_size_points(axes: Axes) -> tuple[float, float]:
    figure = axes.figure
    bounds = axes.get_position().bounds
    width_points = figure.get_figwidth() * 72.0 * bounds[2]
    height_points = figure.get_figheight() * 72.0 * bounds[3]
    return (
        max(_VIEWPORT_EPSILON, width_points),
        max(_VIEWPORT_EPSILON, height_points),
    )
