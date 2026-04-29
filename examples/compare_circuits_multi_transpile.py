"""Compare one Qiskit circuit against several transpilation levels."""

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

DEFAULT_COMPARE_FIGSIZE: tuple[float, float] = (10.6, 5.8)


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


def build_config(*, output: Path | None, show: bool) -> CircuitCompareConfig:
    """Build the compare config used by this demo."""

    return CircuitCompareConfig(
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
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_COMPARE_FIGSIZE),
    )


def main() -> None:
    """Compare a source circuit and several transpilation levels."""

    output_path, show = _parse_args()
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
    result = None
    try:
        result = compare_circuits(
            source,
            level_0,
            level_1,
            level_3,
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved compare-circuits-multi-transpile to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(
        description="Compare a source circuit and several transpilation levels."
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
