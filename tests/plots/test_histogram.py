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
    HistogramMode,
    HistogramResult,
    HistogramSort,
    HistogramStateLabelMode,
)
from quantum_circuit_drawer.drawing.runtime import RuntimeContext
from quantum_circuit_drawer.histogram import plot_histogram
from quantum_circuit_drawer.plots.histogram_render import (
    comparison_secondary_color,
    format_histogram_value,
    negative_bar_color,
)
from quantum_circuit_drawer.style.theme import resolve_theme
from tests.support import (
    assert_figure_has_visible_content,
    assert_saved_image_has_visible_content,
    build_public_histogram_config,
)


def test_public_package_exports_histogram_types() -> None:
    assert quantum_circuit_drawer.HistogramConfig is HistogramConfig
    assert quantum_circuit_drawer.HistogramDrawStyle is HistogramDrawStyle
    assert quantum_circuit_drawer.HistogramKind is HistogramKind
    assert quantum_circuit_drawer.HistogramMode is HistogramMode
    assert quantum_circuit_drawer.HistogramResult is HistogramResult
    assert quantum_circuit_drawer.HistogramStateLabelMode is HistogramStateLabelMode
    assert quantum_circuit_drawer.HistogramSort is HistogramSort
    assert HistogramConfig().kind is HistogramKind.AUTO
    assert HistogramConfig().mode is HistogramMode.AUTO
    assert HistogramConfig().hover is True
    assert HistogramConfig().state_label_mode is HistogramStateLabelMode.BINARY


def test_plot_histogram_returns_histogram_result_for_counts_dict() -> None:
    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(mode=HistogramMode.STATIC, show=False),
    )

    assert isinstance(result, HistogramResult)
    assert isinstance(result.figure.canvas, FigureCanvasAgg)
    assert result.axes.figure is result.figure
    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("00", "11")
    assert result.values == (5.0, 3.0)
    assert result.qubits is None
    assert result.saved_path is None
    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)


def test_plot_histogram_draws_value_labels_that_fit_inside_each_bin() -> None:
    result = plot_histogram(
        {"0": 123456, "1": 7},
        config=build_public_histogram_config(
            mode=HistogramMode.STATIC,
            show=False,
            figsize=(3.2, 2.4),
        ),
    )

    result.figure.canvas.draw()
    renderer = result.figure.canvas.get_renderer()
    bars = [patch for patch in result.axes.patches if isinstance(patch, Rectangle)]
    value_labels = [text for text in result.axes.texts if text.get_text() in {"1.235e5", "7"}]

    assert [text.get_text() for text in value_labels] == ["1.235e5", "7"]
    for bar, label in zip(bars, value_labels, strict=True):
        bar_bbox = bar.get_window_extent(renderer=renderer)
        label_bbox = label.get_window_extent(renderer=renderer)

        assert label_bbox.width <= bar_bbox.width + 1.0
        assert bar_bbox.x0 <= label_bbox.x0
        assert label_bbox.x1 <= bar_bbox.x1

    plt.close(result.figure)


def test_plot_histogram_skips_value_labels_for_dense_static_histograms() -> None:
    data = {format(index, "07b"): index + 1 for index in range(65)}

    result = plot_histogram(
        data,
        config=build_public_histogram_config(
            mode=HistogramMode.STATIC,
            show=False,
        ),
    )

    assert len(result.axes.texts) == 0

    plt.close(result.figure)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (324, "324"),
        (1031, "1031"),
        (-12, "-12"),
        (1.3234, "1.323"),
        (12.424, "12.42"),
        (0.32, "0.32"),
        (-0.13114, "-0.1311"),
        (0.00012345, "0.0001234"),
        (0.000012345, "1.234e-5"),
        (1.2e10, "1.2e10"),
    ],
)
def test_format_histogram_value_uses_four_significant_digits(value: float, expected: str) -> None:
    assert format_histogram_value(value, HistogramKind.QUASI) == expected


