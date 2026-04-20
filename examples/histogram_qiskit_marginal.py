"""Qiskit marginal histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

try:
    from examples._histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        run_histogram_example,
    )
except ImportError:
    from _histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        run_histogram_example,
    )

from quantum_circuit_drawer import HistogramConfig


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a Qiskit result payload reduced to a joint marginal."""

    del request
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.x(2)
    circuit.measure_all()
    result = StatevectorSampler().run([circuit], shots=256).result()
    return HistogramDemoPayload(
        data=result,
        config=HistogramConfig(qubits=(2, 0), show=False),
    )


def main() -> None:
    """Run the Qiskit marginal histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a Qiskit joint marginal histogram demo.",
        saved_label="histogram-qiskit-marginal",
    )


if __name__ == "__main__":
    main()
