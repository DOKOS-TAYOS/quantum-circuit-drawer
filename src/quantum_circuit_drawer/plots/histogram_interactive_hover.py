"""Hover helpers for interactive histogram figures."""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.patches import Rectangle

from ..renderers._matplotlib_figure import HoverState, set_hover_state
from .histogram_models import HistogramKind, HistogramStateLabelMode
from .histogram_render import display_state_label

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from ..style.theme import DrawTheme

_HOVER_ZORDER = 10_000


def attach_usage_hover(
    axes: Axes,
    *,
    theme: DrawTheme,
    text: str,
) -> None:
    """Attach one lightweight usage tooltip to a control axes."""

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
    is_visible = False

    def hide_annotation() -> None:
        nonlocal is_visible
        if annotation.get_visible():
            annotation.set_visible(False)
            is_visible = False
            canvas.draw_idle()

    def on_motion(event: Event) -> None:
        nonlocal is_visible
        if not isinstance(event, MouseEvent) or event.inaxes is not axes:
            hide_annotation()
            return
        annotation.xy = (event.x, event.y)
        annotation.set_text(text)
        if is_visible:
            return
        annotation.set_visible(True)
        is_visible = True
        canvas.draw_idle()

    callback_id = canvas.mpl_connect("motion_notify_event", on_motion)
    set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))


def attach_histogram_hover(
    axes: Axes,
    *,
    state_labels: tuple[str, ...],
    values: tuple[float, ...],
    kind: HistogramKind,
    label_mode: HistogramStateLabelMode,
    theme: DrawTheme,
) -> None:
    """Attach hover annotations to histogram bars."""

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
    bars = tuple(patch for patch in axes.patches if isinstance(patch, Rectangle))

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
        hovered_index = _hovered_bar_index(bars, event)
        if hovered_index is None:
            hide_annotation()
            return
        if active_index == hovered_index:
            return
        annotation.xy = (event.x, event.y)
        annotation.set_text(
            _histogram_hover_text(
                state_labels[hovered_index],
                values[hovered_index],
                kind,
                label_mode=label_mode,
            )
        )
        annotation.set_visible(True)
        active_index = hovered_index
        canvas.draw_idle()

    callback_id = canvas.mpl_connect("motion_notify_event", on_motion)
    set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))


def _hovered_bar_index(bars: tuple[Rectangle, ...], event: MouseEvent) -> int | None:
    for index, bar in enumerate(bars):
        contains, _ = bar.contains(event)
        if contains:
            return index
    return None


def _histogram_hover_text(
    state_label: str,
    value: float,
    kind: HistogramKind,
    *,
    label_mode: HistogramStateLabelMode,
) -> str:
    value_label = "Counts" if kind is HistogramKind.COUNTS else "Quasi-probability"
    if label_mode is HistogramStateLabelMode.BINARY:
        displayed_state_label = state_label
        state_label_name = "Bitstring"
    else:
        displayed_state_label = display_state_label(
            state_label,
            mode=HistogramStateLabelMode.DECIMAL,
        )
        state_label_name = "Decimal"
    return (
        f"{state_label_name}: {displayed_state_label}\n"
        f"{value_label}: {_formatted_histogram_value(value, kind)}"
    )


def _formatted_histogram_value(value: float, kind: HistogramKind) -> str:
    if kind is HistogramKind.COUNTS and float(value).is_integer():
        return str(int(value))
    return f"{float(value):.6g}"


__all__ = ["attach_histogram_hover", "attach_usage_hover"]
