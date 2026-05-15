from __future__ import annotations

from collections import defaultdict

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import MouseEvent, PickEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Annotation

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    DiagnosticSeverity,
    DrawConfig,
    DrawMode,
    HistogramCompareConfig,
    HistogramCompareMetrics,
    HistogramCompareOptions,
    HistogramCompareResult,
    HistogramCompareSort,
    HistogramConfig,
    HistogramKind,
    RenderDiagnostic,
    StylePreset,
    UnsupportedPolicy,
    compare_histograms,
    draw_quantum_circuit,
    plot_histogram,
)
from quantum_circuit_drawer.drawing.runtime import RuntimeContext
from quantum_circuit_drawer.exceptions import UnsupportedOperationError
from quantum_circuit_drawer.renderers._matplotlib_figure import get_hover_state
from tests.support import (
    FakeMyQLMCircuit,
    FakeMyQLMGateDefinition,
    FakeMyQLMOp,
    FakeMyQLMSyntax,
    assert_figure_has_visible_content,
    assert_saved_image_has_visible_content,
    build_public_draw_config,
    build_public_histogram_compare_config,
    build_public_histogram_config,
    build_sample_ir,
    install_fake_myqlm,
    normalize_rendered_text,
)


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


def _dispatch_pick_event(figure: Figure, artist: object) -> None:
    event = PickEvent(
        "pick_event",
        figure.canvas,
        MouseEvent("button_press_event", figure.canvas, 0.0, 0.0, button=1),
        artist,
    )
    figure.canvas.callbacks.process("pick_event", event)


def build_placeholder_ready_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "H": FakeMyQLMGateDefinition(name="H", arity=1, syntax=FakeMyQLMSyntax(name="H")),
        "RESET": FakeMyQLMGateDefinition(
            name="RESET",
            arity=1,
            syntax=FakeMyQLMSyntax(name="RESET"),
        ),
    }
    return FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(gate="H", qbits=(0,)),
            FakeMyQLMOp(type="RESET", qbits=(0,), cbits=(0,)),
        ),
        gate_dic=gate_dic,
        nbqbits=1,
        nbcbits=1,
        name="placeholder_ready",
    )


def build_placeholder_fallback_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "H": FakeMyQLMGateDefinition(name="H", arity=1, syntax=FakeMyQLMSyntax(name="H")),
    }
    return FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(gate="H", qbits=(0,)),
            FakeMyQLMOp(type="CUSTOMBOX", qbits=(0,)),
        ),
        gate_dic=gate_dic,
        nbqbits=1,
        nbcbits=0,
        name="placeholder_fallback",
    )


def build_structurally_invalid_myqlm_measurement_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "H": FakeMyQLMGateDefinition(name="H", arity=1, syntax=FakeMyQLMSyntax(name="H")),
    }
    return FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(gate="H", qbits=(0,)),
            FakeMyQLMOp(type="MEASURE", qbits=(0, 1), cbits=(0,)),
        ),
        gate_dic=gate_dic,
        nbqbits=2,
        nbcbits=1,
        name="invalid_measurement_shape",
    )


def test_public_package_exports_diagnostics_preset_and_compare_types() -> None:
    assert quantum_circuit_drawer.RenderDiagnostic is RenderDiagnostic
    assert quantum_circuit_drawer.DiagnosticSeverity is DiagnosticSeverity
    assert quantum_circuit_drawer.StylePreset is StylePreset
    assert quantum_circuit_drawer.UnsupportedPolicy is UnsupportedPolicy
    assert quantum_circuit_drawer.HistogramCompareConfig is HistogramCompareConfig
    assert quantum_circuit_drawer.HistogramCompareMetrics is HistogramCompareMetrics
    assert quantum_circuit_drawer.HistogramCompareResult is HistogramCompareResult
    assert quantum_circuit_drawer.HistogramCompareSort is HistogramCompareSort
    assert quantum_circuit_drawer.compare_histograms is compare_histograms
    assert DrawConfig().unsupported_policy is UnsupportedPolicy.RAISE
    assert HistogramConfig().preset is None


