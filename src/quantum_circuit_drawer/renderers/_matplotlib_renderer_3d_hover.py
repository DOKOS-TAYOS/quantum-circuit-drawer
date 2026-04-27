"""Hover-target assembly helpers for the Matplotlib 3D renderer."""

from __future__ import annotations

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent

from ..hover import HoverOptions
from ..layout.scene import SceneHoverData
from ._matplotlib_figure import HoverState, set_hover_state
from ._matplotlib_hover import build_hover_text
from ._matplotlib_hover_position import position_hover_annotation

_HOVER_ZORDER = 10_000.0
_DEFAULT_VISIBLE_HOVER_SIZE_PIXELS = 64.0

HoverPayload3D = str | SceneHoverData
HoverTarget3D = tuple[Artist, HoverPayload3D]


def attach_hover_3d(
    axes: Axes,
    *,
    hover_targets: list[HoverTarget3D],
    hover_options: HoverOptions,
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
        for artist, payload in hover_targets:
            contains, _ = artist.contains(event) if hasattr(artist, "contains") else (False, {})
            if contains:
                annotation.set_text(_hover_text_for_payload(artist, payload, hover_options))
                position_hover_annotation(
                    annotation,
                    anchor_x=float(getattr(event, "x", 0.0)),
                    anchor_y=float(getattr(event, "y", 0.0)),
                )
                annotation.set_visible(True)
                figure.canvas.draw_idle()
                return
        if annotation.get_visible():
            annotation.set_visible(False)
            figure.canvas.draw_idle()

    if figure.canvas is not None:
        callback_id = figure.canvas.mpl_connect("motion_notify_event", _on_move)
        set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))


def _hover_text_for_payload(
    artist: Artist,
    payload: HoverPayload3D,
    hover_options: HoverOptions,
) -> str:
    if isinstance(payload, str):
        return payload
    visible_width, visible_height = _artist_visible_size_pixels(artist)
    return build_hover_text(payload, hover_options, visible_width, visible_height)


def _artist_visible_size_pixels(artist: Artist) -> tuple[float, float]:
    try:
        renderer = artist.figure.canvas.get_renderer() if artist.figure.canvas is not None else None
        bbox = artist.get_window_extent(renderer=renderer)
    except (AttributeError, NotImplementedError, RuntimeError, ValueError):
        return (_DEFAULT_VISIBLE_HOVER_SIZE_PIXELS, _DEFAULT_VISIBLE_HOVER_SIZE_PIXELS)

    if bbox.width <= 0.0 or bbox.height <= 0.0:
        return (_DEFAULT_VISIBLE_HOVER_SIZE_PIXELS, _DEFAULT_VISIBLE_HOVER_SIZE_PIXELS)
    return (float(bbox.width), float(bbox.height))
