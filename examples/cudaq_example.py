"""CUDA-Q example for quantum-circuit-drawer."""

from __future__ import annotations

from pathlib import Path

import cudaq

from quantum_circuit_drawer import draw_quantum_circuit


@cudaq.kernel
def build_kernel() -> None:
    qubits = cudaq.qvector(3)
    h(qubits[0])
    x.ctrl(qubits[0], qubits[1])
    z.ctrl(qubits[0], qubits[1], qubits[2])
    mz(qubits)


def main() -> None:
    output = Path("examples/output/cudaq_circuit.png")

    draw_quantum_circuit(
        build_kernel,
        style={"theme": "paper", "font_size": 12.5, "show_params": True},
        output=output,
    )
    print(f"Saved CUDA-Q example to {output}")


if __name__ == "__main__":
    main()
