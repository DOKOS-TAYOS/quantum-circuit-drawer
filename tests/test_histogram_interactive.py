from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
from matplotlib.text import Annotation

from quantum_circuit_drawer import HistogramConfig, HistogramKind, HistogramMode, HistogramSort
from quantum_circuit_drawer.histogram import plot_histogram
from quantum_circuit_drawer.renderers._matplotlib_figure import get_histogram_state
from tests.support import assert_saved_image_has_visible_content


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


def test_plot_histogram_interactive_mode_attaches_controls_and_windowed_view() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=HistogramConfig(
            mode=HistogramMode.INTERACTIVE,
            show=False,
            figsize=(8.0, 4.0),
        ),
    )

    state = get_histogram_state(result.figure)

    assert state is not None
    assert state.horizontal_slider is not None
    assert state.order_button is not None
    assert state.slider_toggle_button is not None
    assert state.marginal_text_box is not None
    assert state.slider_enabled is True
    assert state.visible_bin_count < len(result.state_labels)
    assert len(result.axes.patches) == state.visible_bin_count

    plt.close(result.figure)


def test_histogram_interactive_cycle_sort_updates_status_and_visible_labels() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 9, "11": 1},
        config=HistogramConfig(
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

    state.cycle_sort()
    assert state.current_sort is HistogramSort.VALUE_ASC
    assert state.current_labels == ("11", "01", "00", "10")

    state.cycle_sort()
    assert state.current_sort is HistogramSort.VALUE_DESC
    assert state.current_labels == ("10", "00", "01", "11")
    assert "Counts descending" in state.status_text.get_text()

    plt.close(result.figure)


def test_histogram_interactive_slider_toggle_expands_to_full_distribution() -> None:
    result = plot_histogram(
        _dense_histogram_counts(),
        config=HistogramConfig(
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

    plt.close(result.figure)


def test_histogram_interactive_marginal_text_updates_distribution_and_preserves_last_valid_state() -> (
    None
):
    result = plot_histogram(
        _dense_histogram_counts(),
        config=HistogramConfig(
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
    assert "q0,q2,q5" in state.status_text.get_text()

    state.submit_marginal_text("0, bad")
    assert state.active_qubits == (0, 2, 5)
    assert "comma-separated" in state.message_text.get_text()

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
        config=HistogramConfig(
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
        config=HistogramConfig(
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
