"""Comparison helpers for aligned histogram overlays."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.patches import Rectangle

from ..renderers._matplotlib_figure import HoverState, clear_hover_state, set_hover_state
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
    from matplotlib.legend import Legend

_HOVER_ZORDER = 10_000


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
) -> tuple[tuple[Rectangle, ...], ...]:
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
    bar_groups: list[tuple[Rectangle, ...]] = []

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
        bar_groups.append((back_bar, front_bar))

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
    legend = axes.legend(handles=legend_handles, frameon=False)
    _style_compare_legend(legend=legend, theme=theme)
    axes.margins(x=0.02)
    return tuple(bar_groups)


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


def attach_histogram_compare_hover(
    axes: Axes,
    *,
    bar_groups: tuple[tuple[Rectangle, ...], ...],
    state_labels: tuple[str, ...],
    left_values: tuple[float, ...],
    right_values: tuple[float, ...],
    kind: HistogramKind,
    theme: DrawTheme,
    left_label: str,
    right_label: str,
) -> None:
    """Attach one hover annotation that compares both series for the hovered bin."""

    clear_hover_state(axes)
    annotation = axes.annotate(
        "",
        xy=(0.0, 0.0),
        xycoords="figure pixels",
        xytext=(10.0, 10.0),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=max(8.0, axes.figure.dpi / 12.0),
        color=theme.hover_text_color,
        zorder=_HOVER_ZORDER,
        annotation_clip=False,
        bbox={
            "boxstyle": "round,pad=0.18",
            "fc": theme.hover_facecolor,
            "ec": theme.hover_edgecolor,
            "alpha": 0.9,
        },
    )
    annotation.set_visible(False)
    canvas = axes.figure.canvas
    if canvas is None:
        return
    active_index: int | None = None

    def hide_annotation() -> None:
        nonlocal active_index
        if annotation.get_visible():
            annotation.set_visible(False)
            active_index = None
            canvas.draw_idle()

    def on_motion(event: Event) -> None:
        nonlocal active_index
        if not isinstance(event, MouseEvent) or event.inaxes is not axes:
            hide_annotation()
            return
        hovered_index = _hovered_compare_bar_index(bar_groups, event)
        if hovered_index is None:
            hide_annotation()
            return
        if active_index == hovered_index:
            return
        annotation.xy = (event.x, event.y)
        annotation.set_text(
            _compare_histogram_hover_text(
                state_label=state_labels[hovered_index],
                left_value=left_values[hovered_index],
                right_value=right_values[hovered_index],
                kind=kind,
                left_label=left_label,
                right_label=right_label,
            )
        )
        annotation.set_visible(True)
        active_index = hovered_index
        canvas.draw_idle()

    callback_id = canvas.mpl_connect("motion_notify_event", on_motion)
    set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))


def _hovered_compare_bar_index(
    bar_groups: tuple[tuple[Rectangle, ...], ...],
    event: MouseEvent,
) -> int | None:
    for index, bars in enumerate(bar_groups):
        for bar in bars:
            contains, _ = bar.contains(event)
            if contains:
                return index
    return None


def _compare_histogram_hover_text(
    *,
    state_label: str,
    left_value: float,
    right_value: float,
    kind: HistogramKind,
    left_label: str,
    right_label: str,
) -> str:
    value_label = "counts" if kind is HistogramKind.COUNTS else "quasi-probability"
    delta_value = left_value - right_value
    return (
        f"State: {state_label}\n"
        f"{left_label} {value_label}: {_formatted_histogram_value(left_value, kind)}\n"
        f"{right_label} {value_label}: {_formatted_histogram_value(right_value, kind)}\n"
        f"Delta: {_formatted_histogram_value(delta_value, kind)}"
    )


def _formatted_histogram_value(value: float, kind: HistogramKind) -> str:
    if kind is HistogramKind.COUNTS and float(value).is_integer():
        return str(int(value))
    return f"{float(value):.6g}"


def _style_compare_legend(*, legend: Legend | None, theme: DrawTheme) -> None:
    if legend is None:
        return
    for text in legend.get_texts():
        text.set_color(theme.text_color)


__all__ = [
    "build_compare_metrics",
    "draw_histogram_compare_axes",
    "ordered_comparison_state_labels",
    "resolve_comparison_kind",
]
