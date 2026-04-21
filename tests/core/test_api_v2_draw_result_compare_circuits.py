from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType, SimpleNamespace

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
    fake_module.Circuit = FakeCirqCircuit
    fake_module.ClassicallyControlledOperation = type("ClassicallyControlledOperation", (), {})
    fake_module.CircuitOperation = type("CircuitOperation", (), {})
    fake_module.ControlledOperation = type("ControlledOperation", (), {})
    fake_module.unitary = lambda operation, default=None: default
    monkeypatch.setitem(sys.modules, "cirq", fake_module)


def install_fake_pennylane(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("pennylane")
    fake_module.tape = SimpleNamespace(
        QuantumTape=FakePennyLaneQuantumTape,
        QuantumScript=FakePennyLaneQuantumTape,
    )
    monkeypatch.setitem(sys.modules, "pennylane", fake_module)


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


def test_draw_quantum_circuit_supports_myqlm_input_through_public_v2_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    result = draw_quantum_circuit(
        build_sample_myqlm_circuit(),
        config=DrawConfig(framework="myqlm", mode=DrawMode.FULL, show=False),
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
        config=DrawConfig(framework="cudaq", mode=DrawMode.FULL, show=False),
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
        left_config=DrawConfig(framework="cirq", show=False),
        right_config=DrawConfig(show=False),
        config=CircuitCompareConfig(show=False),
    )

    assert result.left_result.detected_framework == "cirq"
    assert result.right_result.detected_framework == "ir"
    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)


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
        left_config=DrawConfig(framework="pennylane", show=False),
        right_config=DrawConfig(show=False),
        config=CircuitCompareConfig(show=False),
    )

    assert result.left_result.detected_framework == "pennylane"
    assert result.right_result.detected_framework == "ir"
    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)


def test_compare_circuits_supports_mixed_myqlm_and_ir_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    result = compare_circuits(
        build_sample_myqlm_circuit(),
        build_single_qubit_reference_ir(),
        left_config=DrawConfig(framework="myqlm", show=False),
        right_config=DrawConfig(show=False),
        config=CircuitCompareConfig(show=False),
    )

    assert result.left_result.detected_framework == "myqlm"
    assert result.right_result.detected_framework == "ir"
    assert result.metrics.differing_layer_count > 0
    assert_figure_has_visible_content(result.figure)

    plt.close(result.figure)


def test_compare_circuits_supports_mixed_cudaq_and_ir_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_kernel_type = install_fake_cudaq_support(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    kernel = fake_kernel_type()

    result = compare_circuits(
        kernel,
        build_single_qubit_reference_ir(),
        left_config=DrawConfig(framework="cudaq", show=False),
        right_config=DrawConfig(show=False),
        config=CircuitCompareConfig(show=False),
    )

    assert result.left_result.detected_framework == "cudaq"
    assert result.right_result.detected_framework == "ir"
    assert result.metrics.differing_layer_count > 0
    assert_figure_has_visible_content(result.figure)

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
