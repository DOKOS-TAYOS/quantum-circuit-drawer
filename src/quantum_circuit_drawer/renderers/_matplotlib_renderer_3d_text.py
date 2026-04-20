"""Text-path helpers for the Matplotlib 3D renderer."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D, Bbox

from ..layout.scene_3d import LayoutScene3D
from ..utils.formatting import format_gate_text_block, format_parameter_text, format_visible_label
from .matplotlib_primitives import _default_font_properties

_MULTILINE_TEXT_LINE_SPACING = 1.2
_TextPathCacheKey = tuple[str, float, str, str]


@lru_cache(maxsize=256)
def _aligned_text_path(key: _TextPathCacheKey) -> Path:
    text, font_size, ha, va = key
    if "\n" in text:
        text_path = _multiline_text_path(text, font_size)
    else:
        text_path = TextPath((0.0, 0.0), text, size=font_size, prop=_default_font_properties())
    extents = text_path.get_extents()
    x_anchor = _text_horizontal_anchor(extents, ha)
    y_anchor = _text_vertical_anchor(extents, va)
    return Affine2D().translate(-x_anchor, -y_anchor).transform_path(text_path)


def _multiline_text_path(text: str, font_size: float) -> Path:
    line_paths: list[Path] = []
    line_height = 0.0
    for line in text.split("\n"):
        current_path = TextPath((0.0, 0.0), line, size=font_size, prop=_default_font_properties())
        current_extents = current_path.get_extents()
        line_height = max(line_height, float(current_extents.height))
        line_paths.append(current_path)

    if not line_paths:
        return Path(np.empty((0, 2), dtype=float), np.empty((0,), dtype=np.uint8))

    positioned_paths: list[Path] = []
    line_count = len(line_paths)
    for index, line_path in enumerate(line_paths):
        extents = line_path.get_extents()
        center_x = float(extents.x0 + (extents.width / 2.0))
        center_y = float(extents.y0 + (extents.height / 2.0))
        target_center_y = (
            ((line_count - 1) / 2.0 - index) * line_height * _MULTILINE_TEXT_LINE_SPACING
        )
        positioned_paths.append(
            Affine2D().translate(-center_x, target_center_y - center_y).transform_path(line_path)
        )
    return Path.make_compound_path(*positioned_paths)


def _text_horizontal_anchor(extents: Bbox, ha: str) -> float:
    resolved_ha = ha.lower()
    if resolved_ha == "left":
        return float(extents.x0)
    if resolved_ha == "right":
        return float(extents.x1)
    return float(extents.x0 + (extents.width / 2.0))


def _text_vertical_anchor(extents: Bbox, va: str) -> float:
    resolved_va = va.lower()
    if resolved_va == "bottom":
        return float(extents.y0)
    if resolved_va == "top":
        return float(extents.y1)
    if resolved_va in {"baseline", "center_baseline"}:
        return 0.0
    return float(extents.y0 + (extents.height / 2.0))


def _visible_3d_text_value(text: str, *, role: str, scene: LayoutScene3D) -> str:
    if role == "gate_label_block":
        label, _, subtitle = text.partition("\n")
        return format_gate_text_block(
            label,
            subtitle or None,
            use_mathtext=scene.style.use_mathtext,
        )
    if role == "parameter":
        return format_parameter_text(text, use_mathtext=scene.style.use_mathtext)
    return format_visible_label(text, use_mathtext=scene.style.use_mathtext)
