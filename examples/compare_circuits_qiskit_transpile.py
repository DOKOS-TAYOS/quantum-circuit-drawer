"""Compare a Qiskit circuit before and after transpilation."""

from __future__ import annotations

from qiskit import QuantumCircuit, transpile

try:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        parse_compare_example_args,
    )
except ImportError:
    from _compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        parse_compare_example_args,
    )

from quantum_circuit_drawer import CircuitCompareConfig, compare_circuits


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
            left_title="Original",
            right_title="Transpiled",
            show=False,
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

    request = parse_compare_example_args(
        description="Compare a Qiskit circuit before and after transpilation.",
    )
    payload = build_demo(request)
    base_config = payload.config
    config = CircuitCompareConfig(
        left_title=request.left_label or base_config.left_title,
        right_title=request.right_label or base_config.right_title,
        highlight_differences=(
            base_config.highlight_differences
            if request.highlight_differences is None
            else request.highlight_differences
        ),
        show_summary=base_config.show_summary
        if request.show_summary is None
        else request.show_summary,
        show=request.show,
        output_path=request.output,
        figsize=request.figsize,
    )
    result = compare_circuits(
        payload.left_data,
        payload.right_data,
        config=config,
    )
    if hasattr(result.figure, "set_label"):
        result.figure.set_label("compare-circuits-qiskit-transpile")
    if request.output is not None:
        print(f"Saved compare-circuits-qiskit-transpile to {request.output}")


if __name__ == "__main__":
    main()
