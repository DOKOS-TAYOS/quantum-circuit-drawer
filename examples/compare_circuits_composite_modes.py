"""Compare compact and expanded composite rendering for one Qiskit workflow."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT

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

from quantum_circuit_drawer import CircuitCompareConfig, DrawConfig, compare_circuits


def build_demo(request: CompareExampleRequest) -> CompareDemoPayload:
    """Build a compare payload for compact and expanded composite rendering."""

    del request
    circuit = build_workflow_circuit()
    return CompareDemoPayload(
        compare_kind="circuits",
        left_data=circuit,
        right_data=circuit,
        config=CircuitCompareConfig(
            left_title="Compact composites",
            right_title="Expanded composites",
            show=False,
        ),
        left_config=DrawConfig(framework="qiskit", show=False, composite_mode="compact"),
        right_config=DrawConfig(framework="qiskit", show=False, composite_mode="expand"),
    )


def build_workflow_circuit() -> QuantumCircuit:
    """Build a Qiskit circuit with a reusable composite block."""

    circuit = QuantumCircuit(4, 4, name="composite_modes_source")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.append(QFT(3).decompose(reps=1).to_instruction(label="QFT3"), [0, 1, 2])
    circuit.cz(2, 3)
    circuit.measure(range(4), range(4))
    return circuit


def main() -> None:
    """Run the composite-modes compare demo as a normal user-facing script."""

    request = parse_compare_example_args(
        description="Compare compact and expanded composite handling in Qiskit.",
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
        left_config=payload.left_config,
        right_config=payload.right_config,
        config=config,
    )
    if hasattr(result.figure, "set_label"):
        result.figure.set_label("compare-circuits-composite-modes")
    if request.output is not None:
        print(f"Saved compare-circuits-composite-modes to {request.output}")


if __name__ == "__main__":
    main()
