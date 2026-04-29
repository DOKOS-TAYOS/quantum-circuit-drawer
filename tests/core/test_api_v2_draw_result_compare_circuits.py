from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import matplotlib.pyplot as plt
import pytest
from matplotlib import patches as matplotlib_patches
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    CircuitBuilder,
    CircuitCompareConfig,
    CircuitCompareMetrics,
    CircuitCompareOptions,
    CircuitCompareResult,
    CircuitCompareSideMetrics,
    CircuitRenderOptions,
    DiagnosticSeverity,
    DrawConfig,
    DrawMode,
    DrawResult,
    DrawSideConfig,
    OutputOptions,
    RenderDiagnostic,
    compare_circuits,
    draw_quantum_circuit,
)
from quantum_circuit_drawer.drawing.runtime import RuntimeContext
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    get_hover_state,
    get_text_scaling_state,
)
from quantum_circuit_drawer.style.theme import resolve_theme
from tests.support import (
    assert_figure_has_visible_content,
    assert_saved_image_has_visible_content,
    build_sample_ir,
    build_sample_myqlm_circuit,
    install_fake_myqlm,
)
from tests.support import (
    install_fake_cudaq as install_fake_cudaq_support,
)


class FakeCirqQubit:
    def __init__(self, label: str) -> None:
        self.label = label

    def __str__(self) -> str:
        return self.label


class FakeCirqOperation:
    def __init__(self, gate: object, qubits: tuple[FakeCirqQubit, ...]) -> None:
        self.gate = gate
        self.qubits = qubits


class FakeCirqMoment:
    def __init__(self, *operations: FakeCirqOperation) -> None:
        self.operations = operations


class FakeCirqCircuit:
    def __init__(self, *moments: FakeCirqMoment) -> None:
        self._moments = moments

    def all_qubits(self) -> set[FakeCirqQubit]:
        return {
            qubit
            for moment in self._moments
            for operation in moment.operations
            for qubit in operation.qubits
        }

    def __iter__(self) -> Iterator[FakeCirqMoment]:
        return iter(self._moments)


class FakeCirqMeasurementGate:
    def __init__(self, key: str) -> None:
        self.key = key


class FakeCirqHPowGate:
    exponent = 1


class FakeCirqCNotPowGate:
    exponent = 1


class FakePennyLaneQuantumTape:
    def __init__(
        self,
        *,
        wires: tuple[object, ...],
        operations: tuple[object, ...],
        measurements: tuple[object, ...],
    ) -> None:
        self.wires = wires
        self.operations = operations
        self.measurements = measurements


class FakePennyLaneOperation:
    def __init__(
        self,
        *,
        name: str,
        wires: tuple[object, ...],
        parameters: tuple[object, ...] = (),
        control_wires: tuple[object, ...] = (),
        target_wires: tuple[object, ...] | None = None,
    ) -> None:
        self.name = name
        self.wires = wires
        self.parameters = parameters
        self.control_wires = control_wires
        self.target_wires = target_wires


class FakePennyLaneMeasurement:
    def __init__(self, wires: tuple[object, ...]) -> None:
        self.wires = wires


class FakePennyLaneQNodeLikeWrapper:
    def __init__(self, tape: FakePennyLaneQuantumTape) -> None:
        self._tape = tape

    @property
    def qtape(self) -> object:
        raise AssertionError("qtape property should not be touched when _tape is present")

    @property
    def tape(self) -> object:
        raise AssertionError("tape property should not be touched when _tape is present")


