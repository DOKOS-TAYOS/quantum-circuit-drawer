from __future__ import annotations

from typing import cast

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import proj3d  # type: ignore[import-untyped]
from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

from quantum_circuit_drawer.drawing.pipeline import PreparedDrawPipeline, _compute_3d_scene
from quantum_circuit_drawer.drawing.request import DrawPipelineOptions
from quantum_circuit_drawer.hover import HoverOptions
from quantum_circuit_drawer.ir.lowering import lower_semantic_circuit
from quantum_circuit_drawer.ir.operations import OperationKind
from quantum_circuit_drawer.ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
    SemanticProvenanceIR,
)
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine_3d import LayoutEngine3D
from quantum_circuit_drawer.layout.scene import SceneVisualState
from quantum_circuit_drawer.managed.page_window_3d import (
    configure_3d_page_window,
    windowed_3d_page_scenes,
)
from quantum_circuit_drawer.managed.slider_3d import Managed3DPageSliderState
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    create_managed_figure,
    get_page_slider,
    set_page_window,
)
from quantum_circuit_drawer.renderers.matplotlib_renderer_3d import MatplotlibRenderer3D
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_wrapped_ir
from tests.support import draw_quantum_circuit_legacy as draw_quantum_circuit


def test_3d_page_slider_selection_survives_topology_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
        page_slider=True,
    )

    try:
        page_slider = cast(Managed3DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.exploration is not None

        selected_gate = next(gate for gate in page_slider.current_scene.gates if gate.operation_id)
        assert selected_gate.operation_id is not None

        _dispatch_click_at_3d_point(figure, axes, selected_gate.center)

        assert page_slider.exploration.selected_operation_id == selected_gate.operation_id
        assert any(
            gate.operation_id == selected_gate.operation_id
            and gate.visual_state is SceneVisualState.HIGHLIGHTED
            for gate in page_slider.current_scene.gates
        )

        page_slider.select_topology("star")

        assert page_slider.exploration.selected_operation_id == selected_gate.operation_id
        assert any(
            gate.operation_id == selected_gate.operation_id
            and gate.visual_state is SceneVisualState.HIGHLIGHTED
            for gate in page_slider.current_scene.gates
        )
    finally:
        plt.close(figure)


def test_3d_page_window_block_toggle_expands_selection_and_preserves_it_across_topology() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_block_circuits()
    current_circuit = lower_semantic_circuit(current_semantic_ir)
    style = DrawStyle(max_page_width=3.0)
    layout_engine = LayoutEngine3D()
    draw_options = DrawPipelineOptions(
        composite_mode="compact",
        view="3d",
        topology="line",
        topology_menu=True,
        direct=True,
        hover=HoverOptions(enabled=True),
    )
    initial_scene = _compute_3d_scene(
        layout_engine,
        current_circuit,
        style,
        topology_name="line",
        direct=True,
        hover_enabled=True,
    )
    pipeline = PreparedDrawPipeline(
        normalized_style=style,
        ir=current_circuit,
        semantic_ir=current_semantic_ir,
        expanded_semantic_ir=expanded_semantic_ir,
        layout_engine=layout_engine,
        paged_scene=initial_scene,
        renderer=MatplotlibRenderer3D(),
        draw_options=draw_options,
    )
    page_scenes = windowed_3d_page_scenes(pipeline, figure_size=(6.0, 4.2))
    figure, axes = create_managed_figure(
        initial_scene,
        figure_width=6.0,
        figure_height=4.2,
        use_agg=True,
        projection="3d",
    )

    try:
        page_window = configure_3d_page_window(
            figure=figure,
            axes=axes,
            pipeline=pipeline,
            page_scenes=page_scenes,
            set_page_window=set_page_window,
        )
        display_axes = page_window.display_axes[0]
        selected_gate = next(
            gate for gate in page_window.current_scene.gates if gate.operation_id == "op:0"
        )

        _dispatch_click_at_3d_point(figure, display_axes, selected_gate.center)

        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id == "op:0"
        assert page_window.block_toggle_button is not None

        page_window.toggle_selected_block()

        assert page_window.exploration.selected_operation_id == "op:0.0"
        assert "QFT" not in {gate.label for gate in page_window.current_scene.gates}
        assert any(
            gate.group_highlighted
            for gate in page_window.current_scene.gates
            if gate.operation_id in {"op:0.0", "op:0.1"}
        )

        page_window.select_topology("star")

        assert page_window.exploration.selected_operation_id == "op:0.0"
        assert any(
            gate.operation_id == "op:0.0" and gate.visual_state is SceneVisualState.HIGHLIGHTED
            for gate in page_window.current_scene.gates
        )
    finally:
        plt.close(figure)


def _dispatch_click_at_3d_point(
    figure: Figure,
    axes: Axes3D,
    point: object,
) -> None:
    figure.canvas.draw()
    projected_x, projected_y, _ = proj3d.proj_transform(
        float(getattr(point, "x")),
        float(getattr(point, "y")),
        float(getattr(point, "z")),
        axes.get_proj(),
    )
    display_x, display_y = axes.transData.transform((projected_x, projected_y))
    event = MouseEvent(
        "button_press_event",
        figure.canvas,
        float(display_x),
        float(display_y),
        button=1,
    )
    figure.canvas.callbacks.process("button_press_event", event)


def _semantic_block_circuits() -> tuple[SemanticCircuitIR, SemanticCircuitIR]:
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(3)
    )
    current_semantic_ir = SemanticCircuitIR(
        quantum_wires=quantum_wires,
        layers=(
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="QFT",
                        label="QFT",
                        target_wires=("q0", "q1"),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="QFT",
                            native_kind="composite",
                            composite_label="QFT",
                            location=(0,),
                        ),
                        metadata={"collapsed_block": True},
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="X",
                            native_kind="gate",
                            location=(1,),
                        ),
                    ),
                )
            ),
        ),
    )
    expanded_semantic_ir = SemanticCircuitIR(
        quantum_wires=quantum_wires,
        layers=(
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        target_wires=("q0",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="H",
                            native_kind="gate",
                            decomposition_origin="QFT",
                            composite_label="QFT",
                            location=(0, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="CX",
                            native_kind="gate",
                            decomposition_origin="QFT",
                            composite_label="QFT",
                            location=(0, 1),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="X",
                            native_kind="gate",
                            location=(1, 0),
                        ),
                    ),
                )
            ),
        ),
    )
    return current_semantic_ir, expanded_semantic_ir
