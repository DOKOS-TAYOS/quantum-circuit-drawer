from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer.adapters.pennylane_adapter import PennyLaneAdapter
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind
from quantum_circuit_drawer.ir.semantic import SemanticCircuitIR
from tests.support import (
    OperationSignature,
    assert_classical_wire_bundles,
    assert_operation_signatures,
    assert_quantum_wire_labels,
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
        control_values: tuple[object, ...] = (),
        target_wires: tuple[object, ...] | None = None,
        has_decomposition: bool = False,
        decomposition: tuple[object, ...] = (),
    ) -> None:
        self.name = name
        self.wires = wires
        self.parameters = parameters
        self.control_wires = control_wires
        self.control_values = control_values
        self.target_wires = target_wires
        self.has_decomposition = has_decomposition
        self._decomposition = decomposition

    def decomposition(self) -> tuple[object, ...]:
        return self._decomposition


class FakeMidMeasureOperation(FakeOperation):
    def __init__(self, *, wires: tuple[object, ...], measurement_id: str) -> None:
        super().__init__(name="MidMeasureMP", wires=wires)
        self.id = measurement_id


class FakeMeasurement:
    def __init__(self, wires: tuple[object, ...], *, obs: object | None = None) -> None:
        self.wires = wires
        self.obs = obs
        self.mv = None


class SampleMP(FakeMeasurement):
    pass


class ProbabilityMP(FakeMeasurement):
    pass


class ExpectationMP(FakeMeasurement):
    pass


class StateMP(FakeMeasurement):
    pass


class FakeObservable:
    def __init__(
        self,
        *,
        name: str,
        wires: tuple[object, ...],
        operands: tuple[FakeObservable, ...] = (),
    ) -> None:
        self.name = name
        self.wires = wires
        self.operands = operands


class FakeObservableWithTerms(FakeObservable):
    def __init__(
        self,
        *,
        name: str,
        wires: tuple[object, ...],
        term_coefficients: tuple[object, ...],
        term_operands: tuple[object, ...],
    ) -> None:
        super().__init__(name=name, wires=wires)
        self._term_coefficients = term_coefficients
        self._term_operands = term_operands

    def terms(self) -> tuple[tuple[object, ...], tuple[object, ...]]:
        return self._term_coefficients, self._term_operands


class FakeStringMeasurement:
    def __init__(self, *, representation: str, wires: tuple[object, ...] = ()) -> None:
        self._representation = representation
        self.wires = wires
        self.obs = None
        self.observable = None

    def __repr__(self) -> str:
        return self._representation


class FakeFloatScalar:
    def __float__(self) -> float:
        return 2.5


class FakeMeasurementValue:
    def __init__(
        self,
        *,
        measurements: tuple[object, ...],
        branches: dict[tuple[int, ...], bool],
    ) -> None:
        self.measurements = measurements
        self.branches = branches


class FakeConditionalOperation:
    def __init__(self, *, base: FakeOperation, meas_val: FakeMeasurementValue) -> None:
        self.base = base
        self.meas_val = meas_val
        self.name = base.name
        self.wires = base.wires
        self.parameters = base.parameters


class FakeTapeWrapper:
    def __init__(self, tape: FakeQuantumTape) -> None:
        self.qtape = tape


class FakeQNodeLikeWrapper:
    def __init__(self, tape: FakeQuantumTape) -> None:
        self._tape = tape

    @property
    def qtape(self) -> object:
        raise AssertionError("qtape property should not be touched when _tape is already built")

    @property
    def tape(self) -> object:
        raise AssertionError("tape property should not be touched when _tape is already built")

    def construct(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("construct() must not be called implicitly")


def install_fake_pennylane(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("pennylane")
    fake_module.tape = SimpleNamespace(
        QuantumTape=FakeQuantumTape,
        QuantumScript=FakeQuantumTape,
    )
    monkeypatch.setitem(sys.modules, "pennylane", fake_module)


def build_basic_fake_tape() -> FakeQuantumTape:
    return FakeQuantumTape(
        wires=(0, 1),
        operations=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(
                name="CNOT",
                wires=(0, 1),
                control_wires=(0,),
                target_wires=(1,),
            ),
        ),
        measurements=(SampleMP((1,)),),
    )


def test_pennylane_adapter_contract_converts_basic_stubbed_tape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(build_basic_fake_tape()))

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


