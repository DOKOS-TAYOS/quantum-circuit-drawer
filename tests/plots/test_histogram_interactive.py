from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.figure import Figure
from matplotlib.text import Annotation

from quantum_circuit_drawer import (
    HistogramKind,
    HistogramMode,
    HistogramSort,
    HistogramStateLabelMode,
)
from quantum_circuit_drawer.drawing.runtime import RuntimeContext
from quantum_circuit_drawer.histogram import plot_histogram
from quantum_circuit_drawer.renderers._matplotlib_figure import get_histogram_state, get_hover_state
from tests.support import assert_saved_image_has_visible_content, build_public_histogram_config


def _dense_histogram_counts(*, bit_width: int = 7) -> dict[str, int]:
    return {
        format(index, f"0{bit_width}b"): ((index * 17) % 41) + (index % 7) + 3
        for index in range(2**bit_width)
    }


def _dispatch_motion_event(figure: Figure, patch: object) -> None:
    renderer = figure.canvas.get_renderer()
    x, y, width, height = patch.get_window_extent(renderer=renderer).bounds
    event = MouseEvent(
        "motion_notify_event",
        figure.canvas,
        x + (width / 2.0),
        y + (height / 2.0),
    )
    figure.canvas.callbacks.process("motion_notify_event", event)


def _dispatch_motion_event_at_patch_corner(
    figure: Figure,
    patch: object,
    *,
    inset: float = 1.0,
) -> None:
    renderer = figure.canvas.get_renderer()
    x, y, width, height = patch.get_window_extent(renderer=renderer).bounds
    event = MouseEvent(
        "motion_notify_event",
        figure.canvas,
        x + width - inset,
        y + height - inset,
    )
    figure.canvas.callbacks.process("motion_notify_event", event)


def _dispatch_motion_event_at_axes_center(figure: Figure, axes: object) -> None:
    x, y, width, height = axes.get_window_extent(renderer=figure.canvas.get_renderer()).bounds
    event = MouseEvent(
        "motion_notify_event",
        figure.canvas,
        x + (width / 2.0),
        y + (height / 2.0),
    )
    figure.canvas.callbacks.process("motion_notify_event", event)


def _dispatch_motion_event_at_axes_corner(
    figure: Figure,
    axes: object,
    *,
    inset: float = 1.0,
) -> None:
    x, y, width, height = axes.get_window_extent(renderer=figure.canvas.get_renderer()).bounds
    event = MouseEvent(
        "motion_notify_event",
        figure.canvas,
        x + width - inset,
        y + height - inset,
    )
    figure.canvas.callbacks.process("motion_notify_event", event)


def _dispatch_motion_event_at_data(figure: Figure, axes: object, *, x: float, y: float) -> None:
    display_x, display_y = axes.transData.transform((x, y))
    event = MouseEvent(
        "motion_notify_event",
        figure.canvas,
        float(display_x),
        float(display_y),
    )
    figure.canvas.callbacks.process("motion_notify_event", event)


def _dispatch_key_press(figure: Figure, key: str) -> None:
    event = KeyEvent(
        "key_press_event",
        figure.canvas,
        key=key,
    )
    figure.canvas.callbacks.process("key_press_event", event)


def test_plot_histogram_interactive_mode_attaches_controls_and_windowed_view() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.horizontal_slider is not None
    assert state.order_button is not None
    assert state.label_mode_button is not None
    assert state.slider_toggle_button is not None
    assert state.marginal_text_box is not None
    assert state.slider_enabled is True
    assert state.visible_bin_count < len(result.state_labels)
    assert len(result.axes.patches) == state.visible_bin_count
    assert state.order_button.label.get_text().startswith("Order: ")
    assert state.label_mode_button.label.get_text() == "Labels: Binary"
    assert state.slider_toggle_button.label.get_text() == "Slider On"

    plt.close(result.figure)


