from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer.adapters.pennylane_adapter import PennyLaneAdapter
from quantum_circuit_drawer.exceptions import UnsupportedFrameworkError, UnsupportedOperationError
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.style import DrawStyle
from tests.support import (
    OperationSignature,
    assert_axes_contains_circuit_artists,
    assert_classical_wire_bundles,
    assert_figure_has_visible_content,
    assert_operation_signatures,
    assert_quantum_wire_labels,
    flatten_operations,
    normalize_rendered_text,
)
from tests.support import (
    draw_quantum_circuit_legacy as draw_quantum_circuit,
)

pytestmark = pytest.mark.optional

skip_real_pennylane_on_windows = pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="PennyLane collection is not reliable on native Windows",
)


class FakeQuantumTape:
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


class FakeOperation:
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


class FakeMeasurement:
    def __init__(self, wires: tuple[object, ...], *, obs: object | None = None) -> None:
        self.wires = wires
        self.obs = obs
        self.mv = None


class SampleMP(FakeMeasurement):
    pass


class ProbabilityMP(FakeMeasurement):
    pass


class CountsMP(FakeMeasurement):
    pass


class StateMP(FakeMeasurement):
    pass


class DensityMatrixMP(FakeMeasurement):
    pass


class ExpectationMP(FakeMeasurement):
    pass


class VarianceMP(FakeMeasurement):
    pass


class FakeObservable:
    def __init__(
        self,
        *,
        name: str,
        wires: tuple[object, ...],
        operands: tuple[FakeObservable, ...] = (),
        scalar: float | int | None = None,
        base: FakeObservable | None = None,
        coeffs: tuple[float | int, ...] = (),
    ) -> None:
        self.name = name
        self.wires = wires
        self.operands = operands
        self.scalar = scalar
        self.base = base
        self.coeffs = coeffs

    def __repr__(self) -> str:
        if self.base is not None and self.scalar is not None:
            base_repr = repr(self.base)
            if getattr(self.base, "operands", ()) or getattr(self.base, "base", None) is not None:
                base_repr = f"({base_repr})"
            return f"{self.scalar:g} * {base_repr}"
        if not self.operands:
            wires = ", ".join(str(wire) for wire in self.wires)
            return f"{self.name}({wires})"
        separator = " @ " if self.name in {"Prod", "Tensor"} else " + "
        joined = separator.join(repr(operand) for operand in self.operands)
        return f"{self.name}({joined})"


class ProdObservable(FakeObservable):
    pass


class SProdObservable(FakeObservable):
    pass


class SumObservable(FakeObservable):
    pass


class HamiltonianObservable(FakeObservable):
    pass


class OpaqueObservable(FakeObservable):
    pass


class FakeTapeWrapper:
    def __init__(self, tape: FakeQuantumTape) -> None:
        self.qtape = tape


def build_anonymous_long_named_observable(
    *,
    name: str,
    wires: tuple[object, ...],
) -> object:
    anonymous_type = type("", (), {})
    observable = anonymous_type()
    observable.name = name
    observable.wires = wires
    observable.operands = ()
    observable.scalar = None
    observable.base = None
    observable.coeffs = ()
    return observable


def install_fake_pennylane(
    monkeypatch: pytest.MonkeyPatch,
    *,
    matrix_function: object | None = None,
) -> None:
    fake_module = ModuleType("pennylane")
    fake_module.tape = SimpleNamespace(QuantumTape=FakeQuantumTape, QuantumScript=FakeQuantumTape)
    if matrix_function is not None:
        fake_module.matrix = matrix_function
    monkeypatch.setitem(sys.modules, "pennylane", fake_module)


def build_fake_tape() -> FakeQuantumTape:
    return FakeQuantumTape(
        wires=(0, 1),
        operations=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(name="CNOT", wires=(0, 1), control_wires=(0,), target_wires=(1,)),
        ),
        measurements=(SampleMP((1,)),),
    )


