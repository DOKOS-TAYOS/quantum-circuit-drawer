"""Configurable random-looking Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from random import Random

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
    from examples._shared import ExampleRequest, add_render_arguments, request_from_namespace
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result
    from _shared import ExampleRequest, add_render_arguments, request_from_namespace

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    HoverOptions,
    OutputOptions,
    draw_quantum_circuit,
)

DEFAULT_QUBITS = 10
DEFAULT_COLUMNS = 18
DEFAULT_SEED = 7
DEFAULT_FIGSIZE: tuple[float, float] = (10.6, 5.8)


def build_circuit(*, qubit_count: int, column_count: int, seed: int) -> QuantumCircuit:
    """Build a deterministic random-looking Qiskit circuit."""

    quantum = QuantumRegister(qubit_count, "q")
    classical = ClassicalRegister(qubit_count, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_random_demo")
    rng = Random(seed)

    single_qubit_gates = ("h", "x", "rx", "ry", "rz")
    two_qubit_gates = ("cx", "cz", "swap")

    for column_index in range(column_count):
        if column_index % 2 == 0:
            for wire in range(qubit_count):
                gate_name = single_qubit_gates[
                    (column_index + wire + rng.randrange(len(single_qubit_gates)))
                    % len(single_qubit_gates)
                ]
                _apply_single_qubit_gate(
                    circuit,
                    gate_name=gate_name,
                    wire=wire,
                    angle=_angle_for(rng, column_index, wire),
                )
        else:
            shuffled_wires = list(range(qubit_count))
            rng.shuffle(shuffled_wires)
            for pair_index in range(0, len(shuffled_wires) - 1, 2):
                left = shuffled_wires[pair_index]
                right = shuffled_wires[pair_index + 1]
                gate_name = two_qubit_gates[
                    (column_index + pair_index + seed) % len(two_qubit_gates)
                ]
                if gate_name != "swap" and (column_index + pair_index + seed) % 2 == 1:
                    left, right = right, left
                _apply_two_qubit_gate(circuit, gate_name=gate_name, left=left, right=right)
            if len(shuffled_wires) % 2 == 1:
                leftover_wire = shuffled_wires[-1]
                gate_name = "rx" if column_index % 4 == 1 else "rz"
                _apply_single_qubit_gate(
                    circuit,
                    gate_name=gate_name,
                    wire=leftover_wire,
                    angle=_angle_for(rng, column_index, leftover_wire),
                )

    for wire in range(qubit_count):
        circuit.measure(wire, classical[wire])
    return circuit


def _apply_single_qubit_gate(
    circuit: QuantumCircuit,
    *,
    gate_name: str,
    wire: int,
    angle: float,
) -> None:
    if gate_name == "h":
        circuit.h(wire)
    elif gate_name == "x":
        circuit.x(wire)
    elif gate_name == "rx":
        circuit.rx(angle, wire)
    elif gate_name == "ry":
        circuit.ry(angle, wire)
    elif gate_name == "rz":
        circuit.rz(angle, wire)


def _apply_two_qubit_gate(
    circuit: QuantumCircuit,
    *,
    gate_name: str,
    left: int,
    right: int,
) -> None:
    if gate_name == "cx":
        circuit.cx(left, right)
    elif gate_name == "cz":
        circuit.cz(left, right)
    else:
        circuit.swap(left, right)


def _angle_for(rng: Random, column_index: int, wire: int) -> float:
    base = 0.18 + (0.07 * ((column_index + wire) % 5))
    return round(base + (0.11 * (wire + 1)) + rng.uniform(0.03, 0.31), 2)


def main() -> None:
    """Render a broad Qiskit circuit useful for exploring modes and layouts."""

    request = _parse_request(_parse_args())
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(
                qubit_count=request.qubits,
                column_count=request.columns,
                seed=request.seed,
            ),
            config=DrawConfig(
                side=DrawSideConfig(
                    render=CircuitRenderOptions(
                        view=request.view,
                        mode=DrawMode(request.mode),
                        composite_mode=request.composite_mode,
                        topology=request.topology,
                        topology_menu=request.view == "3d"
                        and request.mode in {"pages_controls", "slider"},
                        direct=request.view != "3d",
                        unsupported_policy=request.unsupported_policy,
                    ),
                    appearance=CircuitAppearanceOptions(
                        preset=request.preset,
                        hover=HoverOptions(
                            enabled=request.hover,
                            show_size=request.hover_show_size,
                            show_matrix=request.hover_matrix,
                            matrix_max_qubits=request.hover_matrix_max_qubits,
                        ),
                    ),
                ),
                output=OutputOptions(
                    output_path=request.output,
                    show=request.show,
                    figsize=request.figsize,
                ),
            ),
        )
        if request.output is not None:
            print(f"Saved qiskit-random to {request.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_request(args: Namespace) -> ExampleRequest:
    return request_from_namespace(
        args,
        default_qubits=DEFAULT_QUBITS,
        default_columns=DEFAULT_COLUMNS,
    )


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a larger Qiskit circuit that is useful for trying draw modes."
    )
    add_render_arguments(
        parser,
        default_qubits=DEFAULT_QUBITS,
        default_columns=DEFAULT_COLUMNS,
        columns_help="How many random-looking columns to build.",
        default_seed=DEFAULT_SEED,
    )
    parser.set_defaults(figsize=DEFAULT_FIGSIZE)
    _override_figsize_help(parser)
    return parser.parse_args()


def _override_figsize_help(parser: ArgumentParser) -> None:
    default_width, default_height = DEFAULT_FIGSIZE
    for action in parser._actions:
        if "--figsize" not in action.option_strings:
            continue
        action.help = (
            f"Managed figure size in inches. Default: {default_width:g} {default_height:g}."
        )
        return


if __name__ == "__main__":
    main()
