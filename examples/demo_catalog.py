"""Central catalog for runnable example demos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DemoSpec:
    """Metadata needed to run one demo from the shared example entrypoint."""

    demo_id: str
    description: str
    module_name: str
    builder_name: str
    framework: str | None
    default_qubits: int
    default_columns: int
    columns_help: str
    dependency_module: str | None = None


def examples_directory() -> Path:
    """Return the absolute examples directory."""

    return Path(__file__).resolve().parent


def get_demo_catalog() -> tuple[DemoSpec, ...]:
    """Return the full list of example demos exposed by the shared runner."""

    return (
        DemoSpec(
            demo_id="qiskit-random",
            description="Configurable random Qiskit circuit",
            module_name="examples.qiskit_random",
            builder_name="build_circuit",
            framework="qiskit",
            default_qubits=10,
            default_columns=18,
            columns_help="Random circuit columns to generate",
            dependency_module="qiskit",
        ),
        DemoSpec(
            demo_id="qiskit-qaoa",
            description="Configurable QAOA / MaxCut circuit in Qiskit",
            module_name="examples.qiskit_qaoa",
            builder_name="build_circuit",
            framework="qiskit",
            default_qubits=8,
            default_columns=6,
            columns_help="QAOA layers to generate",
            dependency_module="qiskit",
        ),
        DemoSpec(
            demo_id="qiskit-2d-exploration-showcase",
            description=(
                "Qiskit showcase for managed 2D exploration, active-wire filtering, "
                "and contextual block controls"
            ),
            module_name="examples.qiskit_2d_exploration_showcase",
            builder_name="build_circuit",
            framework="qiskit",
            default_qubits=18,
            default_columns=9,
            columns_help="Repeated composite motifs to place across the exploration showcase",
            dependency_module="qiskit",
        ),
        DemoSpec(
            demo_id="qiskit-3d-exploration-showcase",
            description=(
                "Qiskit showcase for managed 3D exploration, topology-aware selection, "
                "and contextual block controls"
            ),
            module_name="examples.qiskit_3d_exploration_showcase",
            builder_name="build_circuit",
            framework="qiskit",
            default_qubits=25,
            default_columns=6,
            columns_help="Repeated composite motifs to place across the 3D exploration showcase",
            dependency_module="qiskit",
        ),
        DemoSpec(
            demo_id="qiskit-control-flow-showcase",
            description="Qiskit showcase for compact control-flow boxes and open controls",
            module_name="examples.qiskit_control_flow_showcase",
            builder_name="build_circuit",
            framework="qiskit",
            default_qubits=5,
            default_columns=4,
            columns_help="Loop span to show in the compact Qiskit control-flow box",
            dependency_module="qiskit",
        ),
        DemoSpec(
            demo_id="qiskit-composite-modes-showcase",
            description="Qiskit showcase for compact versus expanded composite instructions",
            module_name="examples.qiskit_composite_modes_showcase",
            builder_name="build_circuit",
            framework="qiskit",
            default_qubits=5,
            default_columns=4,
            columns_help="Extra rotation motifs to append after the composite block",
            dependency_module="qiskit",
        ),
        DemoSpec(
            demo_id="openqasm-showcase",
            description="OpenQASM text workflow rendered through the Qiskit parser path",
            module_name="examples.openqasm_showcase",
            builder_name="build_circuit",
            framework="qasm",
            default_qubits=3,
            default_columns=2,
            columns_help="Extra alternating OpenQASM gate motifs to append before measurement",
            dependency_module="qiskit",
        ),
        DemoSpec(
            demo_id="cirq-random",
            description="Configurable random Cirq circuit",
            module_name="examples.cirq_random",
            builder_name="build_circuit",
            framework="cirq",
            default_qubits=10,
            default_columns=18,
            columns_help="Random circuit columns to generate",
            dependency_module="cirq",
        ),
        DemoSpec(
            demo_id="cirq-qaoa",
            description="Configurable QAOA / MaxCut circuit in Cirq",
            module_name="examples.cirq_qaoa",
            builder_name="build_circuit",
            framework="cirq",
            default_qubits=8,
            default_columns=6,
            columns_help="QAOA layers to generate",
            dependency_module="cirq",
        ),
        DemoSpec(
            demo_id="cirq-native-controls-showcase",
            description="Cirq showcase for native controls, classical control, and CircuitOperation provenance",
            module_name="examples.cirq_native_controls_showcase",
            builder_name="build_circuit",
            framework="cirq",
            default_qubits=4,
            default_columns=3,
            columns_help="Additional native-control motifs to append after the structural showcase",
            dependency_module="cirq",
        ),
        DemoSpec(
            demo_id="pennylane-random",
            description="Configurable random PennyLane tape",
            module_name="examples.pennylane_random",
            builder_name="build_tape",
            framework="pennylane",
            default_qubits=10,
            default_columns=18,
            columns_help="Random circuit columns to generate",
            dependency_module="pennylane",
        ),
        DemoSpec(
            demo_id="pennylane-qaoa",
            description="Configurable QAOA / MaxCut tape in PennyLane",
            module_name="examples.pennylane_qaoa",
            builder_name="build_tape",
            framework="pennylane",
            default_qubits=8,
            default_columns=6,
            columns_help="QAOA layers to generate",
            dependency_module="pennylane",
        ),
        DemoSpec(
            demo_id="pennylane-terminal-outputs-showcase",
            description="PennyLane showcase for mid-measurement, qml.cond(...), and terminal-output boxes",
            module_name="examples.pennylane_terminal_outputs_showcase",
            builder_name="build_tape",
            framework="pennylane",
            default_qubits=4,
            default_columns=3,
            columns_help="Extra rotation motifs to append before the terminal outputs",
            dependency_module="pennylane",
        ),
        DemoSpec(
            demo_id="myqlm-random",
            description="Configurable random myQLM circuit",
            module_name="examples.myqlm_random",
            builder_name="build_circuit",
            framework="myqlm",
            default_qubits=10,
            default_columns=18,
            columns_help="Random circuit columns to generate",
            dependency_module="qat",
        ),
        DemoSpec(
            demo_id="myqlm-structural-showcase",
            description="myQLM showcase for compact composite routines on the native adapter path",
            module_name="examples.myqlm_structural_showcase",
            builder_name="build_circuit",
            framework="myqlm",
            default_qubits=5,
            default_columns=3,
            columns_help="Composite routine applications to place across the myQLM circuit",
            dependency_module="qat",
        ),
        DemoSpec(
            demo_id="cudaq-random",
            description="Configurable random CUDA-Q kernel",
            module_name="examples.cudaq_random",
            builder_name="build_kernel",
            framework="cudaq",
            default_qubits=10,
            default_columns=18,
            columns_help="Random circuit columns to generate",
            dependency_module="cudaq",
        ),
        DemoSpec(
            demo_id="cudaq-kernel-showcase",
            description="CUDA-Q showcase for the supported subset with reset and basis measurements",
            module_name="examples.cudaq_kernel_showcase",
            builder_name="build_kernel",
            framework="cudaq",
            default_qubits=3,
            default_columns=4,
            columns_help="Extra phased steps to append inside the CUDA-Q kernel",
            dependency_module="cudaq",
        ),
        DemoSpec(
            demo_id="ir-basic-workflow",
            description="Framework-free workflow built directly from the public CircuitIR types",
            module_name="examples.ir_basic_workflow",
            builder_name="build_circuit",
            framework="ir",
            default_qubits=4,
            default_columns=3,
            columns_help="Extra phase motifs to add to the public IR circuit",
        ),
    )


def catalog_by_id() -> dict[str, DemoSpec]:
    """Return the demo catalog keyed by demo id."""

    return {demo.demo_id: demo for demo in get_demo_catalog()}