def test_package_level_compare_histograms_forwards_flat_common_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected_result = HistogramCompareResult(
        figure=object(),
        axes=object(),
        kind=HistogramKind.COUNTS,
        state_labels=("0",),
        left_values=(1.0,),
        right_values=(0.0,),
        delta_values=(1.0,),
        metrics=HistogramCompareMetrics(1.0, 1.0),
        qubits=None,
    )

    def fake_compare_histograms(
        left_data: object,
        right_data: object,
        *additional_data: object,
        kind: object = None,
        sort: object = None,
        qubits: tuple[int, ...] | None = None,
        top_k: int | None = None,
        result_index: int | None = None,
        data_key: str | None = None,
        left_label: str | None = None,
        right_label: str | None = None,
        series_labels: tuple[str, ...] | None = None,
        show: bool | None = None,
        output_path: object = None,
        figsize: tuple[float, float] | None = None,
        config: HistogramCompareConfig | None = None,
        ax: object = None,
    ) -> HistogramCompareResult:
        captured["left_data"] = left_data
        captured["right_data"] = right_data
        captured["additional_data"] = additional_data
        captured["kind"] = kind
        captured["sort"] = sort
        captured["qubits"] = qubits
        captured["top_k"] = top_k
        captured["result_index"] = result_index
        captured["data_key"] = data_key
        captured["left_label"] = left_label
        captured["right_label"] = right_label
        captured["series_labels"] = series_labels
        captured["show"] = show
        captured["output_path"] = output_path
        captured["figsize"] = figsize
        captured["config"] = config
        captured["ax"] = ax
        return expected_result

    monkeypatch.setattr(
        "quantum_circuit_drawer.histogram.compare_histograms",
        fake_compare_histograms,
    )

    figure, axes = plt.subplots()
    config = build_public_histogram_compare_config(show=False)

    result = quantum_circuit_drawer.compare_histograms(
        {"0": 1},
        {"0": 0},
        {"0": 2},
        kind="counts",
        sort="delta_desc",
        qubits=(0,),
        top_k=1,
        result_index=0,
        data_key="c",
        left_label="Before",
        right_label="After",
        series_labels=("Before", "After", "Third"),
        show=False,
        output_path="compare-histogram.png",
        figsize=(3.0, 2.0),
        config=config,
        ax=axes,
    )

    assert result is expected_result
    assert captured["additional_data"] == ({"0": 2},)
    assert captured["kind"] == "counts"
    assert captured["sort"] == "delta_desc"
    assert captured["qubits"] == (0,)
    assert captured["top_k"] == 1
    assert captured["result_index"] == 0
    assert captured["data_key"] == "c"
    assert captured["left_label"] == "Before"
    assert captured["right_label"] == "After"
    assert captured["series_labels"] == ("Before", "After", "Third")
    assert captured["show"] is False
    assert captured["output_path"] == "compare-histogram.png"
    assert captured["figsize"] == (3.0, 2.0)
    assert captured["config"] is config
    assert captured["ax"] is axes

    plt.close(figure)


def test_draw_quantum_circuit_reports_runtime_diagnostics_for_auto_mode_and_hidden_hover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=build_public_draw_config(show=False, hover=True),
    )

    diagnostic_codes = {diagnostic.code for diagnostic in result.diagnostics}

    assert "auto_mode_resolved" in diagnostic_codes
    assert "hover_disabled_hidden_2d" in diagnostic_codes

    plt.close(result.primary_figure)


def test_plot_histogram_reports_runtime_diagnostic_when_auto_mode_falls_back_to_static(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="inline"),
    )

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=False),
    )

    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "auto_mode_resolved",
        "histogram_auto_mode_fallback_static",
    }

    plt.close(result.figure)


def test_draw_quantum_circuit_warns_when_show_true_uses_noninteractive_wsl_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )
    monkeypatch.setattr("quantum_circuit_drawer.drawing.runtime._running_in_wsl", lambda: True)
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime._platform_system",
        lambda: "Linux",
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=build_public_draw_config(show=True),
    )

    warning = next(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "show_requested_without_interactive_backend"
    )

    assert warning.severity is DiagnosticSeverity.WARNING
    assert "python3-tk" in warning.message
    assert "WSL2" in warning.message

    plt.close(result.primary_figure)


def test_plot_histogram_warns_when_show_true_uses_noninteractive_linux_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )
    monkeypatch.setattr("quantum_circuit_drawer.drawing.runtime._running_in_wsl", lambda: False)
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime._platform_system",
        lambda: "Linux",
    )

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=True),
    )

    warning = next(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "show_requested_without_interactive_backend"
    )

    assert warning.severity is DiagnosticSeverity.WARNING
    assert "python3-tk" in warning.message
    assert "Linux" in warning.message

    plt.close(result.figure)


