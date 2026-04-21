"""Public package exports for :mod:`quantum_circuit_drawer`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._version import __version__
from .builder import CircuitBuilder
from .circuit_compare import CircuitCompareConfig, CircuitCompareMetrics, CircuitCompareResult
from .config import DrawConfig, DrawMode, UnsupportedPolicy
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
from .histogram import (
    HistogramCompareConfig,
    HistogramCompareMetrics,
    HistogramCompareResult,
    HistogramCompareSort,
    HistogramConfig,
    HistogramDrawStyle,
    HistogramKind,
    HistogramMode,
    HistogramResult,
    HistogramSort,
    HistogramStateLabelMode,
)
from .hover import HoverOptions
from .presets import StylePreset
from .result import DrawResult
from .style import DrawStyle, DrawTheme
from .topology import HardwareTopology

if TYPE_CHECKING:
    from matplotlib.axes import Axes


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
    *,
    config: HistogramCompareConfig | None = None,
    ax: Axes | None = None,
) -> HistogramCompareResult:
    """Overlay two histograms on the same bins and return comparison data."""

    from .histogram import compare_histograms as _compare_histograms

    return _compare_histograms(
        left_data,
        right_data,
        config=config,
        ax=ax,
    )


def compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *,
    left_config: DrawConfig | None = None,
    right_config: DrawConfig | None = None,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, Axes] | None = None,
) -> CircuitCompareResult:
    """Draw two circuits side by side and return comparison metadata."""

    from .circuit_compare import compare_circuits as _compare_circuits

    return _compare_circuits(
        left_circuit,
        right_circuit,
        left_config=left_config,
        right_config=right_config,
        config=config,
        axes=axes,
    )


__all__ = [
    "CircuitBuilder",
    "CircuitCompareConfig",
    "CircuitCompareMetrics",
    "CircuitCompareResult",
    "DiagnosticSeverity",
    "DrawConfig",
    "DrawMode",
    "DrawResult",
    "DrawStyle",
    "DrawTheme",
    "HistogramCompareConfig",
    "HistogramCompareMetrics",
    "HistogramCompareResult",
    "HistogramCompareSort",
    "HistogramConfig",
    "HistogramDrawStyle",
    "HistogramKind",
    "HistogramMode",
    "HistogramResult",
    "HistogramStateLabelMode",
    "HardwareTopology",
    "HistogramSort",
    "HoverOptions",
    "LayoutError",
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
    "compare_circuits",
    "compare_histograms",
    "draw_quantum_circuit",
    "plot_histogram",
]