def test_pennylane_adapter_contract_uses_prebuilt_private_tape_without_touching_properties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    wrapper = FakeQNodeLikeWrapper(build_basic_fake_tape())

    assert PennyLaneAdapter.can_handle(wrapper) is True

    ir = PennyLaneAdapter().to_ir(wrapper)

    assert ir.metadata["framework"] == "pennylane"
    assert [operation.name for layer in ir.layers for operation in layer.operations] == [
        "H",
        "X",
        "SAMPLE",
    ]


def test_pennylane_adapter_contract_converts_stubbed_mid_measure_and_conditional_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    measured_bit = FakeMidMeasureOperation(wires=(0,), measurement_id="m0")
    conditional_x = FakeConditionalOperation(
        base=FakeOperation(name="PauliX", wires=(1,)),
        meas_val=FakeMeasurementValue(
            measurements=(measured_bit,),
            branches={(1,): True},
        ),
    )
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(measured_bit, conditional_x),
        measurements=(),
    )

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.kind for operation in operations] == [
        OperationKind.MEASUREMENT,
        OperationKind.GATE,
    ]
    assert operations[1].name == "X"
    assert operations[1].classical_conditions[0].wire_ids == ("c0",)
    assert operations[1].classical_conditions[0].expression == "if c[0]=1"


def test_pennylane_adapter_contract_expands_stubbed_composite_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    composite = FakeOperation(
        name="QFT",
        wires=(0, 1),
        has_decomposition=True,
        decomposition=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(
                name="CNOT",
                wires=(0, 1),
                control_wires=(0,),
                target_wires=(1,),
            ),
        ),
    )
    tape = FakeQuantumTape(wires=(0, 1), operations=(composite,), measurements=())

    compact_ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    expanded_ir = PennyLaneAdapter().to_ir(
        FakeTapeWrapper(tape),
        options={"composite_mode": "expand"},
    )

    compact_operations = [
        operation.name for layer in compact_ir.layers for operation in layer.operations
    ]
    expanded_operations = [
        operation.name for layer in expanded_ir.layers for operation in layer.operations
    ]

    assert compact_operations == ["QFT"]
    assert expanded_operations == ["H", "X"]


def test_pennylane_adapter_contract_exposes_semantic_conditional_and_decomposition_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    measured_bit = FakeMidMeasureOperation(wires=(0,), measurement_id="m0")
    conditional_x = FakeConditionalOperation(
        base=FakeOperation(name="PauliX", wires=(1,)),
        meas_val=FakeMeasurementValue(
            measurements=(measured_bit,),
            branches={(1,): True},
        ),
    )
    composite = FakeOperation(
        name="QFT",
        wires=(0, 1),
        has_decomposition=True,
        decomposition=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(
                name="CNOT",
                wires=(0, 1),
                control_wires=(0,),
                target_wires=(1,),
            ),
        ),
    )
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(measured_bit, conditional_x, composite),
        measurements=(),
    )

    semantic_ir = PennyLaneAdapter().to_semantic_ir(
        FakeTapeWrapper(tape),
        options={"composite_mode": "expand", "explicit_matrices": False},
    )

    assert isinstance(semantic_ir, SemanticCircuitIR)
    assert semantic_ir.layers[1].operations[0].provenance.framework == "pennylane"
    assert semantic_ir.layers[1].operations[0].hover_details == ("conditional on: if c[0]=1",)
    assert semantic_ir.layers[2].operations[0].provenance.decomposition_origin == "QFT"


def test_pennylane_adapter_contract_assigns_stable_locations_to_expanded_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    composite = FakeOperation(
        name="QFT",
        wires=(0, 1),
        has_decomposition=True,
        decomposition=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(
                name="CNOT",
                wires=(0, 1),
                control_wires=(0,),
                target_wires=(1,),
            ),
        ),
    )
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(FakeOperation(name="Hadamard", wires=(0,)), composite),
        measurements=(),
    )

    semantic_ir = PennyLaneAdapter().to_semantic_ir(
        FakeTapeWrapper(tape),
        options={"composite_mode": "expand", "explicit_matrices": False},
    )
    operations = [operation for layer in semantic_ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["H", "H", "X"]
    assert [operation.provenance.location for operation in operations] == [
        (0,),
        (1, 0),
        (1, 1),
    ]


def test_pennylane_adapter_contract_keeps_terminal_outputs_as_gate_like_semantic_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(),
        measurements=(
            ExpectationMP((0,), obs=FakeObservable(name="PauliZ", wires=(0,))),
            ProbabilityMP((0, 1)),
            StateMP(()),
        ),
    )

    semantic_ir = PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape))
    operations = [operation for layer in semantic_ir.layers for operation in layer.operations]

    assert semantic_ir.classical_wires == ()
    assert [operation.name for operation in operations] == ["EXPVAL", "PROBS", "STATE"]
    assert all(operation.kind is OperationKind.GATE for operation in operations)
    assert operations[0].metadata["pennylane_terminal_kind"] == "expval"
    assert operations[0].metadata["pennylane_observable_label"] == "PauliZ"
    assert operations[1].target_wires == ("q0", "q1")
    assert operations[2].target_wires == ("q0", "q1")


