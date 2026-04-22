"""Public histogram plotting API facade."""

from __future__ import annotations

from .plots.histogram import (
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
    compare_histograms,
    plot_histogram,
)

__all__ = [
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
    "HistogramSort",
    "HistogramViewOptions",
    "compare_histograms",
    "plot_histogram",
]
