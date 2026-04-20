from __future__ import annotations

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramDrawStyle,
    HistogramKind,
    HistogramResult,
    HistogramSort,
)
from quantum_circuit_drawer.histogram import plot_histogram
from quantum_circuit_drawer.style.theme import resolve_theme
from tests.support import assert_figure_has_visible_content, assert_saved_image_has_visible_content


def test_public_package_exports_histogram_types() -> None:
    assert quantum_circuit_drawer.HistogramConfig is HistogramConfig
    assert quantum_circuit_drawer.HistogramDrawStyle is HistogramDrawStyle
    assert quantum_circuit_drawer.HistogramKind is HistogramKind
    assert quantum_circuit_drawer.HistogramResult is HistogramResult
    assert quantum_circuit_drawer.HistogramSort is HistogramSort
    assert HistogramConfig().kind is HistogramKind.AUTO


def test_plot_histogram_returns_histogram_result_for_counts_dict() -> None:
    result = plot_histogram(
        {"00": 5, "11": 3},
        config=HistogramConfig(show=False),
    )

    assert isinstance(result, HistogramResult)
    assert isinstance(result.figure.canvas, FigureCanvasAgg)
    assert result.axes.figure is result.figure
    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("00", "11")
    assert result.values == (5.0, 3.0)
    assert result.qubits is None
    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)


def test_package_level_plot_histogram_forwards_config_and_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected_result = HistogramResult(
        figure=object(),
        axes=object(),
        kind=HistogramKind.COUNTS,
        state_labels=("0",),
        values=(1.0,),
        qubits=None,
    )

    def fake_plot_histogram(
        data: object,
        *,
        config: HistogramConfig | None = None,
        ax: object = None,
    ) -> HistogramResult:
        captured["data"] = data
        captured["config"] = config
        captured["ax"] = ax
        return expected_result

    monkeypatch.setattr(
        "quantum_circuit_drawer.histogram.plot_histogram",
        fake_plot_histogram,
    )

    figure, axes = plt.subplots()
    config = HistogramConfig(show=False)

    result = quantum_circuit_drawer.plot_histogram(
        {"0": 1},
        config=config,
        ax=axes,
    )

    assert result is expected_result
    assert captured["config"] is config
    assert captured["ax"] is axes

    plt.close(figure)


def test_plot_histogram_normalizes_integer_state_keys_to_padded_bitstrings() -> None:
    result = plot_histogram(
        {0: 5, 3: 3},
        config=HistogramConfig(show=False),
    )

    assert result.state_labels == ("00", "11")
    assert result.values == (5.0, 3.0)

    plt.close(result.figure)


def test_plot_histogram_returns_joint_marginal_for_selected_qubits_in_requested_order() -> None:
    result = plot_histogram(
        {"101": 2, "001": 1, "111": 3},
        config=HistogramConfig(show=False, qubits=(0, 2)),
    )

    assert result.qubits == (0, 2)
    assert result.state_labels == ("00", "01", "10", "11")
    assert result.values == (0.0, 0.0, 1.0, 5.0)

    plt.close(result.figure)


def test_plot_histogram_changes_joint_marginal_labels_when_qubit_order_changes() -> None:
    result = plot_histogram(
        {"101": 2, "001": 1, "111": 3},
        config=HistogramConfig(show=False, qubits=(2, 0)),
    )

    assert result.state_labels == ("00", "01", "10", "11")
    assert result.values == (0.0, 1.0, 0.0, 5.0)

    plt.close(result.figure)


def test_plot_histogram_rejects_duplicate_qubits() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        HistogramConfig(qubits=(1, 1))


def test_plot_histogram_rejects_negative_qubits() -> None:
    with pytest.raises(ValueError, match="non-negative integers"):
        HistogramConfig(qubits=(0, -1))


def test_plot_histogram_rejects_figsize_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="figsize cannot be used with ax"):
        plot_histogram(
            {"0": 1},
            config=HistogramConfig(show=False, figsize=(6.0, 4.0)),
            ax=axes,
        )

    plt.close(figure)


def test_plot_histogram_rejects_unsupported_objects() -> None:
    with pytest.raises(TypeError, match="does not support objects"):
        plot_histogram(object(), config=HistogramConfig(show=False))


def test_plot_histogram_rejects_counts_override_for_negative_quasi_values() -> None:
    with pytest.raises(ValueError, match="non-negative integer values"):
        plot_histogram(
            {"00": 0.6, "11": -0.2},
            config=HistogramConfig(show=False, kind=HistogramKind.COUNTS),
        )


def test_plot_histogram_rejects_qubits_outside_available_state_width() -> None:
    with pytest.raises(ValueError, match="available state width"):
        plot_histogram(
            {"00": 5, "11": 3},
            config=HistogramConfig(show=False, qubits=(2,)),
        )