def test_pennylane_adapter_matches_canonical_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pennylane(monkeypatch)

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(build_fake_tape()))
    terminal_output = flatten_operations(ir)[-1]

    assert ir.metadata["framework"] == "pennylane"
    assert_quantum_wire_labels(ir, ["0", "1"])
    assert_classical_wire_bundles(ir, [])
    assert_operation_signatures(
        ir,
        [
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.H,
                "H",
                (),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.CONTROLLED_GATE,
                CanonicalGateFamily.X,
                "X",
                (),
                ("q1",),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.CUSTOM,
                "SAMPLE",
                (),
                ("q1",),
            ),
        ],
    )
    assert terminal_output.metadata["pennylane_terminal_kind"] == "sample"
    assert terminal_output.metadata["pennylane_measurement_wires"] == ("q1",)
    assert terminal_output.metadata["hover_details"] == (
        "terminal output: sample",
        "selected wires: 1",
    )


def test_pennylane_adapter_converts_tape_like_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pennylane(monkeypatch)

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(build_fake_tape()))

    kinds = [operation.kind for layer in ir.layers for operation in layer.operations]
    names = [operation.name for layer in ir.layers for operation in layer.operations]

    assert ir.metadata["framework"] == "pennylane"
    assert [wire.label for wire in ir.quantum_wires] == ["0", "1"]
    assert len(ir.classical_wires) == 0
    assert OperationKind.GATE in kinds
    assert OperationKind.CONTROLLED_GATE in kinds
    assert OperationKind.MEASUREMENT not in kinds
    assert "H" in names
    assert "X" in names
    assert "SAMPLE" in names


@pytest.mark.parametrize(
    ("measurement", "expected_name", "expected_targets", "expected_kind", "observable_label"),
    [
        (
            ExpectationMP((0,), obs=FakeObservable(name="PauliZ", wires=(0,))),
            "EXPVAL",
            ("q0",),
            "expval",
            "PauliZ",
        ),
        (
            VarianceMP(
                (0, 1),
                obs=FakeObservable(
                    name="Prod",
                    wires=(0, 1),
                    operands=(
                        FakeObservable(name="PauliX", wires=(0,)),
                        FakeObservable(name="PauliZ", wires=(1,)),
                    ),
                ),
            ),
            "VAR",
            ("q0", "q1"),
            "var",
            "PauliX @ PauliZ",
        ),
        (ProbabilityMP((0, 1)), "PROBS", ("q0", "q1"), "probs", None),
        (SampleMP((1,)), "SAMPLE", ("q1",), "sample", None),
        (CountsMP((0, 1)), "COUNTS", ("q0", "q1"), "counts", None),
        (StateMP(()), "STATE", ("q0", "q1"), "state", None),
        (DensityMatrixMP((1,)), "DM", ("q1",), "density_matrix", None),
    ],
)
def test_pennylane_adapter_converts_terminal_outputs_to_compact_boxes(
    monkeypatch: pytest.MonkeyPatch,
    measurement: FakeMeasurement,
    expected_name: str,
    expected_targets: tuple[str, ...],
    expected_kind: str,
    observable_label: str | None,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(FakeOperation(name="Hadamard", wires=(0,)),),
        measurements=(measurement,),
    )

    semantic_ir = PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape))
    semantic_operation = next(
        operation
        for layer in semantic_ir.layers
        for operation in layer.operations
        if operation.metadata.get("pennylane_terminal_kind") == expected_kind
    )
    lowered_operation = next(
        operation
        for layer in PennyLaneAdapter().to_ir(FakeTapeWrapper(tape)).layers
        for operation in layer.operations
        if operation.metadata.get("pennylane_terminal_kind") == expected_kind
    )

    assert semantic_ir.classical_wires == ()
    assert semantic_operation.kind is OperationKind.GATE
    assert semantic_operation.name == expected_name
    assert semantic_operation.target_wires == expected_targets
    assert lowered_operation.kind is OperationKind.GATE
    assert lowered_operation.name == expected_name
    assert lowered_operation.target_wires == expected_targets
    assert lowered_operation.metadata["pennylane_terminal_kind"] == expected_kind
    assert lowered_operation.metadata["pennylane_measurement_wires"] == expected_targets
    assert lowered_operation.metadata["semantic_provenance"]["native_kind"] == expected_kind

    if observable_label is None:
        assert "pennylane_observable_label" not in lowered_operation.metadata
    else:
        assert lowered_operation.metadata["pennylane_observable_label"] == observable_label
        assert f"observable: {observable_label}" in lowered_operation.metadata["hover_details"]