def install_fake_cirq(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("cirq")
    fake_module.__path__ = []
    fake_module.Circuit = FakeCirqCircuit
    fake_module.ClassicallyControlledOperation = type("ClassicallyControlledOperation", (), {})
    fake_module.CircuitOperation = type("CircuitOperation", (), {})
    fake_module.ControlledOperation = type("ControlledOperation", (), {})
    fake_module.unitary = lambda operation, default=None: default
    fake_circuits = ModuleType("cirq.circuits")
    fake_circuits.Circuit = FakeCirqCircuit
    fake_circuits.FrozenCircuit = FakeCirqCircuit
    fake_circuits.CircuitOperation = fake_module.CircuitOperation
    fake_ops = ModuleType("cirq.ops")
    fake_classically_controlled_operation = ModuleType("cirq.ops.classically_controlled_operation")
    fake_classically_controlled_operation.ClassicallyControlledOperation = (
        fake_module.ClassicallyControlledOperation
    )
    fake_controlled_operation = ModuleType("cirq.ops.controlled_operation")
    fake_controlled_operation.ControlledOperation = fake_module.ControlledOperation
    fake_protocols = ModuleType("cirq.protocols")
    fake_protocols.unitary = fake_module.unitary
    fake_module.circuits = fake_circuits
    fake_module.ops = fake_ops
    fake_module.protocols = fake_protocols
    fake_ops.classically_controlled_operation = fake_classically_controlled_operation
    fake_ops.controlled_operation = fake_controlled_operation
    monkeypatch.setitem(sys.modules, "cirq", fake_module)
    monkeypatch.setitem(sys.modules, "cirq.circuits", fake_circuits)
    monkeypatch.setitem(sys.modules, "cirq.ops", fake_ops)
    monkeypatch.setitem(
        sys.modules,
        "cirq.ops.classically_controlled_operation",
        fake_classically_controlled_operation,
    )
    monkeypatch.setitem(
        sys.modules,
        "cirq.ops.controlled_operation",
        fake_controlled_operation,
    )
    monkeypatch.setitem(sys.modules, "cirq.protocols", fake_protocols)


def install_fake_pennylane(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("pennylane")
    fake_module.__path__ = []
    fake_tape = ModuleType("pennylane.tape")
    fake_tape.QuantumTape = FakePennyLaneQuantumTape
    fake_tape.QuantumScript = FakePennyLaneQuantumTape
    fake_module.tape = fake_tape
    monkeypatch.setitem(sys.modules, "pennylane", fake_module)
    monkeypatch.setitem(sys.modules, "pennylane.tape", fake_tape)


def build_reference_compare_ir() -> object:
    return CircuitBuilder(2, 1, name="reference").h(0).cx(0, 1).measure(1, 0).build()


def build_candidate_compare_ir() -> object:
    return (
        CircuitBuilder(2, 1, name="candidate").h(0).x(1).cx(0, 1).swap(0, 1).measure(0, 0).build()
    )


def build_single_qubit_reference_ir() -> object:
    return CircuitBuilder(1, 1, name="single-qubit-reference").h(0).measure(0, 0).build()


def test_public_package_exports_compare_circuit_types() -> None:
    assert quantum_circuit_drawer.compare_circuits is compare_circuits
    assert quantum_circuit_drawer.CircuitCompareConfig is CircuitCompareConfig
    assert quantum_circuit_drawer.CircuitCompareMetrics is CircuitCompareMetrics
    assert quantum_circuit_drawer.CircuitCompareSideMetrics is CircuitCompareSideMetrics
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
        config=DrawConfig(
            side=DrawSideConfig(appearance=CircuitAppearanceOptions(hover=True)),
            output=OutputOptions(show=False, output_path=output_path),
        ),
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


def test_draw_quantum_circuit_logs_managed_cleanup_failures_without_breaking_pages_mode(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output_path = sandbox_tmp_path / "managed-pages.png"
    original_close = plt.close

    def fail_close(figure: object | None = None) -> None:
        if figure is not None:
            raise RuntimeError("close failed")
        original_close(figure)

    monkeypatch.setattr(plt, "close", fail_close)
    caplog.set_level("WARNING", logger="quantum_circuit_drawer")

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(
            side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.PAGES)),
            output=OutputOptions(show=False, output_path=output_path),
        ),
    )

    assert result.mode is DrawMode.PAGES
    assert result.page_count >= 1
    assert result.saved_path == str(output_path.resolve())
    assert any(
        "best-effort cleanup" in record.getMessage() and "managed 2D" in record.getMessage()
        for record in caplog.records
    )

    monkeypatch.setattr(plt, "close", original_close)
    for figure in result.figures:
        plt.close(figure)


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
        config=DrawConfig(
            side=DrawSideConfig(
                render=CircuitRenderOptions(mode=DrawMode.FULL),
                appearance=CircuitAppearanceOptions(hover=True),
            ),
            output=OutputOptions(show=False),
        ),
        ax=axes,
    )

    assert result.hover_enabled is True
    assert result.interactive_enabled is True
    assert result.detected_framework == "ir"

    plt.close(figure)


