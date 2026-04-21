"""Control creation and synchronization for interactive histograms."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..managed.controls import _style_control_axes, _style_slider, _style_text_box
from ..managed.ui_palette import managed_ui_palette
from .histogram_interactive_hover import attach_usage_hover
from .histogram_models import HistogramKind, HistogramSort, HistogramStateLabelMode

if TYPE_CHECKING:
    from matplotlib.widgets import Slider

    from .histogram_interactive_state import HistogramInteractiveState
    from .histogram_models import HistogramConfig

_CONTROL_ORDER_BOUNDS = (0.08, 0.025, 0.18, 0.06)
_CONTROL_LABEL_MODE_BOUNDS = (0.28, 0.025, 0.16, 0.06)
_CONTROL_KIND_TOGGLE_BOUNDS = (0.46, 0.025, 0.14, 0.06)
_CONTROL_SLIDER_TOGGLE_BOUNDS = (0.62, 0.025, 0.12, 0.06)
_CONTROL_MARGINAL_BOUNDS = (0.76, 0.025, 0.18, 0.06)
_HORIZONTAL_SLIDER_BOUNDS = (0.08, 0.115, 0.88, 0.045)


def attach_histogram_controls(
    *,
    state: HistogramInteractiveState,
    config: HistogramConfig,
) -> None:
    """Attach the fixed interactive controls to one histogram figure."""

    from matplotlib.widgets import Button, TextBox

    palette = managed_ui_palette(state.theme)

    order_axes = state.figure.add_axes(_CONTROL_ORDER_BOUNDS, facecolor=palette.surface_facecolor)
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

    label_mode_axes = state.figure.add_axes(
        _CONTROL_LABEL_MODE_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(label_mode_axes, palette=palette)
    label_mode_button = Button(
        label_mode_axes,
        "Labels: Binary",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
    )
    label_mode_button.label.set_color(palette.text_color)
    label_mode_button.on_clicked(lambda _event: state.toggle_label_mode())
    state.label_mode_axes = label_mode_axes
    state.label_mode_button = label_mode_button

    if state.kind_toggle_available():
        kind_toggle_axes = state.figure.add_axes(
            _CONTROL_KIND_TOGGLE_BOUNDS,
            facecolor=palette.surface_facecolor,
        )
        _style_control_axes(kind_toggle_axes, palette=palette)
        kind_toggle_button = Button(
            kind_toggle_axes,
            f"Mode: {kind_description(state.kind)}",
            color=palette.surface_facecolor,
            hovercolor=palette.surface_hover_facecolor,
        )
        kind_toggle_button.label.set_color(palette.text_color)
        kind_toggle_button.on_clicked(lambda _event: state.toggle_kind())
        state.kind_toggle_axes = kind_toggle_axes
        state.kind_toggle_button = kind_toggle_button

    marginal_axes = state.figure.add_axes(
        _CONTROL_MARGINAL_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(marginal_axes, palette=palette)
    marginal_text_box = TextBox(
        marginal_axes,
        "Marginal qubits",
        initial=marginal_text(config.qubits),
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
    marginal_text_box.on_submit(lambda text: handle_marginal_submit(state, text))
    state.marginal_axes = marginal_axes
    state.marginal_text_box = marginal_text_box
    if config.hover:
        attach_usage_hover(
            marginal_axes,
            theme=state.theme,
            text="Use comma-separated\nqubit indices like 0,2,5.\nLeave blank for\nthe full register.",
        )


def ensure_slider_toggle_control(
    state: HistogramInteractiveState,
    *,
    should_show_toggle: bool,
) -> None:
    """Ensure the slider toggle button matches the current visibility needs."""

    if not should_show_toggle:
        remove_slider_toggle_control(state)
        return

    if state.slider_toggle_button is not None and state.slider_toggle_axes is not None:
        return

    from matplotlib.widgets import Button

    palette = managed_ui_palette(state.theme)
    slider_toggle_axes = state.figure.add_axes(
        _CONTROL_SLIDER_TOGGLE_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(slider_toggle_axes, palette=palette)
    slider_toggle_button = Button(
        slider_toggle_axes,
        "Slider On",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
    )
    slider_toggle_button.label.set_color(palette.text_color)
    slider_toggle_button.on_clicked(lambda _event: state.toggle_slider())
    state.slider_toggle_axes = slider_toggle_axes
    state.slider_toggle_button = slider_toggle_button


def remove_slider_toggle_control(state: HistogramInteractiveState) -> None:
    """Remove the slider toggle button when it is not needed."""

    if state.slider_toggle_button is not None and hasattr(
        state.slider_toggle_button,
        "disconnect_events",
    ):
        state.slider_toggle_button.disconnect_events()
    if state.slider_toggle_axes is not None:
        state.slider_toggle_axes.remove()
    state.slider_toggle_button = None
    state.slider_toggle_axes = None


def ensure_slider_control(
    state: HistogramInteractiveState,
    *,
    should_show_slider: bool,
) -> None:
    """Ensure the horizontal window slider matches the current visible window."""

    if not should_show_slider:
        remove_slider_control(state)
        return

    if (
        state.horizontal_slider is not None
        and state.horizontal_slider.valmax == float(state.max_window_start)
        and state.slider_axes is not None
    ):
        return

    remove_slider_control(state)
    from matplotlib.widgets import Slider

    palette = managed_ui_palette(state.theme)
    slider_axes = state.figure.add_axes(
        _HORIZONTAL_SLIDER_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(slider_axes, palette=palette)
    horizontal_slider = Slider(
        ax=slider_axes,
        label="",
        valmin=0.0,
        valmax=float(state.max_window_start),
        valinit=float(state.window_start),
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
    horizontal_slider.on_changed(lambda value: state.set_window_start(round(float(value))))
    state.horizontal_slider = horizontal_slider
    state.slider_axes = slider_axes


def remove_slider_control(state: HistogramInteractiveState) -> None:
    """Remove the window slider and its axes."""

    if state.horizontal_slider is not None:
        state.horizontal_slider.disconnect_events()
    if state.slider_axes is not None:
        state.slider_axes.remove()
    state.horizontal_slider = None
    state.slider_axes = None


def sync_slider(state: HistogramInteractiveState) -> None:
    """Synchronize the slider position with the current state window."""

    if state.horizontal_slider is None:
        return
    set_slider_value_silently(state.horizontal_slider, float(state.window_start))


def sync_marginal_text_box(state: HistogramInteractiveState) -> None:
    """Synchronize the marginal text box with the active qubit selection."""

    if state.marginal_text_box is None:
        return
    state.is_syncing_marginal_text = True
    try:
        state.marginal_text_box.set_val(marginal_text(state.active_qubits))
    finally:
        state.is_syncing_marginal_text = False


def refresh_histogram_controls(state: HistogramInteractiveState) -> None:
    """Refresh visible button labels after one state transition."""

    if state.order_button is not None:
        state.order_button.label.set_text(
            f"Order: {sort_description(state.current_sort, state.kind)}"
        )
    if state.label_mode_button is not None:
        state.label_mode_button.label.set_text(
            f"Labels: {label_mode_description(state.label_mode)}"
        )
    if state.kind_toggle_button is not None:
        state.kind_toggle_button.label.set_text(f"Mode: {kind_description(state.kind)}")
    if state.slider_toggle_button is not None:
        slider_label = "On" if state.slider_enabled else "Off"
        state.slider_toggle_button.label.set_text(f"Slider {slider_label}")


def handle_marginal_submit(state: HistogramInteractiveState, text: str) -> None:
    """Handle one text-box submit event unless the control is syncing itself."""

    if state.is_syncing_marginal_text:
        return
    state.submit_marginal_text(text)


def marginal_text(qubits: tuple[int, ...] | None) -> str:
    """Serialize the current marginal-qubit selection for the text box."""

    if qubits is None:
        return ""
    return ",".join(str(qubit) for qubit in qubits)


def qubit_status_label(qubits: tuple[int, ...]) -> str:
    """Format one concise visible label for selected qubits."""

    return ",".join(f"q{qubit}" for qubit in qubits)


def parse_marginal_qubits(text: str) -> tuple[int, ...] | None:
    """Parse one text-box value into a validated tuple of qubit indices."""

    stripped_text = text.strip()
    if not stripped_text:
        return None
    pieces = [piece.strip() for piece in stripped_text.split(",")]
    if any(not piece for piece in pieces):
        raise ValueError("Marginal qubits must be a comma-separated list of non-negative integers.")
    try:
        qubits = tuple(int(piece) for piece in pieces)
    except ValueError as exc:
        raise ValueError(
            "Marginal qubits must be a comma-separated list of non-negative integers."
        ) from exc
    if any(qubit < 0 for qubit in qubits):
        raise ValueError("Marginal qubits must be a comma-separated list of non-negative integers.")
    if len(set(qubits)) != len(qubits):
        raise ValueError("Marginal qubits must not contain duplicates.")
    return qubits


def sort_description(sort: HistogramSort, kind: HistogramKind) -> str:
    """Describe the active sort in user-facing language."""

    if sort is HistogramSort.STATE:
        return "Binary ascending"
    if sort is HistogramSort.STATE_DESC:
        return "Binary descending"
    value_label = "Counts" if kind is HistogramKind.COUNTS else "Probability"
    if sort is HistogramSort.VALUE_ASC:
        return f"{value_label} ascending"
    return f"{value_label} descending"


def label_mode_description(label_mode: HistogramStateLabelMode) -> str:
    """Describe the active label mode in user-facing language."""

    if label_mode is HistogramStateLabelMode.BINARY:
        return "Binary"
    return "Decimal"


def kind_description(kind: HistogramKind) -> str:
    """Describe the active histogram value mode in user-facing language."""

    if kind is HistogramKind.COUNTS:
        return "Counts"
    return "Quasi"


def set_slider_value_silently(slider: Slider, value: float) -> None:
    """Set the slider value without triggering its callback."""

    if float(slider.val) == float(value):
        return
    previous_event_state = slider.eventson
    slider.eventson = False
    try:
        slider.set_val(float(value))
    finally:
        slider.eventson = previous_event_state


__all__ = ["attach_histogram_controls"]
