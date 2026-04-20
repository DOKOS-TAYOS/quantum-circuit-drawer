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

from quantum_circuit_drawer import HistogramConfig, HistogramSort


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a Qiskit result payload reduced to a joint marginal."""

    del request
    circuit = QuantumCircuit(5)
    circuit.ry(1.18, 0)
    circuit.ry(0.92, 2)
    circuit.h(4)
    circuit.cx(0, 1)
    circuit.cx(2, 3)
    circuit.measure_all()
    result = StatevectorSampler().run([circuit], shots=512).result()
    return HistogramDemoPayload(
        data=result,
        config=HistogramConfig(
            qubits=(4, 2, 0),
            sort=HistogramSort.STATE,
            show=False,
        ),
    )


def main() -> None:
    """Run the Qiskit marginal histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a Qiskit joint marginal histogram demo.",
        saved_label="histogram-marginal",
    )


if __name__ == "__main__":
    main()
