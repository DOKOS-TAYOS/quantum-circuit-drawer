"""Configurable random-looking Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import Literal, cast

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
    DrawSideConfig,
    HoverOptions,
    draw_quantum_circuit,
)

DEFAULT_QUBITS = 10
DEFAULT_COLUMNS = 18
DEFAULT_SEED = 7
DEFAULT_FIGSIZE: tuple[float, float] = (10.6, 5.8)
SUPPORTED_TOPOLOGIES: tuple[str, ...] = ("line", "grid", "star", "star_tree", "honeycomb")

ViewMode = Literal["2d", "3d"]
RenderMode = Literal["auto", "pages", "pages_controls", "slider", "full"]
HoverMatrixMode = Literal["never", "auto", "always"]
CompositeMode = Literal["compact", "expand"]
UnsupportedPolicyMode = Literal["raise", "placeholder"]
StylePresetMode = Literal["paper", "notebook", "compact", "presentation", "accessible"]


@dataclass(frozen=True, slots=True)
class QiskitRandomRequest:
    qubits: int
    columns: int
    mode: RenderMode
    view: ViewMode
    topology: str
    seed: int
    output: Path | None
    show: bool
    figsize: tuple[float, float]
    hover: bool
    hover_matrix: HoverMatrixMode
    hover_matrix_max_qubits: int
    hover_show_size: bool
    preset: StylePresetMode | None
    composite_mode: CompositeMode
    unsupported_policy: UnsupportedPolicyMode


def build_circuit(
    request: object | None = None,
    /,
    *,
    qubit_count: int | None = None,
    column_count: int | None = None,
    seed: int | None = None,
) -> QuantumCircuit:
    """Build a deterministic random-looking Qiskit circuit."""

    resolved_qubit_count, resolved_column_count, resolved_seed = _resolved_build_circuit_inputs(
        request,
        qubit_count=qubit_count,
        column_count=column_count,
        seed=seed,
    )

    quantum = QuantumRegister(resolved_qubit_count, "q")
    classical = ClassicalRegister(resolved_qubit_count, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_random_demo")
    rng = Random(resolved_seed)

    single_qubit_gates = ("h", "x", "rx", "ry", "rz")
    two_qubit_gates = ("cx", "cz", "swap")

    for column_index in range(resolved_column_count):
        if column_index % 2 == 0:
            for wire in range(resolved_qubit_count):
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
            shuffled_wires = list(range(resolved_qubit_count))
            rng.shuffle(shuffled_wires)
            for pair_index in range(0, len(shuffled_wires) - 1, 2):
                left = shuffled_wires[pair_index]
                right = shuffled_wires[pair_index + 1]
                gate_name = two_qubit_gates[
                    (column_index + pair_index + resolved_seed) % len(two_qubit_gates)
                ]
                if gate_name != "swap" and (column_index + pair_index + resolved_seed) % 2 == 1:
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

    for wire in range(resolved_qubit_count):
        circuit.measure(wire, classical[wire])
    return circuit


def _resolved_build_circuit_inputs(
    request: object | None,
    *,
    qubit_count: int | None,
    column_count: int | None,
    seed: int | None,
) -> tuple[int, int, int]:
    if request is not None:
        return (
            int(getattr(request, "qubits")),
            int(getattr(request, "columns")),
            int(getattr(request, "seed")),
        )
    if qubit_count is None or column_count is None or seed is None:
        raise TypeError(
            "build_circuit() requires either a request or qubit_count, column_count, and seed"
        )
    return qubit_count, column_count, seed


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
            mode=request.mode,
            show=request.show,
            output_path=request.output,
            figsize=request.figsize,
            view=request.view,
            composite_mode=request.composite_mode,
            topology=request.topology,
            config=DrawConfig(
                side=DrawSideConfig(
                    render=CircuitRenderOptions(
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
            ),
        )
        if request.output is not None:
            print(f"Saved qiskit-random to {request.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_request(args: Namespace) -> QiskitRandomRequest:
    return QiskitRandomRequest(
        qubits=args.qubits,
        columns=args.columns,
        mode=cast(RenderMode, args.mode),
        view=cast(ViewMode, args.view),
        topology=str(args.topology),
        seed=args.seed,
        preset=cast(StylePresetMode | None, args.preset),
        composite_mode=cast(CompositeMode, args.composite_mode),
        unsupported_policy=cast(UnsupportedPolicyMode, args.unsupported_policy),
        output=args.output,
        show=bool(args.show),
        figsize=(float(args.figsize[0]), float(args.figsize[1])),
        hover=bool(args.hover),
        hover_matrix=cast(HoverMatrixMode, args.hover_matrix),
        hover_matrix_max_qubits=args.hover_matrix_max_qubits,
        hover_show_size=bool(args.hover_show_size),
    )


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a larger Qiskit circuit that is useful for trying draw modes."
    )
    parser.add_argument("--qubits", type=_positive_int, default=DEFAULT_QUBITS)
    parser.add_argument(
        "--columns",
        type=_positive_int,
        default=DEFAULT_COLUMNS,
        help="How many random-looking columns to build.",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "pages", "pages_controls", "slider", "full"),
        default="auto",
        help="Draw mode to use for the rendered circuit.",
    )
    parser.add_argument(
        "--view", choices=("2d", "3d"), default="2d", help="Render the circuit in 2D or 3D."
    )
    parser.add_argument(
        "--topology",
        choices=SUPPORTED_TOPOLOGIES,
        default="line",
        help="Topology used by the 3D view and topology-aware hover details.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--preset",
        choices=("paper", "notebook", "compact", "presentation", "accessible"),
        help="Optional style preset.",
    )
    parser.add_argument(
        "--composite-mode",
        choices=("compact", "expand"),
        default="compact",
        help="How supported composite instructions should be shown by the adapter.",
    )
    parser.add_argument(
        "--unsupported-policy",
        choices=("raise", "placeholder"),
        default="raise",
        help="How recoverable unsupported operations should be handled.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument(
        "--figsize",
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        type=_positive_float,
        default=DEFAULT_FIGSIZE,
        help="Managed figure size in inches.",
    )
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    parser.add_argument("--hover", dest="hover", action="store_true", default=True)
    parser.add_argument("--no-hover", dest="hover", action="store_false")
    parser.add_argument(
        "--hover-matrix",
        choices=("never", "auto", "always"),
        default="auto",
        help="Control whether hover tooltips include the gate matrix.",
    )
    parser.add_argument(
        "--hover-matrix-max-qubits",
        type=_positive_int,
        default=2,
        help="Maximum gate width, in qubits, for showing full matrices in hover.",
    )
    parser.add_argument(
        "--hover-show-size",
        action="store_true",
        help="Also include the visual gate size in the hover tooltip.",
    )
    return parser.parse_args()


def _positive_int(raw_value: str) -> int:
    value = int(raw_value)
    if value < 1:
        raise ArgumentTypeError("value must be at least 1")
    return value


def _positive_float(raw_value: str) -> float:
    value = float(raw_value)
    if value <= 0.0:
        raise ArgumentTypeError("value must be positive")
    return value


if __name__ == "__main__":
    main()
