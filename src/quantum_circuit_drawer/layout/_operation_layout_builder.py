"""Builder helpers for operation layout scene assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._operation_layout_collections import build_wire_and_label_collections

if TYPE_CHECKING:
    from ._operation_layout import _OperationSceneBuilder, _SceneCollections


def build_scene_collections_impl(builder: _OperationSceneBuilder) -> _SceneCollections:
    wires, texts = build_wire_and_label_collections(builder)

    for column, layer in enumerate(builder.scaffold.normalized_layers):
        x = builder.scaffold.x_centers[column]
        for operation in layer.operations:
            builder._layout_operation(
                operation=operation,
                metrics=builder.scaffold.operation_metrics[id(operation)],
                column=column,
                x=x,
            )

    return builder.scene_collections_type(
        wires=wires,
        texts=texts,
        gates=tuple(builder.gates),
        gate_annotations=tuple(builder.gate_annotations),
        controls=tuple(builder.controls),
        connections=tuple(builder.connections),
        swaps=tuple(builder.swaps),
        barriers=tuple(builder.barriers),
        measurements=tuple(builder.measurements),
    )
