"""Qiskit showcase centered on managed 2D exploration controls."""

from __future__ import annotations

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit import Instruction

try:
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> QuantumCircuit:
    """Build a Qiskit circuit tailored for managed 2D exploration workflows."""

    left = QuantumRegister(2, "left")
    ancillas = AncillaRegister(2, "anc")
    right = QuantumRegister(_right_register_size(request), "right")
    classical = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(left, ancillas, right, classical, name="qiskit_2d_exploration")

    prep_block = _prep_instruction()
    relay_block = _relay_instruction()

    focus_wire = right[1]
    edge_wire = right[-1]
    for step in range(_motif_count(request)):
        phase = 0.17 * float(step + 1)
        circuit.append(prep_block, [left[0], focus_wire, ancillas[0]])
        circuit.rzz(phase, focus_wire, edge_wire)
        circuit.rz(phase / 2.0, edge_wire)
        circuit.append(relay_block, [left[0], ancillas[0], focus_wire, edge_wire])
        if step % 2 == 0:
            circuit.cx(focus_wire, edge_wire)
        else:
            circuit.cz(left[1], edge_wire)
        circuit.barrier(left[0], left[1], ancillas[0], focus_wire, edge_wire)

    circuit.measure(left[0], classical[0])
    circuit.measure(focus_wire, classical[1])
    circuit.measure(edge_wire, classical[2])
    return circuit


def _right_register_size(request: ExampleRequest) -> int:
    return max(6, request.qubits - 2)


def _motif_count(request: ExampleRequest) -> int:
    return max(4, min(request.columns, 10))


def _prep_instruction() -> Instruction:
    block = QuantumCircuit(3, name="Prep")
    block.h(0)
    block.cx(0, 1)
    block.x(2)
    block.cz(2, 1)
    return block.to_instruction(label="Prep")


def _relay_instruction() -> Instruction:
    block = QuantumCircuit(4, name="Relay")
    block.ry(0.45, 0)
    block.cx(0, 2)
    block.crz(0.35, 1, 2)
    block.swap(2, 3)
    return block.to_instruction(label="Relay")


def main() -> None:
    """Run the 2D exploration showcase as a normal user-facing script."""

    run_example(
        build_circuit,
        description=(
            "Render a Qiskit workflow designed for managed 2D exploration, including "
            "wire filtering, topology-aware hover details, ancilla toggles, and contextual "
            "block controls."
        ),
        framework="qiskit",
        saved_label="qiskit-2d-exploration-showcase",
        default_qubits=18,
        default_columns=9,
        columns_help="Repeated composite motifs to place across the exploration showcase",
        default_topology="grid",
    )


if __name__ == "__main__":
    main()
