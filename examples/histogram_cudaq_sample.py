"""CUDA-Q-sample histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

import cudaq

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
    """Build a histogram directly from a CUDA-Q sample result."""

    del request
    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(3)
    kernel.h(qubits[0])
    kernel.cx(qubits[0], qubits[1])
    kernel.ry(0.41, qubits[2])
    kernel.mz(qubits)
    result = cudaq.sample(kernel, shots_count=512)
    return HistogramDemoPayload(
        data=result,
        config=HistogramConfig(
            sort=HistogramSort.VALUE_DESC,
            show=False,
        ),
    )


def main() -> None:
    """Run the CUDA-Q-sample histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a histogram directly from a CUDA-Q SampleResult.",
        saved_label="histogram-cudaq-sample",
    )


if __name__ == "__main__":
    main()
