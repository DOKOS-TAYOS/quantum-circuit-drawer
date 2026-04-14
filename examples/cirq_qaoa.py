"""Configurable QAOA Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from math import pi

import cirq

try:
    from examples._families import QaoaLayerSpec, build_cycle_edges, build_qaoa_layers
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import QaoaLayerSpec, build_cycle_edges, build_qaoa_layers
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> cirq.Circuit:
    """Build a ring-QAOA Cirq circuit."""

    qubits = cirq.LineQubit.range(request.qubits)
    moments: list[cirq.Moment] = [cirq.Moment(cirq.H(qubit) for qubit in qubits)]
    edges = build_cycle_edges(request.qubits)

    for layer in build_qaoa_layers(layers=request.columns):
        moments.extend(_cost_moments(qubits, edges, layer))
        moments.append(cirq.Moment(cirq.rx(2.0 * layer.beta)(qubit) for qubit in qubits))

    moments.append(
        cirq.Moment(cirq.measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits))
    )
    return cirq.Circuit(*moments)


def _cost_moments(
    qubits: list[cirq.LineQubit],
    edges: tuple[tuple[int, int], ...],
    layer: QaoaLayerSpec,
) -> list[cirq.Moment]:
    even_edges = edges[::2]
    odd_edges = edges[1::2]
    moments: list[cirq.Moment] = []
    if even_edges:
        moments.append(
            cirq.Moment(
                cirq.ZZPowGate(exponent=layer.gamma / pi)(qubits[left], qubits[right])
                for left, right in even_edges
            )
        )
    if odd_edges:
        moments.append(
            cirq.Moment(
                cirq.ZZPowGate(exponent=layer.gamma / pi)(qubits[left], qubits[right])
                for left, right in odd_edges
            )
        )
    return moments


def main() -> None:
    run_example(
        build_circuit,
        description="Render a configurable QAOA MaxCut circuit in Cirq.",
        framework="cirq",
        saved_label="Cirq QAOA demo",
        default_qubits=8,
        default_columns=6,
        columns_help="QAOA layers to generate",
    )


if __name__ == "__main__":
    main()
