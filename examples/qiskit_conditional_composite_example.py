"""Qiskit demo showing classical conditions and composite expansion."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def _entangling_block(*, name: str) -> QuantumCircuit:
    block = QuantumCircuit(2, name=name)
    block.h(0)
    block.cx(0, 1)
    block.rz(0.37, 1)
    return block


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(4, "q")
    classical = ClassicalRegister(2, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_conditional_composite_demo")

    warmup_block = _entangling_block(name="warmup")
    conditional_block = _entangling_block(name="conditional")

    circuit.append(warmup_block.to_instruction(), [quantum[0], quantum[1]])
    circuit.ry(0.52, quantum[2])
    circuit.cz(quantum[1], quantum[2])
    circuit.measure(quantum[0], classical[0])

    with circuit.if_test((classical[0], 1)):
        circuit.append(conditional_block.to_instruction(), [quantum[2], quantum[3]])
        circuit.x(quantum[3])

    circuit.measure(quantum[3], classical[1])
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a Qiskit demo with classical control and expanded composite blocks.",
        framework=None,
        style=demo_style(max_page_width=7.0),
        page_slider=False,
        composite_mode="expand",
        saved_label="Qiskit conditional/composite example",
    )


if __name__ == "__main__":
    main()
