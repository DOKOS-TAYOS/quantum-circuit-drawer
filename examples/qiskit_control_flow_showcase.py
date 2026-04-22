"""Showcase Qiskit example focused on native control-flow support."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import XGate

try:
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> QuantumCircuit:
    """Build a Qiskit circuit that highlights compact control-flow rendering."""

    qubit_count = max(5, request.qubits)
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
    circuit.for_loop(range(_loop_span(request)), None, loop_body, [quantum[4]], ())

    while_body = QuantumCircuit(1, 1, name="echo_step")
    while_body.x(0)
    circuit.while_loop((classical[2], 1), while_body, [quantum[0]], [classical[2]])

    for wire in range(qubit_count):
        circuit.measure(quantum[wire], classical[wire])
    return circuit


def _loop_span(request: ExampleRequest) -> int:
    return max(2, min(request.columns, 7))


def main() -> None:
    run_example(
        build_circuit,
        description="Render a Qiskit control-flow showcase with compact native boxes and open controls.",
        framework="qiskit",
        saved_label="Qiskit control-flow showcase",
        default_qubits=5,
        default_columns=4,
        columns_help="Loop span to show in the compact Qiskit control-flow box",
    )


if __name__ == "__main__":
    main()
