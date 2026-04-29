"""Qiskit showcase centered on managed 3D exploration controls."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit import Instruction

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)


def build_circuit(*, qubit_count: int, motif_count: int) -> QuantumCircuit:
    """Build a Qiskit circuit tailored for managed 3D exploration workflows."""

    total_wires = max(10, qubit_count)
    source = QuantumRegister(2, "src")
    ancillas = AncillaRegister(2, "anc")
    target = QuantumRegister(total_wires - 4, "dst")
    classical = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(source, ancillas, target, classical, name="qiskit_3d_exploration")

    prep_block = _prep_instruction()
    relay_block = _relay_instruction()

    focus_wire = target[1]
    edge_wire = target[-1]
    for step in range(motif_count):
        phase = 0.19 * float(step + 1)
        circuit.append(prep_block, [source[0], focus_wire, ancillas[0]])
        circuit.rzz(phase, focus_wire, edge_wire)
        circuit.append(relay_block, [source[0], ancillas[0], focus_wire, edge_wire])
        if step % 2 == 0:
            circuit.cx(focus_wire, edge_wire)
        else:
            circuit.cz(source[1], edge_wire)
        circuit.barrier(source[0], source[1], ancillas[0], focus_wire, edge_wire)

    circuit.measure(source[0], classical[0])
    circuit.measure(focus_wire, classical[1])
    circuit.measure(edge_wire, classical[2])
    return circuit


def _prep_instruction() -> Instruction:
    block = QuantumCircuit(3, name="Prep3D")
    block.h(0)
    block.cx(0, 1)
    block.x(2)
    block.cz(2, 1)
    return block.to_instruction(label="Prep3D")


def _relay_instruction() -> Instruction:
    block = QuantumCircuit(4, name="Relay3D")
    block.ry(0.41, 0)
    block.cx(0, 2)
    block.crz(0.33, 1, 2)
    block.swap(2, 3)
    return block.to_instruction(label="Relay3D")


def main() -> None:
    """Render a Qiskit workflow designed for managed 3D exploration."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, motif_count=args.motifs),
            config=DrawConfig(
                side=DrawSideConfig(
                    render=CircuitRenderOptions(
                        view="3d",
                        mode=DrawMode(args.mode),
                        topology=args.topology,
                        topology_menu=args.mode in {"pages_controls", "slider"},
                        direct=False,
                    ),
                    appearance=CircuitAppearanceOptions(hover=True),
                ),
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=(11.8, 6.2),
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved qiskit-3d-exploration-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a Qiskit circuit designed for 3D managed exploration."
    )
    parser.add_argument(
        "--qubits",
        type=int,
        default=12,
        help="Approximate total quantum wires to show. Values below 10 use the minimum layout.",
    )
    parser.add_argument(
        "--motifs",
        type=int,
        default=4,
        help="How many composite motifs to place across the showcase circuit.",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "pages", "pages_controls", "slider", "full"),
        default="pages_controls",
        help="Draw mode to use for the rendered circuit.",
    )
    parser.add_argument(
        "--topology",
        choices=("line", "grid", "star", "star_tree", "honeycomb"),
        default="grid",
        help="Topology used by the managed 3D view.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
