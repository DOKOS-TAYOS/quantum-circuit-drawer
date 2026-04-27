"""Compare one Qiskit circuit against several transpilation levels."""

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
    CircuitAppearanceOptions,
    CircuitCompareConfig,
    CircuitCompareOptions,
    DrawSideConfig,
    OutputOptions,
)


def build_demo(request: CompareExampleRequest) -> CompareDemoPayload:
    """Build a multi-circuit comparison across Qiskit optimization levels."""

    del request
    source = build_source_circuit()
    level_0 = transpile(
        source,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=0,
        seed_transpiler=13,
    )
    level_1 = transpile(
        source,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=1,
        seed_transpiler=13,
    )
    level_3 = transpile(
        source,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=3,
        seed_transpiler=13,
    )
    return CompareDemoPayload(
        compare_kind="circuits",
        left_data=source,
        right_data=level_0,
        extra_data=(level_1, level_3),
        config=CircuitCompareConfig(
            shared=DrawSideConfig(
                appearance=CircuitAppearanceOptions(
                    hover=True,
                )
            ),
            compare=CircuitCompareOptions(
                left_title="Source",
                right_title="Opt level 0",
                titles=("Source", "Opt level 0", "Opt level 1", "Opt level 3"),
            ),
            output=OutputOptions(show=False),
        ),
    )


def build_source_circuit() -> QuantumCircuit:
    """Build a compact Qiskit workflow that gives the transpiler useful work."""

    circuit = QuantumCircuit(4, 4, name="multi_transpile_source")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.rzz(0.31, 1, 2)
    circuit.ry(0.42, 2)
    circuit.cz(2, 3)
    circuit.rxx(0.27, 0, 3)
    circuit.barrier()
    circuit.measure(range(4), range(4))
    return circuit


def main() -> None:
    """Run the multi-transpilation compare demo as a normal script."""

    run_compare_example(
        build_demo,
        description="Compare a Qiskit source circuit and several transpilation levels.",
        saved_label="compare-circuits-multi-transpile",
    )


if __name__ == "__main__":
    main()
