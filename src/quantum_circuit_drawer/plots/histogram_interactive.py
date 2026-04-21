"""Managed interactive helpers for histogram plots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..managed.controls import _style_control_axes, _style_slider, _style_text_box
from ..managed.ui_palette import managed_ui_palette
from ..renderers._matplotlib_figure import (
    HoverState,
    clear_hover_state,
    set_histogram_state,
    set_hover_state,
)
from .histogram import (
    HistogramKind,
    HistogramSort,
    _apply_joint_marginal,
    _draw_histogram_axes,
    _order_histogram_values,
    _resolved_histogram_bit_width,
    _save_histogram_if_requested,
    _uniform_reference_value,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.text import Text
    from matplotlib.widgets import Button, Slider, TextBox

    from ..style.theme import DrawTheme
    from .histogram import HistogramConfig, HistogramDrawStyle, HistogramKind, HistogramSort


_CONTROL_ORDER_BOUNDS = (0.08, 0.055, 0.17, 0.065)
_CONTROL_SLIDER_TOGGLE_BOUNDS = (0.28, 0.055, 0.17, 0.065)
_CONTROL_MARGINAL_BOUNDS = (0.58, 0.05, 0.29, 0.075)
_HORIZONTAL_SLIDER_BOUNDS = (0.08, 0.18, 0.88, 0.05)
_MAIN_AXES_BOUNDS = (0.08, 0.15, 0.88, 0.74)
_MAIN_AXES_WITH_SLIDER_BOUNDS = (0.08, 0.28, 0.88, 0.61)
_STATUS_TEXT_POSITION = (0.08, 0.965)
_MESSAGE_TEXT_POSITION = (0.08, 0.93)
_MIN_BIN_WIDTH_PIXELS = 18.0
_HOVER_ZORDER = 10_000
_SORT_CYCLE: tuple[HistogramSort, ...] = (
    HistogramSort.STATE,
    HistogramSort.STATE_DESC,
    HistogramSort.VALUE_ASC,
    HistogramSort.VALUE_DESC,
)


@dataclass(slots=True)
class HistogramInteractiveState:
    """Interactive histogram state attached to one managed figure."""

    figure: Figure
    axes: Axes
    base_values_by_state: Mapping[str, float]
    bit_width: int
    kind: HistogramKind
    theme: DrawTheme
    draw_style: HistogramDrawStyle
    show_uniform_reference: bool
    top_k: int | None
    current_sort: HistogramSort
    active_qubits: tuple[int, ...] | None
    slider_enabled: bool
    status_text: Text
    message_text: Text
    order_button: Button | None = None
    slider_toggle_button: Button | None = None
    marginal_text_box: TextBox | None = None
    order_axes: Axes | None = None
    slider_toggle_axes: Axes | None = None
    marginal_axes: Axes | None = None
    slider_axes: Axes | None = None
    horizontal_slider: Slider | None = None
    current_labels: tuple[str, ...] = ()
    current_values: tuple[float, ...] = ()
    visible_labels: tuple[str, ...] = ()
    visible_values: tuple[float, ...] = ()
    visible_bin_count: int = 0
    window_start: int = 0
    max_window_start: int = 0
    resize_callback_id: int | None = None
    is_syncing_marginal_text: bool = False

    def cycle_sort(self) -> None:
        """Advance to the next public histogram sort mode and redraw."""

        cycle = tuple(self._resolved_sort_cycle())
        current_index = cycle.index(self.current_sort)
        self.current_sort = cycle[(current_index + 1) % len(cycle)]
        self._set_message("")
        self.redraw()

    def toggle_slider(self) -> None:
        """Toggle the windowed slider viewport without losing the current state."""

        self.slider_enabled = not self.slider_enabled
        if not self.slider_enabled:
            self.window_start = 0
        self._set_message("")
        self.redraw()

    def set_window_start(self, start: int) -> None:
        """Move the active histogram window to one new starting bin."""

        self.window_start = min(max(0, int(start)), self.max_window_start)
        self.redraw()

    def submit_marginal_text(self, text: str) -> None:
        """Apply one marginal-qubits text submission if valid."""

        try:
            requested_qubits = _parse_marginal_qubits(text)
            current_values_by_state = _apply_joint_marginal(
                self.base_values_by_state,
                qubits=requested_qubits,
                bit_width=self.bit_width,
            )
        except ValueError as exc:
            self._sync_marginal_text_box()
            self._set_message(str(exc), error=True)
            return

        self.active_qubits = requested_qubits
        self.window_start = 0
        self._set_message("")
        self.redraw(precomputed_values_by_state=current_values_by_state)

    def redraw(
        self,
        *,
        precomputed_values_by_state: Mapping[str, float] | None = None,
    ) -> None:
        """Recompute the visible histogram view and redraw the managed figure."""

        values_by_state = (
            dict(precomputed_values_by_state)
            if precomputed_values_by_state is not None
            else _apply_joint_marginal(
                self.base_values_by_state,
                qubits=self.active_qubits,
                bit_width=self.bit_width,
            )
        )
        ordered_values_by_state = _order_histogram_values(
            values_by_state,
            sort=self.current_sort,
            top_k=self.top_k,
        )
        self.current_labels = tuple(ordered_values_by_state)
        self.current_values = tuple(float(value) for value in ordered_values_by_state.values())
        self.visible_bin_count = self._resolved_visible_bin_count()
        self.max_window_start = max(0, len(self.current_labels) - self.visible_bin_count)
        self.window_start = min(max(0, self.window_start), self.max_window_start)

        if self.slider_enabled:
            window_stop = self.window_start + self.visible_bin_count
            self.visible_labels = self.current_labels[self.window_start:window_stop]
            self.visible_values = self.current_values[self.window_start:window_stop]
        else:
            self.visible_labels = self.current_labels
            self.visible_values = self.current_values

        display_slider = self.slider_enabled and self.max_window_start > 0
        self._ensure_slider_control(display_slider)
        clear_hover_state(self.axes)
        self.axes.clear()
        self.axes.set_position(
            _MAIN_AXES_WITH_SLIDER_BOUNDS if display_slider else _MAIN_AXES_BOUNDS
        )
        uniform_reference_value = _uniform_reference_value(
            values_by_state,
            kind=self.kind,
            bit_width=_resolved_histogram_bit_width(
                bit_width=self.bit_width,
                qubits=self.active_qubits,
            ),
            show_uniform_reference=self.show_uniform_reference,
        )
        _draw_histogram_axes(
            figure=self.figure,
            axes=self.axes,
            state_labels=self.visible_labels,
            values=self.visible_values,
            kind=self.kind,
            theme=self.theme,
            draw_style=self.draw_style,
            uniform_reference_value=uniform_reference_value,
            thin_xlabels=True,
        )
        _attach_histogram_hover(
            self.axes,
            state_labels=self.visible_labels,
            values=self.visible_values,
            kind=self.kind,
            theme=self.theme,
        )
        self._sync_slider()
        self._sync_marginal_text_box()
        self._refresh_status()
        canvas = getattr(self.figure, "canvas", None)
        if canvas is not None:
            canvas.draw_idle()

    def save_current_view(self, *, output_path: object) -> None:
        """Save one clean snapshot of the current visible histogram view."""

        snapshot_figure = Figure(
            figsize=tuple(float(value) for value in self.figure.get_size_inches()),
        )
        FigureCanvasAgg(snapshot_figure)
        snapshot_axes = snapshot_figure.add_subplot(111)
        snapshot_figure.subplots_adjust(left=0.08, right=0.98, top=0.94, bottom=0.16)
        full_values_by_state = _apply_joint_marginal(
            self.base_values_by_state,
            qubits=self.active_qubits,
            bit_width=self.bit_width,
        )
        uniform_reference_value = _uniform_reference_value(
            full_values_by_state,
            kind=self.kind,
            bit_width=_resolved_histogram_bit_width(
                bit_width=self.bit_width,
                qubits=self.active_qubits,
            ),
            show_uniform_reference=self.show_uniform_reference,
        )
        _draw_histogram_axes(
            figure=snapshot_figure,
            axes=snapshot_axes,
            state_labels=self.visible_labels,
            values=self.visible_values,
            kind=self.kind,
            theme=self.theme,
            draw_style=self.draw_style,
            uniform_reference_value=uniform_reference_value,
            thin_xlabels=True,
        )
        _save_histogram_if_requested(snapshot_figure, output_path=output_path)

    def remove(self) -> None:
        """Disconnect callbacks and remove interactive artists."""

        clear_hover_state(self.axes)
        for widget in (self.order_button, self.slider_toggle_button, self.marginal_text_box):
            if widget is not None and hasattr(widget, "disconnect_events"):
                widget.disconnect_events()
        if self.horizontal_slider is not None:
            self.horizontal_slider.disconnect_events()
        for control_axes in (
            self.order_axes,
            self.slider_toggle_axes,
            self.marginal_axes,
            self.slider_axes,
        ):
            if control_axes is not None:
                control_axes.remove()
        if self.resize_callback_id is not None and self.figure.canvas is not None:
            self.figure.canvas.mpl_disconnect(self.resize_callback_id)

    def _resolved_visible_bin_count(self) -> int:
        if not self.slider_enabled or not self.current_labels:
            return len(self.current_labels)
        axes_width_fraction = _MAIN_AXES_WITH_SLIDER_BOUNDS[2]
        figure_width_pixels = self.figure.get_size_inches()[0] * float(self.figure.dpi)
        visible_count = int((figure_width_pixels * axes_width_fraction) / _MIN_BIN_WIDTH_PIXELS)
        return min(len(self.current_labels), max(1, visible_count))

    def _ensure_slider_control(self, should_show_slider: bool) -> None:
        if not should_show_slider:
            self._remove_slider_control()
            return

        if (
            self.horizontal_slider is not None
            and self.horizontal_slider.valmax == float(self.max_window_start)
            and self.slider_axes is not None
        ):
            return

        self._remove_slider_control()
        from matplotlib.widgets import Slider

        palette = managed_ui_palette(self.theme)
        slider_axes = self.figure.add_axes(
            _HORIZONTAL_SLIDER_BOUNDS,
            facecolor=palette.surface_facecolor,
        )
        _style_control_axes(slider_axes, palette=palette)
        horizontal_slider = Slider(
            ax=slider_axes,
            label="",
            valmin=0.0,
            valmax=float(self.max_window_start),
            valinit=float(self.window_start),
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
        horizontal_slider.on_changed(lambda value: self.set_window_start(round(float(value))))
        self.horizontal_slider = horizontal_slider
        self.slider_axes = slider_axes

    def _remove_slider_control(self) -> None:
        if self.horizontal_slider is not None:
            self.horizontal_slider.disconnect_events()
        if self.slider_axes is not None:
            self.slider_axes.remove()
        self.horizontal_slider = None
        self.slider_axes = None

    def _sync_slider(self) -> None:
        if self.horizontal_slider is None:
            return
        _set_slider_value_silently(self.horizontal_slider, float(self.window_start))

    def _sync_marginal_text_box(self) -> None:
        if self.marginal_text_box is None:
            return
        self.is_syncing_marginal_text = True
        try:
            self.marginal_text_box.set_val(_marginal_text(self.active_qubits))
        finally:
            self.is_syncing_marginal_text = False

    def _refresh_status(self) -> None:
        slider_label = "On" if self.slider_enabled else "Off"
        marginal_label = "full register" if self.active_qubits is None else _qubit_status_label(
            self.active_qubits
        )
        self.status_text.set_text(
            f"Order: {_sort_description(self.current_sort, self.kind)} | "
            f"Slider: {slider_label} | Marginal: {marginal_label}"
        )

    def _set_message(self, message: str, *, error: bool = False) -> None:
        self.message_text.set_text(message)
        self.message_text.set_color(self.theme.hover_edgecolor if error else self.theme.text_color)

    def _resolved_sort_cycle(self) -> tuple[HistogramSort, ...]:
        return _SORT_CYCLE


def attach_histogram_interactivity(
    *,
    figure: Figure,
    axes: Axes,
    values_by_state: Mapping[str, float],
    bit_width: int,
    kind: HistogramKind,
    config: HistogramConfig,
) -> HistogramInteractiveState:
    """Attach histogram widgets, hover, and state to one managed figure."""

    from matplotlib.widgets import Button, TextBox

    palette = managed_ui_palette(config.theme)
    status_text = figure.text(
        *_STATUS_TEXT_POSITION,
        "",
        ha="left",
        va="top",
        color=config.theme.text_color,
        fontsize=10.0,
    )
    message_text = figure.text(
        *_MESSAGE_TEXT_POSITION,
        "",
        ha="left",
        va="top",
        color=config.theme.text_color,
        fontsize=9.5,
    )
    state = HistogramInteractiveState(
        figure=figure,
        axes=axes,
        base_values_by_state=dict(values_by_state),
        bit_width=bit_width,
        kind=kind,
        theme=config.theme,
        draw_style=config.draw_style,
        show_uniform_reference=config.show_uniform_reference,
        top_k=config.top_k,
        current_sort=config.sort,
        active_qubits=config.qubits,
        slider_enabled=True,
        status_text=status_text,
        message_text=message_text,
    )

    order_axes = figure.add_axes(_CONTROL_ORDER_BOUNDS, facecolor=palette.surface_facecolor)
    _style_control_axes(order_axes, palette=palette)
    order_button = Button(
        order_axes,
        "Cycle order",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
    )
    order_button.label.set_color(palette.text_color)
    order_button.on_clicked(lambda _event: state.cycle_sort())
    state.order_axes = order_axes
    state.order_button = order_button

    slider_toggle_axes = figure.add_axes(
        _CONTROL_SLIDER_TOGGLE_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(slider_toggle_axes, palette=palette)
    slider_toggle_button = Button(
        slider_toggle_axes,
        "Toggle slider",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
    )
    slider_toggle_button.label.set_color(palette.text_color)
    slider_toggle_button.on_clicked(lambda _event: state.toggle_slider())
    state.slider_toggle_axes = slider_toggle_axes
    state.slider_toggle_button = slider_toggle_button

    marginal_axes = figure.add_axes(_CONTROL_MARGINAL_BOUNDS, facecolor=palette.surface_facecolor)
    _style_control_axes(marginal_axes, palette=palette)
    marginal_text_box = TextBox(
        marginal_axes,
        "Marginal qubits",
        initial=_marginal_text(config.qubits),
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
        textalignment="center",
    )
    _style_text_box(
        marginal_text_box,
        text_color=palette.text_color,
        border_color=palette.surface_edgecolor,
        facecolor=palette.surface_facecolor,
    )
    marginal_text_box.on_submit(lambda text: _handle_marginal_submit(state, text))
    state.marginal_axes = marginal_axes
    state.marginal_text_box = marginal_text_box

    if figure.canvas is not None:
        state.resize_callback_id = figure.canvas.mpl_connect(
            "resize_event",
            lambda _event: state.redraw(),
        )

    set_histogram_state(figure, state)
    state.redraw()
    if config.output_path is not None:
        state.save_current_view(output_path=config.output_path)
    return state


def _handle_marginal_submit(state: HistogramInteractiveState, text: str) -> None:
    if state.is_syncing_marginal_text:
        return
    state.submit_marginal_text(text)


def _marginal_text(qubits: tuple[int, ...] | None) -> str:
    if qubits is None:
        return ""
    return ",".join(str(qubit) for qubit in qubits)


def _qubit_status_label(qubits: tuple[int, ...]) -> str:
    return ",".join(f"q{qubit}" for qubit in qubits)


def _parse_marginal_qubits(text: str) -> tuple[int, ...] | None:
    stripped_text = text.strip()
    if not stripped_text:
        return None
    pieces = [piece.strip() for piece in stripped_text.split(",")]
    if any(not piece for piece in pieces):
        raise ValueError(
            "Marginal qubits must be a comma-separated list of non-negative integers."
        )
    try:
        qubits = tuple(int(piece) for piece in pieces)
    except ValueError as exc:
        raise ValueError(
            "Marginal qubits must be a comma-separated list of non-negative integers."
        ) from exc
    if any(qubit < 0 for qubit in qubits):
        raise ValueError(
            "Marginal qubits must be a comma-separated list of non-negative integers."
        )
    if len(set(qubits)) != len(qubits):
        raise ValueError("Marginal qubits must not contain duplicates.")
    return qubits


def _sort_description(sort: HistogramSort, kind: HistogramKind) -> str:
    if sort is HistogramSort.STATE:
        return "Binary ascending"
    if sort is HistogramSort.STATE_DESC:
        return "Binary descending"
    value_label = "Counts" if kind is HistogramKind.COUNTS else "Quasi-probability"
    if sort is HistogramSort.VALUE_ASC:
        return f"{value_label} ascending"
    return f"{value_label} descending"


def _set_slider_value_silently(slider: Slider, value: float) -> None:
    if float(slider.val) == float(value):
        return
    previous_event_state = slider.eventson
    slider.eventson = False
    try:
        slider.set_val(float(value))
    finally:
        slider.eventson = previous_event_state


def _attach_histogram_hover(
    axes: Axes,
    *,
    state_labels: tuple[str, ...],
    values: tuple[float, ...],
    kind: HistogramKind,
    theme: DrawTheme,
) -> None:
    annotation = axes.annotate(
        "",
        xy=(0.0, 0.0),
        xycoords="figure pixels",
        xytext=(10.0, 10.0),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=max(8.0, axes.figure.dpi / 12.0),
        color=theme.hover_text_color,
        zorder=_HOVER_ZORDER,
        annotation_clip=False,
        bbox={
            "boxstyle": "round,pad=0.18",
            "fc": theme.hover_facecolor,
            "ec": theme.hover_edgecolor,
            "alpha": 0.9,
        },
    )
    annotation.set_visible(False)
    canvas = axes.figure.canvas
    if canvas is None:
        return
    active_index: int | None = None
    bars: tuple[object, ...] = tuple(axes.patches)

    def hide_annotation() -> None:
        nonlocal active_index
        if annotation.get_visible():
            annotation.set_visible(False)
            active_index = None
            canvas.draw_idle()

    def on_motion(event: Event) -> None:
        nonlocal active_index
        if not isinstance(event, MouseEvent) or event.inaxes is not axes:
            hide_annotation()
            return
        hovered_index = _hovered_bar_index(bars, event)
        if hovered_index is None:
            hide_annotation()
            return
        if active_index == hovered_index:
            return
        annotation.xy = (event.x, event.y)
        annotation.set_text(_histogram_hover_text(state_labels[hovered_index], values[hovered_index], kind))
        annotation.set_visible(True)
        active_index = hovered_index
        canvas.draw_idle()

    callback_id = canvas.mpl_connect("motion_notify_event", on_motion)
    set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))


def _hovered_bar_index(bars: tuple[object, ...], event: MouseEvent) -> int | None:
    for index, bar in enumerate(bars):
        contains, _ = bar.contains(event)
        if contains:
            return index
    return None


def _histogram_hover_text(
    state_label: str,
    value: float,
    kind: HistogramKind,
) -> str:
    value_label = "Counts" if kind is HistogramKind.COUNTS else "Quasi-probability"
    return f"Bitstring: {state_label}\n{value_label}: {_formatted_histogram_value(value, kind)}"


def _formatted_histogram_value(value: float, kind: HistogramKind) -> str:
    if kind is HistogramKind.COUNTS and float(value).is_integer():
        return str(int(value))
    return f"{float(value):.6g}"
