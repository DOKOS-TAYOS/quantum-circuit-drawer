from __future__ import annotations

import builtins
import importlib
import sys
from dataclasses import dataclass
from types import ModuleType

import pytest

from quantum_circuit_drawer.api import draw_quantum_circuit
from quantum_circuit_drawer.exceptions import UnsupportedOperationError
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind
from tests.support import (
    FakeMyQLMCircuit,
    FakeMyQLMCircuitImplementation,
    FakeMyQLMGateDefinition,
    FakeMyQLMOp,
    FakeMyQLMSyntax,
    install_fake_myqlm,
)


def load_myqlm_adapter_type() -> type[object]:
    try:
        module = importlib.import_module("quantum_circuit_drawer.adapters.myqlm_adapter")
    except ModuleNotFoundError as exc:
        pytest.fail(f"myqlm adapter module is missing: {exc}")
    return module.MyQLMAdapter


def build_common_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "H": FakeMyQLMGateDefinition(name="H", arity=1, syntax=FakeMyQLMSyntax(name="H")),
        "X": FakeMyQLMGateDefinition(name="X", arity=1, syntax=FakeMyQLMSyntax(name="X")),
        "_cx": FakeMyQLMGateDefinition(
            name="_cx",
            arity=2,
            syntax=FakeMyQLMSyntax(name="C-X"),
            nbctrls=1,
            subgate="X",
        ),
    }
    return FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(gate="H", qbits=(0,)),
            FakeMyQLMOp(gate="_cx", qbits=(0, 1)),
            FakeMyQLMOp(type="MEASURE", qbits=(1,), cbits=(0,)),
        ),
        gate_dic=gate_dic,
        nbqbits=2,
        nbcbits=2,
        name="myqlm_common_demo",
    )


def build_extended_gate_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "PH": FakeMyQLMGateDefinition(
            name="PH",
            arity=1,
            syntax=FakeMyQLMSyntax(name="PH", parameters=(0.125,)),
        ),
        "U3": FakeMyQLMGateDefinition(
            name="U3",
            arity=1,
            syntax=FakeMyQLMSyntax(name="U3", parameters=(0.1, 0.2, 0.3)),
        ),
        "ISWAP": FakeMyQLMGateDefinition(
            name="ISWAP",
            arity=2,
            syntax=FakeMyQLMSyntax(name="ISWAP"),
        ),
        "D-T": FakeMyQLMGateDefinition(
            name="D-T",
            arity=1,
            syntax=FakeMyQLMSyntax(name="D-T"),
        ),
    }
    return FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(gate="PH", qbits=(0,)),
            FakeMyQLMOp(gate="U3", qbits=(1,)),
            FakeMyQLMOp(gate="ISWAP", qbits=(0, 1)),
            FakeMyQLMOp(gate="D-T", qbits=(1,)),
        ),
        gate_dic=gate_dic,
        nbqbits=2,
        nbcbits=0,
        name="myqlm_extended_demo",
    )


def build_controlled_csign_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "_csign": FakeMyQLMGateDefinition(
            name="_csign",
            arity=2,
            syntax=FakeMyQLMSyntax(name="CSIGN"),
            nbctrls=1,
            subgate="CSIGN",
        ),
    }
    return FakeMyQLMCircuit(
        ops=(FakeMyQLMOp(gate="_csign", qbits=(0, 1)),),
        gate_dic=gate_dic,
        nbqbits=2,
        nbcbits=0,
        name="myqlm_controlled_csign_demo",
    )


def build_classic_control_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "H": FakeMyQLMGateDefinition(name="H", arity=1, syntax=FakeMyQLMSyntax(name="H")),
        "X": FakeMyQLMGateDefinition(name="X", arity=1, syntax=FakeMyQLMSyntax(name="X")),
        "RESET": FakeMyQLMGateDefinition(
            name="RESET", arity=1, syntax=FakeMyQLMSyntax(name="RESET")
        ),
    }
    return FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(gate="H", qbits=(0,)),
            FakeMyQLMOp(type="MEASURE", qbits=(0,), cbits=(0,)),
            FakeMyQLMOp(gate="X", qbits=(1,), type="CLASSICCTRL", cbits=(0,)),
            FakeMyQLMOp(type="RESET", qbits=(1,)),
        ),
        gate_dic=gate_dic,
        nbqbits=2,
        nbcbits=2,
        name="myqlm_classic_ctrl_demo",
    )


