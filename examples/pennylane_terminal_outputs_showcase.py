"""Showcase PennyLane example focused on terminal-output boxes."""

from __future__ import annotations

from pennylane import cond, measure
from pennylane.measurements import counts, density_matrix, expval, probs
from pennylane.ops import CNOT, RX, RY, Hadamard, PauliZ
from pennylane.tape import QuantumTape

try:
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _shared import ExampleRequest, run_example


def build_tape(request: ExampleRequest) -> QuantumTape:
    """Build a PennyLane tape that highlights mid-measure and terminal outputs."""

    qubit_count = max(3, request.qubits)

    with QuantumTape() as tape:
        Hadamard(wires=0)
        CNOT(wires=[0, 1])
        RX(0.25, wires=2)

        measured_bit = measure(0)
        cond(measured_bit, RX)(0.45, wires=1)

        for step in range(_motif_count(request)):
            target_wire = 2 + (step % max(1, qubit_count - 2))
            RY(0.16 * float(step + 1), wires=target_wire)

        probs(wires=[0, 1])
        counts(wires=[0, 1])
        expval(PauliZ(wires=min(2, qubit_count - 1)))
        density_matrix(wires=[qubit_count - 2, qubit_count - 1])
    return tape


def _motif_count(request: ExampleRequest) -> int:
    return max(1, min(request.columns, 4))


def main() -> None:
    run_example(
        build_tape,
        description="Render a PennyLane showcase with mid-measurement and terminal-output boxes.",
        framework="pennylane",
        saved_label="PennyLane terminal outputs showcase",
        default_qubits=4,
        default_columns=3,
        columns_help="Extra rotation motifs to append before the terminal outputs",
    )


if __name__ == "__main__":
    main()
