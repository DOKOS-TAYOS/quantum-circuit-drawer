"""Show HardwareTopology.from_qiskit_backend with a topology-aware 3D render."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitAppearanceOptions,
    CircuitBuilder,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    HardwareTopology,
    OutputOptions,
    draw_quantum_circuit,
)

DEFAULT_FIGSIZE: tuple[float, float] = (11.3, 5.8)


@dataclass(frozen=True, slots=True)
class DemoBackend:
    """Small Qiskit-backend-like object for the public topology helper."""

    name: str
    num_qubits: int
    coupling_map: tuple[tuple[int, int], ...]


def build_circuit(*, qubit_count: int, motif_count: int) -> object:
    """Build a circuit that is easy to read on a backend-derived topology."""

    builder = CircuitBuilder(qubit_count, qubit_count, name="qiskit_backend_topology")
    builder.h(0)
    for index in range(qubit_count - 1):
        builder.cx(index, index + 1)
    for step in range(motif_count):
        target = step % qubit_count
        partner = (target + 2) % qubit_count
        remote = (target + 3) % qubit_count
        phase = 0.2 * float(step + 1)
        builder.rz(phase, target)
        builder.rzz(phase + 0.11, target, partner)
        builder.cz(target, remote)
    builder.measure_all()
    return builder.build()


def build_backend(qubit_count: int) -> DemoBackend:
    """Build a lightweight BackendV1/BackendV2-like object."""

    return DemoBackend(
        name="demo_qiskit_backend",
        num_qubits=qubit_count,
        coupling_map=tuple((index, index + 1) for index in range(qubit_count - 1)),
    )


def main() -> None:
    """Render a backend-derived topology in 3D."""

    args = _parse_args()
    topology = HardwareTopology.from_qiskit_backend(build_backend(args.qubits))
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, motif_count=args.motifs),
            config=DrawConfig(
                side=DrawSideConfig(
                    render=CircuitRenderOptions(
                        view="3d",
                        mode=DrawMode.PAGES,
                        topology=topology,
                        topology_qubits="all",
                        direct=False,
                    ),
                    appearance=CircuitAppearanceOptions(hover=True),
                ),
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_FIGSIZE,
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved qiskit-backend-topology-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a circuit on a backend-derived 3D topology.")
    parser.add_argument(
        "--qubits", type=int, default=6, help="Number of qubits in the topology and circuit."
    )
    parser.add_argument(
        "--motifs",
        type=int,
        default=3,
        help="Extra long-range motifs to append before the measurements.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
