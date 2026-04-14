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
    )


def catalog_by_id() -> dict[str, DemoSpec]:
    """Return the demo catalog keyed by demo id."""

    return {demo.demo_id: demo for demo in get_demo_catalog()}