def test_draw_quantum_circuit_keeps_supported_myqlm_reset_drawable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    result = draw_quantum_circuit(
        build_placeholder_ready_myqlm_circuit(),
        config=build_public_draw_config(
            framework="myqlm",
            show=False,
            unsupported_policy=UnsupportedPolicy.PLACEHOLDER,
        ),
    )
    texts = [normalize_rendered_text(text.get_text()) for text in result.primary_axes.texts]

    assert "RESET" in texts
    assert not any(
        diagnostic.code == "unsupported_operation_placeholder" for diagnostic in result.diagnostics
    )
    assert_figure_has_visible_content(result.primary_figure)

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_uses_placeholder_for_recoverable_unsupported_myqlm_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    result = draw_quantum_circuit(
        build_placeholder_fallback_myqlm_circuit(),
        config=build_public_draw_config(
            framework="myqlm",
            mode=DrawMode.FULL,
            show=False,
            unsupported_policy=UnsupportedPolicy.PLACEHOLDER,
        ),
    )
    texts = [normalize_rendered_text(text.get_text()) for text in result.primary_axes.texts]

    assert any("CUSTOMBOX" in text and "unsupported" in text for text in texts)
    assert any(
        diagnostic.code == "unsupported_operation_placeholder"
        and diagnostic.severity is DiagnosticSeverity.WARNING
        for diagnostic in result.diagnostics
    )
    assert_figure_has_visible_content(result.primary_figure)

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_keeps_structural_errors_even_with_placeholder_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    with pytest.raises(UnsupportedOperationError, match="matching qubit/cbit counts"):
        draw_quantum_circuit(
            build_structurally_invalid_myqlm_measurement_circuit(),
            config=build_public_draw_config(
                framework="myqlm",
                show=False,
                unsupported_policy=UnsupportedPolicy.PLACEHOLDER,
            ),
        )


def test_draw_preset_applies_theme_and_explicit_style_keeps_priority() -> None:
    preset_result = draw_quantum_circuit(
        build_sample_ir(),
        config=build_public_draw_config(show=False, preset=StylePreset.PAPER),
    )
    override_result = draw_quantum_circuit(
        build_sample_ir(),
        config=build_public_draw_config(
            show=False,
            preset=StylePreset.PAPER,
            style={"theme": "dark"},
        ),
    )

    assert preset_result.primary_figure.get_facecolor() == pytest.approx(
        plt.matplotlib.colors.to_rgba("#fffdf7")
    )
    assert override_result.primary_figure.get_facecolor() == pytest.approx(
        plt.matplotlib.colors.to_rgba("#0b0f14")
    )

    plt.close(preset_result.primary_figure)
    plt.close(override_result.primary_figure)


def test_histogram_preset_applies_theme_and_explicit_theme_keeps_priority() -> None:
    preset_result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=False, preset=StylePreset.PAPER),
    )
    override_result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(
            show=False,
            preset=StylePreset.PAPER,
            theme="light",
        ),
    )

    assert preset_result.figure.get_facecolor() == pytest.approx(
        plt.matplotlib.colors.to_rgba("#fffdf7")
    )
    assert override_result.figure.get_facecolor() == pytest.approx(
        plt.matplotlib.colors.to_rgba("#ffffff")
    )

    plt.close(preset_result.figure)
    plt.close(override_result.figure)


def test_compare_histograms_returns_overlay_result_with_metrics_and_diagnostics() -> None:
    result = compare_histograms(
        {"00": 8, "01": 2, "11": 5},
        {"00": 4, "10": 7, "11": 6},
        config=build_public_histogram_compare_config(
            show=False,
            sort=HistogramCompareSort.DELTA_DESC,
            left_label="Reference",
            right_label="Candidate",
        ),
    )

    assert isinstance(result, HistogramCompareResult)
    assert isinstance(result.figure.canvas, FigureCanvasAgg)
    assert result.axes.figure is result.figure
    assert result.state_labels == ("10", "00", "01", "11")
    assert result.left_values == (0.0, 8.0, 2.0, 5.0)
    assert result.right_values == (7.0, 4.0, 0.0, 6.0)
    assert result.delta_values == (-7.0, 4.0, 2.0, -1.0)
    assert result.metrics == HistogramCompareMetrics(
        total_variation_distance=7.0,
        max_absolute_delta=7.0,
    )
    assert result.diagnostics == ()
    assert result.saved_path is None
    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)