def test_pennylane_adapter_contract_maps_stubbed_control_values_to_semantic_ir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1, 2),
        operations=(
            FakeOperation(
                name="MultiControlledX",
                wires=(0, 1, 2),
                control_wires=(0, 1),
                control_values=(False, True),
                target_wires=(2,),
            ),
        ),
        measurements=(),
    )

    semantic_ir = PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape))
    operation = semantic_ir.layers[0].operations[0]

    assert operation.kind is OperationKind.CONTROLLED_GATE
    assert operation.control_values == ((0,), (1,))


@pytest.mark.parametrize(
    ("measurement", "expected_kind"),
    [
        (FakeStringMeasurement(representation="expval(PauliZ)", wires=(0,)), "expval"),
        (FakeStringMeasurement(representation="var(PauliX)", wires=(0,)), "var"),
        (FakeStringMeasurement(representation="probs(wires=[0, 1])", wires=(0, 1)), "probs"),
        (FakeStringMeasurement(representation="sample(wires=[0])", wires=(0,)), "sample"),
        (FakeStringMeasurement(representation="CountsMP(wires=[0])", wires=(0,)), "counts"),
        (FakeStringMeasurement(representation="state()", wires=()), "state"),
    ],
)
def test_pennylane_adapter_contract_detects_terminal_measurement_kind_from_repr(
    measurement: object,
    expected_kind: str,
) -> None:
    assert PennyLaneAdapter()._terminal_measurement_kind(measurement) == expected_kind


def test_pennylane_adapter_contract_falls_back_to_sample_for_wire_measurements_without_observable() -> (
    None
):
    measurement = FakeStringMeasurement(representation="mystery()", wires=(0, 1))

    assert PennyLaneAdapter()._terminal_measurement_kind(measurement) == "sample"


def test_pennylane_adapter_contract_summarizes_scaled_product_observables_with_truncation() -> None:
    adapter = PennyLaneAdapter()
    product = FakeObservable(
        name="Prod",
        wires=(0, 1, 2),
        operands=(
            FakeObservable(name="PauliX", wires=(0,)),
            FakeObservable(
                name="Prod",
                wires=(1, 2),
                operands=(
                    FakeObservable(name="PauliY", wires=(1,)),
                    FakeObservable(name="PauliZ", wires=(2,)),
                ),
            ),
        ),
    )
    scaled = SimpleNamespace(
        name="SProd",
        wires=(0, 1, 2),
        scalar=3,
        base=product,
    )

    summary = adapter._summarize_observable(scaled)

    assert summary.label == "3 * ..."
    assert summary.native_type == "SProd"
    assert summary.component_count == 1
    assert summary.component_label == "terms"
    assert summary.truncated is True
    assert summary.structure == "scaled"


def test_pennylane_adapter_contract_summarizes_linear_combination_terms() -> None:
    adapter = PennyLaneAdapter()
    observable = SimpleNamespace(
        name="Hamiltonian",
        wires=(0, 1),
        coeffs=(1.0, -0.5),
        operands=(
            FakeObservable(name="PauliX", wires=(0,)),
            FakeObservable(name="PauliZ", wires=(1,)),
        ),
    )

    summary = adapter._summarize_observable(observable)

    assert summary.label == "1 * PauliX + ..."
    assert summary.component_count == 2
    assert summary.component_label == "terms"
    assert summary.structure == "sum"


