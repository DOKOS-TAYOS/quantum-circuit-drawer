"""Cirq-result histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from cirq.circuits import Circuit
from cirq.devices import LineQubit
from cirq.ops import CNOT, H, measure
from cirq.sim import Simulator

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

from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramStateLabelMode,
    HistogramViewOptions,
    OutputOptions,
)


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a histogram directly from a Cirq measurement result."""

    del request
    q0, q1, q2 = LineQubit.range(3)
    circuit = Circuit(
        H(q0),
        CNOT(q0, q1),
        H(q2),
        measure(q0, q1, key="alpha"),
        measure(q2, key="beta"),
    )
    result = Simulator(seed=11).run(circuit, repetitions=384)
    return HistogramDemoPayload(
        data=result,
        config=HistogramConfig(
            view=HistogramViewOptions(state_label_mode=HistogramStateLabelMode.DECIMAL),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the Cirq-result histogram demo."""

    run_histogram_example(
        build_demo,
        description=(
            "Render a histogram directly from a Cirq Result with two measurement registers."
        ),
        saved_label="histogram-cirq-result",
    )


if __name__ == "__main__":
    main()