def test_pennylane_adapter_uses_deterministic_fallback_for_long_observable_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    composite_observable = ProdObservable(
        name="Prod",
        wires=(0, 1, 2, 3),
        operands=(
            FakeObservable(name="PauliX", wires=(0,)),
            FakeObservable(name="PauliY", wires=(1,)),
            FakeObservable(name="PauliZ", wires=(2,)),
            FakeObservable(name="Hadamard", wires=(3,)),
        ),
    )
    tape = FakeQuantumTape(
        wires=(0, 1, 2, 3),
        operations=(),
        measurements=(ExpectationMP((0, 1, 2, 3), obs=composite_observable),),
    )

    semantic_ir = PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape))
    terminal_output = semantic_ir.layers[0].operations[0]

    assert terminal_output.metadata["pennylane_observable_label"] == "PauliX @ PauliY @ ..."
    assert terminal_output.hover_details == (
        "terminal output: expval",
        "observable: PauliX @ PauliY @ ...",
        "observable type: Prod",
        "observable operands: 4",
        "observable summary: truncated",
        "all wires",
    )


def test_pennylane_adapter_avoids_generic_fallback_for_anonymous_long_named_observable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    observable = build_anonymous_long_named_observable(
        name="AnonymousObservableNativeTypeThatNeedsDeterministicFallback",
        wires=(0,),
    )
    tape = FakeQuantumTape(
        wires=(0,),
        operations=(),
        measurements=(ExpectationMP((0,), obs=observable),),
    )

    terminal_output = (
        PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape)).layers[0].operations[0]
    )

    observable_label = terminal_output.metadata["pennylane_observable_label"]
    assert observable_label != "composite observable"
    assert observable_label.endswith("[...]")
    assert terminal_output.hover_details == (
        "terminal output: expval",
        f"observable: {observable_label}",
        "observable type: AnonymousObservableNativeTypeThatNeedsDeterministicFallback",
        "all wires",
    )


def test_pennylane_adapter_flattens_nested_prod_observables_in_hover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    observable = ProdObservable(
        name="Prod",
        wires=(0, 1, 2),
        operands=(
            FakeObservable(name="PauliX", wires=(0,)),
            ProdObservable(
                name="Prod",
                wires=(1, 2),
                operands=(
                    FakeObservable(name="PauliY", wires=(1,)),
                    FakeObservable(name="PauliZ", wires=(2,)),
                ),
            ),
        ),
    )
    tape = FakeQuantumTape(
        wires=(0, 1, 2),
        operations=(),
        measurements=(VarianceMP((0, 1, 2), obs=observable),),
    )

    terminal_output = (
        PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape)).layers[0].operations[0]
    )

    assert terminal_output.metadata["pennylane_observable_label"] == "PauliX @ PauliY @ PauliZ"
    assert terminal_output.hover_details == (
        "terminal output: var",
        "observable: PauliX @ PauliY @ PauliZ",
        "observable type: Prod",
        "observable operands: 3",
        "all wires",
    )


