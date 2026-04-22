# ruff: noqa: F401
from __future__ import annotations

import warnings
from importlib.util import find_spec
from pathlib import Path
from typing import cast

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from matplotlib.transforms import Bbox

import quantum_circuit_drawer.managed.rendering as managed_module
import quantum_circuit_drawer.renderers.matplotlib_primitives as matplotlib_primitives
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout._layering import normalize_draw_layers
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.layout.scene import LayoutScene
from quantum_circuit_drawer.managed.slider import (
    Managed2DPageSliderState,
    _horizontal_scene_for_start_column,
)
from quantum_circuit_drawer.managed.viewport import (
    viewport_adaptive_paged_scene as viewport_adaptive_paged_scene_impl,
)
from quantum_circuit_drawer.managed.zoom import current_text_scale
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    create_managed_figure,
    get_base_font_size,
    get_hover_state,
    get_page_slider,
    get_page_window,
    get_text_scaling_state,
    get_topology_menu_state,
    get_viewport_width,
)
from quantum_circuit_drawer.renderers._render_support import (
    figure_backend_name,
    normalize_backend_name,
    show_figure_if_supported,
)
from quantum_circuit_drawer.style import DrawStyle
from quantum_circuit_drawer.utils import format_visible_label
from tests.support import (
    assert_saved_image_has_visible_content,
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


def _hover_payload_count(scene: object) -> int:
    return sum(
        1
        for item in (
            *scene.gates,
            *scene.controls,
            *scene.connections,
            *scene.swaps,
            *scene.measurements,
        )
        if getattr(item, "hover_data", None) is not None
    )


def _zoom_text_scaling_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[
            WireIR(
                id="c0",
                index=0,
                kind=WireKind.CLASSICAL,
                label="c",
                metadata={"bundle_size": 23},
            )
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RZZ",
                        target_wires=("q0", "q1"),
                        parameters=(0.7,),
                    )
                ]
            ),
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                        metadata={"classical_bit_label": "dest"},
                    )
                ]
            ),
        ],
    )


def _long_label_margin_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(
                id="q0",
                index=0,
                kind=WireKind.QUANTUM,
                label="quantum_register_zero",
            ),
            WireIR(
                id="q1",
                index=1,
                kind=WireKind.QUANTUM,
                label="quantum_register_one",
            ),
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q1",))]
            ),
        ],
    )


def _tall_measured_ir(*, quantum_wire_count: int, layer_count: int = 2) -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(quantum_wire_count)
        ],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c")],
        layers=[
            *[
                LayerIR(
                    operations=[
                        OperationIR(
                            kind=OperationKind.GATE,
                            name="RX",
                            target_wires=(f"q{layer_index % quantum_wire_count}",),
                            parameters=(0.5,),
                        )
                    ]
                )
                for layer_index in range(layer_count)
            ],
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=(f"q{quantum_wire_count - 1}",),
                        classical_target="c0",
                    )
                ]
            ),
        ],
    )


def _overlapping_raw_layer_ir(*, raw_layer_count: int) -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE, name=f"H{layer_index}", target_wires=("q0",)
                    ),
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    ),
                ]
            )
            for layer_index in range(raw_layer_count)
        ],
    )


def _variable_width_slider_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="LONGSUPERGATE",
                        target_wires=("q0",),
                        parameters=(123456789.0,),
                    )
                ]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q1",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Y", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Z", target_wires=("q1",))]
            ),
        ],
    )


def _vertical_window_multiqubit_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(18)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="BIG",
                        target_wires=("q0", "q1", "q2"),
                    )
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        control_wires=("q4",),
                        target_wires=("q6",),
                    )
                ]
            ),
        ],
    )


def _matching_text_artists(axes: object, text: str) -> list[object]:
    return [
        text_artist
        for text_artist in axes.texts
        if normalize_rendered_text(text_artist.get_text()) == text
    ]


def _font_size_by_text(axes: object, text: str) -> float:
    return max(text_artist.get_fontsize() for text_artist in _matching_text_artists(axes, text))


def _text_artist_by_text(axes: object, text: str) -> object:
    return next(iter(_matching_text_artists(axes, text)))


def _expected_box_fitted_font_size(
    axes: object,
    scene: object,
    *,
    text: str,
    width: float,
    height: float,
    height_fraction: float,
) -> float:
    text_artist = _text_artist_by_text(axes, text)
    text_scaling_state = get_text_scaling_state(axes)
    visible_text = format_visible_label(text, use_mathtext=scene.style.use_mathtext)

    assert text_scaling_state is not None

    base_font_size = get_base_font_size(
        text_artist,
        default=float(text_artist.get_fontsize()),
    )
    return matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=matplotlib_primitives._build_gate_text_fitting_context(axes, scene),
        width=width,
        height=height,
        text=visible_text,
        default_font_size=base_font_size,
        height_fraction=height_fraction,
        max_font_size=base_font_size * current_text_scale(axes, text_scaling_state),
        cache={},
    )


def _adapted_scene_for_axes(
    circuit: CircuitIR,
    axes: object,
    *,
    style: DrawStyle,
    hover_enabled: bool = False,
) -> tuple[LayoutScene, float]:
    layout_engine = LayoutEngine()
    initial_scene = layout_engine.compute(circuit, style)
    return viewport_adaptive_paged_scene_impl(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
    )


def _gate_box_line_width(axes: object) -> float:
    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    return float(gate_patch.get_linewidth())


__all__ = [name for name in globals() if not name.startswith("__")]