def test_draw_quantum_circuit_supports_myqlm_input_through_public_v2_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    result = draw_quantum_circuit(
        build_sample_myqlm_circuit(),
        config=DrawConfig(
            side=DrawSideConfig(
                render=CircuitRenderOptions(framework="myqlm", mode=DrawMode.FULL),
            ),
            output=OutputOptions(show=False),
        ),
    )

    assert result.detected_framework == "myqlm"
    assert_figure_has_visible_content(result.primary_figure)

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_supports_cudaq_input_through_public_v2_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_kernel_type = install_fake_cudaq_support(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")

    result = draw_quantum_circuit(
        fake_kernel_type(),
        config=DrawConfig(
            side=DrawSideConfig(
                render=CircuitRenderOptions(framework="cudaq", mode=DrawMode.FULL),
            ),
            output=OutputOptions(show=False),
        ),
    )

    assert result.detected_framework == "cudaq"
    assert_figure_has_visible_content(result.primary_figure)

    plt.close(result.primary_figure)


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
    figure, axes = plt.subplots(1, 2)
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.FULL)),
            compare=CircuitCompareOptions(
                left_title="Before",
                right_title="After",
            ),
            output=OutputOptions(show=False),
        ),
        axes=(axes[0], axes[1]),
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
        diff_markers = [
            patch
            for patch in axes.patches
            if getattr(patch, "get_gid", lambda: None)() == "circuit-compare-diff-marker"
        ]
        assert diff_markers
        assert not [
            patch
            for patch in axes.patches
            if getattr(patch, "get_gid", lambda: None)() == "circuit-compare-diff-band"
        ]

    assert_figure_has_visible_content(result.figure)

    plt.close(figure)


def test_compare_circuits_keeps_hover_zoom_state_and_no_axes_titles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.request.figure_backend_name",
        lambda _figure: "qtagg",
    )

    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.2))
    theme = resolve_theme("dark")

    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(
                appearance=CircuitAppearanceOptions(
                    hover=True,
                    style={"theme": "dark"},
                )
            ),
            output=OutputOptions(show=False),
        ),
        axes=(axes[0], axes[1]),
    )

    assert result.axes == (axes[0], axes[1])
    assert get_hover_state(result.axes[0]) is not None
    assert get_hover_state(result.axes[1]) is not None
    assert get_text_scaling_state(result.axes[0]) is not None
    assert get_text_scaling_state(result.axes[1]) is not None
    assert result.axes[0].get_title() == ""
    assert result.axes[1].get_title() == ""
    assert figure._suptitle is None
    assert {"Metric", "Left", "Right", "Δ"}.issubset({text.get_text() for text in figure.texts})
    assert any(
        text.get_color() == theme.text_color for text in figure.texts if text.get_text() == "Metric"
    )
    summary_card = next(
        patch
        for patch in figure.patches
        if getattr(patch, "get_gid", lambda: None)() == "circuit-compare-summary-card"
    )
    summary_row_positions = [
        text.get_position()[1]
        for text in figure.texts
        if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-row"
    ]
    assert summary_card.get_height() >= 0.14
    assert summary_row_positions
    assert min(summary_row_positions) >= summary_card.get_y() + 0.015

    diff_markers = [
        patch
        for patch in result.axes[0].patches
        if getattr(patch, "get_gid", lambda: None)() == "circuit-compare-diff-marker"
    ]
    assert diff_markers
    assert diff_markers[0].get_alpha() < 0.12

    plt.close(figure)