def test_pennylane_adapter_contract_summarizes_sum_terms_without_unity_coefficients() -> None:
    adapter = PennyLaneAdapter()
    observable = FakeObservableWithTerms(
        name="Sum",
        wires=(0, 1),
        term_coefficients=(1.0, 2.0),
        term_operands=(
            FakeObservable(name="PauliX", wires=(0,)),
            FakeObservable(name="PauliZ", wires=(1,)),
        ),
    )

    summary = adapter._summarize_observable(observable)

    assert summary.label == "PauliX + 2 * PauliZ"
    assert summary.component_count == 2
    assert summary.component_label == "terms"
    assert summary.structure == "sum"


def test_pennylane_adapter_contract_uses_simple_observable_fallback_for_long_labels() -> None:
    adapter = PennyLaneAdapter()
    observable = FakeObservable(
        name="ObservableNameThatIsFarTooLongToDisplayDirectly",
        wires=(0, 1),
    )

    summary = adapter._summarize_observable(observable)

    assert summary.label == "FakeObservable"
    assert summary.native_type == "FakeObservable"
    assert summary.truncated is False
    assert summary.structure == "simple"


def test_pennylane_adapter_contract_truncates_long_class_name_fallbacks() -> None:
    fallback = PennyLaneAdapter()._class_name_fallback(
        "ObservableNameThatIsFarTooLongToDisplayDirectly"
    )

    assert fallback is not None
    assert fallback.endswith("[...]")


def test_pennylane_adapter_contract_formats_observable_scalars_and_names() -> None:
    adapter = PennyLaneAdapter()

    assert adapter._format_observable_scalar(True) == "1"
    assert adapter._format_observable_scalar(3) == "3"
    assert adapter._format_observable_scalar(FakeFloatScalar()) == "2.5"
    assert adapter._format_observable_scalar(["", "ObservableLabel"]) == "ObservableLabel"
    assert adapter._normalized_observable_name(["", "PauliX"]) == "PauliX"
    assert adapter._normalized_observable_name(None) is None


def test_pennylane_adapter_contract_normalizes_control_values_and_mid_measure_ids() -> None:
    adapter = PennyLaneAdapter()
    operation = SimpleNamespace(control_values=(False, (1, 0)))
    no_control_values = SimpleNamespace(control_values=None)
    hyper_measure = SimpleNamespace(id=None, hyperparameters={"id": "mid-1"})

    assert adapter._control_values_for_operation(operation) == ((0,), (1, 0))
    assert adapter._control_values_for_operation(no_control_values) == ()
    assert adapter._mid_measure_id(hyper_measure) == "mid-1"


def test_pennylane_adapter_contract_builds_multi_bit_classical_condition() -> None:
    adapter = PennyLaneAdapter()
    measurement_a = FakeMidMeasureOperation(wires=(0,), measurement_id="m0")
    measurement_b = FakeMidMeasureOperation(wires=(1,), measurement_id="m1")
    measurement_value = FakeMeasurementValue(
        measurements=(measurement_a, measurement_b),
        branches={(1, 0): True},
    )

    condition = adapter._condition_from_measurement_value(
        measurement_value,
        {
            "m0": ("c0", "c[0]"),
            "m1": ("c1", "c[1]"),
        },
    )

    assert condition.wire_ids == ("c0", "c1")
    assert condition.expression == "if c=2"


def test_pennylane_adapter_contract_handles_decomposition_and_matrix_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = PennyLaneAdapter()
    nested = FakeOperation(name="PauliX", wires=(0,))
    operation = FakeOperation(
        name="Custom",
        wires=(0,),
        has_decomposition=True,
        decomposition=(nested,),
    )

    decomposition = adapter._decomposition(operation)
    assert len(decomposition) == 1
    assert decomposition[0] is nested

    direct_matrix_operation = SimpleNamespace(matrix=lambda: [[1.0, 0.0], [0.0, 1.0]])
    assert adapter._matrix_metadata(direct_matrix_operation) == {"matrix": [[1.0, 0.0], [0.0, 1.0]]}

    fake_qml = ModuleType("pennylane")
    fake_qml.matrix = lambda _operation: [[1.0, 0.0], [0.0, 1.0]]
    monkeypatch.setitem(sys.modules, "pennylane", fake_qml)

    imported_matrix_operation = SimpleNamespace(matrix=None)
    assert adapter._matrix_metadata(imported_matrix_operation) == {
        "matrix": [[1.0, 0.0], [0.0, 1.0]]
    }
