"""Showcase myQLM example focused on composite structure."""

from __future__ import annotations

from qat.lang.AQASM import CNOT, RX, H, Program, QRoutine

try:
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> object:
    """Build a myQLM circuit that highlights reusable composite structure."""

    qubit_count = max(4, request.qubits)
    program = Program()
    qbits = program.qalloc(qubit_count)
    cbits = program.calloc(qubit_count)
    routine = _build_showcase_routine()

    for start in range(_motif_count(request)):
        left = start % (qubit_count - 1)
        program.apply(routine, qbits[left], qbits[left + 1])

    H(qbits[-1])
    CNOT(qbits[0], qbits[-1])
    program.measure(list(qbits), list(cbits))
    return program.to_circ()


def _build_showcase_routine() -> QRoutine:
    routine = QRoutine()
    wires = routine.new_wires(2)
    H(wires[0])
    CNOT(wires[0], wires[1])
    RX(0.35)(wires[1])
    return routine


def _motif_count(request: ExampleRequest) -> int:
    return max(2, min(request.columns, 5))


def main() -> None:
    run_example(
        build_circuit,
        description="Render a myQLM showcase centered on compact composite routines.",
        framework="myqlm",
        saved_label="myQLM structural showcase",
        default_qubits=5,
        default_columns=3,
        columns_help="Composite routine applications to place across the myQLM circuit",
    )


if __name__ == "__main__":
    main()
