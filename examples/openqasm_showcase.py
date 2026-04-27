"""OpenQASM text workflow rendered through the Qiskit parser path."""

from __future__ import annotations

try:
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> str:
    """Build an OpenQASM 2 program from the public demo request."""

    qubit_count = max(2, request.qubits)
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{qubit_count}];",
        f"creg c[{qubit_count}];",
        "h q[0];",
    ]
    for index in range(qubit_count - 1):
        lines.append(f"cx q[{index}], q[{index + 1}];")
    for step in range(max(1, request.columns)):
        target = step % qubit_count
        control = (target + 1) % qubit_count
        angle = 0.125 * float(step + 1)
        lines.append(f"rz({angle:.3f}) q[{target}];")
        lines.append(f"rx({angle / 2.0:.3f}) q[{control}];")
        lines.append(f"cx q[{target}], q[{control}];")
    lines.append("barrier q;")
    lines.append("measure q -> c;")
    return "\n".join(lines)


def main() -> None:
    """Run the OpenQASM showcase as a normal user-facing script."""

    run_example(
        build_circuit,
        description="Render an OpenQASM text program through the Qiskit parser path.",
        framework="qasm",
        saved_label="openqasm-showcase",
        default_qubits=3,
        default_columns=2,
        columns_help="Extra alternating OpenQASM gate motifs to append before measurement",
    )


if __name__ == "__main__":
    main()
