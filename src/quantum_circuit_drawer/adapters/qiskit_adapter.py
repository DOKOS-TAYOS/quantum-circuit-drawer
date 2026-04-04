"""Qiskit adapter."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol, cast

from ..exceptions import UnsupportedOperationError
from ..ir.circuit import CircuitIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR, WireKind
from ..utils.formatting import format_gate_name
from .base import BaseAdapter


class _QiskitRegisterLike(Protocol):
    name: str | None

    def __iter__(self) -> Iterable[object]: ...


class _QiskitCircuitLike(Protocol):
    qubits: Sequence[object]
    clbits: Sequence[object]
    data: Sequence[object]
    cregs: Sequence[_QiskitRegisterLike]
    name: str | None


class QiskitAdapter(BaseAdapter):
    """Convert qiskit.QuantumCircuit objects into CircuitIR."""

    framework_name = "qiskit"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        try:
            from qiskit.circuit import QuantumCircuit
        except ImportError:
            return False
        return isinstance(circuit, QuantumCircuit)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        if not self.can_handle(circuit):
            raise TypeError("QiskitAdapter received a non-Qiskit circuit")

        typed_circuit = cast(_QiskitCircuitLike, circuit)
        qubits = list(typed_circuit.qubits)
        clbits = list(typed_circuit.clbits)
        qubit_ids = {bit: f"q{index}" for index, bit in enumerate(qubits)}
        classical_wires, classical_targets = self._build_classical_wires(typed_circuit, clbits)

        quantum_wires = [
            WireIR(id=qubit_ids[bit], index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index, bit in enumerate(qubits)
        ]

        operations = [
            self._convert_instruction(entry, qubit_ids, classical_targets)
            for entry in typed_circuit.data
        ]
        layers = self.pack_operations(operations)
        return CircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=layers,
            name=typed_circuit.name,
            metadata={"framework": self.framework_name},
        )

    def _convert_instruction(
        self,
        entry: object,
        qubit_ids: dict[object, str],
        classical_targets: dict[object, tuple[str, str]],
    ) -> OperationIR:
        operation, qubits, clbits = self._normalize_entry(entry)
        name = getattr(operation, "name", operation.__class__.__name__).lower()
        target_wires = tuple(qubit_ids[qubit] for qubit in qubits)
        parameters = tuple(getattr(operation, "params", ()) or ())

        if name == "measure":
            classical_target, classical_bit_label = classical_targets[clbits[0]]
            return MeasurementIR(
                kind=OperationKind.MEASUREMENT,
                name="M",
                target_wires=(target_wires[0],),
                classical_target=classical_target,
                metadata={"classical_bit_label": classical_bit_label},
            )
        if name == "barrier":
            return OperationIR(
                kind=OperationKind.BARRIER, name="BARRIER", target_wires=target_wires
            )
        if name == "swap":
            return OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=target_wires)

        control_count = int(getattr(operation, "num_ctrl_qubits", 0) or 0)
        if control_count > 0 and len(target_wires) > control_count:
            base_gate = getattr(operation, "base_gate", None)
            base_name = getattr(base_gate, "name", None) or name.removeprefix("c")
            return OperationIR(
                kind=OperationKind.CONTROLLED_GATE,
                name=format_gate_name(base_name),
                target_wires=target_wires[control_count:],
                control_wires=target_wires[:control_count],
                parameters=parameters,
            )

        if not target_wires:
            raise UnsupportedOperationError(f"Qiskit operation '{name}' has no drawable targets")
        return OperationIR(
            kind=OperationKind.GATE,
            name=format_gate_name(name),
            target_wires=target_wires,
            parameters=parameters,
        )

    def _normalize_entry(
        self, entry: object
    ) -> tuple[object, tuple[object, ...], tuple[object, ...]]:
        if hasattr(entry, "operation") and hasattr(entry, "qubits") and hasattr(entry, "clbits"):
            return entry.operation, tuple(entry.qubits), tuple(entry.clbits)
        if isinstance(entry, tuple) and len(entry) == 3:
            operation, qubits, clbits = entry
            return operation, tuple(qubits), tuple(clbits)
        raise UnsupportedOperationError(f"unsupported Qiskit instruction shape: {type(entry)!r}")

    def _build_classical_wires(
        self,
        circuit: _QiskitCircuitLike,
        clbits: list[object],
    ) -> tuple[list[WireIR], dict[object, tuple[str, str]]]:
        if not clbits:
            return [], {}

        classical_wires: list[WireIR] = []
        classical_targets: dict[object, tuple[str, str]] = {}
        mapped_bits: set[object] = set()

        registers = tuple(getattr(circuit, "cregs", ()) or ())
        if registers:
            for index, register in enumerate(registers):
                wire_id = f"c{index}"
                label = getattr(register, "name", None) or wire_id
                bits = tuple(register)
                classical_wires.append(
                    WireIR(
                        id=wire_id,
                        index=index,
                        kind=WireKind.CLASSICAL,
                        label=label,
                        metadata={"bundle_size": len(bits)},
                    )
                )
                for bit_index, bit in enumerate(bits):
                    classical_targets[bit] = (wire_id, f"{label}[{bit_index}]")
                    mapped_bits.add(bit)

        unmapped_bits = [bit for bit in clbits if bit not in mapped_bits]
        if unmapped_bits:
            wire_id = f"c{len(classical_wires)}"
            classical_wires.append(
                WireIR(
                    id=wire_id,
                    index=len(classical_wires),
                    kind=WireKind.CLASSICAL,
                    label="c",
                    metadata={"bundle_size": len(unmapped_bits)},
                )
            )
            for bit_index, bit in enumerate(unmapped_bits):
                classical_targets[bit] = (wire_id, f"c[{bit_index}]")
        elif not classical_wires:
            classical_wires.append(
                WireIR(
                    id="c0",
                    index=0,
                    kind=WireKind.CLASSICAL,
                    label="c",
                    metadata={"bundle_size": len(clbits)},
                )
            )
            for bit_index, bit in enumerate(clbits):
                classical_targets[bit] = ("c0", f"c[{bit_index}]")

        return classical_wires, classical_targets
