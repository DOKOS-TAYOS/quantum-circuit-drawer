"""PennyLane-probability histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

import pennylane as qml

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
    """Build a histogram from a PennyLane probability vector."""

    del request
    device = qml.device("default.qubit", wires=4)

    @qml.qnode(device)
    def probability_demo() -> object:
        qml.Hadamard(wires=0)
        qml.CNOT(wires=[0, 1])
        qml.RY(0.43, wires=2)
        qml.CNOT(wires=[2, 3])
        return qml.probs(wires=[0, 1, 2, 3])

    return HistogramDemoPayload(
        data=probability_demo(),
        config=HistogramConfig(
            sort=HistogramSort.VALUE_DESC,
            show_uniform_reference=True,
            show=False,
        ),
    )


def main() -> None:
    """Run the PennyLane-probability histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a histogram from a PennyLane qml.probs() result vector.",
        saved_label="histogram-pennylane-probs",
    )


if __name__ == "__main__":
    main()