def test_compare_circuits_summary_card_is_narrower_taller_and_omits_diff_columns() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(output=OutputOptions(show=False)),
    )

    summary_card = next(
        patch
        for patch in result.figure.patches
        if getattr(patch, "get_gid", lambda: None)() == "circuit-compare-summary-card"
    )
    summary_text = {
        text.get_text()
        for text in result.figure.texts
        if getattr(text, "get_gid", lambda: None)()
        in {"circuit-compare-summary-header", "circuit-compare-summary-row"}
    }

    assert result.figure.get_size_inches()[0] <= 4.0
    assert summary_card.get_width() >= 0.8
    assert summary_card.get_height() >= 0.2
    assert summary_card.get_y() < 0.2
    assert "Diff cols" not in summary_text

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_summary_figure_rows_have_readable_spacing() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(output=OutputOptions(show=False)),
    )

    row_positions = sorted(
        {
            round(text.get_position()[1], 4)
            for text in result.figure.texts
            if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-row"
        },
        reverse=True,
    )
    row_gaps = [
        upper_row - lower_row
        for upper_row, lower_row in zip(row_positions, row_positions[1:], strict=False)
    ]

    assert len(row_positions) == 5
    assert min(row_gaps) >= 0.075

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_auto_mode_defaults_to_three_normal_figures() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(output=OutputOptions(show=False)),
    )

    assert result.figure is not result.left_result.primary_figure
    assert result.figure is not result.right_result.primary_figure
    assert result.left_result.primary_figure is not result.right_result.primary_figure
    assert result.left_result.mode is DrawMode.PAGES_CONTROLS
    assert result.right_result.mode is DrawMode.PAGES_CONTROLS
    assert result.axes == (result.left_result.primary_axes, result.right_result.primary_axes)
    assert not [
        patch
        for axes in result.axes
        for patch in axes.patches
        if getattr(patch, "get_gid", lambda: None)() == "circuit-compare-diff-marker"
    ]

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_accepts_multiple_circuits_with_summary_columns() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        build_single_qubit_reference_ir(),
        config=CircuitCompareConfig(
            compare=CircuitCompareOptions(
                left_title="Reference",
                right_title="Candidate",
                titles=("Reference", "Candidate", "Compact"),
            ),
            output=OutputOptions(show=False),
        ),
    )

    assert result.titles == ("Reference", "Candidate", "Compact")
    assert len(result.axes) == 3
    assert len(result.side_results) == 3
    assert result.left_result is result.side_results[0]
    assert result.right_result is result.side_results[1]
    assert result.side_metrics == (
        CircuitCompareSideMetrics(
            title="Reference",
            layer_count=3,
            operation_count=3,
            multi_qubit_count=1,
            measurement_count=1,
            swap_count=0,
        ),
        CircuitCompareSideMetrics(
            title="Candidate",
            layer_count=4,
            operation_count=5,
            multi_qubit_count=2,
            measurement_count=1,
            swap_count=1,
        ),
        CircuitCompareSideMetrics(
            title="Compact",
            layer_count=2,
            operation_count=2,
            multi_qubit_count=0,
            measurement_count=1,
            swap_count=0,
        ),
    )

    summary_text = {
        text.get_text()
        for text in result.figure.texts
        if getattr(text, "get_gid", lambda: None)()
        in {"circuit-compare-summary-header", "circuit-compare-summary-row"}
    }
    summary_colors = {
        text.get_color()
        for text in result.figure.texts
        if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-row"
    }

    assert {"Metric", "Reference", "Candidate", "Compact"}.issubset(summary_text)
    assert "\u0394" not in summary_text
    assert "#16a34a" in summary_colors
    assert "#dc2626" in summary_colors

    for figure in (
        *result.side_results[0].figures,
        *result.side_results[1].figures,
        *result.side_results[2].figures,
        result.figure,
    ):
        plt.close(figure)


