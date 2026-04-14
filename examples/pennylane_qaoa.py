"""Configurable QAOA PennyLane example for quantum-circuit-drawer."""

from __future__ import annotations

import pennylane as qml

try:
    from examples._families import build_cycle_edges, build_qaoa_layers
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import build_cycle_edges, build_qaoa_layers
    from _shared import ExampleRequest, run_example


def build_tape(request: ExampleRequest) -> qml.tape.QuantumTape:
    """Build a ring-QAOA PennyLane tape."""

    edges = build_cycle_edges(request.qubits)

    with qml.tape.QuantumTape() as tape:
        for wire in range(request.qubits):
            qml.Hadamard(wires=wire)

        for layer in build_qaoa_layers(layers=request.columns):
            for left, right in edges:
                qml.IsingZZ(layer.gamma, wires=[left, right])
            for wire in range(request.qubits):
                qml.RX(2.0 * layer.beta, wires=wire)

        for wire in range(request.qubits):
            qml.probs(wires=[wire])
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
