from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    CircuitBuilder,
    CircuitCompareConfig,
    CircuitCompareMetrics,
    CircuitCompareResult,
    DiagnosticSeverity,
    DrawConfig,
    DrawMode,
    DrawResult,
    RenderDiagnostic,
    compare_circuits,
    draw_quantum_circuit,
)
from quantum_circuit_drawer.drawing.runtime import RuntimeContext
from tests.support import (
    assert_figure_has_visible_content,
    assert_saved_image_has_visible_content,
    build_sample_ir,
)


def build_reference_compare_ir() -> object:
    return CircuitBuilder(2, 1, name="reference").h(0).cx(0, 1).measure(1, 0).build()


def build_candidate_compare_ir() -> object:
    return (
        CircuitBuilder(2, 1, name="candidate").h(0).x(1).cx(0, 1).swap(0, 1).measure(0, 0).build()
    )


def test_public_package_exports_compare_circuit_types() -> None:
    assert quantum_circuit_drawer.compare_circuits is compare_circuits
    assert quantum_circuit_drawer.CircuitCompareConfig is CircuitCompareConfig
    assert quantum_circuit_drawer.CircuitCompareMetrics is CircuitCompareMetrics
    assert quantum_circuit_drawer.CircuitCompareResult is CircuitCompareResult


def test_draw_result_exposes_runtime_metadata_and_saved_path(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    output_path = sandbox_tmp_path / "saved-circuit.png"
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(show=False, hover=True, output_path=output_path),
    )

    assert result.detected_framework == "ir"
    assert result.mode is DrawMode.PAGES_CONTROLS
    assert result.resolved_mode is result.mode
    assert result.hover_enabled is False
    assert result.interactive_enabled is False
    assert result.saved_path == str(output_path.resolve())
    assert result.warnings == ()
    assert_saved_image_has_visible_content(output_path)

    plt.close(result.primary_figure)


def test_draw_result_marks_interactive_hover_when_caller_axes_support_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    figure, axes = plt.subplots()
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.request.figure_backend_name",
        lambda _figure: "qtagg",
    )
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.api.figure_backend_name",
        lambda _figure: "qtagg",
        raising=False,
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(mode=DrawMode.FULL, hover=True, show=False),
        ax=axes,
    )

    assert result.hover_enabled is True
    assert result.interactive_enabled is True
    assert result.detected_framework == "ir"

    plt.close(figure)


def test_draw_result_warning_property_filters_warning_diagnostics() -> None:
    info_diagnostic = RenderDiagnostic(
        code="info_only",
        message="info",
        severity=DiagnosticSeverity.INFO,
    )
    warning_diagnostic = RenderDiagnostic(
        code="warning_only",
        message="warn",
        severity=DiagnosticSeverity.WARNING,
    )
    result = DrawResult(
        primary_figure=object(),
        primary_axes=object(),
        figures=(object(),),
        axes=(object(),),
        mode=DrawMode.FULL,
        page_count=1,
        diagnostics=(info_diagnostic, warning_diagnostic),
    )

    assert result.warnings == (warning_diagnostic,)


def test_compare_circuits_returns_side_by_side_results_metrics_and_diff_bands() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(
            left_title="Before",
            right_title="After",
            show=False,
        ),
    )

    assert isinstance(result, CircuitCompareResult)
    assert isinstance(result.figure.canvas, FigureCanvasAgg)
    assert len(result.axes) == 2
    assert result.left_result.primary_figure is result.figure
    assert result.right_result.primary_figure is result.figure
    assert result.left_result.primary_axes is result.axes[0]
    assert result.right_result.primary_axes is result.axes[1]
    assert result.left_result.detected_framework == "ir"
    assert result.right_result.detected_framework == "ir"
    assert result.saved_path is None
    assert result.metrics == CircuitCompareMetrics(
        left_layer_count=3,
        right_layer_count=4,
        layer_delta=1,
        left_operation_count=3,
        right_operation_count=5,
        operation_delta=2,
        left_multi_qubit_count=1,
        right_multi_qubit_count=2,
        multi_qubit_delta=1,
        left_measurement_count=1,
        right_measurement_count=1,
        measurement_delta=0,
        left_swap_count=0,
        right_swap_count=1,
        swap_delta=1,
        differing_layer_count=2,
        left_only_layer_count=0,
        right_only_layer_count=1,
    )

    for axes in result.axes:
        diff_bands = [
            patch
            for patch in axes.patches
            if getattr(patch, "get_gid", lambda: None)() == "circuit-compare-diff-band"
        ]
        assert diff_bands

    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)


def test_compare_circuits_uses_caller_managed_axes_and_saves_single_output(
    sandbox_tmp_path: Path,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.2))
    output_path = sandbox_tmp_path / "circuit-compare.png"

    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(show=False, output_path=output_path),
        axes=(axes[0], axes[1]),
    )

    assert result.figure is figure
    assert result.axes == (axes[0], axes[1])
    assert result.saved_path == str(output_path.resolve())
    assert_saved_image_has_visible_content(output_path)

    plt.close(figure)


@pytest.mark.optional
@pytest.mark.integration
def test_compare_circuits_supports_mixed_qiskit_and_ir_inputs() -> None:
    qiskit = pytest.importorskip("qiskit")
    qiskit_circuit = qiskit.QuantumCircuit(2, 1)
    qiskit_circuit.h(0)
    qiskit_circuit.cx(0, 1)
    qiskit_circuit.measure(1, 0)

    result = compare_circuits(
        qiskit_circuit,
        build_reference_compare_ir(),
        left_config=DrawConfig(framework="qiskit", show=False),
        right_config=DrawConfig(show=False),
        config=CircuitCompareConfig(show=False),
    )

    assert result.left_result.detected_framework == "qiskit"
    assert result.right_result.detected_framework == "ir"

    plt.close(result.figure)


@pytest.mark.parametrize(
    ("config_side", "draw_config"),
    [
        ("left", DrawConfig(view="3d", show=False)),
        ("right", DrawConfig(mode=DrawMode.SLIDER, show=False)),
    ],
)
def test_compare_circuits_rejects_unsupported_draw_modes_for_v1(
    config_side: str,
    draw_config: DrawConfig,
) -> None:
    kwargs = {"left_config": None, "right_config": None}
    kwargs[f"{config_side}_config"] = draw_config

    with pytest.raises(ValueError, match="compare_circuits"):
        compare_circuits(
            build_reference_compare_ir(),
            build_candidate_compare_ir(),
            config=CircuitCompareConfig(show=False),
            **kwargs,
        )
