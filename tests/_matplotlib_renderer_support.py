# ruff: noqa: F401
from __future__ import annotations

import matplotlib.pyplot as plt
import pytest
from matplotlib.artist import Artist
from matplotlib.backend_bases import MouseEvent
from matplotlib.collections import EllipseCollection
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch
from matplotlib.text import Annotation, Text
from pytest import approx

import quantum_circuit_drawer.renderers.matplotlib_primitives as matplotlib_primitives
import quantum_circuit_drawer.renderers.matplotlib_renderer as matplotlib_renderer_module
from quantum_circuit_drawer import HoverOptions
from quantum_circuit_drawer.ir import ClassicalConditionIR
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.layout.scene import LayoutScene, SceneGate, ScenePage, SceneWire
from quantum_circuit_drawer.renderers.matplotlib_renderer import MatplotlibRenderer
from quantum_circuit_drawer.style import DrawStyle
from tests.support import (
    assert_axes_contains_circuit_artists,
    assert_figure_has_visible_content,
    build_dense_rotation_ir,
    build_sample_ir,
    build_sample_scene,
    build_wrapped_ir,
    normalize_rendered_text,
)
from tests.support import (
    draw_quantum_circuit_legacy as draw_quantum_circuit,
)

pytestmark = pytest.mark.renderer


def _display_patch_ratio(figure: object, patch: object) -> float:
    renderer = figure.canvas.get_renderer()
    bounds = patch.get_window_extent(renderer=renderer).bounds
    _, _, width, height = bounds
    return width / height


def _display_bounds(figure: object, artist: object) -> tuple[float, float, float, float]:
    renderer = figure.canvas.get_renderer()
    bounds = artist.get_window_extent(renderer=renderer).bounds
    return bounds


def _normalized_axis_text_values(axes: object) -> set[str]:
    return {normalize_rendered_text(text.get_text()) for text in axes.texts}


def _find_axis_text(axes: object, expected_text: str) -> Text:
    return next(
        text for text in axes.texts if normalize_rendered_text(text.get_text()) == expected_text
    )


def _measurement_register_ir(*, measurement_count: int) -> CircuitIR:
    quantum_wires = [
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(measurement_count)
    ]
    return CircuitIR(
        quantum_wires=quantum_wires,
        classical_wires=[
            WireIR(
                id="c",
                index=0,
                kind=WireKind.CLASSICAL,
                label="c",
                metadata={"bundle_size": measurement_count},
            )
        ],
        layers=[
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=(f"q{layer_index}",),
                        classical_target="c",
                        metadata={"classical_bit_label": f"c[{layer_index}]"},
                    )
                ]
            )
            for layer_index in range(measurement_count)
        ],
    )


def _single_measurement_ir(*, classical_label: str, bit_label: str) -> CircuitIR:
    return CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label=classical_label)],
        layers=[
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                        metadata={"classical_bit_label": bit_label},
                    )
                ]
            )
        ],
    )


def _overlap_count(figure: object, texts: list[Text]) -> int:
    renderer = figure.canvas.get_renderer()
    overlap_count = 0
    for left, right in zip(texts, texts[1:]):
        if left.get_window_extent(renderer=renderer).overlaps(
            right.get_window_extent(renderer=renderer)
        ):
            overlap_count += 1
    return overlap_count


def _outside_axes_artist_count(figure: object, axes: object, artists: object) -> int:
    renderer = figure.canvas.get_renderer()
    axes_bounds = axes.get_window_extent(renderer=renderer)
    outside = 0
    for artist in artists:
        x, y, width, height = artist.get_window_extent(renderer=renderer).bounds
        if (
            x < axes_bounds.x0
            or x + width > axes_bounds.x1
            or y < axes_bounds.y0
            or y + height > axes_bounds.y1
        ):
            outside += 1
    return outside


def _line_artist_count(axes: object) -> int:
    collection_count = sum(
        1
        for collection in axes.collections
        if hasattr(collection, "get_segments") and len(collection.get_segments()) > 0
    )
    return len(axes.lines) + collection_count


def _background_line_zorders(axes: object) -> list[float]:
    zorders = [line.get_zorder() for line in axes.lines if line.get_zorder() <= 2]
    zorders.extend(
        collection.get_zorder()
        for collection in axes.collections
        if hasattr(collection, "get_segments")
        and len(collection.get_segments()) > 0
        and collection.get_zorder() <= 2
    )
    return zorders


def _ellipse_collections(axes: object) -> list[EllipseCollection]:
    return [
        collection for collection in axes.collections if isinstance(collection, EllipseCollection)
    ]


def _dispatch_motion_event(figure: object, axes: object, artist: object) -> None:
    renderer = figure.canvas.get_renderer()
    x, y, width, height = artist.get_window_extent(renderer=renderer).bounds
    event = MouseEvent(
        "motion_notify_event",
        figure.canvas,
        x + (width / 2.0),
        y + (height / 2.0),
    )
    figure.canvas.callbacks.process("motion_notify_event", event)


def _dispatch_motion_event_at(
    figure: object,
    x: float,
    y: float,
) -> None:
    event = MouseEvent(
        "motion_notify_event",
        figure.canvas,
        x,
        y,
    )
    figure.canvas.callbacks.process("motion_notify_event", event)


def _single_gate_with_matrix_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q0",),
                        metadata={"matrix": ((0, 1), (1, 0))},
                    )
                ]
            )
        ],
    )


def _single_gate_without_matrix_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q0",))]
            )
        ],
    )


def _hover_batching_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
            WireIR(id="q2", index=2, kind=WireKind.QUANTUM, label="q2"),
            WireIR(id="q3", index=3, kind=WireKind.QUANTUM, label="q3"),
        ],
        classical_wires=[
            WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0"),
            WireIR(id="c1", index=1, kind=WireKind.CLASSICAL, label="c1"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        canonical_family=CanonicalGateFamily.X,
                        target_wires=("q1",),
                        control_wires=("q0",),
                    ),
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        canonical_family=CanonicalGateFamily.X,
                        target_wires=("q3",),
                        control_wires=("q2",),
                    ),
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=("q0", "q1")),
                    OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=("q2", "q3")),
                ]
            ),
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q1",),
                        classical_target="c0",
                    ),
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q3",),
                        classical_target="c1",
                    ),
                ]
            ),
        ],
    )


__all__ = [name for name in globals() if not name.startswith("__")]