def test_plot_histogram_sorts_by_value_descending_with_state_tiebreak() -> None:
    result = plot_histogram(
        {"01": 5, "10": 5, "00": 7, "11": 2},
        config=HistogramConfig(show=False, sort=HistogramSort.VALUE_DESC),
    )

    assert result.state_labels == ("00", "01", "10", "11")
    assert result.values == (7.0, 5.0, 5.0, 2.0)

    plt.close(result.figure)


def test_plot_histogram_sorts_by_value_ascending_with_state_tiebreak() -> None:
    result = plot_histogram(
        {"01": 5, "10": 5, "00": 7, "11": 2},
        config=HistogramConfig(show=False, sort=HistogramSort.VALUE_ASC),
    )

    assert result.state_labels == ("11", "01", "10", "00")
    assert result.values == (2.0, 5.0, 5.0, 7.0)

    plt.close(result.figure)


def test_plot_histogram_limits_to_top_k_after_sorting() -> None:
    result = plot_histogram(
        {"000": 11, "001": 7, "010": 5, "011": 3},
        config=HistogramConfig(
            show=False,
            sort=HistogramSort.VALUE_DESC,
            top_k=2,
        ),
    )

    assert result.state_labels == ("000", "001")
    assert result.values == (11.0, 7.0)
    assert len(result.axes.patches) == 2

    plt.close(result.figure)


def test_plot_histogram_rejects_non_positive_top_k() -> None:
    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        HistogramConfig(top_k=0)


def test_plot_histogram_draws_uniform_reference_for_counts_using_full_state_space() -> None:
    result = plot_histogram(
        {"00": 5, "01": 3, "10": 1, "11": 7},
        config=HistogramConfig(
            show=False,
            sort=HistogramSort.VALUE_DESC,
            top_k=2,
            show_uniform_reference=True,
        ),
    )

    horizontal_lines = [line for line in result.axes.lines if tuple(line.get_ydata()) == (4.0, 4.0)]

    assert horizontal_lines

    plt.close(result.figure)


def test_plot_histogram_draws_uniform_reference_for_marginal_quasi_using_subset_width() -> None:
    result = plot_histogram(
        {"000": 0.30, "001": 0.20, "110": 0.15, "111": 0.35},
        config=HistogramConfig(
            show=False,
            kind=HistogramKind.QUASI,
            qubits=(2, 0),
            show_uniform_reference=True,
        ),
    )

    horizontal_lines = [
        line for line in result.axes.lines if tuple(line.get_ydata()) == (0.25, 0.25)
    ]

    assert horizontal_lines

    plt.close(result.figure)


def test_plot_histogram_uses_dark_theme_by_default() -> None:
    result = plot_histogram(
        {"00": 5, "11": 3},
        config=HistogramConfig(show=False),
    )

    dark_theme = resolve_theme("dark")

    assert result.figure.get_facecolor() == pytest.approx(
        plt.matplotlib.colors.to_rgba(dark_theme.figure_facecolor)
    )
    assert result.axes.get_facecolor() == pytest.approx(
        plt.matplotlib.colors.to_rgba(dark_theme.axes_facecolor)
    )

    plt.close(result.figure)


def test_plot_histogram_outline_style_draws_unfilled_bars() -> None:
    result = plot_histogram(
        {"00": 5, "11": 3},
        config=HistogramConfig(
            show=False,
            draw_style=HistogramDrawStyle.OUTLINE,
        ),
    )

    bars = [patch for patch in result.axes.patches if isinstance(patch, Rectangle)]

    assert bars
    assert all(bar.get_fill() is False for bar in bars)

    plt.close(result.figure)


def test_plot_histogram_draws_negative_quasi_values_below_zero() -> None:
    result = plot_histogram(
        {"00": 0.6, "11": -0.2},
        config=HistogramConfig(show=False, kind=HistogramKind.QUASI),
    )

    bars = [patch for patch in result.axes.patches if isinstance(patch, Rectangle)]
    negative_bars = [bar for bar in bars if bar.get_height() < 0.0]

    assert result.kind is HistogramKind.QUASI
    assert negative_bars
    assert all(bar.get_y() == 0.0 for bar in negative_bars)

    plt.close(result.figure)


def test_plot_histogram_saves_non_empty_output(sandbox_tmp_path) -> None:
    output = sandbox_tmp_path / "histogram.png"

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=HistogramConfig(show=False, output_path=output),
    )

    assert_saved_image_has_visible_content(output)
    plt.close(result.figure)


def test_plot_histogram_uses_pyplot_show_for_managed_figures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show_calls: list[bool] = []

    def fake_show(*args: object, **kwargs: object) -> None:
        del args, kwargs
        show_calls.append(True)

    def fail_figure_show(self: Figure, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        raise AssertionError("plot_histogram should not call Figure.show directly")

    monkeypatch.setattr(plt, "show", fake_show)
    monkeypatch.setattr(Figure, "show", fail_figure_show)

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=HistogramConfig(show=True),
    )

    assert show_calls == [True]
    plt.close(result.figure)
