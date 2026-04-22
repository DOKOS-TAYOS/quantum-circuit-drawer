"""Collection assembly helpers for operation layout scene building."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._layout_scaffold import bundle_size
from .scene import SceneText, SceneWire

if TYPE_CHECKING:
    from ._operation_layout import _OperationSceneBuilder


def build_wire_and_label_collections(
    builder: _OperationSceneBuilder,
) -> tuple[tuple[SceneWire, ...], tuple[SceneText, ...]]:
    x_end = builder.scaffold.draw_style.margin_left + (
        builder.scaffold.pages[0].content_width
        if builder.scaffold.pages
        else builder.scaffold.draw_style.gate_width
    )
    wires = tuple(
        SceneWire(
            id=wire.id,
            label=wire.label or wire.id,
            kind=wire.kind,
            y=builder.scaffold.wire_positions[wire.id],
            x_start=builder.scaffold.draw_style.margin_left,
            x_end=x_end,
            bundle_size=bundle_size(wire),
        )
        for wire in builder.circuit.all_wires
    )
    texts = wire_labels(builder)
    return wires, texts


def wire_labels(builder: _OperationSceneBuilder) -> tuple[SceneText, ...]:
    style = builder.scaffold.draw_style
    if not style.show_wire_labels:
        return ()
    return tuple(
        SceneText(
            x=style.margin_left - style.label_margin,
            y=builder.scaffold.wire_positions[wire.id],
            text=wire.label or wire.id,
            ha="right",
            font_size=style.font_size,
            wire_id=wire.id,
        )
        for wire in builder.circuit.all_wires
    )
