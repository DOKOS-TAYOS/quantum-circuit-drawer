"""Configurable QAOA PennyLane example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from pennylane.measurements import probs
from pennylane.ops import RX, Hadamard, IsingZZ
from pennylane.tape import QuantumTape

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402


def build_tape(*, qubit_count: int, layer_count: int) -> QuantumTape:
    """Build a ring-QAOA PennyLane tape."""

    edges = _build_cycle_edges(qubit_count)

    with QuantumTape() as tape:
        for wire in range(qubit_count):
            Hadamard(wires=wire)

        for gamma, beta in _build_qaoa_layers(layer_count):
            for left, right in edges:
                IsingZZ(gamma, wires=[left, right])
            for wire in range(qubit_count):
                RX(2.0 * beta, wires=wire)

        for wire in range(qubit_count):
            probs(wires=[wire])
    return tape


def _build_cycle_edges(qubit_count: int) -> tuple[tuple[int, int], ...]:
    if qubit_count < 2:
        return ()
    if qubit_count == 2:
        return ((0, 1),)
    return tuple((wire, (wire + 1) % qubit_count) for wire in range(qubit_count))


def _build_qaoa_layers(layer_count: int) -> tuple[tuple[float, float], ...]:
    layers: list[tuple[float, float]] = []
    for layer_index in range(layer_count):
        position = (layer_index + 1) / (layer_count + 1)
        gamma = round(0.35 + (0.55 * position), 2)
        beta = round(0.62 - (0.26 * position), 2)
        layers.append((gamma, beta))
    return tuple(layers)


def main() -> None:
    """Render a structured QAOA tape in PennyLane."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_tape(qubit_count=args.qubits, layer_count=args.layers),
            config=DrawConfig(
                output=OutputOptions(output_path=args.output, show=args.show),
            ),
        )
        if args.output is not None:
            print(f"Saved pennylane-qaoa to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a structured QAOA / MaxCut tape in PennyLane.")
    parser.add_argument("--qubits", type=int, default=8, help="Number of wires in the QAOA ring.")
    parser.add_argument("--layers", type=int, default=6, help="How many QAOA layers to apply.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