def test_pennylane_adapter_summarizes_scaled_products_in_hover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    base = ProdObservable(
        name="Prod",
        wires=(0, 1),
        operands=(
            FakeObservable(name="PauliX", wires=(0,)),
            FakeObservable(name="PauliZ", wires=(1,)),
        ),
    )
    observable = SProdObservable(
        name="SProd",
        wires=(0, 1),
        scalar=0.5,
        base=base,
    )
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(),
        measurements=(ExpectationMP((0, 1), obs=observable),),
    )

    terminal_output = (
        PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape)).layers[0].operations[0]
    )

    assert terminal_output.metadata["pennylane_observable_label"] == "0.5 * (PauliX @ PauliZ)"
    assert terminal_output.hover_details == (
        "terminal output: expval",
        "observable: 0.5 * (PauliX @ PauliZ)",
        "observable type: SProd",
        "observable terms: 1",
        "all wires",
    )


def test_pennylane_adapter_truncates_linear_combinations_informatively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    observable = SumObservable(
        name="LinearCombination",
        wires=(0, 1, 2),
        operands=(
            FakeObservable(name="PauliX", wires=(0,)),
            ProdObservable(
                name="Prod",
                wires=(1, 2),
                operands=(
                    FakeObservable(name="PauliZ", wires=(1,)),
                    FakeObservable(name="PauliY", wires=(2,)),
                ),
            ),
        ),
        coeffs=(0.5, -1.25),
    )
    tape = FakeQuantumTape(
        wires=(0, 1, 2),
        operations=(),
        measurements=(ExpectationMP((0, 1, 2), obs=observable),),
    )

    terminal_output = (
        PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape)).layers[0].operations[0]
    )

    assert terminal_output.metadata["pennylane_observable_label"] == "0.5 * PauliX + ..."
    assert terminal_output.hover_details == (
        "terminal output: expval",
        "observable: 0.5 * PauliX + ...",
        "observable type: LinearCombination",
        "observable terms: 2",
        "observable summary: truncated",
        "all wires",
    )


def test_pennylane_adapter_uses_structural_fallback_for_large_hamiltonians(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    observable = HamiltonianObservable(
        name="Hamiltonian",
        wires=(0, 1, 2, 3, 4),
        operands=(
            FakeObservable(name="VeryLongObservableAlpha", wires=(0,)),
            FakeObservable(name="VeryLongObservableBeta", wires=(1,)),
            FakeObservable(name="VeryLongObservableGamma", wires=(2,)),
            FakeObservable(name="VeryLongObservableDelta", wires=(3,)),
            FakeObservable(name="VeryLongObservableEpsilon", wires=(4,)),
        ),
        coeffs=(1, 1, 1, 1, 1),
    )
    tape = FakeQuantumTape(
        wires=(0, 1, 2, 3, 4),
        operations=(),
        measurements=(ExpectationMP((0, 1, 2, 3, 4), obs=observable),),
    )

    terminal_output = (
        PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape)).layers[0].operations[0]
    )

    assert terminal_output.metadata["pennylane_observable_label"] == "Hamiltonian[5 terms]"
    assert terminal_output.hover_details == (
        "terminal output: expval",
        "observable: Hamiltonian[5 terms]",
        "observable type: Hamiltonian",
        "observable terms: 5",
        "observable summary: truncated",
        "all wires",
    )


def test_pennylane_adapter_uses_class_name_for_opaque_observable_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    observable = OpaqueObservable(name="", wires=(0,))
    tape = FakeQuantumTape(
        wires=(0,),
        operations=(),
        measurements=(ExpectationMP((0,), obs=observable),),
    )

    terminal_output = (
        PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape)).layers[0].operations[0]
    )

    assert terminal_output.metadata["pennylane_observable_label"] == "OpaqueObservable"
    assert terminal_output.hover_details == (
        "terminal output: expval",
        "observable: OpaqueObservable",
        "observable type: OpaqueObservable",
        "all wires",
    )