def test_plot_histogram_rotates_and_shrinks_dense_x_labels_to_avoid_overlap() -> None:
    data = {format(index, "06b"): index + 1 for index in range(8)}

    result = plot_histogram(
        data,
        config=build_public_histogram_config(
            mode=HistogramMode.STATIC,
            show=False,
            figsize=(4.0, 2.8),
        ),
    )

    result.figure.canvas.draw()
    renderer = result.figure.canvas.get_renderer()
    tick_labels = [text for text in result.axes.get_xticklabels() if text.get_text()]
    tick_bboxes = [text.get_window_extent(renderer=renderer) for text in tick_labels]

    assert tick_labels
    assert all(text.get_rotation() == pytest.approx(35.0) for text in tick_labels)
    assert max(text.get_fontsize() for text in tick_labels) < 10.0
    for left, right in zip(tick_bboxes, tick_bboxes[1:], strict=False):
        assert left.x1 <= right.x0 + 1.0

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
        kind: object = None,
        mode: object = None,
        sort: object = None,
        state_label_mode: object = None,
        qubits: tuple[int, ...] | None = None,
        top_k: int | None = None,
        result_index: int | None = None,
        data_key: str | None = None,
        show: bool | None = None,
        output_path: object = None,
        figsize: tuple[float, float] | None = None,
        config: HistogramConfig | None = None,
        ax: object = None,
    ) -> HistogramResult:
        captured["data"] = data
        captured["kind"] = kind
        captured["mode"] = mode
        captured["sort"] = sort
        captured["state_label_mode"] = state_label_mode
        captured["qubits"] = qubits
        captured["top_k"] = top_k
        captured["result_index"] = result_index
        captured["data_key"] = data_key
        captured["show"] = show
        captured["output_path"] = output_path
        captured["figsize"] = figsize
        captured["config"] = config
        captured["ax"] = ax
        return expected_result

    monkeypatch.setattr(
        "quantum_circuit_drawer.histogram.plot_histogram",
        fake_plot_histogram,
    )

    figure, axes = plt.subplots()
    config = build_public_histogram_config(show=False)

    result = quantum_circuit_drawer.plot_histogram(
        {"0": 1},
        kind="counts",
        mode="static",
        sort="value_desc",
        state_label_mode="decimal",
        qubits=(0,),
        top_k=1,
        result_index=0,
        data_key="c",
        show=False,
        output_path="histogram.png",
        figsize=(3.0, 2.0),
        config=config,
        ax=axes,
    )

    assert result is expected_result
    assert captured["kind"] == "counts"
    assert captured["mode"] == "static"
    assert captured["sort"] == "value_desc"
    assert captured["state_label_mode"] == "decimal"
    assert captured["qubits"] == (0,)
    assert captured["top_k"] == 1
    assert captured["result_index"] == 0
    assert captured["data_key"] == "c"
    assert captured["show"] is False
    assert captured["output_path"] == "histogram.png"
    assert captured["figsize"] == (3.0, 2.0)
    assert captured["config"] is config
    assert captured["ax"] is axes

    plt.close(figure)


def test_plot_histogram_accepts_flat_common_kwargs() -> None:
    result = plot_histogram(
        {"00": 7, "01": 5, "10": 5, "11": 2},
        kind="counts",
        mode="static",
        sort="value_desc",
        state_label_mode="decimal",
        top_k=3,
        show=False,
        figsize=(4.0, 2.5),
    )

    tick_labels = tuple(text.get_text() for text in result.axes.get_xticklabels())

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("00", "01", "10")
    assert result.values == (7.0, 5.0, 5.0)
    assert tick_labels == ("0", "1", "2")
    assert tuple(result.figure.get_size_inches()) == pytest.approx((4.0, 2.5))

    plt.close(result.figure)


