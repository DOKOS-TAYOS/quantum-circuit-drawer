"""PennyLane tape example for quantum-circuit-drawer."""

from __future__ import annotations

from pathlib import Path

import pennylane as qml

from quantum_circuit_drawer import draw_quantum_circuit


def build_tape() -> object:
    with qml.tape.QuantumTape() as tape:
        qml.Hadamard(wires=0)
        qml.CNOT(wires=[0, 1])
        qml.RY(0.432, wires=1)
        qml.SWAP(wires=[0, 2])
        qml.probs(wires=[1])
    return tape


def main() -> None:
    tape = build_tape()
    output = Path("examples/output/pennylane_circuit.png")

    draw_quantum_circuit(
        tape,
        framework="pennylane",
        style={"theme": "paper", "show_params": True, "wire_spacing": 1.35},
        output=output,
    )
    print(f"Saved PennyLane example to {output}")


if __name__ == "__main__":
    main()