def build_composite_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "H": FakeMyQLMGateDefinition(name="H", arity=1, syntax=FakeMyQLMSyntax(name="H")),
        "PH": FakeMyQLMGateDefinition(
            name="PH",
            arity=1,
            syntax=FakeMyQLMSyntax(name="PH", parameters=(0.5,)),
        ),
        "_cph": FakeMyQLMGateDefinition(
            name="_cph",
            arity=2,
            syntax=FakeMyQLMSyntax(name="C-PH", parameters=(0.5,)),
            nbctrls=1,
            subgate="PH",
        ),
        "_routine": FakeMyQLMGateDefinition(
            name="_routine",
            arity=2,
            syntax=FakeMyQLMSyntax(name="QFT2"),
            circuit_implementation=FakeMyQLMCircuitImplementation(
                ops=(
                    FakeMyQLMOp(gate="H", qbits=(0,)),
                    FakeMyQLMOp(gate="_cph", qbits=(1, 0)),
                ),
                nbqbits=2,
            ),
        ),
    }
    return FakeMyQLMCircuit(
        ops=(FakeMyQLMOp(gate="_routine", qbits=(0, 1)),),
        gate_dic=gate_dic,
        nbqbits=2,
        nbcbits=0,
        name="myqlm_composite_demo",
    )


@dataclass(slots=True)
class FakeMyQLMParam:
    is_abstract: bool | None = None
    type: int | None = None
    int_p: int | None = None
    double_p: float | None = None
    string_p: str | None = None
    matrix_p: object | None = None
    serialized_p: object | None = None
    complex_p: object | None = None


def build_parametric_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "RX_theta": FakeMyQLMGateDefinition(
            name="RX_theta",
            arity=1,
            syntax=FakeMyQLMSyntax(
                name="RX",
                parameters=(FakeMyQLMParam(is_abstract=True, string_p="theta"),),
            ),
        ),
        "RY_half": FakeMyQLMGateDefinition(
            name="RY_half",
            arity=1,
            syntax=FakeMyQLMSyntax(
                name="RY",
                parameters=(FakeMyQLMParam(type=1, double_p=0.5),),
            ),
        ),
    }
    return FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(gate="RX_theta", qbits=(0,)),
            FakeMyQLMOp(gate="RY_half", qbits=(1,)),
        ),
        gate_dic=gate_dic,
        nbqbits=2,
        nbcbits=0,
        name="myqlm_parametric_demo",
    )


def test_myqlm_adapter_converts_common_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()

    ir = adapter_type().to_ir(build_common_myqlm_circuit())

    operations = [operation for layer in ir.layers for operation in layer.operations]
    assert ir.metadata["framework"] == "myqlm"
    assert [wire.label for wire in ir.quantum_wires] == ["q0", "q1"]
    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].metadata["bundle_size"] == 2
    assert [operation.kind for operation in operations] == [
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.MEASUREMENT,
    ]
    assert operations[0].name == "H"
    assert operations[1].name == "X"
    assert operations[1].control_wires == ("q0",)
    assert operations[1].target_wires == ("q1",)
    assert operations[2].metadata["classical_bit_label"] == "c[0]"


def test_myqlm_adapter_maps_additional_canonical_gate_families(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()

    ir = adapter_type().to_ir(build_extended_gate_myqlm_circuit())
    signatures = [
        (operation.kind, operation.canonical_family, operation.name, tuple(operation.parameters))
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.P, "P", (0.125,)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.U, "U", (0.1, 0.2, 0.3)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.ISWAP, "iSWAP", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.TDG, "Tdg", ()) in signatures


def test_myqlm_adapter_maps_controlled_csign_to_canonical_z(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()

    ir = adapter_type().to_ir(build_controlled_csign_myqlm_circuit())
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) == 1
    assert operations[0].kind is OperationKind.CONTROLLED_GATE
    assert operations[0].name == "Z"
    assert operations[0].canonical_family is CanonicalGateFamily.Z
    assert operations[0].control_wires == ("q0",)
    assert operations[0].target_wires == ("q1",)


def test_myqlm_adapter_converts_reset_and_classicctrl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()

    ir = adapter_type().to_ir(build_classic_control_myqlm_circuit())
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[2].name == "X"
    assert operations[2].classical_conditions[0].wire_ids == ("c0",)
    assert operations[2].classical_conditions[0].expression == "if c[0]=1"
    assert operations[3].kind is OperationKind.GATE
    assert operations[3].canonical_family is CanonicalGateFamily.RESET
    assert operations[3].target_wires == ("q1",)


def test_myqlm_adapter_converts_numeric_classicctrl_operation_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()
    gate_dic = {
        "X": FakeMyQLMGateDefinition(name="X", arity=1, syntax=FakeMyQLMSyntax(name="X")),
    }
    circuit = FakeMyQLMCircuit(
        ops=(FakeMyQLMOp(gate="X", qbits=(0,), cbits=(0,), type=4),),
        gate_dic=gate_dic,
        nbqbits=1,
        nbcbits=1,
    )

    ir = adapter_type().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[0].name == "X"
    assert operations[0].classical_conditions[0].wire_ids == ("c0",)
    assert operations[0].classical_conditions[0].expression == "if c[0]=1"


def test_myqlm_adapter_keeps_composite_operations_compact_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()

    ir = adapter_type().to_ir(build_composite_myqlm_circuit())
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) == 1
    assert operations[0].name == "QFT2"
    assert operations[0].target_wires == ("q0", "q1")