def test_compare_circuits_multi_summary_headers_fit_without_overlap() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        build_single_qubit_reference_ir(),
        build_reference_compare_ir(),
        config=CircuitCompareConfig(
            compare=CircuitCompareOptions(
                left_title="Source",
                right_title="Opt level 0",
                titles=("Source", "Opt level 0", "Opt level 1", "Opt level 3"),
            ),
            output=OutputOptions(show=False),
        ),
    )

    try:
        result.figure.canvas.draw()
        renderer = result.figure.canvas.get_renderer()
        header_texts = [
            text
            for text in result.figure.texts
            if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-header"
            and text.get_text() != "Metric"
        ]
        figure_bbox = result.figure.bbox

        assert [text.get_text() for text in header_texts] == [
            "Source",
            "Opt level 0",
            "Opt level 1",
            "Opt level 3",
        ]

        header_bboxes = [text.get_window_extent(renderer=renderer) for text in header_texts]

        assert all(bbox.x0 >= figure_bbox.x0 + 12.0 for bbox in header_bboxes)
        assert all(bbox.x1 <= figure_bbox.x1 - 20.0 for bbox in header_bboxes)
        assert all(
            not left_bbox.overlaps(right_bbox)
            for left_bbox, right_bbox in zip(header_bboxes, header_bboxes[1:], strict=False)
        )
    finally:
        for figure in (
            *result.side_results[0].figures,
            *result.side_results[1].figures,
            *result.side_results[2].figures,
            *result.side_results[3].figures,
            result.figure,
        ):
            plt.close(figure)


def test_compare_circuits_multi_summary_headers_fit_inside_caller_managed_summary_axes() -> None:
    figure = plt.figure(figsize=(11.0, 7.0), constrained_layout=True)
    grid = figure.add_gridspec(2, 4)
    summary_axes = figure.add_subplot(grid[1, :])
    side_axes = tuple(figure.add_subplot(grid[0, index]) for index in range(4))

    compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        build_single_qubit_reference_ir(),
        build_reference_compare_ir(),
        config=CircuitCompareConfig(
            compare=CircuitCompareOptions(
                left_title="Source",
                right_title="Opt level 0",
                titles=("Source", "Opt level 0", "Opt level 1", "Opt level 3"),
            ),
            output=OutputOptions(show=False),
        ),
        axes=side_axes,
        summary_ax=summary_axes,
    )

    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        summary_bounds = summary_axes.get_position()
        header_texts = [
            text
            for text in figure.texts
            if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-header"
            and text.get_text() != "Metric"
        ]
        header_bboxes = [text.get_window_extent(renderer=renderer) for text in header_texts]
        figure_width = float(figure.bbox.width)
        figure_height = float(figure.bbox.height)

        assert [text.get_text() for text in header_texts] == [
            "Source",
            "Opt level 0",
            "Opt level 1",
            "Opt level 3",
        ]
        assert all(
            summary_bounds.x0 <= float(bbox.x0) / figure_width
            and float(bbox.x1) / figure_width <= summary_bounds.x1
            and summary_bounds.y0 <= float(bbox.y0) / figure_height
            and float(bbox.y1) / figure_height <= summary_bounds.y1
            for bbox in header_bboxes
        )
        assert all(
            not left_bbox.overlaps(right_bbox)
            for left_bbox, right_bbox in zip(header_bboxes, header_bboxes[1:], strict=False)
        )
    finally:
        plt.close(figure)


