"""Configurable QAOA Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

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

DEFAULT_FIGSIZE: tuple[float, float] = (10.6, 5.8)
DEFAULT_3D_PAGES_CONTROLS_FIGSIZE: tuple[float, float] = (10.6, 4.8)


def build_circuit(
    request: object | None = None,
    *,
    qubit_count: int | None = None,
    layer_count: int | None = None,
) -> QuantumCircuit:
    """Build a ring-QAOA Qiskit circuit."""

    if request is not None:
        if qubit_count is None:
            qubit_count = int(getattr(request, "qubits"))
        if layer_count is None:
            layer_count = int(getattr(request, "columns"))
    if qubit_count is None or layer_count is None:
        raise TypeError("build_circuit() needs qubit_count and layer_count.")

    quantum = QuantumRegister(qubit_count, "q")
    classical = ClassicalRegister(qubit_count, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_qaoa_demo")

    for wire in range(qubit_count):
        circuit.h(wire)

    edges = _build_cycle_edges(qubit_count)
    for gamma, beta in _build_qaoa_layers(layer_count):
        for left, right in edges:
            circuit.rzz(gamma, left, right)
        for wire in range(qubit_count):
            circuit.rx(2.0 * beta, wire)

    for wire in range(qubit_count):
        circuit.measure(wire, classical[wire])
    return circuit


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
    """Render a structured QAOA circuit in Qiskit."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, layer_count=args.layers),
            config=DrawConfig(
                side=DrawSideConfig(
                    render=CircuitRenderOptions(
                        view=args.view,
                        mode=DrawMode(args.mode),
                        topology=args.topology,
                        topology_menu=args.view == "3d"
                        and args.mode in {"pages_controls", "slider"},
                        direct=args.view != "3d",
                    ),
                    appearance=CircuitAppearanceOptions(hover=True),
                ),
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=_resolve_figsize(view=args.view, mode=args.mode),
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved qiskit-qaoa to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a structured QAOA / MaxCut circuit in Qiskit.")
    parser.add_argument("--qubits", type=int, default=8, help="Number of qubits in the QAOA ring.")
    parser.add_argument("--layers", type=int, default=6, help="How many QAOA layers to apply.")
    parser.add_argument(
        "--view", choices=("2d", "3d"), default="2d", help="Render the circuit in 2D or 3D."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "pages", "pages_controls", "slider", "full"),
        default="auto",
        help="Draw mode to use for the rendered circuit.",
    )
    parser.add_argument(
        "--topology",
        choices=("line", "grid", "star", "star_tree", "honeycomb"),
        default="line",
        help="Topology used by the 3D view or topology-aware hover details.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


def _resolve_figsize(*, view: str, mode: str) -> tuple[float, float]:
    if view == "3d" and mode == "pages_controls":
        return DEFAULT_3D_PAGES_CONTROLS_FIGSIZE
    return DEFAULT_FIGSIZE


if __name__ == "__main__":
    main()
