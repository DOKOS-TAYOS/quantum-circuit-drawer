from __future__ import annotations

from collections import defaultdict

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    DiagnosticSeverity,
    DrawConfig,
    HistogramCompareConfig,
    HistogramCompareMetrics,
    HistogramCompareResult,
    HistogramCompareSort,
    HistogramConfig,
    RenderDiagnostic,
    StylePreset,
    UnsupportedPolicy,
    compare_histograms,
    draw_quantum_circuit,
    plot_histogram,
)
from quantum_circuit_drawer.drawing.runtime import RuntimeContext
from quantum_circuit_drawer.exceptions import UnsupportedOperationError
from tests.support import (
    FakeMyQLMCircuit,
    FakeMyQLMGateDefinition,
    FakeMyQLMOp,
    FakeMyQLMSyntax,
    assert_figure_has_visible_content,
    build_sample_ir,
    install_fake_myqlm,
    normalize_rendered_text,
)


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


def test_draw_quantum_circuit_reports_runtime_diagnostics_for_auto_mode_and_hidden_hover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(show=False, hover=True),
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
        config=HistogramConfig(show=False),
    )

    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "auto_mode_resolved",
        "histogram_auto_mode_fallback_static",
    }

    plt.close(result.figure)


def test_draw_quantum_circuit_uses_placeholder_for_supported_recoverable_unsupported_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    result = draw_quantum_circuit(
        build_placeholder_ready_myqlm_circuit(),
        config=DrawConfig(
            framework="myqlm",
            show=False,
            unsupported_policy=UnsupportedPolicy.PLACEHOLDER,
        ),
    )
    texts = [normalize_rendered_text(text.get_text()) for text in result.primary_axes.texts]

    assert any("RESET" in text and "unsupported" in text for text in texts)
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
            config=DrawConfig(
                framework="myqlm",
                show=False,
                unsupported_policy=UnsupportedPolicy.PLACEHOLDER,
            ),
        )


def test_draw_preset_applies_theme_and_explicit_style_keeps_priority() -> None:
    preset_result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(show=False, preset=StylePreset.PAPER),
    )
    override_result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(
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
        config=HistogramConfig(show=False, preset=StylePreset.PAPER),
    )
    override_result = plot_histogram(
        {"00": 5, "11": 3},
        config=HistogramConfig(show=False, preset=StylePreset.PAPER, theme="light"),
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
        config=HistogramCompareConfig(
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
    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)


def test_compare_histograms_overlay_uses_same_bin_position_colors_and_front_bar_visibility() -> (
    None
):
    result = compare_histograms(
        {"00": 3, "01": 9},
        {"00": 7, "01": 2},
        config=HistogramCompareConfig(show=False),
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
