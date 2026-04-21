from __future__ import annotations

from collections import Counter

import pytest

from quantum_circuit_drawer.builder import (
    CircuitBuilder,
    _build_wires,
    _resolve_wire_id,
    _wire_id_lookup,
)
from quantum_circuit_drawer.ir.operations import OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from tests.support import flatten_operations


def test_circuit_builder_supports_remaining_convenience_gate_methods() -> None:
    circuit = (
        CircuitBuilder(["left", "middle", "right"], ["c0", "c1", "c2"])
        .gate("SWAP", "left", "right", label="swap-via-gate")
        .i("left")
        .y("middle")
        .z("right")
        .s("left")
        .sdg("middle")
        .t("right")
        .tdg("left")
        .sx("middle")
        .sxdg("right")
        .p("theta", "left")
        .rx(0.1, "left")
        .ry(0.2, "middle")
        .rz(0.3, "right")
        .rxx(0.4, "left", "middle")
        .ryy(0.5, "middle", "right")
        .rzz(0.6, "left", "right")
        .rzx(0.7, "right", "middle")
        .u(0.8, 0.9, 1.0, "left")
        .u2("phi", "lam", "middle")
        .cy("left", "middle")
        .cz("middle", "right")
        .ch("right", "left")
        .cp("alpha", "left", "right")
        .crx("beta", "right", "middle")
        .cry("gamma", "middle", "left")
        .crz("delta", "left", "middle")
        .cu(1, 2, 3, 4, "middle", "right")
        .barrier()
        .build()
    )

    operations = flatten_operations(circuit)

    assert Counter(
        (
            operation.kind,
            operation.name,
            tuple(operation.parameters),
            tuple(operation.target_wires),
            tuple(operation.control_wires),
            operation.label,
        )
        for operation in operations
    ) == Counter(
        [
            (OperationKind.SWAP, "SWAP", (), ("q0", "q2"), (), "swap-via-gate"),
            (OperationKind.GATE, "I", (), ("q0",), (), "I"),
            (OperationKind.GATE, "Y", (), ("q1",), (), "Y"),
            (OperationKind.GATE, "Z", (), ("q2",), (), "Z"),
            (OperationKind.GATE, "S", (), ("q0",), (), "S"),
            (OperationKind.GATE, "SDG", (), ("q1",), (), "SDG"),
            (OperationKind.GATE, "T", (), ("q2",), (), "T"),
            (OperationKind.GATE, "TDG", (), ("q0",), (), "TDG"),
            (OperationKind.GATE, "SX", (), ("q1",), (), "SX"),
            (OperationKind.GATE, "SXDG", (), ("q2",), (), "SXDG"),
            (OperationKind.GATE, "P", ("theta",), ("q0",), (), "P"),
            (OperationKind.GATE, "RX", (0.1,), ("q0",), (), "RX"),
            (OperationKind.GATE, "RY", (0.2,), ("q1",), (), "RY"),
            (OperationKind.GATE, "RZ", (0.3,), ("q2",), (), "RZ"),
            (OperationKind.GATE, "RXX", (0.4,), ("q0", "q1"), (), "RXX"),
            (OperationKind.GATE, "RYY", (0.5,), ("q1", "q2"), (), "RYY"),
            (OperationKind.GATE, "RZZ", (0.6,), ("q0", "q2"), (), "RZZ"),
            (OperationKind.GATE, "RZX", (0.7,), ("q2", "q1"), (), "RZX"),
            (OperationKind.GATE, "U", (0.8, 0.9, 1.0), ("q0",), (), "U"),
            (OperationKind.GATE, "U2", ("phi", "lam"), ("q1",), (), "U2"),
            (OperationKind.CONTROLLED_GATE, "Y", (), ("q1",), ("q0",), "Y"),
            (OperationKind.CONTROLLED_GATE, "Z", (), ("q2",), ("q1",), "Z"),
            (OperationKind.CONTROLLED_GATE, "H", (), ("q0",), ("q2",), "H"),
            (OperationKind.CONTROLLED_GATE, "P", ("alpha",), ("q2",), ("q0",), "P"),
            (OperationKind.CONTROLLED_GATE, "RX", ("beta",), ("q1",), ("q2",), "RX"),
            (OperationKind.CONTROLLED_GATE, "RY", ("gamma",), ("q0",), ("q1",), "RY"),
            (OperationKind.CONTROLLED_GATE, "RZ", ("delta",), ("q1",), ("q0",), "RZ"),
            (OperationKind.CONTROLLED_GATE, "U", (1, 2, 3, 4), ("q2",), ("q1",), "U"),
            (OperationKind.BARRIER, "BARRIER", (), ("q0", "q1", "q2"), (), "BARRIER"),
        ]
    )


def test_circuit_builder_validates_gate_inputs_and_measure_all_requirements() -> None:
    with pytest.raises(ValueError, match="gate name cannot be empty"):
        CircuitBuilder(1).gate(" ", 0)

    with pytest.raises(ValueError, match="gate requires at least one target"):
        CircuitBuilder(1).gate("X")

    with pytest.raises(
        ValueError,
        match="measure_all requires the same number of classical and quantum wires",
    ):
        CircuitBuilder(2, 1).measure_all()


@pytest.mark.parametrize(
    ("values", "kind", "message"),
    [
        (True, WireKind.QUANTUM, "quantum wire count must be an integer or a sequence of names"),
        (-1, WireKind.CLASSICAL, "classical wire count cannot be negative"),
        ("abc", WireKind.QUANTUM, "quantum wire names must be provided as a sequence of strings"),
        (("alpha", " "), WireKind.CLASSICAL, "classical wire names cannot be empty"),
        (("dup", "dup"), WireKind.QUANTUM, "quantum wire names must be unique"),
    ],
)
def test_build_wires_rejects_invalid_counts_and_names(
    values: object,
    kind: WireKind,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _build_wires(values, prefix="w", kind=kind)  # type: ignore[arg-type]


@pytest.mark.parametrize(("reference",), [(True,), (1.5,)])
def test_resolve_wire_id_rejects_invalid_reference_types(reference: object) -> None:
    with pytest.raises(ValueError, match="quantum wire references must be integers or strings"):
        _resolve_wire_id(reference, lookup={"q0": "q0"}, kind="quantum")  # type: ignore[arg-type]


def test_resolve_wire_id_rejects_unknown_references() -> None:
    with pytest.raises(ValueError, match=r"unknown classical wire reference 'missing'"):
        _resolve_wire_id("missing", lookup={"c0": "c0"}, kind="classical")


def test_wire_id_lookup_skips_missing_labels() -> None:
    lookup = _wire_id_lookup((WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label=None),))

    assert lookup == {
        0: "q0",
        "q0": "q0",
    }
