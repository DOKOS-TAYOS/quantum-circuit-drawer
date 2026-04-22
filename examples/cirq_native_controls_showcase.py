"""Showcase Cirq example focused on native controls and structure."""

from __future__ import annotations

from cirq.circuits import Circuit, CircuitOperation, FrozenCircuit, Moment
from cirq.devices import LineQubit
from cirq.ops import CNOT, H, X, Z, measure, rx

try:
    from examples._shared import ExampleRequest, build_draw_config, parse_example_args
except ImportError:
    from _shared import ExampleRequest, build_draw_config, parse_example_args

from quantum_circuit_drawer import draw_quantum_circuit


def build_circuit(request: ExampleRequest) -> Circuit:
    """Build a Cirq circuit that highlights native controls and provenance."""

    qubit_count = max(4, request.qubits)
    qubits = LineQubit.range(qubit_count)
    moments: list[Moment] = [
        Moment(H(qubits[0]), H(qubits[1]), rx(0.35)(qubits[2])),
        Moment(X(qubits[2]).controlled_by(qubits[0], control_values=[0])),
        Moment(Z(qubits[3]).controlled_by(qubits[0], qubits[1], control_values=[0, 1])),
        Moment(measure(qubits[0], key="m")),
        Moment(X(qubits[1]).with_classical_controls("m")),
        Moment(_build_circuit_operation(qubits[2], qubits[3])),
    ]

    for step in range(_motif_count(request)):
        target = 2 + (step % max(1, qubit_count - 2))
        moments.append(Moment(rx(0.18 * float(step + 1))(qubits[target])))

    moments.append(Moment(measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits)))
    return Circuit(*moments)


def _build_circuit_operation(control: LineQubit, target: LineQubit) -> CircuitOperation:
    nested = FrozenCircuit(H(control), CNOT(control, target))
    return CircuitOperation(nested)


def _motif_count(request: ExampleRequest) -> int:
    return max(1, min(request.columns, 5))


def main() -> None:
    request = parse_example_args(
        description="Render a Cirq showcase with open controls, classical control, and CircuitOperation provenance.",
        default_qubits=4,
        default_columns=3,
        columns_help="Additional native-control motifs to append after the structural showcase",
    )
    draw_quantum_circuit(
        build_circuit(request),
        config=build_draw_config(request, framework="cirq"),
    )
    if request.output is not None:
        print(f"Saved cirq-native-controls-showcase to {request.output}")


if __name__ == "__main__":
    main()
