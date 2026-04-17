"""Configurable QAOA Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from math import pi

from cirq.circuits import Circuit, Moment
from cirq.devices import LineQubit
from cirq.ops import H, ZZPowGate, measure, rx

try:
    from examples._families import QaoaLayerSpec, build_cycle_edges, build_qaoa_layers
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import QaoaLayerSpec, build_cycle_edges, build_qaoa_layers
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> Circuit:
    """Build a ring-QAOA Cirq circuit."""

    qubits = LineQubit.range(request.qubits)
    moments: list[Moment] = [Moment(H(qubit) for qubit in qubits)]
    edges = build_cycle_edges(request.qubits)

    for layer in build_qaoa_layers(layers=request.columns):
        moments.extend(_cost_moments(qubits, edges, layer))
        moments.append(Moment(rx(2.0 * layer.beta)(qubit) for qubit in qubits))

    moments.append(Moment(measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits)))
    return Circuit(*moments)


def _cost_moments(
    qubits: list[LineQubit],
    edges: tuple[tuple[int, int], ...],
    layer: QaoaLayerSpec,
) -> list[Moment]:
    even_edges = edges[::2]
    odd_edges = edges[1::2]
    moments: list[Moment] = []
    if even_edges:
        moments.append(
            Moment(
                ZZPowGate(exponent=layer.gamma / pi)(qubits[left], qubits[right])
                for left, right in even_edges
            )
        )
    if odd_edges:
        moments.append(
            Moment(
                ZZPowGate(exponent=layer.gamma / pi)(qubits[left], qubits[right])
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