def test_compare_histograms_accepts_flat_common_kwargs() -> None:
    result = compare_histograms(
        {"00": 7, "01": 5, "11": 2},
        {"00": 1, "01": 5, "11": 9},
        kind="counts",
        sort="delta_desc",
        top_k=2,
        left_label="Before",
        right_label="After",
        show=False,
        figsize=(4.0, 2.5),
    )

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("11", "00")
    assert result.left_values == (2.0, 7.0)
    assert result.right_values == (9.0, 1.0)
    assert result.series_labels == ("Before", "After")
    assert tuple(result.figure.get_size_inches()) == pytest.approx((4.0, 2.5))

    plt.close(result.figure)


def test_compare_histograms_flat_kwargs_override_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_show(*args: object, **kwargs: object) -> None:
        pytest.fail("flat show=False should override config.output.show=True")

    monkeypatch.setattr(
        "quantum_circuit_drawer.renderers._render_support.show_figure_if_supported",
        fail_show,
    )
    config = build_public_histogram_compare_config(
        show=True,
        sort=HistogramCompareSort.STATE,
        top_k=None,
        left_label="Left",
        right_label="Right",
        figsize=(7.0, 5.0),
    )

    result = compare_histograms(
        {"00": 7, "01": 5, "11": 2},
        {"00": 1, "01": 5, "11": 9},
        sort="delta_desc",
        top_k=1,
        left_label="Before",
        right_label="After",
        show=False,
        figsize=(3.0, 2.0),
        config=config,
    )

    assert result.state_labels == ("11",)
    assert result.series_labels == ("Before", "After")
    assert tuple(result.figure.get_size_inches()) == pytest.approx((3.0, 2.0))

    plt.close(result.figure)


def test_compare_histograms_flat_strings_and_enums_match() -> None:
    left_data = {"00": 7, "01": 5, "11": 2}
    right_data = {"00": 1, "01": 5, "11": 9}

    enum_result = compare_histograms(
        left_data,
        right_data,
        kind=HistogramKind.COUNTS,
        sort=HistogramCompareSort.DELTA_DESC,
        show=False,
    )
    string_result = compare_histograms(
        left_data,
        right_data,
        kind="counts",
        sort="delta_desc",
        show=False,
    )

    assert enum_result.kind is string_result.kind
    assert enum_result.state_labels == string_result.state_labels
    assert enum_result.left_values == string_result.left_values
    assert enum_result.right_values == string_result.right_values

    plt.close(enum_result.figure)
    plt.close(string_result.figure)


def test_compare_histograms_rejects_flat_figsize_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="figsize cannot be used with ax"):
        compare_histograms(
            {"00": 7},
            {"00": 1},
            show=False,
            figsize=(3.0, 2.0),
            ax=axes,
        )

    plt.close(figure)


def test_compare_histograms_reports_normalized_saved_path(sandbox_tmp_path) -> None:
    output = sandbox_tmp_path / "compare-histograms.png"

    result = compare_histograms(
        {"00": 8, "01": 2},
        {"00": 4, "01": 5},
        config=build_public_histogram_compare_config(show=False, output_path=output),
    )

    assert_saved_image_has_visible_content(output)
    assert result.saved_path == str(output.resolve())

    plt.close(result.figure)


def test_compare_histograms_overlay_uses_same_bin_position_colors_and_front_bar_visibility() -> (
    None
):
    result = compare_histograms(
        {"00": 3, "01": 9},
        {"00": 7, "01": 2},
        config=build_public_histogram_compare_config(show=False),
    )

    grouped_patches: dict[float, list[object]] = defaultdict(list)
    for patch in result.axes.patches:
        center_x = round(float(patch.get_x() + (patch.get_width() / 2.0)), 6)
        grouped_patches[center_x].append(patch)

    assert len(grouped_patches) == len(result.state_labels)
    assert len(result.axes.lines) >= len(result.state_labels)

    for index, center_x in enumerate(sorted(grouped_patches)):
        patches = grouped_patches[center_x]
        assert len(patches) == 2
        ordered_by_z = sorted(patches, key=lambda patch: float(patch.get_zorder()))
        back_patch, front_patch = ordered_by_z
        assert float(front_patch.get_height()) == pytest.approx(
            min(result.left_values[index], result.right_values[index])
        )
        assert float(back_patch.get_height()) == pytest.approx(
            max(result.left_values[index], result.right_values[index])
        )
        assert front_patch.get_alpha() is not None
        assert float(front_patch.get_alpha()) < 1.0
        assert front_patch.get_facecolor() != back_patch.get_facecolor()

    plt.close(result.figure)


