"""Qiskit showcase centered on managed 3D exploration controls."""

from __future__ import annotations

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit import Instruction

try:
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> QuantumCircuit:
    """Build a Qiskit circuit tailored for managed 3D exploration workflows."""

    source = QuantumRegister(2, "src")
    ancillas = AncillaRegister(2, "anc")
    target = QuantumRegister(_target_register_size(request), "dst")
    classical = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(source, ancillas, target, classical, name="qiskit_3d_exploration")

    prep_block = _prep_instruction()
    relay_block = _relay_instruction()

    focus_wire = target[1]
    edge_wire = target[-1]
    for step in range(_motif_count(request)):
        phase = 0.19 * float(step + 1)
        circuit.append(prep_block, [source[0], focus_wire, ancillas[0]])
        circuit.rzz(phase, focus_wire, edge_wire)
        circuit.append(relay_block, [source[0], ancillas[0], focus_wire, edge_wire])
        if step % 2 == 0:
            circuit.cx(focus_wire, edge_wire)
        else:
            circuit.cz(source[1], edge_wire)
        circuit.barrier(source[0], source[1], ancillas[0], focus_wire, edge_wire)

    circuit.measure(source[0], classical[0])
    circuit.measure(focus_wire, classical[1])
    circuit.measure(edge_wire, classical[2])
    return circuit


def _target_register_size(request: ExampleRequest) -> int:
    return max(6, request.qubits - 2)


def _motif_count(request: ExampleRequest) -> int:
    return max(4, min(request.columns, 9))


def _prep_instruction() -> Instruction:
    block = QuantumCircuit(3, name="Prep3D")
    block.h(0)
    block.cx(0, 1)
    block.x(2)
    block.cz(2, 1)
    return block.to_instruction(label="Prep3D")


def _relay_instruction() -> Instruction:
    block = QuantumCircuit(4, name="Relay3D")
    block.ry(0.41, 0)
    block.cx(0, 2)
    block.crz(0.33, 1, 2)
    block.swap(2, 3)
    return block.to_instruction(label="Relay3D")


def main() -> None:
    """Run the 3D exploration showcase as a normal user-facing script."""

    run_example(
        build_circuit,
        description=(
            "Render a Qiskit workflow designed for managed 3D exploration, including "
            "topology-aware hover, controlled interactions, ancilla toggles, and contextual "
            "block controls."
        ),
        framework="qiskit",
        saved_label="qiskit-3d-exploration-showcase",
        default_qubits=25,
        default_columns=6,
        columns_help="Repeated composite motifs to place across the 3D exploration showcase",
        default_mode="pages_controls",
        default_view="3d",
        default_topology="grid",
    )


if __name__ == "__main__":
    main()