def test_plot_histogram_flat_kwargs_override_config(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_show(*args: object, **kwargs: object) -> None:
        pytest.fail("flat show=False should override config.output.show=True")

    monkeypatch.setattr(
        "quantum_circuit_drawer.renderers._render_support.show_figure_if_supported",
        fail_show,
    )
    config = build_public_histogram_config(
        show=True,
        sort=HistogramSort.STATE_DESC,
        top_k=None,
        figsize=(7.0, 5.0),
    )

    result = plot_histogram(
        {"00": 7, "01": 5, "11": 2},
        sort="value_asc",
        top_k=2,
        show=False,
        figsize=(3.0, 2.0),
        config=config,
    )

    assert result.state_labels == ("11", "01")
    assert result.values == (2.0, 5.0)
    assert tuple(result.figure.get_size_inches()) == pytest.approx((3.0, 2.0))

    plt.close(result.figure)


def test_plot_histogram_flat_strings_and_enums_match() -> None:
    data = {"00": 7, "01": 5, "11": 2}

    enum_result = plot_histogram(
        data,
        kind=HistogramKind.COUNTS,
        mode=HistogramMode.STATIC,
        sort=HistogramSort.VALUE_ASC,
        state_label_mode=HistogramStateLabelMode.DECIMAL,
        show=False,
    )
    string_result = plot_histogram(
        data,
        kind="counts",
        mode="static",
        sort="value_asc",
        state_label_mode="decimal",
        show=False,
    )

    assert enum_result.kind is string_result.kind
    assert enum_result.state_labels == string_result.state_labels
    assert enum_result.values == string_result.values
    assert tuple(text.get_text() for text in enum_result.axes.get_xticklabels()) == tuple(
        text.get_text() for text in string_result.axes.get_xticklabels()
    )

    plt.close(enum_result.figure)
    plt.close(string_result.figure)


def test_plot_histogram_normalizes_integer_state_keys_to_padded_bitstrings() -> None:
    result = plot_histogram(
        {0: 5, 3: 3},
        config=build_public_histogram_config(show=False),
    )

    assert result.state_labels == ("00", "11")
    assert result.values == (5.0, 3.0)

    plt.close(result.figure)


def test_plot_histogram_sums_state_keys_that_normalize_to_same_label() -> None:
    result = plot_histogram(
        {0: 5, "0": 3, "1": 2},
        config=build_public_histogram_config(show=False),
    )

    assert result.state_labels == ("0", "1")
    assert result.values == (8.0, 2.0)

    plt.close(result.figure)


def test_plot_histogram_returns_joint_marginal_for_selected_qubits_in_requested_order() -> None:
    result = plot_histogram(
        {"101": 2, "001": 1, "111": 3},
        config=build_public_histogram_config(show=False, qubits=(0, 2)),
    )

    assert result.qubits == (0, 2)
    assert result.state_labels == ("00", "01", "10", "11")
    assert result.values == (0.0, 0.0, 1.0, 5.0)

    plt.close(result.figure)


def test_plot_histogram_changes_joint_marginal_labels_when_qubit_order_changes() -> None:
    result = plot_histogram(
        {"101": 2, "001": 1, "111": 3},
        config=build_public_histogram_config(show=False, qubits=(2, 0)),
    )

    assert result.state_labels == ("00", "01", "10", "11")
    assert result.values == (0.0, 1.0, 0.0, 5.0)

    plt.close(result.figure)


def test_plot_histogram_can_display_decimal_labels_for_spaced_registers() -> None:
    result = plot_histogram(
        {"10 011": 7, "01 101": 3},
        config=build_public_histogram_config(
            show=False,
            state_label_mode=HistogramStateLabelMode.DECIMAL,
        ),
    )

    tick_labels = tuple(text.get_text() for text in result.axes.get_xticklabels())

    assert result.state_labels == ("01 101", "10 011")
    assert tick_labels == ("1 5", "2 3")

    plt.close(result.figure)


def test_plot_histogram_rejects_duplicate_qubits() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        build_public_histogram_config(qubits=(1, 1))


def test_plot_histogram_rejects_negative_qubits() -> None:
    with pytest.raises(ValueError, match="non-negative integers"):
        build_public_histogram_config(qubits=(0, -1))


def test_plot_histogram_rejects_figsize_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="figsize cannot be used with ax"):
        plot_histogram(
            {"0": 1},
            config=build_public_histogram_config(show=False, figsize=(6.0, 4.0)),
            ax=axes,
        )

    plt.close(figure)


def test_plot_histogram_rejects_flat_figsize_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="figsize cannot be used with ax"):
        plot_histogram(
            {"0": 1},
            mode="static",
            show=False,
            figsize=(6.0, 4.0),
            ax=axes,
        )

    plt.close(figure)


def test_plot_histogram_rejects_unsupported_objects() -> None:
    with pytest.raises(TypeError, match="does not support objects"):
        plot_histogram(object(), config=build_public_histogram_config(show=False))


def test_plot_histogram_rejects_counts_override_for_negative_quasi_values() -> None:
    with pytest.raises(ValueError, match="non-negative integer values"):
        plot_histogram(
            {"00": 0.6, "11": -0.2},
            config=build_public_histogram_config(show=False, kind=HistogramKind.COUNTS),
        )


def test_plot_histogram_rejects_qubits_outside_available_state_width() -> None:
    with pytest.raises(ValueError, match="available state width"):
        plot_histogram(
            {"00": 5, "11": 3},
            config=build_public_histogram_config(show=False, qubits=(2,)),
        )


def test_plot_histogram_sorts_by_value_descending_with_state_tiebreak() -> None:
    result = plot_histogram(
        {"01": 5, "10": 5, "00": 7, "11": 2},
        config=build_public_histogram_config(show=False, sort=HistogramSort.VALUE_DESC),
    )

    assert result.state_labels == ("00", "01", "10", "11")
    assert result.values == (7.0, 5.0, 5.0, 2.0)

    plt.close(result.figure)


def test_plot_histogram_sorts_by_state_descending() -> None:
    result = plot_histogram(
        {"01": 5, "10": 5, "00": 7, "11": 2},
        config=build_public_histogram_config(show=False, sort=HistogramSort.STATE_DESC),
    )

    assert result.state_labels == ("11", "10", "01", "00")
    assert result.values == (2.0, 5.0, 5.0, 7.0)

    plt.close(result.figure)


