"""Hover-target assembly helpers for the Matplotlib 3D renderer."""

from __future__ import annotations

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent

from ._matplotlib_figure import HoverState, set_hover_state

_HOVER_ZORDER = 10_000.0


def attach_hover_3d(
    axes: Axes,
    *,
    hover_targets: list[tuple[Artist, str]],
    hover_facecolor: str,
    hover_edgecolor: str,
    hover_text_color: str,
) -> None:
    """Attach hover annotations to a 3D axes."""

    figure = axes.figure
    annotation = axes.annotate(
        "",
        xy=(0.0, 0.0),
        xytext=(10.0, 10.0),
        xycoords="figure pixels",
        textcoords="offset points",
        visible=False,
        bbox={
            "boxstyle": "round,pad=0.18",
            "fc": hover_facecolor,
            "ec": hover_edgecolor,
            "alpha": 0.9,
        },
        color=hover_text_color,
        annotation_clip=False,
    )
    annotation.set_zorder(_HOVER_ZORDER)
    annotation.set_clip_on(False)

    def _on_move(event: Event) -> None:
        if not isinstance(event, MouseEvent):
            return
        if getattr(event, "inaxes", None) is not axes:
            if annotation.get_visible():
                annotation.set_visible(False)
                figure.canvas.draw_idle()
            return
        for artist, text in hover_targets:
            contains, _ = artist.contains(event) if hasattr(artist, "contains") else (False, {})
            if contains:
                annotation.xy = (
                    float(getattr(event, "x", 0.0)),
                    float(getattr(event, "y", 0.0)),
                )
                annotation.set_text(text)
                annotation.set_visible(True)
                figure.canvas.draw_idle()
                return
        if annotation.get_visible():
            annotation.set_visible(False)
            figure.canvas.draw_idle()

    if figure.canvas is not None:
        callback_id = figure.canvas.mpl_connect("motion_notify_event", _on_move)
        set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))
