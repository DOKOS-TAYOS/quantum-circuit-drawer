"""Viewport-aware placement helpers for Matplotlib hover annotations."""

from __future__ import annotations

from matplotlib.backend_bases import RendererBase
from matplotlib.text import Annotation
from matplotlib.transforms import Bbox

_DEFAULT_HOVER_OFFSET_POINTS = 10.0
_DEFAULT_VIEWPORT_PADDING_PIXELS = 4.0


def position_hover_annotation(
    annotation: Annotation,
    *,
    anchor_x: float,
    anchor_y: float,
    offset_points: float = _DEFAULT_HOVER_OFFSET_POINTS,
    viewport_padding_pixels: float = _DEFAULT_VIEWPORT_PADDING_PIXELS,
) -> None:
    """Place one hover annotation near the cursor while keeping it on-screen."""

    annotation.xy = (anchor_x, anchor_y)
    figure = annotation.figure
    canvas = figure.canvas if figure is not None else None
    if figure is None or canvas is None:
        return

    renderer = _annotation_renderer(canvas)
    if renderer is None:
        return

    width_pixels, height_pixels = _annotation_size_pixels(annotation, renderer)
    if width_pixels <= 0.0 or height_pixels <= 0.0:
        return

    figure_width = float(figure.bbox.width)
    figure_height = float(figure.bbox.height)
    offset_pixels = _points_to_pixels(offset_points, dpi=float(figure.dpi))

    place_left = not _fits_right(
        anchor_x,
        width_pixels,
        offset_pixels,
        figure_width,
        viewport_padding_pixels,
    ) and _fits_left(anchor_x, width_pixels, offset_pixels, viewport_padding_pixels)
    place_below = not _fits_above(
        anchor_y,
        height_pixels,
        offset_pixels,
        figure_height,
        viewport_padding_pixels,
    ) and _fits_below(anchor_y, height_pixels, offset_pixels, viewport_padding_pixels)

    x_offset_points = -offset_points if place_left else offset_points
    y_offset_points = -offset_points if place_below else offset_points
    annotation.set_horizontalalignment("right" if place_left else "left")
    annotation.set_verticalalignment("top" if place_below else "bottom")
    annotation.set_position((x_offset_points, y_offset_points))

    clamped_x_points, clamped_y_points = _clamped_annotation_offset_points(
        annotation,
        renderer,
        dpi=float(figure.dpi),
        viewport_padding_pixels=viewport_padding_pixels,
        x_offset_points=x_offset_points,
        y_offset_points=y_offset_points,
        figure_width=figure_width,
        figure_height=figure_height,
    )
    annotation.set_position((clamped_x_points, clamped_y_points))


def _clamped_annotation_offset_points(
    annotation: Annotation,
    renderer: RendererBase,
    *,
    dpi: float,
    viewport_padding_pixels: float,
    x_offset_points: float,
    y_offset_points: float,
    figure_width: float,
    figure_height: float,
) -> tuple[float, float]:
    bbox = _annotation_bbox(annotation, renderer)
    shift_x_pixels = 0.0
    shift_y_pixels = 0.0

    left_bound = viewport_padding_pixels
    right_bound = figure_width - viewport_padding_pixels
    bottom_bound = viewport_padding_pixels
    top_bound = figure_height - viewport_padding_pixels

    if bbox.x0 < left_bound:
        shift_x_pixels = left_bound - float(bbox.x0)
    elif bbox.x1 > right_bound:
        shift_x_pixels = right_bound - float(bbox.x1)

    if bbox.y0 < bottom_bound:
        shift_y_pixels = bottom_bound - float(bbox.y0)
    elif bbox.y1 > top_bound:
        shift_y_pixels = top_bound - float(bbox.y1)

    return (
        x_offset_points + _pixels_to_points(shift_x_pixels, dpi=dpi),
        y_offset_points + _pixels_to_points(shift_y_pixels, dpi=dpi),
    )


def _annotation_size_pixels(
    annotation: Annotation,
    renderer: RendererBase,
) -> tuple[float, float]:
    bbox = _annotation_bbox(annotation, renderer)
    return (float(bbox.width), float(bbox.height))


def _annotation_bbox(
    annotation: Annotation,
    renderer: RendererBase,
) -> Bbox:
    was_visible = annotation.get_visible()
    if not was_visible:
        annotation.set_visible(True)
    try:
        return annotation.get_window_extent(renderer=renderer)
    finally:
        annotation.set_visible(was_visible)


def _annotation_renderer(canvas: object) -> RendererBase | None:
    if not hasattr(canvas, "get_renderer"):
        return None
    try:
        renderer = canvas.get_renderer()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    return renderer if isinstance(renderer, RendererBase) else renderer


def _fits_right(
    anchor_x: float,
    width_pixels: float,
    offset_pixels: float,
    figure_width: float,
    viewport_padding_pixels: float,
) -> bool:
    return anchor_x + offset_pixels + width_pixels <= figure_width - viewport_padding_pixels


def _fits_left(
    anchor_x: float,
    width_pixels: float,
    offset_pixels: float,
    viewport_padding_pixels: float,
) -> bool:
    return anchor_x - offset_pixels - width_pixels >= viewport_padding_pixels


def _fits_above(
    anchor_y: float,
    height_pixels: float,
    offset_pixels: float,
    figure_height: float,
    viewport_padding_pixels: float,
) -> bool:
    return anchor_y + offset_pixels + height_pixels <= figure_height - viewport_padding_pixels


def _fits_below(
    anchor_y: float,
    height_pixels: float,
    offset_pixels: float,
    viewport_padding_pixels: float,
) -> bool:
    return anchor_y - offset_pixels - height_pixels >= viewport_padding_pixels


def _points_to_pixels(value_points: float, *, dpi: float) -> float:
    return float(value_points) * float(dpi) / 72.0


def _pixels_to_points(value_pixels: float, *, dpi: float) -> float:
    return float(value_pixels) * 72.0 / float(dpi)