def test_pennylane_adapter_mixes_mid_measure_conditionals_and_terminal_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    measured_bit = FakeOperation(name="MidMeasureMP", wires=(0,))
    measured_bit.id = "m0"  # type: ignore[attr-defined]
    conditional_x = SimpleNamespace(
        base=FakeOperation(name="PauliX", wires=(1,)),
        meas_val=SimpleNamespace(measurements=(measured_bit,), branches={(1,): True}),
        name="PauliX",
        wires=(1,),
        parameters=(),
    )
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(measured_bit, conditional_x),
        measurements=(ProbabilityMP((0, 1)),),
    )

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].metadata["bundle_size"] == 1
    assert [operation.name for operation in operations] == ["M", "X", "PROBS"]
    assert operations[0].kind is OperationKind.MEASUREMENT
    assert operations[1].classical_conditions[0].expression == "if c[0]=1"
    assert operations[2].kind is OperationKind.GATE
    assert operations[2].metadata["pennylane_terminal_kind"] == "probs"


def test_pennylane_terminal_outputs_render_as_gate_boxes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(FakeOperation(name="Hadamard", wires=(0,)),),
        measurements=(ProbabilityMP((0, 1)),),
    )

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    scene = LayoutEngine().compute(ir, DrawStyle())

    assert len(scene.measurements) == 0
    gate = next(gate for gate in scene.gates if gate.label == "PROBS")
    assert gate.kind is OperationKind.GATE
    assert gate.hover_data is not None
    assert gate.hover_data.details == (
        "terminal output: probs",
        "all wires",
    )

    figure, axes = draw_quantum_circuit(
        FakeTapeWrapper(tape),
        framework="pennylane",
        show=False,
    )
    texts = [normalize_rendered_text(text.get_text()) for text in axes.texts]

    assert "PROBS" in texts
    assert "c" not in texts
    assert_axes_contains_circuit_artists(axes, expected_texts={"PROBS", "0", "1"})
    assert_figure_has_visible_content(figure)


def test_pennylane_adapter_maps_additional_canonical_gate_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(
            FakeOperation(name="PhaseShift", wires=(0,), parameters=(0.125,)),
            FakeOperation(name="Adjoint(S)", wires=(0,)),
            FakeOperation(name="Adjoint(T)", wires=(1,)),
            FakeOperation(name="SX", wires=(1,)),
            FakeOperation(name="U3", wires=(0,), parameters=(0.1, 0.2, 0.3)),
            FakeOperation(name="ISWAP", wires=(0, 1)),
        ),
        measurements=(),
    )

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    signatures = [
        (operation.kind, operation.canonical_family, operation.name, tuple(operation.parameters))
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.P, "P", (0.125,)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.SDG, "Sdg", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.TDG, "Tdg", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.SX, "SX", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.U, "U", (0.1, 0.2, 0.3)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.ISWAP, "iSWAP", ()) in signatures


def test_pennylane_adapter_attaches_framework_matrix_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_matrix(operation: object) -> tuple[tuple[int, int], tuple[int, int]]:
        if getattr(operation, "name", "") == "Hadamard":
            return ((1, 1), (1, -1))
        raise TypeError("matrix not available")

    install_fake_pennylane(monkeypatch, matrix_function=fake_matrix)

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(build_fake_tape()))
    first_operation = next(operation for layer in ir.layers for operation in layer.operations)

    assert first_operation.metadata["matrix"] == ((1, 1), (1, -1))


def test_pennylane_adapter_skips_framework_matrices_when_explicit_matrices_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_matrix(operation: object) -> object:
        raise AssertionError(f"matrix lookup should not run for {operation!r}")

    install_fake_pennylane(monkeypatch, matrix_function=fake_matrix)

    ir = PennyLaneAdapter().to_ir(
        FakeTapeWrapper(build_fake_tape()),
        options={"explicit_matrices": False},
    )
    first_operation = next(operation for layer in ir.layers for operation in layer.operations)

    assert "matrix" not in first_operation.metadata


def test_pennylane_adapter_rejects_non_tape_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pennylane(monkeypatch)

    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"PennyLane support expects .* materialized \.qtape, \.tape, or \._tape",
    ):
        PennyLaneAdapter().to_ir(object())


def test_pennylane_adapter_rejects_wrappers_with_invalid_tape_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)

    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"PennyLane support expects .* materialized \.qtape, \.tape, or \._tape",
    ):
        PennyLaneAdapter().to_ir(SimpleNamespace(tape=object()))