def test_compare_circuits_full_mode_without_axes_uses_three_normal_figures() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.FULL)),
            output=OutputOptions(show=False),
        ),
    )

    assert result.figure is not result.left_result.primary_figure
    assert result.figure is not result.right_result.primary_figure
    assert result.left_result.primary_figure is not result.right_result.primary_figure
    assert result.left_result.mode is DrawMode.FULL
    assert result.right_result.mode is DrawMode.FULL

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_owned_side_titles_use_window_labels_not_axes_titles() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(
            compare=CircuitCompareOptions(
                left_title="Before",
                right_title="After",
            ),
            output=OutputOptions(show=False),
        ),
    )

    assert result.left_result.primary_axes.get_title() == ""
    assert result.right_result.primary_axes.get_title() == ""
    assert result.left_result.primary_figure.get_label() == "Before"
    assert result.right_result.primary_figure.get_label() == "After"

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_shows_three_owned_figures_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quantum_circuit_drawer.drawing import compare as compare_module
    from quantum_circuit_drawer.drawing.preparation import PreparedDrawCall

    real_draw_result_from_prepared_call = compare_module.draw_result_from_prepared_call
    side_show_values: list[bool] = []
    side_defer_values: list[bool] = []
    events: list[str] = []
    show_calls: list[tuple[object, bool]] = []

    def wrapped_draw_result_from_prepared_call(
        prepared: PreparedDrawCall,
        *,
        defer_show: bool = False,
    ) -> DrawResult:
        side_show_values.append(prepared.request.show)
        side_defer_values.append(defer_show)
        result = real_draw_result_from_prepared_call(prepared, defer_show=defer_show)
        events.append("side")
        return result

    def track_show(figure: object, *, show: bool) -> None:
        show_calls.append((figure, show))
        events.append("show")

    monkeypatch.setattr(
        compare_module,
        "draw_result_from_prepared_call",
        wrapped_draw_result_from_prepared_call,
    )
    monkeypatch.setattr(compare_module, "show_figure_if_supported", track_show)

    plt.close("all")
    try:
        result = compare_circuits(
            build_reference_compare_ir(),
            build_candidate_compare_ir(),
            config=CircuitCompareConfig(output=OutputOptions(show=True)),
        )

        assert side_show_values == [True, True]
        assert side_defer_values == [True, True]
        assert events == ["side", "side", "show"]
        assert show_calls == [(result.figure, True)]
        assert result.figure is not result.left_result.primary_figure
        assert result.figure is not result.right_result.primary_figure
    finally:
        plt.close("all")


@pytest.mark.parametrize("mode", [DrawMode.PAGES, DrawMode.SLIDER, DrawMode.PAGES_CONTROLS])
def test_compare_circuits_supports_managed_modes_as_separate_circuit_figures(
    mode: DrawMode,
) -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(render=CircuitRenderOptions(mode=mode)),
            output=OutputOptions(show=False),
        ),
    )

    assert result.figure is not result.left_result.primary_figure
    assert result.figure is not result.right_result.primary_figure
    assert result.left_result.primary_figure is not result.right_result.primary_figure
    assert result.left_result.mode is mode
    assert result.right_result.mode is mode
    assert result.axes == (result.left_result.primary_axes, result.right_result.primary_axes)
    assert result.left_result.page_count >= 1
    assert result.right_result.page_count >= 1
    assert any(
        getattr(patch, "get_gid", lambda: None)() == "circuit-compare-summary-card"
        for patch in result.figure.patches
    )
    assert {
        text.get_text()
        for text in result.figure.texts
        if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-row"
    }.isdisjoint({"Diff cols"})

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_hover_shows_gate_details_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.request.figure_backend_name",
        lambda _figure: "qtagg",
    )
    monkeypatch.setattr(
        "quantum_circuit_drawer.renderers._render_support.pyplot_backend_supports_interaction",
        lambda: True,
    )
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.request.pyplot_backend_supports_interaction",
        lambda: True,
    )

    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(
                render=CircuitRenderOptions(mode=DrawMode.FULL),
                appearance=CircuitAppearanceOptions(
                    hover=True,
                ),
            ),
            output=OutputOptions(show=False),
        ),
    )

    try:
        hover_state = get_hover_state(result.axes[0])

        assert hover_state is not None

        result.left_result.primary_figure.canvas.draw()
        gate_patch = next(
            patch
            for patch in result.axes[0].patches
            if isinstance(patch, matplotlib_patches.FancyBboxPatch)
        )
        _dispatch_motion_event(result.left_result.primary_figure, result.axes[0], gate_patch)

        annotation = hover_state.annotation

        assert annotation.get_visible() is True
        assert annotation.get_text()
    finally:
        for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
            plt.close(figure)


