"""myQLM demo showing classical conditions and composite expansion."""

from __future__ import annotations

from qat.lang.AQASM import CNOT, RY, H, Program, X
from qat.lang.AQASM.qftarith import QFT

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> object:
    program = Program()
    qbits = program.qalloc(4)
    cbits = program.calloc(2)

    H(qbits[0])
    CNOT(qbits[0], qbits[1])
    RY(0.52)(qbits[2])
    program.apply(QFT(2), qbits[2], qbits[3])
    program.measure([qbits[0]], [cbits[0]])
    program.cc_apply(X, cbits[0], qbits[3])
    program.measure([qbits[3]], [cbits[1]])
    return program.to_circ()


def main() -> None:
    run_example(
        build_circuit,
        description="Render a myQLM demo with classical control and expanded composite blocks.",
        framework="myqlm",
        style=demo_style(max_page_width=7.0),
        page_slider=False,
        composite_mode="expand",
        saved_label="myQLM conditional/composite example",
    )


if __name__ == "__main__":
    main()
