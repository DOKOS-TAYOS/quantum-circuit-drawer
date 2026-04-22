"""Central catalog for runnable histogram example demos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class HistogramDemoSpec:
    """Metadata needed to run one histogram demo from the shared entrypoint."""

    demo_id: str
    description: str
    module_name: str
    builder_name: str
    dependency_module: str | None = None
    extra_name: str | None = None


def examples_directory() -> Path:
    """Return the absolute examples directory."""

    return Path(__file__).resolve().parent


def get_demo_catalog() -> tuple[HistogramDemoSpec, ...]:
    """Return the full list of histogram demos exposed by the shared runner."""

    return (
        HistogramDemoSpec(
            demo_id="histogram-binary-order",
            description="Counts histogram ordered by binary state labels",
            module_name="examples.histogram_binary_order",
            builder_name="build_demo",
        ),
        HistogramDemoSpec(
            demo_id="histogram-count-order",
            description="Counts histogram ordered from highest to lowest counts",
            module_name="examples.histogram_count_order",
            builder_name="build_demo",
        ),
        HistogramDemoSpec(
            demo_id="histogram-interactive-large",
            description="Large 7-bit histogram with auto controls, conditional slider, and marginal help",
            module_name="examples.histogram_interactive_large",
            builder_name="build_demo",
        ),
        HistogramDemoSpec(
            demo_id="histogram-multi-register",
            description="Counts histogram with several registers and decimal labels per register",
            module_name="examples.histogram_multi_register",
            builder_name="build_demo",
        ),
        HistogramDemoSpec(
            demo_id="histogram-uniform-reference",
            description="Counts histogram with the uniform reference line",
            module_name="examples.histogram_uniform_reference",
            builder_name="build_demo",
        ),
        HistogramDemoSpec(
            demo_id="histogram-quasi",
            description="Quasi-probability histogram with negative bars",
            module_name="examples.histogram_quasi",
            builder_name="build_demo",
        ),
        HistogramDemoSpec(
            demo_id="histogram-top-k",
            description="Counts histogram focused on top-k ordering and filtering",
            module_name="examples.histogram_top_k",
            builder_name="build_demo",
        ),
        HistogramDemoSpec(
            demo_id="histogram-result-index",
            description="Select one histogram from a tuple of several result payloads",
            module_name="examples.histogram_result_index",
            builder_name="build_demo",
        ),
        HistogramDemoSpec(
            demo_id="histogram-marginal",
            description="Qiskit result histogram reduced to a joint marginal",
            module_name="examples.histogram_marginal",
            builder_name="build_demo",
            dependency_module="qiskit",
        ),
        HistogramDemoSpec(
            demo_id="histogram-cirq-result",
            description="Cirq measurement-result histogram with several registers",
            module_name="examples.histogram_cirq_result",
            builder_name="build_demo",
            dependency_module="cirq",
        ),
        HistogramDemoSpec(
            demo_id="histogram-pennylane-probs",
            description="PennyLane probability-vector histogram from qml.probs()",
            module_name="examples.histogram_pennylane_probs",
            builder_name="build_demo",
            dependency_module="pennylane",
        ),
        HistogramDemoSpec(
            demo_id="histogram-myqlm-result",
            description="myQLM result histogram built directly from raw_data",
            module_name="examples.histogram_myqlm_result",
            builder_name="build_demo",
            dependency_module="qat",
            extra_name="myqlm",
        ),
        HistogramDemoSpec(
            demo_id="histogram-cudaq-sample",
            description="CUDA-Q sample-result histogram from cudaq.sample()",
            module_name="examples.histogram_cudaq_sample",
            builder_name="build_demo",
            dependency_module="cudaq",
        ),
    )


def catalog_by_id() -> dict[str, HistogramDemoSpec]:
    """Return the histogram demo catalog keyed by demo id."""

    return {demo.demo_id: demo for demo in get_demo_catalog()}
