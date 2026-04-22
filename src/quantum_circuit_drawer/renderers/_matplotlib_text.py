"""2D Matplotlib text fitting and label helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from matplotlib.axes import Axes
from matplotlib.textpath import TextPath

from ..layout.scene import LayoutScene, SceneConnection
from ..utils.formatting import format_visible_label
from ._matplotlib_axes import _default_font_properties
from ._matplotlib_figure import get_viewport_width

_GateTextCacheKey = tuple[object, ...]
_GateTextCache = dict[_GateTextCacheKey, float]
_GATE_TEXT_CACHE_MAX_ENTRIES = 4096
_SINGLE_LINE_HEIGHT_FRACTION = 0.62
_STACKED_TEXT_USABLE_HEIGHT_FRACTION = 0.72
_MULTILINE_TEXT_LINE_SPACING = 1.2
_MIN_GATE_TEXT_FONT_SIZE = 0.7
_MATHTEXT_WIDTH_PADDING_FACTOR = 1.25
_MATHTEXT_HEIGHT_PADDING_FACTOR = 1.1
_MEASUREMENT_LABEL_FONT_SCALE = 0.62
_MEASUREMENT_CLASSICAL_LABEL_FONT_SCALE = 0.56
_MEASUREMENT_CLASSICAL_LABEL_PATTERN = re.compile(r"^.+\[(\d+)\]$")
_PLAIN_TEXT_CONNECTION_LABEL_PATTERN = re.compile(r"[&|!<>()]")
_GATE_TEXT_CONTEXT_CACHE_ATTR = "_quantum_circuit_drawer_gate_text_context_cache"
_NUMERIC_TEXT_PATTERN = re.compile(
    r"^[+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?(?:, [+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?)*$"
)
_SHAPE_METRICS_CACHE_SIZE = 256


@dataclass(frozen=True, slots=True)
class _GateTextFittingContext:
    default_scale: float
    points_per_layout_unit: float


@dataclass(frozen=True, slots=True)
class _ConnectionLabelStyle:
    text: str
    font_size: float
    bbox: Mapping[str, object]


def trim_gate_text_fit_cache(
    cache: _GateTextCache,
    *,
    max_entries: int = _GATE_TEXT_CACHE_MAX_ENTRIES,
) -> None:
    """Keep one shared text-fit cache bounded without dropping recent inserts immediately."""

    while len(cache) > max_entries:
        cache.pop(next(iter(cache)))


def _measurement_half_gate_box(scene: LayoutScene) -> tuple[float, float]:
    return scene.style.gate_width * 0.5, scene.style.gate_height * 0.5


def _is_measurement_classical_connection_label(connection: SceneConnection) -> bool:
    return (
        connection.is_classical
        and connection.label is not None
        and not connection.double_line
        and connection.linestyle == "dashed"
    )


def _fit_static_text_font_size(
    ax: Axes,
    scene: LayoutScene,
    *,
    text: str,
    default_font_size: float,
    available_width: float,
    available_height: float,
    context: _GateTextFittingContext | None = None,
    cache: _GateTextCache | None = None,
) -> float:
    resolved_context = context or _build_gate_text_fitting_context(ax, scene)
    return _fit_gate_text_font_size_with_context(
        context=resolved_context,
        width=available_width,
        height=available_height,
        text=text,
        default_font_size=default_font_size,
        height_fraction=1.0,
        max_font_size=default_font_size,
        cache={} if cache is None else cache,
    )


def _compact_measurement_classical_label(label: str) -> str | None:
    match = _MEASUREMENT_CLASSICAL_LABEL_PATTERN.match(label)
    if match is None:
        return None
    return f"[{match.group(1)}]"


def _connection_label_style(
    ax: Axes,
    connection: SceneConnection,
    scene: LayoutScene,
    label: str,
    *,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> _ConnectionLabelStyle:
    default_bbox: Mapping[str, object] = {
        "boxstyle": "round,pad=0.12,rounding_size=0.08",
        "facecolor": scene.style.theme.axes_facecolor,
        "edgecolor": "none",
    }
    if not _is_measurement_classical_connection_label(connection):
        return _ConnectionLabelStyle(
            text=_format_connection_label(label, use_mathtext=scene.style.use_mathtext),
            font_size=scene.style.font_size * 0.7,
            bbox=default_bbox,
        )

    default_font_size = scene.style.font_size * _MEASUREMENT_CLASSICAL_LABEL_FONT_SCALE
    available_width, available_height = _measurement_half_gate_box(scene)
    visible_label = format_visible_label(label, use_mathtext=scene.style.use_mathtext)
    fitted_full_font_size = _fit_static_text_font_size(
        ax,
        scene,
        text=visible_label,
        default_font_size=default_font_size,
        available_width=available_width,
        available_height=available_height,
        context=text_fit_context,
        cache=text_fit_cache,
    )
    compact_label = _compact_measurement_classical_label(label)
    if compact_label is None or fitted_full_font_size >= default_font_size:
        return _ConnectionLabelStyle(
            text=visible_label,
            font_size=fitted_full_font_size,
            bbox={
                "boxstyle": "round,pad=0.06,rounding_size=0.06",
                "facecolor": scene.style.theme.axes_facecolor,
                "edgecolor": "none",
            },
        )

    visible_compact_label = format_visible_label(
        compact_label,
        use_mathtext=scene.style.use_mathtext,
    )
    compact_font_size = _fit_static_text_font_size(
        ax,
        scene,
        text=visible_compact_label,
        default_font_size=default_font_size,
        available_width=available_width,
        available_height=available_height,
        context=text_fit_context,
        cache=text_fit_cache,
    )
    return _ConnectionLabelStyle(
        text=visible_compact_label,
        font_size=compact_font_size,
        bbox={
            "boxstyle": "round,pad=0.05,rounding_size=0.05",
            "facecolor": scene.style.theme.axes_facecolor,
            "edgecolor": "none",
        },
    )


def _format_connection_label(label: str, *, use_mathtext: bool) -> str:
    if use_mathtext and _PLAIN_TEXT_CONNECTION_LABEL_PATTERN.search(label):
        return label
    return format_visible_label(label, use_mathtext=use_mathtext)


def _fit_gate_text_font_size(
    *,
    ax: Axes,
    scene: LayoutScene,
    width: float,
    height: float | None = None,
    text: str,
    default_font_size: float,
    height_fraction: float = _SINGLE_LINE_HEIGHT_FRACTION,
    max_font_size: float | None = None,
    context: _GateTextFittingContext | None = None,
    cache: _GateTextCache | None = None,
) -> float:
    """Shrink gate text when the rendered box is too narrow for the label."""

    resolved_context = context or _build_gate_text_fitting_context(ax, scene)
    return _fit_gate_text_font_size_with_context(
        context=resolved_context,
        width=width,
        height=height,
        text=text,
        default_font_size=default_font_size,
        height_fraction=height_fraction,
        max_font_size=max_font_size,
        cache={} if cache is None else cache,
    )


def _build_gate_text_fitting_context(ax: Axes, scene: LayoutScene) -> _GateTextFittingContext:
    effective_default_scale = _page_wrapped_font_scale(scene)
    axes_width_fraction = ax.get_position().width
    x_limits = ax.get_xlim()
    scene_width = abs(x_limits[1] - x_limits[0])
    figure = ax.figure
    canvas_width_pixels = (
        figure.canvas.get_width_height()[0]
        if figure.canvas is not None
        else figure.get_size_inches()[0] * figure.dpi
    )
    cache_key = (
        round(effective_default_scale, 9),
        round(axes_width_fraction, 9),
        round(x_limits[0], 9),
        round(x_limits[1], 9),
        round(scene_width, 9),
        round(canvas_width_pixels),
        round(figure.dpi, 6),
    )
    cached_context = getattr(ax, _GATE_TEXT_CONTEXT_CACHE_ATTR, None)
    if (
        isinstance(cached_context, tuple)
        and len(cached_context) == 2
        and cached_context[0] == cache_key
        and isinstance(cached_context[1], _GateTextFittingContext)
    ):
        return cached_context[1]

    if axes_width_fraction <= 0.0 or scene_width <= 0.0:
        empty_context = _GateTextFittingContext(
            default_scale=effective_default_scale,
            points_per_layout_unit=0.0,
        )
        setattr(ax, _GATE_TEXT_CONTEXT_CACHE_ATTR, (cache_key, empty_context))
        return empty_context

    effective_scene_width = min(
        scene_width,
        get_viewport_width(figure, default=scene_width),
    )
    axes_width_points = (canvas_width_pixels * axes_width_fraction) * 72.0 / figure.dpi
    available_width_fraction = 0.74
    context = _GateTextFittingContext(
        default_scale=effective_default_scale,
        points_per_layout_unit=(axes_width_points * available_width_fraction)
        / effective_scene_width,
    )
    setattr(ax, _GATE_TEXT_CONTEXT_CACHE_ATTR, (cache_key, context))
    return context


def _fit_gate_text_font_size_with_context(
    *,
    context: _GateTextFittingContext,
    width: float,
    height: float | None = None,
    text: str,
    default_font_size: float,
    height_fraction: float = _SINGLE_LINE_HEIGHT_FRACTION,
    max_font_size: float | None = None,
    cache: _GateTextCache,
) -> float:
    """Shrink gate text using a per-page context and cache."""

    if not text:
        return default_font_size

    effective_default_font_size = (
        max_font_size if max_font_size is not None else default_font_size * context.default_scale
    )
    if context.points_per_layout_unit <= 0.0:
        return effective_default_font_size

    cache_key = _gate_text_fit_cache_key(
        context=context,
        width=width,
        height=height,
        text=text,
        default_font_size=default_font_size,
        height_fraction=height_fraction,
        max_font_size=max_font_size,
    )
    cached_font_size = cache.get(cache_key)
    if cached_font_size is not None:
        return cached_font_size

    available_width_points = context.points_per_layout_unit * width
    text_width_at_one_point = _text_width_in_points(text)
    if _is_mathtext_string(text):
        text_width_at_one_point *= _MATHTEXT_WIDTH_PADDING_FACTOR
    if text_width_at_one_point <= 0.0:
        cache[cache_key] = effective_default_font_size
        return effective_default_font_size

    fitted_font_size = available_width_points / text_width_at_one_point
    resolved_font_size = min(effective_default_font_size, fitted_font_size)
    if height is not None:
        available_height_points = context.points_per_layout_unit * height * height_fraction
        text_height_at_one_point = _text_height_in_points(
            text,
            line_spacing=_resolved_multiline_text_line_spacing(text, resolved_font_size),
        )
        if _is_mathtext_string(text):
            text_height_at_one_point *= _MATHTEXT_HEIGHT_PADDING_FACTOR
        if text_height_at_one_point > 0.0:
            resolved_font_size = min(
                resolved_font_size,
                available_height_points / text_height_at_one_point,
            )
            adjusted_text_height = _text_height_in_points(
                text,
                line_spacing=_resolved_multiline_text_line_spacing(text, resolved_font_size),
            )
            if _is_mathtext_string(text):
                adjusted_text_height *= _MATHTEXT_HEIGHT_PADDING_FACTOR
            if adjusted_text_height > 0.0:
                resolved_font_size = min(
                    resolved_font_size,
                    available_height_points / adjusted_text_height,
                )
    resolved_font_size = max(_MIN_GATE_TEXT_FONT_SIZE, resolved_font_size)
    cache[cache_key] = resolved_font_size
    return resolved_font_size


def _gate_text_fit_cache_key(
    *,
    context: _GateTextFittingContext,
    width: float,
    height: float | None,
    text: str,
    default_font_size: float,
    height_fraction: float,
    max_font_size: float | None,
) -> _GateTextCacheKey:
    return (
        round(context.default_scale, 9),
        round(context.points_per_layout_unit, 9),
        _gate_text_fit_cache_token(text),
        round(width, 9),
        None if height is None else round(height, 9),
        round(default_font_size, 9),
        round(height_fraction, 9),
        None if max_font_size is None else round(max_font_size, 9),
    )


def _page_wrapped_font_scale(scene: LayoutScene) -> float:
    page_count = (
        scene.page_count_for_text_scale
        if scene.page_count_for_text_scale is not None
        else len(scene.pages)
    )
    if page_count <= 1:
        return 1.0
    return 0.9 * max(0.4, 1.0 - ((page_count - 2) * 0.035))


def _gate_text_fit_cache_token(text: str) -> object:
    shape_key = _text_shape_key(text)
    if shape_key is not None:
        return shape_key
    return text


def _is_mathtext_string(text: str) -> bool:
    if "\n" in text:
        text_lines = [line for line in text.split("\n") if line]
        return bool(text_lines) and all(_is_mathtext_string(line) for line in text_lines)
    return len(text) >= 2 and text.startswith("$") and text.endswith("$")


def _text_shape_key(text: str) -> tuple[str, str] | None:
    if not text:
        return None
    if _NUMERIC_TEXT_PATTERN.fullmatch(text):
        return ("numeric", re.sub(r"\d", "0", text))
    return None


def _text_shape_sample(shape_key: tuple[str, str]) -> str:
    shape_kind, normalized_text = shape_key
    if shape_kind == "numeric":
        return normalized_text
    raise ValueError(f"unknown text shape kind: {shape_kind}")


@lru_cache(maxsize=_SHAPE_METRICS_CACHE_SIZE)
def _text_shape_metrics_in_points(shape_key: tuple[str, str]) -> tuple[float, float]:
    sample_text = _text_shape_sample(shape_key)
    extents = TextPath(
        (0.0, 0.0),
        sample_text,
        size=1.0,
        prop=_default_font_properties(),
    ).get_extents()
    return float(extents.width), float(extents.height)


@lru_cache(maxsize=128)
def _text_width_in_points(text: str) -> float:
    if "\n" in text:
        return max((_text_width_in_points(line) for line in text.split("\n")), default=0.0)
    shape_key = _text_shape_key(text)
    if shape_key is not None:
        return _text_shape_metrics_in_points(shape_key)[0]
    return TextPath((0.0, 0.0), text, size=1.0, prop=_default_font_properties()).get_extents().width


@lru_cache(maxsize=128)
def _text_height_in_points(
    text: str,
    *,
    line_spacing: float = _MULTILINE_TEXT_LINE_SPACING,
) -> float:
    if "\n" in text:
        line_heights = [_text_height_in_points(line) for line in text.split("\n")]
        if not line_heights:
            return 0.0
        max_line_height = max(line_heights)
        extra_line_spacing = max(0.0, line_spacing - 1.0)
        return sum(line_heights) + (max_line_height * (len(line_heights) - 1) * extra_line_spacing)
    shape_key = _text_shape_key(text)
    if shape_key is not None:
        return _text_shape_metrics_in_points(shape_key)[1]
    return (
        TextPath((0.0, 0.0), text, size=1.0, prop=_default_font_properties()).get_extents().height
    )


def _multiline_text_line_spacing(font_size: float) -> float:
    if font_size <= 0.0:
        return 0.9
    normalized_font_size = min(1.0, font_size / 12.0)
    return 0.9 + ((_MULTILINE_TEXT_LINE_SPACING - 0.9) * normalized_font_size)


def _resolved_multiline_text_line_spacing(text: str, font_size: float) -> float:
    if "\n" not in text:
        return _MULTILINE_TEXT_LINE_SPACING
    return _multiline_text_line_spacing(font_size)
