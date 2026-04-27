"""Comparison helpers for aligned histogram overlays."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
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
    from matplotlib.lines import Line2D

_HOVER_ZORDER = 10_000


@dataclass(slots=True)
class HistogramCompareArtists:
    """Artists and legend visibility state for one overlay histogram."""

    left_bars: tuple[Rectangle, ...]
    right_bars: tuple[Rectangle, ...]
    left_edges: tuple[Line2D, ...]
    right_edges: tuple[Line2D, ...]
    legend: Legend | None
    visible_series: dict[str, bool] = field(default_factory=lambda: {"left": True, "right": True})


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
) -> HistogramCompareArtists:
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
    left_bars: list[Rectangle] = []
    right_bars: list[Rectangle] = []
    left_edges: list[Line2D] = []
    right_edges: list[Line2D] = []

    for position, left_value, right_value in zip(positions, left_values, right_values, strict=True):
        left_is_back = abs(float(left_value)) >= abs(float(right_value))
        left_bar = axes.bar(
            position,
            (float(left_value),),
            width=bar_width,
            color=left_color,
            edgecolor=theme.gate_edgecolor,
            linewidth=1.6 if left_is_back else 1.1,
            alpha=0.26 if left_is_back else 0.58,
            zorder=2 if left_is_back else 3,
        )[0]
        right_bar = axes.bar(
            position,
            (float(right_value),),
            width=bar_width,
            color=right_color,
            edgecolor=theme.gate_edgecolor,
            linewidth=1.1 if left_is_back else 1.6,
            alpha=0.58 if left_is_back else 0.26,
            zorder=3 if left_is_back else 2,
        )[0]
        left_bar.set_label("_nolegend_")
        left_bar.set_gid("histogram-compare:left")
        right_bar.set_label("_nolegend_")
        right_bar.set_gid("histogram-compare:right")
        left_edge = _draw_bar_top_edge(
            axes=axes,
            position=float(position),
            value=float(left_value),
            width=bar_width,
            color=left_color,
            series_name="left",
        )
        right_edge = _draw_bar_top_edge(
            axes=axes,
            position=float(position),
            value=float(right_value),
            width=bar_width,
            color=right_color,
            series_name="right",
        )
        left_bars.append(left_bar)
        right_bars.append(right_bar)
        left_edges.append(left_edge)
        right_edges.append(right_edge)

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
    return HistogramCompareArtists(
        left_bars=tuple(left_bars),
        right_bars=tuple(right_bars),
        left_edges=tuple(left_edges),
        right_edges=tuple(right_edges),
        legend=legend,
    )


def _draw_bar_top_edge(
    *,
    axes: Axes,
    position: float,
    value: float,
    width: float,
    color: str,
    series_name: str,
) -> Line2D:
    half_width = width / 2.0
    line = axes.plot(
        [position - half_width, position + half_width],
        [value, value],
        color=color,
        linewidth=1.6,
        solid_capstyle="round",
        zorder=4,
    )[0]
    line.set_gid(f"histogram-compare:{series_name}")
    return line


def attach_histogram_compare_hover(
    axes: Axes,
    *,
    artists: HistogramCompareArtists,
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
        hovered_index = _hovered_compare_bar_index(artists, event)
        if hovered_index is None:
            hide_annotation()
            return
        if active_index == hovered_index:
            return
        show_left = artists.left_bars[hovered_index].get_visible()
        show_right = artists.right_bars[hovered_index].get_visible()
        annotation.xy = (event.x, event.y)
        annotation.set_text(
            _compare_histogram_hover_text(
                state_label=state_labels[hovered_index],
                left_value=left_values[hovered_index],
                right_value=right_values[hovered_index],
                kind=kind,
                left_label=left_label,
                right_label=right_label,
                show_left=show_left,
                show_right=show_right,
            )
        )
        annotation.set_visible(True)
        active_index = hovered_index
        canvas.draw_idle()

    callback_id = canvas.mpl_connect("motion_notify_event", on_motion)
    set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))


def _hovered_compare_bar_index(
    artists: HistogramCompareArtists,
    event: MouseEvent,
) -> int | None:
    for index, (left_bar, right_bar) in enumerate(
        zip(artists.left_bars, artists.right_bars, strict=True)
    ):
        for bar in (left_bar, right_bar):
            if not bar.get_visible():
                continue
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
    show_left: bool,
    show_right: bool,
) -> str:
    value_label = "counts" if kind is HistogramKind.COUNTS else "quasi-probability"
    lines = [f"State: {state_label}"]
    if show_left:
        lines.append(f"{left_label} {value_label}: {_formatted_histogram_value(left_value, kind)}")
    if show_right:
        lines.append(
            f"{right_label} {value_label}: {_formatted_histogram_value(right_value, kind)}"
        )
    if show_left and show_right:
        delta_value = left_value - right_value
        lines.append(f"Delta: {_formatted_histogram_value(delta_value, kind)}")
    return "\n".join(lines)


def _formatted_histogram_value(value: float, kind: HistogramKind) -> str:
    if kind is HistogramKind.COUNTS and float(value).is_integer():
        return str(int(value))
    return f"{float(value):.6g}"


def _style_compare_legend(*, legend: Legend | None, theme: DrawTheme) -> None:
    if legend is None:
        return
    for text in legend.get_texts():
        text.set_color(theme.text_color)


def attach_histogram_compare_legend_toggle(
    axes: Axes,
    *,
    artists: HistogramCompareArtists,
    left_values: tuple[float, ...],
    right_values: tuple[float, ...],
    kind: HistogramKind,
) -> None:
    """Select one compare series from legend clicks."""

    legend = artists.legend
    canvas = axes.figure.canvas
    if legend is None or canvas is None:
        return

    handle_artists = tuple(getattr(legend, "legend_handles", ()) or ())
    if len(handle_artists) < 2:
        handle_artists = tuple(getattr(legend, "legendHandles", ()) or ())
    if len(handle_artists) < 2:
        return

    legend_targets = {
        handle_artists[0]: "left",
        handle_artists[1]: "right",
        legend.get_texts()[0]: "left",
        legend.get_texts()[1]: "right",
    }

    for artist in legend_targets:
        if hasattr(artist, "set_picker"):
            artist.set_picker(True)

    def apply_visibility() -> None:
        for bar, edge in zip(artists.left_bars, artists.left_edges, strict=True):
            bar.set_visible(artists.visible_series["left"])
            edge.set_visible(artists.visible_series["left"])
        for bar, edge in zip(artists.right_bars, artists.right_edges, strict=True):
            bar.set_visible(artists.visible_series["right"])
            edge.set_visible(artists.visible_series["right"])

        active_values: list[float] = []
        if artists.visible_series["left"]:
            active_values.extend(float(value) for value in left_values)
        if artists.visible_series["right"]:
            active_values.extend(float(value) for value in right_values)
        if active_values:
            axes.set_ylim(
                *resolved_histogram_y_limits(
                    tuple(active_values),
                    kind=kind,
                    uniform_reference_value=None,
                )
            )
        else:
            axes.set_ylim(0.0, 1.0)

        legend_handle_alpha = {"left": 0.72, "right": 0.72}
        legend_text_alpha = {"left": 1.0, "right": 1.0}
        for series_name, visible in artists.visible_series.items():
            if not visible:
                legend_handle_alpha[series_name] = 0.22
                legend_text_alpha[series_name] = 0.45

        for artist, series_name in legend_targets.items():
            if hasattr(artist, "set_alpha"):
                if artist in handle_artists:
                    artist.set_alpha(legend_handle_alpha[series_name])
                else:
                    artist.set_alpha(legend_text_alpha[series_name])
        canvas.draw_idle()

    def on_pick(event: Event) -> None:
        picked_series = legend_targets.get(getattr(event, "artist", None))
        if picked_series is None:
            return
        for series_name in artists.visible_series:
            artists.visible_series[series_name] = series_name == picked_series
        apply_visibility()

    canvas.mpl_connect("pick_event", on_pick)
    apply_visibility()


__all__ = [
    "HistogramCompareArtists",
    "attach_histogram_compare_hover",
    "attach_histogram_compare_legend_toggle",
    "build_compare_metrics",
    "draw_histogram_compare_axes",
    "ordered_comparison_state_labels",
    "resolve_comparison_kind",
]
