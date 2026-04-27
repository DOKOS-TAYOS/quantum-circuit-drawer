"""Comparison helpers for aligned histogram overlays."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.patches import Rectangle

from ..renderers._matplotlib_figure import (
    HoverState,
    clear_hover_state,
    get_hover_state,
    set_hover_state,
)
from ..renderers._matplotlib_hover_position import position_hover_annotation
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

    series_labels: tuple[str, ...]
    bars_by_series: tuple[tuple[Rectangle, ...], ...]
    edges_by_series: tuple[tuple[Line2D, ...], ...]
    legend: Legend | None
    visible_series: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.visible_series:
            self.visible_series.update(
                {series_key(index): True for index in range(len(self.series_labels))}
            )

    @property
    def left_bars(self) -> tuple[Rectangle, ...]:
        return self.bars_by_series[0] if self.bars_by_series else ()

    @property
    def right_bars(self) -> tuple[Rectangle, ...]:
        return self.bars_by_series[1] if len(self.bars_by_series) > 1 else ()

    @property
    def left_edges(self) -> tuple[Line2D, ...]:
        return self.edges_by_series[0] if self.edges_by_series else ()

    @property
    def right_edges(self) -> tuple[Line2D, ...]:
        return self.edges_by_series[1] if len(self.edges_by_series) > 1 else ()


def series_key(index: int) -> str:
    if index == 0:
        return "left"
    if index == 1:
        return "right"
    return f"series-{index + 1}"


def resolve_comparison_kind(
    *,
    requested_kind: HistogramKind,
    left_kind: HistogramKind | None = None,
    right_kind: HistogramKind | None = None,
    series_kinds: tuple[HistogramKind, ...] | None = None,
) -> HistogramKind:
    """Resolve the final comparison kind from all normalized inputs."""

    if requested_kind is not HistogramKind.AUTO:
        return requested_kind
    kinds = series_kinds if series_kinds is not None else (left_kind, right_kind)
    if any(kind is HistogramKind.QUASI for kind in kinds):
        return HistogramKind.QUASI
    return HistogramKind.COUNTS


def ordered_comparison_state_labels(
    *,
    left_values_by_state: Mapping[str, float] | None = None,
    right_values_by_state: Mapping[str, float] | None = None,
    values_by_state_series: tuple[Mapping[str, float], ...] | None = None,
    sort: HistogramCompareSort,
    top_k: int | None,
) -> tuple[str, ...]:
    """Return one aligned ordering for all histogram series."""

    series = values_by_state_series
    if series is None:
        if left_values_by_state is None or right_values_by_state is None:
            raise ValueError("ordered_comparison_state_labels requires comparison data")
        series = (left_values_by_state, right_values_by_state)
    labels = tuple(sorted(set().union(*(set(values) for values in series)), key=_state_sort_key))
    items = [
        (
            label,
            tuple(float(values.get(label, 0.0)) for values in series),
        )
        for label in labels
    ]
    if sort is HistogramCompareSort.STATE:
        items.sort(key=lambda item: _state_sort_key(item[0]))
    elif sort is HistogramCompareSort.STATE_DESC:
        items.sort(key=lambda item: _state_sort_key(item[0]), reverse=True)
    else:
        items.sort(key=lambda item: (-_spread(item[1]), _state_sort_key(item[0])))
    if top_k is not None:
        items = items[:top_k]
    return tuple(label for label, _ in items)


def _spread(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    return max(values) - min(values)


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
    series_values: tuple[tuple[float, ...], ...],
    kind: HistogramKind,
    theme: DrawTheme,
    series_labels: tuple[str, ...],
) -> HistogramCompareArtists:
    """Draw aligned histogram series as one overlay plot."""

    from matplotlib.patches import Patch

    apply_histogram_theme(figure=figure, axes=axes, theme=theme)
    positions = tuple(range(len(state_labels)))
    bar_width = 0.82
    colors = _compare_series_colors(theme, len(series_values))
    legend_handles = [
        Patch(facecolor=color, edgecolor=theme.gate_edgecolor, alpha=0.72, label=label)
        for color, label in zip(colors, series_labels, strict=True)
    ]
    bars_by_series: list[list[Rectangle]] = [[] for _ in series_values]
    edges_by_series: list[list[Line2D]] = [[] for _ in series_values]

    for state_index, position in enumerate(positions):
        order = sorted(
            range(len(series_values)),
            key=lambda series_index: abs(float(series_values[series_index][state_index])),
            reverse=True,
        )
        zorders_by_series = {
            series_index: 2 + draw_index for draw_index, series_index in enumerate(order)
        }
        alphas_by_series = {
            series_index: 0.24 + (0.36 * (draw_index / max(1, len(order) - 1)))
            for draw_index, series_index in enumerate(order)
        }
        for series_index in order:
            value = float(series_values[series_index][state_index])
            key = series_key(series_index)
            bar = axes.bar(
                position,
                (value,),
                width=bar_width,
                color=colors[series_index],
                edgecolor=theme.gate_edgecolor,
                linewidth=1.6 if zorders_by_series[series_index] == 2 + len(order) - 1 else 1.1,
                alpha=alphas_by_series[series_index],
                zorder=zorders_by_series[series_index],
            )[0]
            bar.set_label("_nolegend_")
            bar.set_gid(f"histogram-compare:{key}")
            edge = _draw_bar_top_edge(
                axes=axes,
                position=float(position),
                value=value,
                width=bar_width,
                color=colors[series_index],
                series_name=key,
            )
            bars_by_series[series_index].append(bar)
            edges_by_series[series_index].append(edge)

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
            tuple(value for values in series_values for value in values),
            kind=kind,
            uniform_reference_value=None,
        )
    )
    legend = axes.legend(
        handles=legend_handles,
        frameon=False,
        loc="upper right",
        bbox_to_anchor=(0.985, 0.985),
        borderaxespad=0.0,
    )
    _style_compare_legend(legend=legend, theme=theme)
    axes.margins(x=0.02)
    return HistogramCompareArtists(
        series_labels=series_labels,
        bars_by_series=tuple(tuple(bars) for bars in bars_by_series),
        edges_by_series=tuple(tuple(edges) for edges in edges_by_series),
        legend=legend,
    )


def _compare_series_colors(theme: DrawTheme, series_count: int) -> tuple[str, ...]:
    palette = (
        theme.accent_color,
        comparison_secondary_color(theme),
        "#f59e0b",
        "#22c55e",
        "#ef4444",
        "#06b6d4",
        "#e879f9",
        "#84cc16",
    )
    return tuple(palette[index % len(palette)] for index in range(series_count))


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
    series_values: tuple[tuple[float, ...], ...],
    kind: HistogramKind,
    theme: DrawTheme,
    series_labels: tuple[str, ...],
) -> None:
    """Attach one hover annotation that compares visible series for the hovered bin."""

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
        annotation.set_text(
            _compare_histogram_hover_text(
                state_label=state_labels[hovered_index],
                values=tuple(values[hovered_index] for values in series_values),
                kind=kind,
                series_labels=series_labels,
                visible_series=artists.visible_series,
            )
        )
        position_hover_annotation(
            annotation,
            anchor_x=float(event.x),
            anchor_y=float(event.y),
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
    state_count = len(artists.bars_by_series[0]) if artists.bars_by_series else 0
    for index in range(state_count):
        for series_index, series_bars in enumerate(artists.bars_by_series):
            if not artists.visible_series.get(series_key(series_index), True):
                continue
            bar = series_bars[index]
            if not bar.get_visible():
                continue
            contains, _ = bar.contains(event)
            if contains:
                return index
    return None


def _compare_histogram_hover_text(
    *,
    state_label: str,
    values: tuple[float, ...],
    kind: HistogramKind,
    series_labels: tuple[str, ...],
    visible_series: Mapping[str, bool],
) -> str:
    value_label = "counts" if kind is HistogramKind.COUNTS else "quasi-probability"
    lines = [f"State: {state_label}"]
    visible_values: list[float] = []
    for series_index, (label, value) in enumerate(zip(series_labels, values, strict=True)):
        if not visible_series.get(series_key(series_index), True):
            continue
        visible_values.append(value)
        lines.append(f"{label} {value_label}: {_formatted_histogram_value(value, kind)}")
    if len(visible_values) == 2 and len(values) == 2:
        delta_value = visible_values[0] - visible_values[1]
        lines.append(f"Delta: {_formatted_histogram_value(delta_value, kind)}")
    elif len(visible_values) > 1:
        spread_value = max(visible_values) - min(visible_values)
        lines.append(f"Range: {_formatted_histogram_value(spread_value, kind)}")
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
    series_values: tuple[tuple[float, ...], ...],
    kind: HistogramKind,
) -> None:
    """Select one compare series from legend clicks."""

    legend = artists.legend
    canvas = axes.figure.canvas
    if legend is None or canvas is None:
        return

    handle_artists = tuple(getattr(legend, "legend_handles", ()) or ())
    if len(handle_artists) < len(artists.series_labels):
        handle_artists = tuple(getattr(legend, "legendHandles", ()) or ())
    if len(handle_artists) < len(artists.series_labels):
        return

    legend_targets = {}
    for index, (handle_artist, text_artist) in enumerate(
        zip(handle_artists, legend.get_texts(), strict=False)
    ):
        if index >= len(artists.series_labels):
            break
        key = series_key(index)
        legend_targets[handle_artist] = key
        legend_targets[text_artist] = key

    for artist in legend_targets:
        if hasattr(artist, "set_picker"):
            artist.set_picker(True)

    def apply_visibility() -> None:
        for series_index, (bars, edges) in enumerate(
            zip(artists.bars_by_series, artists.edges_by_series, strict=True)
        ):
            visible = artists.visible_series[series_key(series_index)]
            for bar, edge in zip(bars, edges, strict=True):
                bar.set_visible(visible)
                edge.set_visible(visible)

        active_values: list[float] = []
        for series_index, values in enumerate(series_values):
            if artists.visible_series[series_key(series_index)]:
                active_values.extend(float(value) for value in values)
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

        hover_state = get_hover_state(axes)
        if (
            hover_state is not None
            and getattr(hover_state.annotation, "get_visible", lambda: False)()
        ):
            hover_state.annotation.set_visible(False)

        legend_handle_alpha = {
            series_key(index): 0.72 for index in range(len(artists.series_labels))
        }
        legend_text_alpha = {series_key(index): 1.0 for index in range(len(artists.series_labels))}
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
        artists.visible_series[picked_series] = not artists.visible_series[picked_series]
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