def test_compare_histograms_uses_theme_text_color_for_legend_in_dark_mode() -> None:
    config = build_public_histogram_compare_config(
        show=False,
        theme="dark",
        left_label="Ideal",
        right_label="Sampled",
    )
    result = compare_histograms(
        {"00": 8, "01": 2},
        {"00": 4, "01": 5},
        config=config,
    )

    legend = result.axes.get_legend()

    assert legend is not None
    assert tuple(text.get_color() for text in legend.get_texts()) == (
        config.theme.text_color,
        config.theme.text_color,
    )

    plt.close(result.figure)


def test_compare_histograms_hover_reports_both_series_values_for_one_bin() -> None:
    result = compare_histograms(
        {"00": 8, "01": 2},
        {"00": 4, "01": 5},
        config=build_public_histogram_compare_config(
            show=False,
            sort=HistogramCompareSort.STATE,
            left_label="Ideal",
            right_label="Sampled",
        ),
    )

    assert get_hover_state(result.axes) is not None

    result.figure.canvas.draw()
    _dispatch_motion_event(result.figure, result.axes.patches[0])
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert "State: 00" in annotation.get_text()
    assert "Ideal counts: 8" in annotation.get_text()
    assert "Sampled counts: 4" in annotation.get_text()
    assert "Delta: 4" in annotation.get_text()

    plt.close(result.figure)


def test_compare_histograms_hover_repositions_inside_figure_near_top_right_bar() -> None:
    result = compare_histograms(
        {"0": 1, "1": 25},
        {"0": 2, "1": 18},
        config=build_public_histogram_compare_config(
            show=False,
            sort=HistogramCompareSort.STATE,
            figsize=(4.0, 3.0),
        ),
    )

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


def test_compare_histograms_hover_can_be_disabled() -> None:
    result = compare_histograms(
        {"00": 8, "01": 2},
        {"00": 4, "01": 5},
        config=build_public_histogram_compare_config(
            show=False,
            hover=False,
        ),
    )

    assert get_hover_state(result.axes) is None

    plt.close(result.figure)


def test_compare_histograms_legend_click_toggles_one_series_and_updates_hover() -> None:
    result = compare_histograms(
        {"00": 8, "01": 2},
        {"00": 4, "01": 5},
        config=build_public_histogram_compare_config(
            show=False,
            sort=HistogramCompareSort.STATE,
            left_label="Ideal",
            right_label="Sampled",
        ),
    )

    legend = result.axes.get_legend()

    assert legend is not None

    _dispatch_pick_event(result.figure, legend.get_texts()[0])

    left_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:left"
    ]
    right_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:right"
    ]

    assert left_patches
    assert right_patches
    assert all(patch.get_visible() is False for patch in left_patches)
    assert all(patch.get_visible() is True for patch in right_patches)
    assert result.axes.get_ylim() == pytest.approx((0.0, 5.25))

    result.figure.canvas.draw()
    _dispatch_motion_event(result.figure, right_patches[0])
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert "Sampled counts: 4" in annotation.get_text()
    assert "Ideal counts" not in annotation.get_text()

    plt.close(result.figure)


def test_compare_histograms_legend_click_works_for_mixed_quasi_and_counts() -> None:
    result = compare_histograms(
        {"00": 0.5, "11": 0.5},
        {"00": 47, "01": 3, "11": 50},
        config=build_public_histogram_compare_config(
            show=False,
            sort=HistogramCompareSort.STATE,
            left_label="Ideal",
            right_label="Sampled",
        ),
    )

    legend = result.axes.get_legend()

    assert legend is not None

    handle_artists = tuple(getattr(legend, "legend_handles", ()) or ())
    assert len(handle_artists) >= 2

    _dispatch_pick_event(result.figure, handle_artists[1])

    left_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:left"
    ]
    right_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:right"
    ]

    assert result.kind.name == "QUASI"
    assert all(patch.get_visible() is True for patch in left_patches)
    assert all(patch.get_visible() is False for patch in right_patches)

    result.figure.canvas.draw()
    _dispatch_motion_event(result.figure, left_patches[0])
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert "Ideal quasi-probability" in annotation.get_text()
    assert "Sampled quasi-probability" not in annotation.get_text()

    plt.close(result.figure)


