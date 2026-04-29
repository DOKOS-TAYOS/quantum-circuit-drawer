"""Compare compact and expanded composite rendering for one Qiskit workflow."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.synthesis.qft import synth_qft_full

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
    CircuitRenderOptions,
    DrawSideConfig,
    OutputOptions,
    compare_circuits,
)

DEFAULT_COMPARE_FIGSIZE: tuple[float, float] = (10.3, 5.5)


def build_workflow_circuit() -> QuantumCircuit:
    """Build a Qiskit circuit with a reusable composite block."""

    circuit = QuantumCircuit(4, 4, name="composite_modes_source")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.append(synth_qft_full(3).to_instruction(label="QFT3"), [0, 1, 2])
    circuit.cz(2, 3)
    circuit.measure(range(4), range(4))
    return circuit


def build_config(*, output: Path | None, show: bool) -> CircuitCompareConfig:
    """Build the compare config used by this demo."""

    return CircuitCompareConfig(
        shared=DrawSideConfig(
            appearance=CircuitAppearanceOptions(
                hover=True,
            )
        ),
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
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_COMPARE_FIGSIZE),
    )


def main() -> None:
    """Compare compact and expanded composite handling in Qiskit."""

    output_path, show = _parse_args()
    circuit = build_workflow_circuit()
    result = None
    try:
        result = compare_circuits(
            circuit,
            circuit,
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved compare-circuits-composite-modes to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(
        description="Compare compact and expanded composite handling in Qiskit."
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