def test_pennylane_adapter_rejects_mid_measure_without_wire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0,),
        operations=(FakeOperation(name="MidMeasureMP", wires=()),),
        measurements=(),
    )

    with pytest.raises(
        UnsupportedOperationError,
        match="mid-measurement operation has no quantum target",
    ):
        PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))


@skip_real_pennylane_on_windows
@pytest.mark.integration
def test_pennylane_adapter_converts_mid_measure_and_conditional_operations() -> None:
    qml = pytest.importorskip("pennylane")

    with qml.tape.QuantumTape() as tape:
        measured_bit = qml.measure(0)
        qml.cond(measured_bit, qml.X)(1)

    ir = PennyLaneAdapter().to_ir(tape)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[0].kind is OperationKind.MEASUREMENT
    assert operations[1].name == "X"
    assert operations[1].classical_conditions[0].wire_ids == ("c0",)
    assert operations[1].classical_conditions[0].expression == "if c[0]=1"


@skip_real_pennylane_on_windows
@pytest.mark.integration
def test_pennylane_adapter_keeps_composite_operations_compact_by_default() -> None:
    qml = pytest.importorskip("pennylane")

    with qml.tape.QuantumTape() as tape:
        qml.QFT(wires=[0, 1, 2])

    ir = PennyLaneAdapter().to_ir(tape)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) == 1
    assert operations[0].name == "QFT"


@skip_real_pennylane_on_windows
@pytest.mark.integration
def test_pennylane_adapter_expands_composite_operations_when_requested() -> None:
    qml = pytest.importorskip("pennylane")

    with qml.tape.QuantumTape() as tape:
        qml.QFT(wires=[0, 1, 2])

    ir = PennyLaneAdapter().to_ir(tape, options={"composite_mode": "expand"})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) > 1
    assert operations[0].name == "H"


@skip_real_pennylane_on_windows
@pytest.mark.integration
def test_pennylane_adapter_converts_multi_wire_terminal_measurements() -> None:
    qml = pytest.importorskip("pennylane")

    with qml.tape.QuantumTape() as tape:
        qml.Hadamard(0)
        qml.CNOT(wires=[0, 1])
        qml.probs(wires=[0, 1])

    ir = PennyLaneAdapter().to_ir(tape)
    terminal_outputs = [
        operation
        for layer in ir.layers
        for operation in layer.operations
        if operation.name == "PROBS"
    ]

    assert ir.classical_wires == ()
    assert len(terminal_outputs) == 1
    assert terminal_outputs[0].kind is OperationKind.GATE
    assert terminal_outputs[0].target_wires == ("q0", "q1")
    assert terminal_outputs[0].metadata["pennylane_terminal_kind"] == "probs"
    assert terminal_outputs[0].metadata["hover_details"] == (
        "terminal output: probs",
        "selected wires: 0, 1",
    )


@skip_real_pennylane_on_windows
@pytest.mark.integration
def test_pennylane_adapter_converts_observable_terminal_outputs() -> None:
    qml = pytest.importorskip("pennylane")

    with qml.tape.QuantumTape() as tape:
        qml.Hadamard(0)
        qml.expval(qml.PauliZ(0))

    ir = PennyLaneAdapter().to_ir(tape)
    terminal_output = [operation for layer in ir.layers for operation in layer.operations][-1]

    assert ir.classical_wires == ()
    assert terminal_output.kind is OperationKind.GATE
    assert terminal_output.name == "EXPVAL"
    assert terminal_output.target_wires == ("q0",)
    assert terminal_output.metadata["pennylane_terminal_kind"] == "expval"
    assert terminal_output.metadata["pennylane_observable_label"] == "PauliZ"
    assert terminal_output.metadata["hover_details"] == (
        "terminal output: expval",
        "observable: PauliZ",
        "observable type: PauliZ",
        "selected wires: 0",
    )


