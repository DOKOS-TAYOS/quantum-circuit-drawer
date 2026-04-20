"""Low-level Matplotlib axes and artist helpers for 2D rendering."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from types import MethodType
from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.collections import EllipseCollection, LineCollection
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from ..layout.scene import LayoutScene

BASE_LAYER_ZORDER = 1
CONNECTION_LAYER_ZORDER = 2
OCCLUSION_LAYER_ZORDER = 4
SYMBOL_LAYER_ZORDER = 5
TEXT_LAYER_ZORDER = 6
LineSegment = tuple[tuple[float, float], tuple[float, float]]
_WINDOWED_CLIP_ATTR = "_quantum_circuit_drawer_windowed_clip"


def prepare_axes(ax: Axes, scene: LayoutScene) -> None:
    """Prepare one 2D Matplotlib axes for scene drawing."""

    ax.set_xlim(0.0, scene.width)
    ax.set_ylim(scene.height, 0.0)
    ax.set_facecolor(scene.style.theme.axes_facecolor)
    ax.set_autoscale_on(False)
    ax.set_aspect("equal", adjustable="box")


def _supports_fast_patch_artist_path(ax: Axes) -> bool:
    return callable(getattr(ax, "_set_artist_props", None)) and isinstance(
        getattr(ax, "_children", None),
        list,
    )


def _supports_fast_text_artist_path(ax: Axes) -> bool:
    return callable(getattr(ax, "_add_text", None))


def _add_patch_artist(ax: Axes, patch: Patch) -> Patch:
    if not _supports_fast_patch_artist_path(ax):
        ax.add_artist(patch)
        _apply_axes_artist_clip(ax, patch)
        return patch

    children = cast(list[object], getattr(ax, "_children"))
    set_artist_props = cast(Any, getattr(ax, "_set_artist_props"))
    patch.axes = ax
    children.append(patch)
    setattr(patch, "_remove_method", children.remove)
    set_artist_props(patch)
    _apply_axes_artist_clip(ax, patch)
    ax.stale = True
    return patch


def _add_text_artist(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    fontdict: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> Text:
    fontdict_dict = dict(fontdict) if fontdict is not None else None
    clip_on = _axes_should_clip_artists(ax)
    if not _supports_fast_text_artist_path(ax):
        resolved_kwargs = dict(kwargs)
        resolved_kwargs.setdefault("clip_on", clip_on)
        if "fontsize" in resolved_kwargs and "fontproperties" not in resolved_kwargs:
            resolved_kwargs["fontproperties"] = _font_properties_for_size(
                float(resolved_kwargs.pop("fontsize"))
            )
        text_artist = ax.text(x, y, text, fontdict=fontdict_dict, **resolved_kwargs)
        _apply_axes_artist_clip(ax, text_artist)
        return text_artist

    effective_kwargs: dict[str, Any] = {
        "verticalalignment": "baseline",
        "horizontalalignment": "left",
        "transform": ax.transData,
        "clip_on": clip_on,
    }
    if fontdict_dict is not None:
        effective_kwargs.update(fontdict_dict)
    effective_kwargs.update(kwargs)
    if "fontsize" in effective_kwargs and "fontproperties" not in effective_kwargs:
        effective_kwargs["fontproperties"] = _font_properties_for_size(
            float(effective_kwargs.pop("fontsize"))
        )
    text_artist = Text(x=x, y=y, text=text, **effective_kwargs)
    add_text = cast(Any, getattr(ax, "_add_text"))
    added_text = cast(Text, add_text(text_artist))
    _apply_axes_artist_clip(ax, added_text)
    return added_text


def _add_line_collection(
    ax: Axes,
    segments: Sequence[LineSegment],
    *,
    color: str,
    linewidth: float,
    zorder: int,
    linestyle: str | tuple[int, tuple[int, int]] = "solid",
    capstyle: str = "round",
) -> LineCollection | None:
    if not segments:
        return None

    clip_on = _axes_should_clip_artists(ax)
    collection = LineCollection(
        segments,
        colors=color,
        linewidths=linewidth,
        linestyles=linestyle,
        capstyle=capstyle,
        zorder=zorder,
        clip_on=clip_on,
    )
    ax.add_collection(collection)
    _apply_axes_artist_clip(ax, collection)
    return collection


def _add_ellipse_collection(
    ax: Axes,
    *,
    widths: Sequence[float],
    heights: Sequence[float],
    offsets: Sequence[tuple[float, float]],
    facecolor: str,
    edgecolor: str,
    linewidth: float,
    zorder: int,
) -> EllipseCollection | None:
    if not offsets:
        return None

    clip_on = _axes_should_clip_artists(ax)
    collection = EllipseCollection(
        widths=widths,
        heights=heights,
        angles=[0.0] * len(offsets),
        units="xy",
        offsets=offsets,
        transOffset=ax.transData,
        facecolors=facecolor,
        edgecolors=edgecolor,
        linewidths=linewidth,
        zorder=zorder,
        clip_on=clip_on,
    )
    ax.add_collection(collection)
    _apply_axes_artist_clip(ax, collection)
    x_min = float("inf")
    x_max = float("-inf")
    y_min = float("inf")
    y_max = float("-inf")
    for (x, y), width, height in zip(offsets, widths, heights, strict=True):
        half_width = width / 2.0
        half_height = height / 2.0
        x_min = min(x_min, x - half_width)
        x_max = max(x_max, x + half_width)
        y_min = min(y_min, y - half_height)
        y_max = max(y_max, y + half_height)
    _set_artist_data_extent(
        ax,
        collection,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
    )
    return collection


def _set_artist_data_extent(
    ax: Axes,
    artist: object,
    *,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    def data_extent(_artist: object, renderer: object = None) -> Bbox:
        del renderer
        return ax.transData.transform_bbox(
            Bbox.from_extents(
                min(x_min, x_max),
                min(y_min, y_max),
                max(x_min, x_max),
                max(y_min, y_max),
            )
        )

    setattr(artist, "get_window_extent", MethodType(data_extent, artist))


def _axes_should_clip_artists(ax: Axes) -> bool:
    return bool(getattr(ax, _WINDOWED_CLIP_ATTR, False))


def _apply_axes_artist_clip(ax: Axes, artist: object) -> None:
    if not _axes_should_clip_artists(ax):
        return
    if hasattr(artist, "set_clip_on"):
        cast(Any, artist).set_clip_on(True)
    if hasattr(artist, "set_clip_path"):
        cast(Any, artist).set_clip_path(ax.patch)


@lru_cache(maxsize=32)
def _font_properties_for_size(font_size: float) -> FontProperties:
    return FontProperties(size=font_size)


@lru_cache(maxsize=1)
def _default_font_properties() -> FontProperties:
    return FontProperties()


def finalize_axes(ax: Axes) -> None:
    """Hide axes furniture after scene drawing."""

    ax.axis("off")
