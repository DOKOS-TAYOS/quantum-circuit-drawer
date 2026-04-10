"""Wide myQLM example for quantum-circuit-drawer."""

from __future__ import annotations

from qat.lang.AQASM import CNOT, CSIGN, PH, RX, RY, RZ, SWAP, H, Program

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> object:
    program = Program()
    qbits = program.qalloc(6)
    cbits = program.calloc(6)

    for wire in range(6):
        H(qbits[wire])

    rounds = (
        (0.31, 0.47, 0.63, 0.82),
        (0.44, 0.58, 0.29, 0.91),
        (0.73, 0.36, 0.54, 0.67),
        (0.52, 0.78, 0.41, 0.88),
    )
    edges = ((0, 1), (1, 2), (2, 4), (4, 5), (0, 5))

    for round_index, (gamma_a, gamma_b, theta_a, theta_b) in enumerate(rounds):
        RX(theta_a)(qbits[round_index % 6])
        RY(theta_b)(qbits[(round_index + 2) % 6])
        RZ(gamma_a)(qbits[(round_index + 4) % 6])

        for left, right in edges:
            PH(gamma_b + (0.08 * round_index)).ctrl()(qbits[left], qbits[right])

        CNOT(qbits[round_index % 6], qbits[(round_index + 1) % 6])
        CSIGN(qbits[(round_index + 2) % 6], qbits[(round_index + 4) % 6])
        SWAP(qbits[(round_index + 1) % 6], qbits[(round_index + 3) % 6])

    program.measure(list(qbits), list(cbits))
    return program.to_circ()


def main() -> None:
    run_example(
        build_circuit,
        description="Render a wide myQLM circuit with a horizontal slider.",
        framework="myqlm",
        style=demo_style(max_page_width=8.5),
        page_slider=True,
        saved_label="myQLM wide example",
    )


if __name__ == "__main__":
    main()
