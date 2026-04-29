"""Configurable QAOA Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from math import pi
from pathlib import Path

from cirq.circuits import Circuit, Moment
from cirq.devices import LineQubit
from cirq.ops import H, ZZPowGate, measure, rx

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402

DEFAULT_FIGSIZE: tuple[float, float] = (10.1, 5.5)


def build_circuit(*, qubit_count: int, layer_count: int) -> Circuit:
    """Build a ring-QAOA Cirq circuit."""

    qubits = LineQubit.range(qubit_count)
    moments: list[Moment] = [Moment(H(qubit) for qubit in qubits)]
    edges = _build_cycle_edges(qubit_count)

    for gamma, beta in _build_qaoa_layers(layer_count):
        even_edges = edges[::2]
        odd_edges = edges[1::2]
        if even_edges:
            moments.append(
                Moment(
                    ZZPowGate(exponent=gamma / pi)(qubits[left], qubits[right])
                    for left, right in even_edges
                )
            )
        if odd_edges:
            moments.append(
                Moment(
                    ZZPowGate(exponent=gamma / pi)(qubits[left], qubits[right])
                    for left, right in odd_edges
                )
            )
        moments.append(Moment(rx(2.0 * beta)(qubit) for qubit in qubits))

    moments.append(Moment(measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits)))
    return Circuit(*moments)


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
    """Render a structured QAOA circuit in Cirq."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, layer_count=args.layers),
            config=DrawConfig(
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_FIGSIZE,
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved cirq-qaoa to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a structured QAOA / MaxCut circuit in Cirq.")
    parser.add_argument("--qubits", type=int, default=8, help="Number of qubits in the QAOA ring.")
    parser.add_argument("--layers", type=int, default=6, help="How many QAOA layers to apply.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