def test_compare_histograms_accepts_multiple_series_and_legend_toggles_one_series() -> None:
    result = compare_histograms(
        {"00": 0.5, "11": 0.5},
        {"00": 47, "01": 3, "11": 50},
        {"00": 45, "10": 5, "11": 50},
        config=HistogramCompareConfig(
            compare=HistogramCompareOptions(
                sort=HistogramCompareSort.STATE,
                series_labels=("Ideal", "Sampled A", "Sampled B"),
            )
        ),
    )

    assert result.series_labels == ("Ideal", "Sampled A", "Sampled B")
    assert result.state_labels == ("00", "01", "10", "11")
    assert result.series_values == (
        (0.5, 0.0, 0.0, 0.5),
        (47.0, 3.0, 0.0, 50.0),
        (45.0, 0.0, 5.0, 50.0),
    )
    assert result.left_values == result.series_values[0]
    assert result.right_values == result.series_values[1]

    legend = result.axes.get_legend()

    assert legend is not None
    assert tuple(text.get_text() for text in legend.get_texts()) == (
        "Ideal",
        "Sampled A",
        "Sampled B",
    )

    _dispatch_pick_event(result.figure, legend.get_texts()[2])

    first_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:left"
    ]
    second_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:right"
    ]
    third_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:series-3"
    ]

    assert all(patch.get_visible() is True for patch in first_patches)
    assert all(patch.get_visible() is True for patch in second_patches)
    assert all(patch.get_visible() is False for patch in third_patches)

    result.figure.canvas.draw()
    _dispatch_motion_event(result.figure, first_patches[0])
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert "Ideal quasi-probability: 0.5" in annotation.get_text()
    assert "Sampled A quasi-probability: 47" in annotation.get_text()
    assert "Sampled B quasi-probability" not in annotation.get_text()
    assert "Range:" in annotation.get_text()

    plt.close(result.figure)


def test_compare_histograms_legend_click_allows_empty_state_and_reactivation() -> None:
    result = compare_histograms(
        {"00": 8, "01": 2},
        {"00": 4, "01": 5},
        config=build_public_histogram_compare_config(
            show=False,
            sort=HistogramCompareSort.STATE,
            left_label="Ideal",
            right_label="Sampled",
        ),
    )

    legend = result.axes.get_legend()

    assert legend is not None

    _dispatch_pick_event(result.figure, legend.get_texts()[0])
    _dispatch_pick_event(result.figure, legend.get_texts()[1])

    left_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:left"
    ]
    right_patches = [
        patch
        for patch in result.axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "histogram-compare:right"
    ]

    assert all(patch.get_visible() is False for patch in left_patches)
    assert all(patch.get_visible() is False for patch in right_patches)
    assert result.axes.get_ylim() == pytest.approx((0.0, 1.0))

    result.figure.canvas.draw()
    _dispatch_motion_event(result.figure, right_patches[0])
    annotation = next(text for text in result.axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is False

    _dispatch_pick_event(result.figure, legend.get_texts()[1])

    assert all(patch.get_visible() is False for patch in left_patches)
    assert all(patch.get_visible() is True for patch in right_patches)
    assert result.axes.get_ylim() == pytest.approx((0.0, 5.25))

    result.figure.canvas.draw()
    _dispatch_motion_event(result.figure, right_patches[0])

    assert annotation.get_visible() is True
    assert "Sampled counts: 4" in annotation.get_text()
    assert "Ideal counts" not in annotation.get_text()

    plt.close(result.figure)


def test_compare_histograms_legend_position_stays_fixed_after_visibility_toggles() -> None:
    result = compare_histograms(
        {"00": 8, "01": 2},
        {"00": 4, "01": 5},
        {"00": 6, "01": 1},
        config=HistogramCompareConfig(
            compare=HistogramCompareOptions(
                sort=HistogramCompareSort.STATE,
                series_labels=("Ideal", "Sampled", "Mitigated"),
            ),
        ),
    )

    legend = result.axes.get_legend()

    assert legend is not None
    result.figure.canvas.draw()
    initial_bbox = legend.get_window_extent(renderer=result.figure.canvas.get_renderer()).bounds

    _dispatch_pick_event(result.figure, legend.get_texts()[0])
    _dispatch_pick_event(result.figure, legend.get_texts()[2])
    result.figure.canvas.draw()
    final_bbox = legend.get_window_extent(renderer=result.figure.canvas.get_renderer()).bounds

    assert final_bbox == pytest.approx(initial_bbox)

    plt.close(result.figure)
