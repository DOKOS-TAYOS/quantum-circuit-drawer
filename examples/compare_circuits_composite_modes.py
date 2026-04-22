"""Compare compact and expanded composite rendering for one Qiskit workflow."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.synthesis.qft import synth_qft_full

try:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        run_compare_example,
    )
except ImportError:
    from _compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        run_compare_example,
    )

from quantum_circuit_drawer import (
    CircuitCompareConfig,
    CircuitCompareOptions,
    CircuitRenderOptions,
    OutputOptions,
)


def build_demo(request: CompareExampleRequest) -> CompareDemoPayload:
    """Build a compare payload for compact and expanded composite rendering."""

    del request
    circuit = build_workflow_circuit()
    return CompareDemoPayload(
        compare_kind="circuits",
        left_data=circuit,
        right_data=circuit,
        config=CircuitCompareConfig(
            left_render=CircuitRenderOptions(
                framework="qiskit",
                composite_mode="compact",
            ),
            right_render=CircuitRenderOptions(
                framework="qiskit",
                composite_mode="expand",
            ),
            compare=CircuitCompareOptions(
                left_title="Compact composites",
                right_title="Expanded composites",
            ),
            output=OutputOptions(show=False),
        ),
    )


def build_workflow_circuit() -> QuantumCircuit:
    """Build a Qiskit circuit with a reusable composite block."""

    circuit = QuantumCircuit(4, 4, name="composite_modes_source")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.append(synth_qft_full(3).to_instruction(label="QFT3"), [0, 1, 2])
    circuit.cz(2, 3)
    circuit.measure(range(4), range(4))
    return circuit


def main() -> None:
    """Run the composite-modes compare demo as a normal user-facing script."""

    run_compare_example(
        build_demo,
        description="Compare compact and expanded composite handling in Qiskit.",
        saved_label="compare-circuits-composite-modes",
    )


if __name__ == "__main__":
    main()