def test_compare_circuits_uses_caller_managed_axes_and_saves_single_output(
    sandbox_tmp_path: Path,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.2))
    output_path = sandbox_tmp_path / "circuit-compare.png"

    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(
            output=OutputOptions(show=False, output_path=output_path),
        ),
        axes=(axes[0], axes[1]),
    )

    assert result.figure is figure
    assert result.axes == (axes[0], axes[1])
    assert result.saved_path == str(output_path.resolve())
    assert_saved_image_has_visible_content(output_path)

    plt.close(figure)


def test_compare_circuits_can_render_summary_into_caller_managed_axes() -> None:
    figure = plt.figure(figsize=(10.0, 7.0), constrained_layout=True)
    grid = figure.add_gridspec(2, 2)
    left_axes = figure.add_subplot(grid[0, 0])
    right_axes = figure.add_subplot(grid[0, 1])
    summary_axes = figure.add_subplot(grid[1, :])

    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(output=OutputOptions(show=False)),
        axes=(left_axes, right_axes),
        summary_ax=summary_axes,
    )

    summary_bounds = summary_axes.get_position()
    summary_texts = [
        text
        for text in figure.texts
        if getattr(text, "get_gid", lambda: None)()
        in {"circuit-compare-summary-header", "circuit-compare-summary-row"}
    ]

    assert result.summary_axes is summary_axes
    assert summary_axes.axison is False
    assert {"Metric", "Left", "Right", "\u0394"}.issubset(
        {text.get_text() for text in summary_texts}
    )
    assert all(
        summary_bounds.x0 <= text.get_position()[0] <= summary_bounds.x1
        and summary_bounds.y0 <= text.get_position()[1] <= summary_bounds.y1
        for text in summary_texts
    )
    row_positions = sorted(
        {
            round(text.get_position()[1], 4)
            for text in summary_texts
            if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-row"
        },
        reverse=True,
    )
    row_gaps = [
        upper_row - lower_row
        for upper_row, lower_row in zip(row_positions, row_positions[1:], strict=False)
    ]

    assert len(row_positions) == 5
    assert min(row_gaps) >= 0.018

    plt.close(figure)


