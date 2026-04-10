"""Balanced myQLM example for quantum-circuit-drawer."""

from __future__ import annotations

from qat.lang.AQASM import CNOT, PH, RY, RZ, SWAP, H, Program, X

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> object:
    program = Program()
    qbits = program.qalloc(4)
    cbits = program.calloc(4)

    H(qbits[0])
    RY(0.61)(qbits[1])
    RZ(0.28)(qbits[2])
    X(qbits[3])

    CNOT(qbits[0], qbits[1])
    PH(0.72).ctrl()(qbits[1], qbits[3])
    SWAP(qbits[0], qbits[2])
    RY(0.39)(qbits[1])
    CNOT(qbits[3], qbits[0])

    program.measure(
        [qbits[0], qbits[2], qbits[3], qbits[1]], [cbits[0], cbits[1], cbits[2], cbits[3]]
    )
    return program.to_circ()


def main() -> None:
    run_example(
        build_circuit,
        description="Render a balanced myQLM circuit in an interactive Matplotlib window.",
        framework="myqlm",
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="myQLM example",
    )


if __name__ == "__main__":
    main()
