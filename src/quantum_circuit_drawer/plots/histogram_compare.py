"""Comparison helpers for aligned histogram overlays."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from ..style.theme import DrawTheme
from .histogram_models import HistogramCompareMetrics, HistogramCompareSort, HistogramKind
from .histogram_normalize import _state_sort_key
from .histogram_render import (
    apply_histogram_theme,
    comparison_secondary_color,
    reference_line_color,
    resolved_histogram_y_limits,
    tick_labels_for_states,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


def resolve_comparison_kind(
    *,
    requested_kind: HistogramKind,
    left_kind: HistogramKind,
    right_kind: HistogramKind,
) -> HistogramKind:
    """Resolve the final comparison kind from both normalized inputs."""

    if requested_kind is not HistogramKind.AUTO:
        return requested_kind
    if left_kind is HistogramKind.QUASI or right_kind is HistogramKind.QUASI:
        return HistogramKind.QUASI
    return HistogramKind.COUNTS


def ordered_comparison_state_labels(
    *,
    left_values_by_state: Mapping[str, float],
    right_values_by_state: Mapping[str, float],
    sort: HistogramCompareSort,
    top_k: int | None,
) -> tuple[str, ...]:
    """Return one aligned ordering for both histogram series."""

    labels = tuple(
        sorted(set(left_values_by_state) | set(right_values_by_state), key=_state_sort_key)
    )
    items = [
        (
            label,
            float(left_values_by_state.get(label, 0.0)),
            float(right_values_by_state.get(label, 0.0)),
        )
        for label in labels
    ]
    if sort is HistogramCompareSort.STATE:
        items.sort(key=lambda item: _state_sort_key(item[0]))
    elif sort is HistogramCompareSort.STATE_DESC:
        items.sort(key=lambda item: _state_sort_key(item[0]), reverse=True)
    else:
        items.sort(key=lambda item: (-abs(item[1] - item[2]), _state_sort_key(item[0])))
    if top_k is not None:
        items = items[:top_k]
    return tuple(label for label, _, _ in items)


def build_compare_metrics(delta_values: tuple[float, ...]) -> HistogramCompareMetrics:
    """Build the public comparison metrics from one aligned delta vector."""

    return HistogramCompareMetrics(
        total_variation_distance=sum(abs(delta_value) for delta_value in delta_values) / 2.0,
        max_absolute_delta=max((abs(delta_value) for delta_value in delta_values), default=0.0),
    )


def draw_histogram_compare_axes(
    *,
    figure: Figure,
    axes: Axes,
    state_labels: tuple[str, ...],
    left_values: tuple[float, ...],
    right_values: tuple[float, ...],
    kind: HistogramKind,
    theme: DrawTheme,
    left_label: str,
    right_label: str,
) -> None:
    """Draw two aligned histograms as one overlay plot."""

    from matplotlib.patches import Patch

    apply_histogram_theme(figure=figure, axes=axes, theme=theme)
    positions = tuple(range(len(state_labels)))
    bar_width = 0.82
    left_color = theme.accent_color
    right_color = comparison_secondary_color(theme)
    legend_handles = [
        Patch(facecolor=left_color, edgecolor=theme.gate_edgecolor, alpha=0.72, label=left_label),
        Patch(
            facecolor=right_color,
            edgecolor=theme.gate_edgecolor,
            alpha=0.72,
            label=right_label,
        ),
    ]

    for position, left_value, right_value in zip(positions, left_values, right_values, strict=True):
        bars = [
            ("left", float(left_value), left_color),
            ("right", float(right_value), right_color),
        ]
        bars.sort(key=lambda item: abs(item[1]), reverse=True)
        back_series_name, back_value, back_color = bars[0]
        front_series_name, front_value, front_color = bars[1]

        back_bar = axes.bar(
            position,
            (back_value,),
            width=bar_width,
            color=back_color,
            edgecolor=theme.gate_edgecolor,
            linewidth=1.6,
            alpha=0.26,
            zorder=2,
        )[0]
        front_bar = axes.bar(
            position,
            (front_value,),
            width=bar_width,
            color=front_color,
            edgecolor=theme.gate_edgecolor,
            linewidth=1.1,
            alpha=0.58,
            zorder=3,
        )[0]
        if front_series_name == back_series_name:
            front_bar.set_zorder(3)
        _draw_back_bar_top_edge(
            axes=axes,
            position=float(position),
            value=back_value,
            width=bar_width,
            color=back_color,
        )
        back_bar.set_label("_nolegend_")
        front_bar.set_label("_nolegend_")

    axes.set_xlabel("State")
    axes.set_ylabel("Counts" if kind is HistogramKind.COUNTS else "Quasi-probability")
    if kind is HistogramKind.QUASI:
        axes.axhline(0.0, color=reference_line_color(theme), linewidth=1.0, linestyle="--")
    axes.set_xticks(list(positions))
    axes.set_xticklabels(tick_labels_for_states(state_labels, thin=False))
    if positions:
        axes.set_xlim(-0.5, len(positions) - 0.5)
    axes.set_ylim(
        *resolved_histogram_y_limits(
            (*left_values, *right_values),
            kind=kind,
            uniform_reference_value=None,
        )
    )
    axes.legend(handles=legend_handles, frameon=False)
    axes.margins(x=0.02)


def _draw_back_bar_top_edge(
    *,
    axes: Axes,
    position: float,
    value: float,
    width: float,
    color: str,
) -> None:
    half_width = width / 2.0
    axes.plot(
        [position - half_width, position + half_width],
        [value, value],
        color=color,
        linewidth=2.2,
        solid_capstyle="round",
        zorder=4,
    )


__all__ = [
    "build_compare_metrics",
    "draw_histogram_compare_axes",
    "ordered_comparison_state_labels",
    "resolve_comparison_kind",
]
