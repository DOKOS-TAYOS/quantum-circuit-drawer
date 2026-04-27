"""Public package exports for :mod:`quantum_circuit_drawer`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._version import __version__
from .analysis import CircuitAnalysisResult
from .builder import CircuitBuilder
from .circuit_compare import (
    CircuitCompareConfig,
    CircuitCompareMetrics,
    CircuitCompareOptions,
    CircuitCompareResult,
    CircuitCompareSideMetrics,
)
from .config import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    UnsupportedPolicy,
)
from .diagnostics import DiagnosticSeverity, RenderDiagnostic
from .exceptions import (
    LayoutError,
    QuantumCircuitDrawerError,
    RenderingError,
    StyleValidationError,
    UnsupportedBackendError,
    UnsupportedFrameworkError,
    UnsupportedOperationError,
)
from .hover import HoverOptions
from .presets import StylePreset
from .result import DrawResult
from .style import DrawStyle, DrawTheme
from .topology import (
    FunctionalTopology,
    HardwareTopology,
    PeriodicTopology1D,
    PeriodicTopology2D,
    grid_topology,
    honeycomb_topology,
    line_topology,
    star_topology,
    star_tree_topology,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from .histogram import (
        HistogramAppearanceOptions,
        HistogramCompareConfig,
        HistogramCompareMetrics,
        HistogramCompareOptions,
        HistogramCompareResult,
        HistogramCompareSort,
        HistogramConfig,
        HistogramDataOptions,
        HistogramDrawStyle,
        HistogramKind,
        HistogramMode,
        HistogramResult,
        HistogramSort,
        HistogramStateLabelMode,
        HistogramViewOptions,
    )


def draw_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult:
    """Draw a supported circuit and always return ``DrawResult``.

    Use ``config`` for the public rendering options and ``ax`` only for
    static caller-managed Matplotlib axes.
    """

    from .api import draw_quantum_circuit as _draw_quantum_circuit

    return _draw_quantum_circuit(
        circuit,
        config=config,
        ax=ax,
    )


def analyze_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
) -> CircuitAnalysisResult:
    """Analyze a supported circuit without rendering figures."""

    from .api import analyze_quantum_circuit as _analyze_quantum_circuit

    return _analyze_quantum_circuit(
        circuit,
        config=config,
    )


def plot_histogram(
    data: object,
    *,
    config: HistogramConfig | None = None,
    ax: Axes | None = None,
) -> HistogramResult:
    """Plot counts or quasi-probability data and return ``HistogramResult``."""

    from .histogram import plot_histogram as _plot_histogram

    return _plot_histogram(
        data,
        config=config,
        ax=ax,
    )


def compare_histograms(
    left_data: object,
    right_data: object,
    *additional_data: object,
    config: HistogramCompareConfig | None = None,
    ax: Axes | None = None,
) -> HistogramCompareResult:
    """Overlay two or more histograms on the same bins and return comparison data."""

    from .histogram import compare_histograms as _compare_histograms

    return _compare_histograms(
        left_data,
        right_data,
        *additional_data,
        config=config,
        ax=ax,
    )


def compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *additional_circuits: object,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, ...] | None = None,
) -> CircuitCompareResult:
    """Draw two or more circuits side by side and return comparison metadata."""

    from .circuit_compare import compare_circuits as _compare_circuits

    return _compare_circuits(
        left_circuit,
        right_circuit,
        *additional_circuits,
        config=config,
        axes=axes,
    )


__all__ = [
    "CircuitBuilder",
    "CircuitAppearanceOptions",
    "CircuitAnalysisResult",
    "CircuitCompareConfig",
    "CircuitCompareMetrics",
    "CircuitCompareOptions",
    "CircuitCompareResult",
    "CircuitCompareSideMetrics",
    "CircuitRenderOptions",
    "DiagnosticSeverity",
    "DrawConfig",
    "DrawMode",
    "DrawResult",
    "DrawSideConfig",
    "DrawStyle",
    "DrawTheme",
    "FunctionalTopology",
    "HistogramAppearanceOptions",
    "HistogramCompareConfig",
    "HistogramCompareMetrics",
    "HistogramCompareOptions",
    "HistogramCompareResult",
    "HistogramCompareSort",
    "HistogramConfig",
    "HistogramDataOptions",
    "HistogramDrawStyle",
    "HistogramKind",
    "HistogramMode",
    "HistogramResult",
    "HistogramStateLabelMode",
    "HardwareTopology",
    "HistogramSort",
    "HistogramViewOptions",
    "HoverOptions",
    "LayoutError",
    "OutputOptions",
    "PeriodicTopology1D",
    "PeriodicTopology2D",
    "QuantumCircuitDrawerError",
    "RenderingError",
    "RenderDiagnostic",
    "StyleValidationError",
    "StylePreset",
    "UnsupportedBackendError",
    "UnsupportedFrameworkError",
    "UnsupportedOperationError",
    "UnsupportedPolicy",
    "__version__",
    "analyze_quantum_circuit",
    "compare_circuits",
    "compare_histograms",
    "draw_quantum_circuit",
    "grid_topology",
    "honeycomb_topology",
    "line_topology",
    "plot_histogram",
    "star_topology",
    "star_tree_topology",
]


def __getattr__(name: str) -> object:
    histogram_exports = {
        "HistogramAppearanceOptions",
        "HistogramCompareConfig",
        "HistogramCompareMetrics",
        "HistogramCompareOptions",
        "HistogramCompareResult",
        "HistogramCompareSort",
        "HistogramConfig",
        "HistogramDataOptions",
        "HistogramDrawStyle",
        "HistogramKind",
        "HistogramMode",
        "HistogramResult",
        "HistogramSort",
        "HistogramStateLabelMode",
        "HistogramViewOptions",
        "compare_histograms",
        "plot_histogram",
    }
    if name in histogram_exports:
        from . import histogram as histogram_module

        value = getattr(histogram_module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