def test_compare_circuits_summary_uses_larger_text() -> None:
    result = compare_circuits(
        build_reference_compare_ir(),
        build_candidate_compare_ir(),
        config=CircuitCompareConfig(output=OutputOptions(show=False)),
    )

    try:
        header_fonts = [
            text.get_fontsize()
            for text in result.figure.texts
            if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-header"
        ]
        row_fonts = [
            text.get_fontsize()
            for text in result.figure.texts
            if getattr(text, "get_gid", lambda: None)() == "circuit-compare-summary-row"
        ]

        assert header_fonts
        assert row_fonts
        assert min(header_fonts) >= 12.0
        assert min(row_fonts) >= 10.8
    finally:
        for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
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
        config=CircuitCompareConfig(
            shared=DrawSideConfig(),
            left_render=CircuitRenderOptions(framework="qiskit"),
            output=OutputOptions(show=False),
        ),
    )

    assert result.left_result.detected_framework == "qiskit"
    assert result.right_result.detected_framework == "ir"

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_supports_mixed_cirq_and_ir_inputs_with_windows_safe_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeCirqQubit("q(0)")
    q1 = FakeCirqQubit("q(1)")
    cirq_circuit = FakeCirqCircuit(
        FakeCirqMoment(FakeCirqOperation(FakeCirqHPowGate(), (q0,))),
        FakeCirqMoment(FakeCirqOperation(FakeCirqCNotPowGate(), (q0, q1))),
        FakeCirqMoment(FakeCirqOperation(FakeCirqMeasurementGate("m"), (q1,))),
    )

    result = compare_circuits(
        cirq_circuit,
        build_reference_compare_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(),
            left_render=CircuitRenderOptions(framework="cirq"),
            output=OutputOptions(show=False),
        ),
    )

    assert result.left_result.detected_framework == "cirq"
    assert result.right_result.detected_framework == "ir"
    assert_figure_has_visible_content(result.figure)

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_supports_mixed_pennylane_and_ir_inputs_with_windows_safe_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    wrapper = FakePennyLaneQNodeLikeWrapper(
        FakePennyLaneQuantumTape(
            wires=(0, 1),
            operations=(
                FakePennyLaneOperation(name="Hadamard", wires=(0,)),
                FakePennyLaneOperation(
                    name="CNOT",
                    wires=(0, 1),
                    control_wires=(0,),
                    target_wires=(1,),
                ),
            ),
            measurements=(FakePennyLaneMeasurement((1,)),),
        )
    )

    result = compare_circuits(
        wrapper,
        build_reference_compare_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(),
            left_render=CircuitRenderOptions(framework="pennylane"),
            output=OutputOptions(show=False),
        ),
    )

    assert result.left_result.detected_framework == "pennylane"
    assert result.right_result.detected_framework == "ir"
    assert_figure_has_visible_content(result.figure)

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_supports_mixed_myqlm_and_ir_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    result = compare_circuits(
        build_sample_myqlm_circuit(),
        build_single_qubit_reference_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(),
            left_render=CircuitRenderOptions(framework="myqlm"),
            output=OutputOptions(show=False),
        ),
    )

    assert result.left_result.detected_framework == "myqlm"
    assert result.right_result.detected_framework == "ir"
    assert result.metrics.differing_layer_count > 0
    assert_figure_has_visible_content(result.figure)

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


def test_compare_circuits_supports_mixed_cudaq_and_ir_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_kernel_type = install_fake_cudaq_support(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    kernel = fake_kernel_type()

    result = compare_circuits(
        kernel,
        build_single_qubit_reference_ir(),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(),
            left_render=CircuitRenderOptions(framework="cudaq"),
            output=OutputOptions(show=False),
        ),
    )

    assert result.left_result.detected_framework == "cudaq"
    assert result.right_result.detected_framework == "ir"
    assert result.metrics.differing_layer_count > 0
    assert_figure_has_visible_content(result.figure)

    for figure in (*result.left_result.figures, *result.right_result.figures, result.figure):
        plt.close(figure)


@pytest.mark.parametrize(
    ("config_side", "render_options"),
    [
        ("left", CircuitRenderOptions(view="3d")),
    ],
)
def test_compare_circuits_rejects_unsupported_draw_modes_for_v1(
    config_side: str,
    render_options: CircuitRenderOptions,
) -> None:
    kwargs = {"left_render": None, "right_render": None}
    kwargs[f"{config_side}_render"] = render_options

    with pytest.raises(ValueError, match="compare_circuits"):
        compare_circuits(
            build_reference_compare_ir(),
            build_candidate_compare_ir(),
            config=CircuitCompareConfig(
                output=OutputOptions(show=False),
                **kwargs,
            ),
        )


def _dispatch_motion_event(
    figure: plt.Figure,
    axes: plt.Axes,
    patch: object,
) -> None:
    bbox = patch.get_window_extent(renderer=figure.canvas.get_renderer())
    event = MouseEvent(
        "motion_notify_event",
        figure.canvas,
        float((bbox.x0 + bbox.x1) / 2.0),
        float((bbox.y0 + bbox.y1) / 2.0),
    )
    event.inaxes = axes
    figure.canvas.callbacks.process("motion_notify_event", event)
