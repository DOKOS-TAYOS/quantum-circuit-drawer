"""Compare a Qiskit circuit before and after transpilation."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from qiskit import QuantumCircuit, transpile

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitAppearanceOptions,
    CircuitCompareConfig,
    CircuitCompareOptions,
    DrawSideConfig,
    OutputOptions,
    compare_circuits,
)

DEFAULT_COMPARE_FIGSIZE: tuple[float, float] = (8.6, 4.6)


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


def build_config(*, output: Path | None, show: bool) -> CircuitCompareConfig:
    """Build the compare config used by this demo."""

    return CircuitCompareConfig(
        shared=DrawSideConfig(
            appearance=CircuitAppearanceOptions(
                hover=True,
            )
        ),
        compare=CircuitCompareOptions(
            left_title="Original",
            right_title="Transpiled",
        ),
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_COMPARE_FIGSIZE),
    )


def main() -> None:
    """Compare a source circuit against its transpiled variant."""

    output_path, show = _parse_args()
    source_circuit = build_source_circuit()
    transpiled_circuit = transpile(
        source_circuit,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=2,
        seed_transpiler=7,
    )
    result = None
    try:
        result = compare_circuits(
            source_circuit,
            transpiled_circuit,
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved compare-circuits-qiskit-transpile to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Compare a Qiskit circuit before and after transpilation.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
