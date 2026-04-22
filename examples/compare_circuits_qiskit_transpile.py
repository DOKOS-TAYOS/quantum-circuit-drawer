"""Compare a Qiskit circuit before and after transpilation."""

from __future__ import annotations

from qiskit import QuantumCircuit, transpile

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
    OutputOptions,
)


def build_demo(request: CompareExampleRequest) -> CompareDemoPayload:
    """Build a compare payload for an original and transpiled Qiskit circuit."""

    del request
    original_circuit = build_source_circuit()
    transpiled_circuit = transpile(
        original_circuit,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=2,
        seed_transpiler=7,
    )
    return CompareDemoPayload(
        compare_kind="circuits",
        left_data=original_circuit,
        right_data=transpiled_circuit,
        config=CircuitCompareConfig(
            compare=CircuitCompareOptions(
                left_title="Original",
                right_title="Transpiled",
            ),
            output=OutputOptions(show=False),
        ),
    )


def build_source_circuit() -> QuantumCircuit:
    """Build a small workflow-style Qiskit circuit before transpilation."""

    circuit = QuantumCircuit(3, 3, name="workflow_source")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.rzz(0.35, 1, 2)
    circuit.ry(0.42, 2)
    circuit.cx(2, 0)
    circuit.barrier()
    circuit.measure(range(3), range(3))
    return circuit


def main() -> None:
    """Run the transpilation compare demo as a normal user-facing script."""

    run_compare_example(
        build_demo,
        description="Compare a Qiskit circuit before and after transpilation.",
        saved_label="compare-circuits-qiskit-transpile",
    )


if __name__ == "__main__":
    main()