def test_histogram_interactive_cycle_sort_updates_button_label_and_visible_labels() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            sort=HistogramSort.STATE,
            figsize=(10.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.current_sort is HistogramSort.STATE
    assert state.current_labels == ("00", "01", "10", "11")

    state.cycle_sort()
    assert state.current_sort is HistogramSort.STATE_DESC
    assert state.current_labels == ("11", "10", "01", "00")
    assert state.order_button.label.get_text() == "Order: Binary descending"

    state.cycle_sort()
    assert state.current_sort is HistogramSort.VALUE_ASC
    assert state.current_labels == ("11", "01", "00", "10")
    assert state.order_button.label.get_text() == "Order: Counts ascending"

    state.cycle_sort()
    assert state.current_sort is HistogramSort.VALUE_DESC
    assert state.current_labels == ("10", "00", "01", "11")
    assert state.order_button.label.get_text() == "Order: Counts descending"

    plt.close(result.figure)


def test_histogram_interactive_cycle_sort_uses_short_probability_labels_for_quasi_data() -> None:
    result = plot_histogram(
        {"00": 0.55, "01": 0.15, "10": 0.35, "11": 0.25},
        config=build_public_histogram_config(
            kind=HistogramKind.QUASI,
            mode=HistogramMode.INTERACTIVE,
            show=False,
            sort=HistogramSort.STATE,
            figsize=(10.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None

    state.cycle_sort()
    state.cycle_sort()
    assert state.current_sort is HistogramSort.VALUE_ASC
    assert state.order_button.label.get_text() == "Order: Probability ascending"

    state.cycle_sort()
    assert state.current_sort is HistogramSort.VALUE_DESC
    assert state.order_button.label.get_text() == "Order: Probability descending"

    plt.close(result.figure)


def test_histogram_interactive_order_button_keeps_probability_label_inside_bounds() -> None:
    result = plot_histogram(
        {"00": 0.55, "01": 0.15, "10": 0.35, "11": 0.25},
        config=build_public_histogram_config(
            kind=HistogramKind.QUASI,
            mode=HistogramMode.INTERACTIVE,
            show=False,
            sort=HistogramSort.STATE,
            figsize=(10.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.order_axes is not None

    state.cycle_sort()
    state.cycle_sort()
    result.figure.canvas.draw()

    renderer = result.figure.canvas.get_renderer()
    label_bbox = state.order_button.label.get_window_extent(renderer=renderer)
    button_bbox = state.order_axes.get_window_extent(renderer=renderer)

    assert label_bbox.x0 >= button_bbox.x0
    assert label_bbox.x1 <= button_bbox.x1

    plt.close(result.figure)


def test_histogram_interactive_counts_show_kind_toggle_button() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.kind_toggle_button is not None
    assert state.kind_toggle_axes is not None
    assert state.kind_toggle_button.label.get_text() == "Mode: Counts"

    plt.close(result.figure)


def test_histogram_interactive_quasi_hides_kind_toggle_button() -> None:
    result = plot_histogram(
        {"00": 0.55, "01": 0.15, "10": 0.35, "11": 0.25},
        config=build_public_histogram_config(
            kind=HistogramKind.QUASI,
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.kind_toggle_button is None
    assert state.kind_toggle_axes is None

    plt.close(result.figure)


def test_histogram_interactive_kind_toggle_switches_counts_to_quasi_view() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            sort=HistogramSort.VALUE_ASC,
            figsize=(10.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.kind is HistogramKind.COUNTS
    assert state.current_values == (1.0, 5.0, 7.0, 9.0)
    assert state.kind_toggle_button is not None

    state.toggle_kind()

    assert state.kind is HistogramKind.QUASI
    assert state.current_values == pytest.approx((1.0 / 22.0, 5.0 / 22.0, 7.0 / 22.0, 9.0 / 22.0))
    assert state.kind_toggle_button.label.get_text() == "Mode: Quasi"
    assert state.order_button.label.get_text() == "Order: Probability ascending"
    assert result.axes.get_ylabel() == "Quasi-probability"

    result.figure.canvas.draw()
    _dispatch_motion_event(result.figure, result.axes.patches[0])
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert "Quasi-probability: 0.0454545" in annotation.get_text()

    plt.close(result.figure)


def test_histogram_interactive_slider_toggle_expands_to_full_distribution() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.visible_bin_count < len(state.current_labels)

    state.toggle_slider()

    assert state.slider_enabled is False
    assert state.horizontal_slider is None
    assert state.visible_bin_count == len(state.current_labels)
    assert len(result.axes.patches) == len(state.current_labels)
    assert state.slider_toggle_button is not None
    assert state.slider_toggle_button.label.get_text() == "Slider Off"

    plt.close(result.figure)


def test_histogram_interactive_keyboard_shortcuts_update_and_reset_view() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.horizontal_slider is not None
    assert state.marginal_text_box is not None

    state.set_window_start(1)
    _dispatch_key_press(result.figure, "right")
    assert state.window_start == 2

    _dispatch_key_press(result.figure, "left")
    assert state.window_start == 1

    _dispatch_key_press(result.figure, "s")
    assert state.current_sort is HistogramSort.STATE_DESC

    _dispatch_key_press(result.figure, "b")
    assert state.label_mode is HistogramStateLabelMode.DECIMAL

    _dispatch_key_press(result.figure, "q")
    assert state.kind is HistogramKind.QUASI

    _dispatch_key_press(result.figure, "m")
    assert state.marginal_text_box.capturekeystrokes is True

    state.marginal_text_box.stop_typing()
    state.submit_marginal_text("0,2,5")
    assert state.active_qubits == (0, 2, 5)

    _dispatch_key_press(result.figure, "0")
    assert state.window_start == 0
    assert state.current_sort is HistogramSort.STATE
    assert state.label_mode is HistogramStateLabelMode.BINARY
    assert state.kind is HistogramKind.COUNTS
    assert state.active_qubits is None
    assert state.slider_enabled is True

    plt.close(result.figure)


def test_histogram_interactive_question_shortcut_toggles_shortcut_help() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.shortcut_help_text is not None
    assert state.shortcut_help_text.get_visible() is False

    _dispatch_key_press(result.figure, "?")
    assert state.shortcut_help_text.get_visible() is True
    assert "Shortcuts" in state.shortcut_help_text.get_text()
    assert state.shortcut_help_text.get_ha() == "left"
    assert "View" in state.shortcut_help_text.get_text()
    assert "Left/Right: Move slider window" in state.shortcut_help_text.get_text()
    assert "Modes" in state.shortcut_help_text.get_text()
    assert "m: Edit marginal qubits" in state.shortcut_help_text.get_text()

    _dispatch_key_press(result.figure, "?")
    assert state.shortcut_help_text.get_visible() is False

    plt.close(result.figure)


def test_histogram_interactive_marginal_text_updates_distribution_and_preserves_last_valid_state() -> (
    None
):
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.active_qubits is None

    state.submit_marginal_text("0,2,5")
    assert state.active_qubits == (0, 2, 5)
    assert state.current_labels == ("000", "001", "010", "011", "100", "101", "110", "111")

    state.submit_marginal_text("0, bad")
    assert state.active_qubits == (0, 2, 5)
    assert "comma-separated" in state.message_text.get_text()
    assert state.message_text.get_horizontalalignment() == "center"
    assert state.message_text.get_position()[0] == pytest.approx(0.5)

    state.submit_marginal_text("")
    assert state.active_qubits is None
    assert len(state.current_labels) == 128

    plt.close(result.figure)


@pytest.mark.parametrize(
    ("data", "kind", "expected_value_label"),
    [
        ({"00": 7, "01": 5, "10": 9, "11": 1}, HistogramKind.COUNTS, "Counts: 7"),
        (
            {"00": 0.55, "01": -0.15, "10": 0.35, "11": 0.25},
            HistogramKind.QUASI,
            "Quasi-probability: 0.55",
        ),
    ],
)
def test_histogram_interactive_hover_reports_bitstring_and_value(
    data: dict[str, int] | dict[str, float],
    kind: HistogramKind,
    expected_value_label: str,
) -> None:
    result = plot_histogram(
        data,
        config=build_public_histogram_config(
            kind=kind,
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    result.figure.canvas.draw()

    _dispatch_motion_event(result.figure, result.axes.patches[0])
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert f"Bitstring: {state.visible_labels[0]}" in annotation.get_text()
    assert expected_value_label in annotation.get_text()

    plt.close(result.figure)


def test_histogram_interactive_hover_repositions_inside_figure_near_top_right_bar() -> None:
    result = plot_histogram(
        {"0": 1, "1": 25},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(4.0, 3.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    result.figure.canvas.draw()

    top_right_patch = max(
        result.axes.patches,
        key=lambda patch: (
            patch.get_window_extent(renderer=result.figure.canvas.get_renderer()).x1,
            patch.get_window_extent(renderer=result.figure.canvas.get_renderer()).y1,
        ),
    )
    _dispatch_motion_event_at_patch_corner(result.figure, top_right_patch)
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))
    bbox = annotation.get_window_extent(renderer=result.figure.canvas.get_renderer())

    assert annotation.get_visible() is True
    assert annotation.get_ha() == "right"
    assert annotation.get_va() == "top"
    assert bbox.x0 >= 0.0
    assert bbox.y0 >= 0.0
    assert bbox.x1 <= result.figure.bbox.width
    assert bbox.y1 <= result.figure.bbox.height

    plt.close(result.figure)


def test_histogram_interactive_uniform_reference_line_shows_explanatory_hover() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            show_uniform_reference=True,
            figsize=(10.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    result.figure.canvas.draw()

    uniform_reference = (7 + 5 + 9 + 1) / 4.0
    _dispatch_motion_event_at_data(result.figure, result.axes, x=1.5, y=uniform_reference)
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert "uniform" in annotation.get_text().lower()
    assert "2^2" in annotation.get_text()
    assert "22" in annotation.get_text()

    plt.close(result.figure)


def test_histogram_interactive_label_button_toggles_decimal_labels_and_hover() -> None:
    result = plot_histogram(
        {"10 011": 7, "01 101": 3},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.label_mode is HistogramStateLabelMode.BINARY
    assert state.label_mode_button is not None

    state.toggle_label_mode()
    result.figure.canvas.draw()

    tick_labels = tuple(text.get_text() for text in result.axes.get_xticklabels())

    assert state.label_mode is HistogramStateLabelMode.DECIMAL
    assert state.label_mode_button.label.get_text() == "Labels: Decimal"
    assert tick_labels == ("1 5", "2 3")

    _dispatch_motion_event(result.figure, result.axes.patches[0])
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert "Decimal: 1 5" in annotation.get_text()
    assert "Counts: 3" in annotation.get_text()

    plt.close(result.figure)


def test_histogram_hover_is_enabled_by_default_and_can_be_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )

    default_result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(show=False),
    )
    default_state = get_histogram_state(default_result.figure)

    assert default_state is not None
    assert get_hover_state(default_result.axes) is not None

    disabled_result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            hover=False,
            show=False,
        ),
    )
    disabled_state = get_histogram_state(disabled_result.figure)

    assert disabled_state is not None
    assert get_hover_state(disabled_result.axes) is None

    plt.close(default_result.figure)
    plt.close(disabled_result.figure)


def test_histogram_interactive_layout_keeps_slider_below_state_labels() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.slider_axes is not None
    result.figure.canvas.draw()

    tick_texts = [text for text in result.axes.get_xticklabels() if text.get_text()]
    lowest_tick_label_y0 = min(
        text.get_window_extent(renderer=result.figure.canvas.get_renderer()).y0
        for text in tick_texts
    )
    _, slider_bottom, _, slider_height = state.slider_axes.get_window_extent(
        renderer=result.figure.canvas.get_renderer()
    ).bounds

    assert slider_bottom + slider_height < lowest_tick_label_y0

    plt.close(result.figure)


def test_histogram_interactive_slider_keeps_fixed_y_scale_across_windows() -> None:
    data = {format(index, "07b"): 1 for index in range(2**7)}
    data["1111111"] = 50

    result = plot_histogram(
        data,
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.horizontal_slider is not None

    initial_y_limits = result.axes.get_ylim()
    initial_bar_heights = tuple(bar.get_height() for bar in result.axes.patches)

    assert max(initial_bar_heights) == 1

    state.set_window_start(state.max_window_start)
    moved_y_limits = result.axes.get_ylim()
    moved_bar_heights = tuple(bar.get_height() for bar in result.axes.patches)

    assert max(moved_bar_heights) == 50
    assert moved_y_limits == pytest.approx(initial_y_limits)

    plt.close(result.figure)


def test_histogram_interactive_layout_keeps_plot_clear_of_controls_when_slider_is_off() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    state.toggle_slider()
    result.figure.canvas.draw()

    tick_texts = [text for text in result.axes.get_xticklabels() if text.get_text()]
    lowest_tick_label_y0 = min(
        text.get_window_extent(renderer=result.figure.canvas.get_renderer()).y0
        for text in tick_texts
    )
    control_tops = [
        axes.get_window_extent(renderer=result.figure.canvas.get_renderer()).y1
        for axes in (state.order_axes, state.slider_toggle_axes, state.marginal_axes)
        if axes is not None
    ]

    assert max(control_tops) < lowest_tick_label_y0

    plt.close(result.figure)


def test_histogram_interactive_hides_slider_button_when_slider_would_never_appear() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.horizontal_slider is None
    assert state.slider_toggle_button is None
    assert state.slider_toggle_axes is None

    plt.close(result.figure)


def test_histogram_interactive_hides_slider_button_after_reducing_to_small_marginal() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.slider_toggle_button is not None

    state.submit_marginal_text("0,2")

    assert state.slider_toggle_button is None
    assert state.slider_toggle_axes is None
    assert state.horizontal_slider is None

    plt.close(result.figure)


def test_histogram_interactive_removes_status_text_from_top_of_figure() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )

    assert not any(text.get_text().startswith("Order: ") for text in result.figure.texts)

    plt.close(result.figure)


def test_histogram_interactive_marginal_box_hover_shows_usage_help() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.marginal_axes is not None
    result.figure.canvas.draw()

    _dispatch_motion_event_at_axes_center(result.figure, state.marginal_axes)
    hover_state = get_hover_state(state.marginal_axes)

    assert hover_state is not None
    assert hover_state.annotation.get_visible() is True
    assert "0,2,5" in hover_state.annotation.get_text()
    assert "blank" in hover_state.annotation.get_text().lower()
    assert "\n" in hover_state.annotation.get_text()

    plt.close(result.figure)


def test_histogram_interactive_marginal_box_hover_repositions_inside_figure_near_top_right_corner() -> (
    None
):
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(7.0, 3.4),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.marginal_axes is not None
    result.figure.canvas.draw()

    _dispatch_motion_event_at_axes_corner(result.figure, state.marginal_axes)
    hover_state = get_hover_state(state.marginal_axes)

    assert hover_state is not None
    assert hover_state.annotation.get_visible() is True

    annotation = hover_state.annotation
    bbox = annotation.get_window_extent(renderer=result.figure.canvas.get_renderer())

    assert annotation.get_ha() == "right"
    assert annotation.get_va() == "bottom"
    assert bbox.x0 >= 0.0
    assert bbox.y0 >= 0.0
    assert bbox.x1 <= result.figure.bbox.width
    assert bbox.y1 <= result.figure.bbox.height

    plt.close(result.figure)


def test_histogram_interactive_marginal_box_matches_other_control_heights() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(10.0, 4.0),
        ),
    )
    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.order_axes is not None
    assert state.slider_toggle_axes is not None
    assert state.marginal_axes is not None

    assert state.marginal_axes.get_position().height == pytest.approx(
        state.order_axes.get_position().height
    )
    assert state.marginal_axes.get_position().height == pytest.approx(
        state.slider_toggle_axes.get_position().height
    )

    plt.close(result.figure)


def test_plot_histogram_saves_interactive_view_without_widgets(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    output = sandbox_tmp_path / "interactive-histogram.png"
    original_savefig = Figure.savefig
    saved_axes_counts: list[int] = []

    def count_savefig(self: Figure, *args: object, **kwargs: object) -> None:
        saved_axes_counts.append(len(self.axes))
        original_savefig(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", count_savefig)

    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode=HistogramMode.INTERACTIVE,
            output_path=output,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )

    assert len(result.figure.axes) > 1
    assert saved_axes_counts == [1]
    assert_saved_image_has_visible_content(output)

    plt.close(result.figure)
