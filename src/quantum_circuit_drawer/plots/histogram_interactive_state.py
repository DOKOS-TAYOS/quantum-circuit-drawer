"""Interactive histogram state and entrypoint."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from ..renderers._matplotlib_figure import clear_hover_state, set_histogram_state
from ..style.theme import resolve_theme
from .histogram_interactive_controls import (
    attach_histogram_controls,
    ensure_slider_control,
    ensure_slider_toggle_control,
    parse_marginal_qubits,
    refresh_histogram_controls,
    sync_marginal_text_box,
    sync_slider,
)
from .histogram_interactive_hover import attach_histogram_hover
from .histogram_models import (
    HistogramConfig,
    HistogramKind,
    HistogramSort,
    HistogramStateLabelMode,
)
from .histogram_render import (
    apply_joint_marginal,
    display_labels_for_states,
    draw_histogram_axes,
    order_histogram_values,
    resolved_histogram_bit_width,
    resolved_histogram_y_limits,
    save_histogram_if_requested,
    uniform_reference_value,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.text import Text
    from matplotlib.widgets import Button, Slider, TextBox

    from ..style.theme import DrawTheme
    from ..typing import OutputPath
    from .histogram_models import HistogramDrawStyle

_MAIN_AXES_BOUNDS = (0.08, 0.23, 0.88, 0.66)
_MAIN_AXES_WITH_SLIDER_BOUNDS = (0.08, 0.25, 0.88, 0.64)
_MESSAGE_TEXT_POSITION = (0.5, 0.965)
_MIN_BIN_WIDTH_PIXELS = 18.0
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
    hover_enabled: bool
    label_mode: HistogramStateLabelMode
    top_k: int | None
    current_sort: HistogramSort
    active_qubits: tuple[int, ...] | None
    slider_enabled: bool
    message_text: Text
    order_button: Button | None = None
    label_mode_button: Button | None = None
    slider_toggle_button: Button | None = None
    marginal_text_box: TextBox | None = None
    order_axes: Axes | None = None
    label_mode_axes: Axes | None = None
    slider_toggle_axes: Axes | None = None
    marginal_axes: Axes | None = None
    slider_axes: Axes | None = None
    horizontal_slider: Slider | None = None
    current_labels: tuple[str, ...] = ()
    current_display_labels: tuple[str, ...] = ()
    current_values: tuple[float, ...] = ()
    visible_labels: tuple[str, ...] = ()
    visible_display_labels: tuple[str, ...] = ()
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

    def toggle_label_mode(self) -> None:
        """Toggle the visible state-label format between binary and decimal."""

        if self.label_mode is HistogramStateLabelMode.BINARY:
            self.label_mode = HistogramStateLabelMode.DECIMAL
        else:
            self.label_mode = HistogramStateLabelMode.BINARY
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
            requested_qubits = parse_marginal_qubits(text)
            current_values_by_state = apply_joint_marginal(
                self.base_values_by_state,
                qubits=requested_qubits,
                bit_width=self.bit_width,
            )
        except ValueError as exc:
            sync_marginal_text_box(self)
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
            else apply_joint_marginal(
                self.base_values_by_state,
                qubits=self.active_qubits,
                bit_width=self.bit_width,
            )
        )
        ordered_values_by_state = order_histogram_values(
            values_by_state,
            sort=self.current_sort,
            top_k=self.top_k,
        )
        self.current_labels = tuple(ordered_values_by_state)
        self.current_display_labels = display_labels_for_states(
            self.current_labels,
            mode=self.label_mode,
        )
        self.current_values = tuple(float(value) for value in ordered_values_by_state.values())
        slider_available = self._slider_available_for_label_count(len(self.current_labels))
        self.visible_bin_count = self._resolved_visible_bin_count()
        self.max_window_start = max(0, len(self.current_labels) - self.visible_bin_count)
        self.window_start = min(max(0, self.window_start), self.max_window_start)

        if self.slider_enabled:
            window_stop = self.window_start + self.visible_bin_count
            self.visible_labels = self.current_labels[self.window_start : window_stop]
            self.visible_display_labels = self.current_display_labels[
                self.window_start : window_stop
            ]
            self.visible_values = self.current_values[self.window_start : window_stop]
        else:
            self.visible_labels = self.current_labels
            self.visible_display_labels = self.current_display_labels
            self.visible_values = self.current_values

        display_slider = self.slider_enabled and slider_available
        ensure_slider_toggle_control(self, should_show_toggle=slider_available)
        ensure_slider_control(self, should_show_slider=display_slider)
        clear_hover_state(self.axes)
        self.axes.clear()
        self.axes.set_position(
            _MAIN_AXES_WITH_SLIDER_BOUNDS if display_slider else _MAIN_AXES_BOUNDS
        )
        uniform_reference = uniform_reference_value(
            values_by_state,
            kind=self.kind,
            bit_width=resolved_histogram_bit_width(
                bit_width=self.bit_width,
                qubits=self.active_qubits,
            ),
            show_uniform_reference=self.show_uniform_reference,
        )
        y_limits = resolved_histogram_y_limits(
            self.current_values,
            kind=self.kind,
            uniform_reference_value=uniform_reference,
        )
        draw_histogram_axes(
            figure=self.figure,
            axes=self.axes,
            state_labels=self.visible_labels,
            display_labels=self.visible_display_labels,
            values=self.visible_values,
            kind=self.kind,
            theme=self.theme,
            draw_style=self.draw_style,
            uniform_reference_value=uniform_reference,
            thin_xlabels=True,
            y_limits=y_limits,
        )
        if self.hover_enabled:
            attach_histogram_hover(
                self.axes,
                state_labels=self.visible_labels,
                values=self.visible_values,
                kind=self.kind,
                label_mode=self.label_mode,
                theme=self.theme,
            )
        sync_slider(self)
        sync_marginal_text_box(self)
        refresh_histogram_controls(self)
        canvas = getattr(self.figure, "canvas", None)
        if canvas is not None:
            canvas.draw_idle()

    def save_current_view(self, *, output_path: OutputPath | None) -> None:
        """Save one clean snapshot of the current visible histogram view."""

        size_inches = self.figure.get_size_inches()
        snapshot_figsize = (float(size_inches[0]), float(size_inches[1]))
        snapshot_figure = Figure(figsize=snapshot_figsize)
        FigureCanvasAgg(snapshot_figure)
        snapshot_axes = snapshot_figure.add_subplot(111)
        snapshot_figure.subplots_adjust(left=0.08, right=0.98, top=0.94, bottom=0.16)
        full_values_by_state = apply_joint_marginal(
            self.base_values_by_state,
            qubits=self.active_qubits,
            bit_width=self.bit_width,
        )
        uniform_reference = uniform_reference_value(
            full_values_by_state,
            kind=self.kind,
            bit_width=resolved_histogram_bit_width(
                bit_width=self.bit_width,
                qubits=self.active_qubits,
            ),
            show_uniform_reference=self.show_uniform_reference,
        )
        y_limits = resolved_histogram_y_limits(
            self.current_values,
            kind=self.kind,
            uniform_reference_value=uniform_reference,
        )
        draw_histogram_axes(
            figure=snapshot_figure,
            axes=snapshot_axes,
            state_labels=self.visible_labels,
            display_labels=self.visible_display_labels,
            values=self.visible_values,
            kind=self.kind,
            theme=self.theme,
            draw_style=self.draw_style,
            uniform_reference_value=uniform_reference,
            thin_xlabels=True,
            y_limits=y_limits,
        )
        save_histogram_if_requested(snapshot_figure, output_path=output_path)

    def remove(self) -> None:
        """Disconnect callbacks and remove interactive artists."""

        clear_hover_state(self.axes)
        if self.marginal_axes is not None:
            clear_hover_state(self.marginal_axes)
        for widget in (
            self.order_button,
            self.label_mode_button,
            self.slider_toggle_button,
            self.marginal_text_box,
        ):
            if widget is not None and hasattr(widget, "disconnect_events"):
                widget.disconnect_events()
        if self.horizontal_slider is not None:
            self.horizontal_slider.disconnect_events()
        for control_axes in (
            self.order_axes,
            self.label_mode_axes,
            self.slider_toggle_axes,
            self.marginal_axes,
            self.slider_axes,
        ):
            if control_axes is not None:
                control_axes.remove()
        if self.resize_callback_id is not None and self.figure.canvas is not None:
            self.figure.canvas.mpl_disconnect(self.resize_callback_id)

    def _resolved_visible_bin_count(self) -> int:
        total_bin_count = len(self.current_labels)
        if total_bin_count == 0:
            return 0
        if not self.slider_enabled or not self._slider_available_for_label_count(total_bin_count):
            return total_bin_count
        return self._resolved_slider_bin_count(total_bin_count)

    def _resolved_slider_bin_count(self, total_bin_count: int) -> int:
        axes_width_fraction = _MAIN_AXES_WITH_SLIDER_BOUNDS[2]
        figure_width_pixels = self.figure.get_size_inches()[0] * float(self.figure.dpi)
        visible_count = int((figure_width_pixels * axes_width_fraction) / _MIN_BIN_WIDTH_PIXELS)
        return min(total_bin_count, max(1, visible_count))

    def _slider_available_for_label_count(self, total_bin_count: int) -> bool:
        if total_bin_count <= 0:
            return False
        return total_bin_count > self._resolved_slider_bin_count(total_bin_count)

    def _set_message(self, message: str, *, error: bool = False) -> None:
        self.message_text.set_text(message)
        self.message_text.set_color(self.theme.hover_edgecolor if error else self.theme.text_color)
        self.message_text.set_visible(bool(message))

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

    theme = resolve_theme(config.theme)
    message_text = figure.text(
        *_MESSAGE_TEXT_POSITION,
        "",
        ha="center",
        va="top",
        color=theme.text_color,
        fontsize=9.5,
    )
    message_text.set_visible(False)
    state = HistogramInteractiveState(
        figure=figure,
        axes=axes,
        base_values_by_state=dict(values_by_state),
        bit_width=bit_width,
        kind=kind,
        theme=theme,
        draw_style=config.draw_style,
        show_uniform_reference=config.show_uniform_reference,
        hover_enabled=config.hover,
        label_mode=config.state_label_mode,
        top_k=config.top_k,
        current_sort=config.sort,
        active_qubits=config.qubits,
        slider_enabled=True,
        message_text=message_text,
    )
    attach_histogram_controls(state=state, config=config)

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


__all__ = ["HistogramInteractiveState", "attach_histogram_interactivity"]