def test_myqlm_adapter_expands_composite_operations_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()

    ir = adapter_type().to_ir(
        build_composite_myqlm_circuit(),
        options={"composite_mode": "expand"},
    )
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["H", "P"]
    assert operations[1].kind is OperationKind.CONTROLLED_GATE
    assert operations[1].control_wires == ("q1",)
    assert operations[1].target_wires == ("q0",)


def test_myqlm_adapter_normalizes_param_objects_to_readable_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()

    ir = adapter_type().to_ir(build_parametric_myqlm_circuit())
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[0].parameters == ("theta",)
    assert operations[1].parameters == (0.5,)


@pytest.mark.parametrize("operation_type", ["BREAK", "CLASSIC", "REMAP"])
def test_myqlm_adapter_rejects_unsupported_operation_types(
    operation_type: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()
    gate_dic = {
        "X": FakeMyQLMGateDefinition(name="X", arity=1, syntax=FakeMyQLMSyntax(name="X")),
    }
    circuit = FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(
                gate="X" if operation_type == "CLASSICCTRL" else None,
                qbits=(0,),
                cbits=(0,),
                type=operation_type,
                remap=(0,) if operation_type == "REMAP" else None,
            ),
        ),
        gate_dic=gate_dic,
        nbqbits=1,
        nbcbits=1,
    )

    with pytest.raises(UnsupportedOperationError, match=operation_type.lower()):
        adapter_type().to_ir(circuit)


def test_myqlm_adapter_rejects_complex_classicctrl_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)
    adapter_type = load_myqlm_adapter_type()
    gate_dic = {
        "X": FakeMyQLMGateDefinition(name="X", arity=1, syntax=FakeMyQLMSyntax(name="X")),
    }
    circuit = FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(
                gate="X",
                qbits=(0,),
                cbits=(0, 1),
                type="CLASSICCTRL",
                formula="AND 0 1",
            ),
        ),
        gate_dic=gate_dic,
        nbqbits=1,
        nbcbits=2,
    )

    with pytest.raises(UnsupportedOperationError, match="classical control"):
        adapter_type().to_ir(circuit)


def test_draw_quantum_circuit_accepts_myqlm_framework_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    figure, axes = draw_quantum_circuit(
        build_common_myqlm_circuit(),
        framework="myqlm",
        show=False,
    )

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_renders_readable_myqlm_param_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    figure, axes = draw_quantum_circuit(
        build_parametric_myqlm_circuit(),
        framework="myqlm",
        show=False,
    )
    texts = [text.get_text() for text in axes.texts]

    assert "theta" in texts
    assert "0.5" in texts
    assert not any("Param(" in text for text in texts)
    assert figure is not None


def test_myqlm_adapter_can_handle_nested_qat_core_circuit_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    class FakeRuntimeCircuit:
        pass

    fake_qat = ModuleType("qat")
    fake_qat.__path__ = []
    fake_qat_core = ModuleType("qat.core")
    fake_qat_core.Circuit = FakeRuntimeCircuit

    monkeypatch.setitem(sys.modules, "qat", fake_qat)
    monkeypatch.setitem(sys.modules, "qat.core", fake_qat_core)

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "qat":
            return fake_qat
        if name == "qat.core":
            return fake_qat
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert load_myqlm_adapter_type().can_handle(FakeRuntimeCircuit()) is True
