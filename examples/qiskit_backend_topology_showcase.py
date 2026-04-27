"""Show HardwareTopology.from_qiskit_backend with a topology-aware 3D render."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from examples._render_support import release_rendered_result
    from examples._shared import ExampleRequest, build_draw_config, parse_example_args
except ImportError:
    from _render_support import release_rendered_result
    from _shared import ExampleRequest, build_draw_config, parse_example_args

from quantum_circuit_drawer import (
    CircuitBuilder,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    HardwareTopology,
    OutputOptions,
    draw_quantum_circuit,
)


@dataclass(frozen=True, slots=True)
class DemoBackend:
    """Small Qiskit-backend-like object for the public topology helper."""

    name: str
    num_qubits: int
    coupling_map: tuple[tuple[int, int], ...]


def build_circuit(request: ExampleRequest) -> object:
    """Build a circuit that is easy to read on a backend-derived topology."""

    qubit_count = max(5, request.qubits)
    builder = CircuitBuilder(qubit_count, qubit_count, name="qiskit_backend_topology")
    builder.h(0)
    for index in range(qubit_count - 1):
        builder.cx(index, index + 1)
    for step in range(max(1, request.columns)):
        target = step % qubit_count
        partner = (target + 2) % qubit_count
        builder.rz(0.2 * float(step + 1), target)
        builder.cz(target, partner)
    builder.measure_all()
    return builder.build()


def build_backend(qubit_count: int) -> DemoBackend:
    """Build a lightweight BackendV1/BackendV2-like object."""

    return DemoBackend(
        name="demo_qiskit_backend",
        num_qubits=qubit_count,
        coupling_map=tuple((index, index + 1) for index in range(qubit_count - 1)),
    )


def main() -> None:
    """Run the Qiskit backend topology showcase."""

    request = parse_example_args(
        description="Render a public IR circuit on a Qiskit backend-derived topology.",
        default_qubits=6,
        default_columns=3,
        columns_help="Backend-topology motifs to append before measurement",
        default_view="3d",
        default_mode="pages",
    )
    topology = HardwareTopology.from_qiskit_backend(build_backend(max(5, request.qubits)))
    circuit = build_circuit(request)
    base_config = build_draw_config(request, framework="ir")
    config = DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                framework="ir",
                view="3d",
                mode=DrawMode.PAGES,
                topology=topology,
                topology_qubits="all",
                direct=False,
            ),
            appearance=base_config.side.appearance,
        ),
        output=OutputOptions(
            show=request.show,
            output_path=request.output,
            figsize=request.figsize,
        ),
    )
    result = None
    try:
        result = draw_quantum_circuit(circuit, config=config)
        if request.output is not None:
            print(f"Saved qiskit-backend-topology-showcase to {request.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


if __name__ == "__main__":
    main()
