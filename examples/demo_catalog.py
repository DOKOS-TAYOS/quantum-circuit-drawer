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
    style: dict[str, object]
    page_slider: bool


def examples_directory() -> Path:
    """Return the absolute examples directory."""

    return Path(__file__).resolve().parent


def get_demo_catalog() -> tuple[DemoSpec, ...]:
    """Return the full list of example demos exposed by the shared runner."""

    return (
        DemoSpec(
            demo_id="qiskit-balanced",
            description="Balanced Qiskit showcase",
            module_name="examples.qiskit_example",
            builder_name="build_circuit",
            framework=None,
            style={"font_size": 12.0, "show_params": True, "max_page_width": 8.25},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="qiskit-wide",
            description="Wide Qiskit circuit with slider",
            module_name="examples.qiskit_wide_example",
            builder_name="build_circuit",
            framework=None,
            style={"font_size": 12.0, "show_params": True, "max_page_width": 9.0},
            page_slider=True,
        ),
        DemoSpec(
            demo_id="qiskit-deep",
            description="Deep Qiskit circuit",
            module_name="examples.qiskit_deep_example",
            builder_name="build_circuit",
            framework=None,
            style={"font_size": 12.0, "show_params": True, "max_page_width": 6.75},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="qiskit-grover",
            description="Grover search in Qiskit",
            module_name="examples.qiskit_grover_example",
            builder_name="build_circuit",
            framework=None,
            style={"font_size": 12.0, "show_params": True, "max_page_width": 7.0},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="qiskit-qaoa",
            description="QAOA / MaxCut in Qiskit",
            module_name="examples.qiskit_qaoa_example",
            builder_name="build_circuit",
            framework=None,
            style={"font_size": 12.0, "show_params": True, "max_page_width": 8.25},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="cirq-balanced",
            description="Balanced Cirq showcase",
            module_name="examples.cirq_example",
            builder_name="build_circuit",
            framework="cirq",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 8.25},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="cirq-wide",
            description="Wide Cirq circuit with slider",
            module_name="examples.cirq_wide_example",
            builder_name="build_circuit",
            framework="cirq",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 9.0},
            page_slider=True,
        ),
        DemoSpec(
            demo_id="cirq-deep",
            description="Deep Cirq circuit",
            module_name="examples.cirq_deep_example",
            builder_name="build_circuit",
            framework="cirq",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 6.75},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="cirq-grover",
            description="Grover search in Cirq",
            module_name="examples.cirq_grover_example",
            builder_name="build_circuit",
            framework="cirq",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 7.0},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="cirq-qaoa",
            description="QAOA / MaxCut in Cirq",
            module_name="examples.cirq_qaoa_example",
            builder_name="build_circuit",
            framework="cirq",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 8.25},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="pennylane-balanced",
            description="Balanced PennyLane showcase",
            module_name="examples.pennylane_example",
            builder_name="build_tape",
            framework="pennylane",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 8.25},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="pennylane-wide",
            description="Wide PennyLane circuit with slider",
            module_name="examples.pennylane_wide_example",
            builder_name="build_tape",
            framework="pennylane",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 9.0},
            page_slider=True,
        ),
        DemoSpec(
            demo_id="pennylane-deep",
            description="Deep PennyLane circuit",
            module_name="examples.pennylane_deep_example",
            builder_name="build_tape",
            framework="pennylane",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 6.75},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="pennylane-grover",
            description="Grover search in PennyLane",
            module_name="examples.pennylane_grover_example",
            builder_name="build_tape",
            framework="pennylane",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 7.0},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="pennylane-qaoa",
            description="QAOA / MaxCut in PennyLane",
            module_name="examples.pennylane_qaoa_example",
            builder_name="build_tape",
            framework="pennylane",
            style={"font_size": 12.0, "show_params": True, "max_page_width": 8.25},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="cudaq-balanced",
            description="Balanced CUDA-Q showcase",
            module_name="examples.cudaq_example",
            builder_name="build_kernel",
            framework=None,
            style={"font_size": 12.0, "show_params": True, "max_page_width": 8.25},
            page_slider=False,
        ),
        DemoSpec(
            demo_id="cudaq-wide",
            description="Wide CUDA-Q circuit with slider",
            module_name="examples.cudaq_wide_example",
            builder_name="build_kernel",
            framework=None,
            style={"font_size": 12.0, "show_params": True, "max_page_width": 9.0},
            page_slider=True,
        ),
        DemoSpec(
            demo_id="cudaq-deep",
            description="Deep CUDA-Q circuit",
            module_name="examples.cudaq_deep_example",
            builder_name="build_kernel",
            framework=None,
            style={"font_size": 12.0, "show_params": True, "max_page_width": 6.75},
            page_slider=False,
        ),
    )


def catalog_by_id() -> dict[str, DemoSpec]:
    """Return the demo catalog keyed by demo id."""

    return {demo.demo_id: demo for demo in get_demo_catalog()}
