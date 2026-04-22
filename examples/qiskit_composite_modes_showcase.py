"""Qiskit showcase centered on compact versus expanded composites."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT

try:
    from examples._shared import (
        ExampleRequest,
        build_draw_config,
        parse_example_args,
    )
except ImportError:
    from _shared import ExampleRequest, build_draw_config, parse_example_args

from quantum_circuit_drawer import draw_quantum_circuit


def build_circuit(request: ExampleRequest) -> QuantumCircuit:
    """Build a Qiskit circuit with a reusable composite block."""

    qubit_count = max(4, request.qubits)
    circuit = QuantumCircuit(qubit_count, qubit_count, name="qiskit_composite_modes_showcase")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.append(QFT(min(3, qubit_count)).to_instruction(label="QFT"), range(min(3, qubit_count)))
    for step in range(_motif_count(request, qubit_count)):
        target = 1 + (step % max(1, qubit_count - 1))
        circuit.ry(0.14 * float(step + 1), target)
    circuit.cz(qubit_count - 2, qubit_count - 1)
    circuit.measure(range(qubit_count), range(qubit_count))
    return circuit


def _motif_count(request: ExampleRequest, qubit_count: int) -> int:
    return max(1, min(request.columns, qubit_count + 1))


def main() -> None:
    """Run the composite-modes showcase as a normal user-facing script."""

    request = parse_example_args(
        description=(
            "Render a Qiskit workflow that is useful for comparing compact and expanded "
            "composite instruction handling."
        ),
        default_qubits=5,
        default_columns=4,
        columns_help="Extra rotation motifs to append after the composite block",
    )
    result = draw_quantum_circuit(
        build_circuit(request),
        config=build_draw_config(request, framework="qiskit"),
    )
    if hasattr(result.primary_figure, "set_label"):
        result.primary_figure.set_label("qiskit-composite-modes-showcase")
    if request.output is not None:
        print(f"Saved qiskit-composite-modes-showcase to {request.output}")


if __name__ == "__main__":
    main()
