"""Public package exports for :mod:`quantum_circuit_drawer`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._version import __version__
from .config import DrawConfig, DrawMode
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
    HistogramConfig,
    HistogramDrawStyle,
    HistogramKind,
    HistogramMode,
    HistogramResult,
    HistogramSort,
    HistogramStateLabelMode,
)
from .hover import HoverOptions
from .result import DrawResult
from .style import DrawStyle, DrawTheme

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


__all__ = [
    "DrawConfig",
    "DrawMode",
    "DrawResult",
    "DrawStyle",
    "DrawTheme",
    "HistogramConfig",
    "HistogramDrawStyle",
    "HistogramKind",
    "HistogramMode",
    "HistogramResult",
    "HistogramStateLabelMode",
    "HistogramSort",
    "HoverOptions",
    "LayoutError",
    "QuantumCircuitDrawerError",
    "RenderingError",
    "StyleValidationError",
    "UnsupportedBackendError",
    "UnsupportedFrameworkError",
    "UnsupportedOperationError",
    "__version__",
    "draw_quantum_circuit",
    "plot_histogram",
]
