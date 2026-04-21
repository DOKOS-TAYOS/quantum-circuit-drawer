"""Internal plotting compatibility facade.

This package remains importable for compatibility, but it is not part of the stable public extension contract.
"""

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
    compare_histograms,
    plot_histogram,
)

__all__ = [
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
    "HistogramSort",
    "compare_histograms",
    "plot_histogram",
]