@skip_real_pennylane_on_windows
@pytest.mark.integration
def test_pennylane_adapter_converts_scaled_prod_terminal_outputs() -> None:
    qml = pytest.importorskip("pennylane")

    with qml.tape.QuantumTape() as tape:
        qml.expval(0.5 * (qml.PauliX(0) @ qml.PauliZ(1)))

    ir = PennyLaneAdapter().to_ir(tape)
    terminal_output = [operation for layer in ir.layers for operation in layer.operations][-1]

    assert terminal_output.kind is OperationKind.GATE
    assert terminal_output.name == "EXPVAL"
    assert terminal_output.target_wires == ("q0", "q1")
    assert terminal_output.metadata["pennylane_observable_label"] == "0.5 * (PauliX @ PauliZ)"
    assert terminal_output.metadata["hover_details"] == (
        "terminal output: expval",
        "observable: 0.5 * (PauliX @ PauliZ)",
        "observable type: SProd",
        "observable terms: 1",
        "all wires",
    )


@skip_real_pennylane_on_windows
@pytest.mark.integration
def test_pennylane_adapter_truncates_real_linear_combination_observables() -> None:
    qml = pytest.importorskip("pennylane")

    with qml.tape.QuantumTape() as tape:
        qml.expval(
            qml.dot(
                [0.5, -1.25],
                [qml.PauliX(0), qml.PauliZ(1) @ qml.PauliY(2)],
            )
        )

    ir = PennyLaneAdapter().to_ir(tape)
    terminal_output = [operation for layer in ir.layers for operation in layer.operations][-1]

    assert terminal_output.kind is OperationKind.GATE
    assert terminal_output.name == "EXPVAL"
    assert terminal_output.target_wires == ("q0", "q1", "q2")
    assert terminal_output.metadata["pennylane_observable_label"] == "0.5 * PauliX + ..."
    assert terminal_output.metadata["hover_details"] == (
        "terminal output: expval",
        "observable: 0.5 * PauliX + ...",
        "observable type: Sum",
        "observable terms: 2",
        "observable summary: truncated",
        "all wires",
    )


def test_pennylane_adapter_supports_additional_common_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1, 2),
        operations=(
            FakeOperation(name="Identity", wires=(0,)),
            FakeOperation(name="Reset", wires=(1,)),
            FakeOperation(name="Delay", wires=(2,), parameters=(12,)),
            FakeOperation(name="ECR", wires=(0, 2)),
            FakeOperation(name="RXX", wires=(0, 1), parameters=(0.5,)),
            FakeOperation(name="RYY", wires=(1, 2), parameters=(0.6,)),
            FakeOperation(name="RZZ", wires=(0, 2), parameters=(0.7,)),
            FakeOperation(name="RZX", wires=(0, 1), parameters=(0.8,)),
            FakeOperation(name="FSim", wires=(1, 2), parameters=(0.2, 0.3)),
            FakeOperation(
                name="RZZ",
                wires=(0, 1, 2),
                parameters=(0.125,),
                control_wires=(0,),
                target_wires=(1, 2),
            ),
        ),
        measurements=(),
    )

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    signatures = [
        (
            operation.kind,
            operation.canonical_family,
            operation.name,
            tuple(operation.parameters),
            tuple(operation.target_wires),
            tuple(operation.control_wires),
        )
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.I, "I", (), ("q0",), ()) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RESET,
        "RESET",
        (),
        ("q1",),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.DELAY,
        "DELAY",
        (12,),
        ("q2",),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.ECR,
        "ECR",
        (),
        ("q0", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RXX,
        "RXX",
        (0.5,),
        ("q0", "q1"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RYY,
        "RYY",
        (0.6,),
        ("q1", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RZZ,
        "RZZ",
        (0.7,),
        ("q0", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RZX,
        "RZX",
        (0.8,),
        ("q0", "q1"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.FSIM,
        "FSIM",
        (0.2, 0.3),
        ("q1", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.RZZ,
        "RZZ",
        (0.125,),
        ("q1", "q2"),
        ("q0",),
    ) in signatures
