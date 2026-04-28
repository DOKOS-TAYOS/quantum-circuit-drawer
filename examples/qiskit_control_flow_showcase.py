"""Showcase Qiskit example focused on native control-flow support."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import XGate

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402

DEFAULT_FIGSIZE: tuple[float, float] = (9.2, 4.8)


def build_circuit(*, qubit_count: int, loop_span: int) -> QuantumCircuit:
    """Build a Qiskit circuit that highlights compact control-flow rendering."""

    quantum = QuantumRegister(qubit_count, "q")
    classical = ClassicalRegister(qubit_count, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_control_flow_showcase")

    circuit.h(quantum[0])
    circuit.h(quantum[1])
    circuit.append(XGate().control(1, ctrl_state=0), [quantum[0], quantum[2]])
    circuit.cz(quantum[1], quantum[3])
    circuit.measure(quantum[0], classical[0])
    circuit.measure(quantum[1], classical[1])
    circuit.measure(quantum[2], classical[2])

    with circuit.if_test((classical[0], 1)):
        circuit.x(quantum[4])
        circuit.rz(0.35, quantum[3])

    with circuit.if_test((classical[1], 1)) as else_:
        circuit.h(quantum[2])
    with else_:
        circuit.z(quantum[2])

    with circuit.switch(classical[0]) as case:
        with case(0):
            circuit.x(quantum[3])
        with case(1):
            circuit.append(XGate().control(1, ctrl_state=0), [quantum[1], quantum[4]])
        with case(case.DEFAULT):
            circuit.h(quantum[3])

    loop_body = QuantumCircuit(1, name="phase_step")
    loop_body.rz(0.22, 0)
    circuit.for_loop(range(loop_span), None, loop_body, [quantum[4]], ())

    while_body = QuantumCircuit(1, 1, name="echo_step")
    while_body.x(0)
    circuit.while_loop((classical[2], 1), while_body, [quantum[0]], [classical[2]])

    for wire in range(qubit_count):
        circuit.measure(quantum[wire], classical[wire])
    return circuit


def main() -> None:
    """Render a Qiskit control-flow showcase with native control structures."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, loop_span=args.loop_span),
            config=DrawConfig(
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_FIGSIZE,
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved qiskit-control-flow-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a Qiskit circuit with if/else, switch, for_loop, and while_loop blocks."
    )
    parser.add_argument("--qubits", type=int, default=5, help="Number of qubits to allocate.")
    parser.add_argument(
        "--loop-span",
        type=int,
        default=4,
        help="How many iterations to show in the compact for-loop box.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
