"""Configurable QAOA PennyLane example for quantum-circuit-drawer."""

from __future__ import annotations

from pennylane.measurements import probs
from pennylane.ops import RX, Hadamard, IsingZZ
from pennylane.tape import QuantumTape

try:
    from examples._families import build_cycle_edges, build_qaoa_layers
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import build_cycle_edges, build_qaoa_layers
    from _shared import ExampleRequest, run_example


def build_tape(request: ExampleRequest) -> QuantumTape:
    """Build a ring-QAOA PennyLane tape."""

    edges = build_cycle_edges(request.qubits)

    with QuantumTape() as tape:
        for wire in range(request.qubits):
            Hadamard(wires=wire)

        for layer in build_qaoa_layers(layers=request.columns):
            for left, right in edges:
                IsingZZ(layer.gamma, wires=[left, right])
            for wire in range(request.qubits):
                RX(2.0 * layer.beta, wires=wire)

        for wire in range(request.qubits):
            probs(wires=[wire])
    return tape


def main() -> None:
    run_example(
        build_tape,
        description="Render a configurable QAOA MaxCut tape in PennyLane.",
        framework="pennylane",
        saved_label="PennyLane QAOA demo",
        default_qubits=8,
        default_columns=6,
        columns_help="QAOA layers to generate",
    )


if __name__ == "__main__":
    main()
