"""Central catalog for runnable compare example demos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CompareKind = Literal["circuits", "histograms"]


@dataclass(frozen=True, slots=True)
class CompareDemoSpec:
    """Metadata needed to run one compare demo from the shared entrypoint."""

    demo_id: str
    description: str
    module_name: str
    builder_name: str
    compare_kind: CompareKind
    dependency_module: str | None = None
    extra_name: str | None = None


def examples_directory() -> Path:
    """Return the absolute examples directory."""

    return Path(__file__).resolve().parent


def get_demo_catalog() -> tuple[CompareDemoSpec, ...]:
    """Return the full list of compare demos exposed by the shared runner."""

    return (
        CompareDemoSpec(
            demo_id="compare-circuits-qiskit-transpile",
            description="Before and after Qiskit transpilation shown side by side",
            module_name="examples.compare_circuits_qiskit_transpile",
            builder_name="build_demo",
            compare_kind="circuits",
            dependency_module="qiskit",
        ),
        CompareDemoSpec(
            demo_id="compare-circuits-composite-modes",
            description="Same Qiskit workflow rendered with compact and expanded composite handling",
            module_name="examples.compare_circuits_composite_modes",
            builder_name="build_demo",
            compare_kind="circuits",
            dependency_module="qiskit",
        ),
        CompareDemoSpec(
            demo_id="compare-circuits-multi-transpile",
            description="One Qiskit source circuit compared with several transpilation optimization levels",
            module_name="examples.compare_circuits_multi_transpile",
            builder_name="build_demo",
            compare_kind="circuits",
            dependency_module="qiskit",
        ),
        CompareDemoSpec(
            demo_id="compare-histograms-ideal-vs-sampled",
            description="Ideal probabilities versus sampled counts over the same state space with clickable legend toggles",
            module_name="examples.compare_histograms_ideal_vs_sampled",
            builder_name="build_demo",
            compare_kind="histograms",
        ),
        CompareDemoSpec(
            demo_id="compare-histograms-multi-series",
            description="Ideal, noisy, raw hardware, and mitigated distributions in one selectable overlay",
            module_name="examples.compare_histograms_multi_series",
            builder_name="build_demo",
            compare_kind="histograms",
        ),
    )


def catalog_by_id() -> dict[str, CompareDemoSpec]:
    """Return the compare demo catalog keyed by demo id."""

    return {demo.demo_id: demo for demo in get_demo_catalog()}