def test_plot_histogram_sorts_by_value_ascending_with_state_tiebreak() -> None:
    result = plot_histogram(
        {"01": 5, "10": 5, "00": 7, "11": 2},
        config=build_public_histogram_config(show=False, sort=HistogramSort.VALUE_ASC),
    )

    assert result.state_labels == ("11", "01", "10", "00")
    assert result.values == (2.0, 5.0, 5.0, 7.0)

    plt.close(result.figure)


def test_plot_histogram_limits_to_top_k_after_sorting() -> None:
    result = plot_histogram(
        {"000": 11, "001": 7, "010": 5, "011": 3},
        config=build_public_histogram_config(
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
        build_public_histogram_config(top_k=0)


def test_plot_histogram_rejects_interactive_mode_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="requires a Matplotlib-managed figure"):
        plot_histogram(
            {"00": 5, "11": 3},
            config=build_public_histogram_config(show=False, mode=HistogramMode.INTERACTIVE),
            ax=axes,
        )

    plt.close(figure)


def test_plot_histogram_rejects_interactive_mode_in_non_widget_notebook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="inline"),
    )

    with pytest.raises(ValueError, match="requires a notebook widget backend"):
        plot_histogram(
            {"00": 5, "11": 3},
            config=build_public_histogram_config(show=False, mode=HistogramMode.INTERACTIVE),
        )


def test_plot_histogram_resolves_auto_mode_to_static_for_hidden_script_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quantum_circuit_drawer.renderers._matplotlib_figure import get_histogram_state

    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=False),
    )

    assert get_histogram_state(result.figure) is None

    plt.close(result.figure)


def test_plot_histogram_resolves_auto_mode_to_interactive_for_visible_scripts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quantum_circuit_drawer.renderers._matplotlib_figure import get_histogram_state

    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=True),
    )

    assert get_histogram_state(result.figure) is not None

    plt.close(result.figure)


def test_plot_histogram_resolves_auto_mode_to_interactive_for_widget_notebooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quantum_circuit_drawer.renderers._matplotlib_figure import get_histogram_state

    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="widget"),
    )

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=True),
    )

    assert get_histogram_state(result.figure) is not None

    plt.close(result.figure)


def test_plot_histogram_resolves_auto_mode_to_static_for_inline_notebooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quantum_circuit_drawer.renderers._matplotlib_figure import get_histogram_state

    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="inline"),
    )

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=False),
    )

    assert get_histogram_state(result.figure) is None

    plt.close(result.figure)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"top_k": True}, "top_k must be a positive integer"),
        ({"result_index": True}, "result_index must be a non-negative integer"),
        ({"qubits": (True,)}, "qubits must be a tuple of non-negative integers"),
        ({"figsize": (True, 4.0)}, "figsize must be a 2-item tuple of positive numbers"),
    ],
)
def test_histogram_config_rejects_boolean_numeric_values(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_public_histogram_config(**kwargs)


def test_plot_histogram_draws_uniform_reference_for_counts_using_full_state_space() -> None:
    result = plot_histogram(
        {"00": 5, "01": 3, "10": 1, "11": 7},
        config=build_public_histogram_config(
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
        config=build_public_histogram_config(
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


def test_plot_histogram_uses_zero_lower_bound_for_non_negative_quasi_values() -> None:
    result = plot_histogram(
        {"00": 0.6, "11": 0.4},
        config=build_public_histogram_config(
            show=False,
            kind=HistogramKind.QUASI,
        ),
    )

    assert result.axes.get_ylim()[0] == pytest.approx(0.0)

    plt.close(result.figure)


def test_plot_histogram_uses_dark_theme_by_default() -> None:
    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=False),
    )

    dark_theme = resolve_theme("dark")

    assert result.figure.get_facecolor() == pytest.approx(
        plt.matplotlib.colors.to_rgba(dark_theme.figure_facecolor)
    )
    assert result.axes.get_facecolor() == pytest.approx(
        plt.matplotlib.colors.to_rgba(dark_theme.axes_facecolor)
    )

    plt.close(result.figure)


def test_accessible_histogram_theme_uses_colorblind_friendly_contrast_colors() -> None:
    theme = resolve_theme("accessible")

    assert negative_bar_color(theme) == "#D55E00"
    assert comparison_secondary_color(theme) == "#D55E00"


def test_plot_histogram_outline_style_draws_unfilled_bars() -> None:
    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(
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
        config=build_public_histogram_config(show=False, kind=HistogramKind.QUASI),
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
        config=build_public_histogram_config(show=False, output_path=output),
    )

    assert_saved_image_has_visible_content(output)
    assert result.saved_path == str(output.resolve())
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
        config=build_public_histogram_config(show=True),
    )

    assert show_calls == [True]
    plt.close(result.figure)
