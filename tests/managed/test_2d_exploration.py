from __future__ import annotations

from typing import cast

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure

import quantum_circuit_drawer.managed.rendering as managed_module
from quantum_circuit_drawer import DrawMode
from quantum_circuit_drawer import draw_quantum_circuit as public_draw_quantum_circuit
from quantum_circuit_drawer.ir.lowering import lower_semantic_circuit
from quantum_circuit_drawer.ir.operations import OperationKind
from quantum_circuit_drawer.ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
    SemanticProvenanceIR,
    semantic_operation_id,
)
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.layout.scene import SceneVisualState
from quantum_circuit_drawer.managed.exploration_2d import (
    WireFilterMode,
    build_exploration_catalog,
    selected_block_action,
    transform_semantic_circuit,
)
from quantum_circuit_drawer.managed.page_window import Managed2DPageWindowState
from quantum_circuit_drawer.managed.slider import Managed2DPageSliderState
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    create_managed_figure,
    get_hover_state,
    get_page_slider,
    get_page_window,
    set_page_slider,
    set_page_window,
)
from quantum_circuit_drawer.renderers._matplotlib_page_projection import (
    page_x_offset,
    page_y_offset,
)
from quantum_circuit_drawer.renderers.matplotlib_renderer import MatplotlibRenderer
from quantum_circuit_drawer.style import DrawStyle
from tests.support import (
    build_dense_rotation_ir,
    build_public_draw_config,
    build_wrapped_ir,
)
from tests.support import draw_quantum_circuit_legacy as draw_quantum_circuit


def test_transform_semantic_circuit_respects_initial_collapsed_blocks() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_block_circuits()
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    assert catalog.initial_collapsed_block_ids == frozenset({"op:0"})

    collapsed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=set(catalog.initial_collapsed_block_ids),
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    expanded = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=set(),
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )

    assert _semantic_operation_names(collapsed.semantic_ir)[0] == "QFT"
    assert _semantic_operation_names(expanded.semantic_ir)[:2] == ["H", "X"]
    assert (
        selected_block_action(
            catalog,
            selected_operation_id="op:0",
            collapsed_block_ids=set(catalog.initial_collapsed_block_ids),
        )
        is not None
    )


def test_transform_semantic_circuit_filters_active_wires_and_tracks_hidden_ranges() -> None:
    semantic_ir = _semantic_filter_circuit()
    catalog = build_exploration_catalog(semantic_ir, semantic_ir)

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=set(),
        wire_filter_mode=WireFilterMode.ACTIVE,
        show_ancillas=False,
    )

    assert [wire.id for wire in transformed.semantic_ir.quantum_wires] == ["q0", "q1"]
    assert len(transformed.hidden_wire_ranges) == 1
    assert transformed.hidden_wire_ranges[0].before_wire_id == "q0"
    assert transformed.hidden_wire_ranges[0].after_wire_id == "q1"
    assert transformed.hidden_wire_ranges[0].hidden_wire_ids == ("anc0",)


def test_transform_semantic_circuit_collapses_interleaved_block_only_once() -> None:
    current_semantic_ir, expanded_semantic_ir = _interleaved_semantic_block_circuits()
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids={"op:1"},
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )

    transformed_operation_ids = [
        semantic_operation_id(operation)
        for layer in transformed.semantic_ir.layers
        for operation in layer.operations
    ]

    assert transformed_operation_ids.count("op:1") == 1
    assert _semantic_operation_names(transformed.semantic_ir).count("Prep") == 1


def test_slider_click_selection_highlights_operation_and_clears_on_background() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        selected_gate = page_slider.scene.gates[0]
        assert selected_gate.operation_id is not None

        _dispatch_click_at_data(
            figure,
            axes,
            x=selected_gate.x,
            y=selected_gate.y,
        )

        assert page_slider.exploration is not None
        assert page_slider.exploration.selected_operation_id == selected_gate.operation_id
        assert any(
            gate.operation_id == selected_gate.operation_id
            and gate.visual_state is SceneVisualState.HIGHLIGHTED
            for gate in page_slider.scene.gates
        )
        assert any(
            gate.operation_id != selected_gate.operation_id
            and gate.visual_state is SceneVisualState.DIMMED
            for gate in page_slider.scene.gates
        )

        _dispatch_click_at_data(figure, axes, x=0.05, y=0.05)

        assert page_slider.exploration.selected_operation_id is None
        assert all(
            gate.visual_state is SceneVisualState.DEFAULT for gate in page_slider.scene.gates
        )
    finally:
        plt.close(figure)


def test_slider_selection_survives_vertical_scroll_when_selected_operation_stays_visible() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.vertical_slider is not None
        ordered_gates = sorted(page_slider.scene.gates, key=lambda gate: gate.y)
        selected_gate = next(gate for gate in ordered_gates if gate.y > ordered_gates[0].y)
        assert selected_gate.operation_id is not None

        _dispatch_click_at_data(
            figure,
            axes,
            x=selected_gate.x,
            y=selected_gate.y,
        )
        page_slider.show_start_row(1)

        assert page_slider.exploration is not None
        assert page_slider.exploration.selected_operation_id == selected_gate.operation_id
        assert any(
            gate.operation_id == selected_gate.operation_id for gate in page_slider.scene.gates
        )
    finally:
        plt.close(figure)


def test_slider_block_toggle_expands_and_recovers_semantic_block() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_block_circuits()
    current_circuit = lower_semantic_circuit(current_semantic_ir)
    layout_engine = LayoutEngine()
    style = DrawStyle(max_page_width=3.0)
    scene = managed_module.build_continuous_slider_scene(
        current_circuit,
        layout_engine,
        style,
        hover_enabled=True,
    )
    figure, axes = create_managed_figure(
        scene,
        figure_width=2.6,
        figure_height=2.8,
        use_agg=True,
    )

    try:
        managed_module.configure_page_slider(
            figure=figure,
            axes=axes,
            scene=scene,
            viewport_width=scene.width,
            set_page_slider=set_page_slider,
            circuit=current_circuit,
            layout_engine=layout_engine,
            renderer=MatplotlibRenderer(),
            normalized_style=style,
            semantic_ir=current_semantic_ir,
            expanded_semantic_ir=expanded_semantic_ir,
        )
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.block_toggle_button is None

        page_slider.select_operation("op:0")

        assert page_slider.block_toggle_button is not None
        assert page_slider.block_toggle_axes is not None

        page_slider.toggle_selected_block()

        assert page_slider.exploration is not None
        assert page_slider.exploration.selected_operation_id == "op:0.0"
        assert "QFT" not in {gate.label for gate in page_slider.scene.gates}
        assert {"H", "X", "Z"}.issubset({gate.label for gate in page_slider.scene.gates})
        assert any(
            getattr(patch, "get_gid", lambda: None)() == "decomposition-group-highlight"
            for patch in axes.patches
        )

        page_slider.toggle_selected_block()

        assert page_slider.exploration.selected_operation_id == "op:0"
        assert "QFT" in {gate.label for gate in page_slider.scene.gates}
    finally:
        plt.close(figure)


def test_slider_expanded_block_keeps_group_highlight_without_selection() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_block_circuits()
    current_circuit = lower_semantic_circuit(current_semantic_ir)
    layout_engine = LayoutEngine()
    style = DrawStyle(max_page_width=3.0)
    scene = managed_module.build_continuous_slider_scene(
        current_circuit,
        layout_engine,
        style,
        hover_enabled=True,
    )
    figure, axes = create_managed_figure(
        scene,
        figure_width=2.6,
        figure_height=2.8,
        use_agg=True,
    )

    try:
        managed_module.configure_page_slider(
            figure=figure,
            axes=axes,
            scene=scene,
            viewport_width=scene.width,
            set_page_slider=set_page_slider,
            circuit=current_circuit,
            layout_engine=layout_engine,
            renderer=MatplotlibRenderer(),
            normalized_style=style,
            semantic_ir=current_semantic_ir,
            expanded_semantic_ir=expanded_semantic_ir,
        )
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None

        page_slider.select_operation("op:0")
        page_slider.toggle_selected_block()
        page_slider.select_operation(None)

        assert page_slider.exploration is not None
        assert page_slider.exploration.selected_operation_id is None
        assert all(
            gate.visual_state is SceneVisualState.DEFAULT for gate in page_slider.scene.gates
        )
        assert any(
            getattr(patch, "get_gid", lambda: None)() == "decomposition-group-highlight"
            for patch in axes.patches
        )
    finally:
        plt.close(figure)


def test_initial_collapsed_long_label_block_restores_original_width() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_long_label_block_circuits()
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=set(catalog.initial_collapsed_block_ids),
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    scene = LayoutEngine().compute(lower_semantic_circuit(transformed.semantic_ir), DrawStyle())

    assert len(scene.gates) == 1
    assert scene.gates[0].label == "ProbabilityFlowBlock"
    assert scene.gates[0].width > DrawStyle().gate_width


def test_synthetic_collapsed_long_label_block_keeps_compact_single_column_width() -> None:
    _, expanded_semantic_ir = _semantic_long_label_block_circuits()
    catalog = build_exploration_catalog(expanded_semantic_ir, expanded_semantic_ir)

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids={"op:0"},
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    scene = LayoutEngine().compute(lower_semantic_circuit(transformed.semantic_ir), DrawStyle())

    assert len(scene.gates) == 1
    assert scene.gates[0].width == pytest.approx(DrawStyle().gate_width)


def test_slider_optional_buttons_place_block_before_wire_and_ancilla_controls() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_controls_circuits()
    current_circuit = lower_semantic_circuit(current_semantic_ir)
    layout_engine = LayoutEngine()
    style = DrawStyle(max_page_width=1.8)
    scene = managed_module.build_continuous_slider_scene(
        current_circuit,
        layout_engine,
        style,
        hover_enabled=True,
    )
    figure, axes = create_managed_figure(
        scene,
        figure_width=3.2,
        figure_height=3.0,
        use_agg=True,
    )

    try:
        managed_module.configure_page_slider(
            figure=figure,
            axes=axes,
            scene=scene,
            viewport_width=scene.width,
            set_page_slider=set_page_slider,
            circuit=current_circuit,
            layout_engine=layout_engine,
            renderer=MatplotlibRenderer(),
            normalized_style=style,
            semantic_ir=current_semantic_ir,
            expanded_semantic_ir=expanded_semantic_ir,
        )
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None

        page_slider.select_operation("op:0")

        assert page_slider.block_toggle_axes is not None
        assert page_slider.wire_filter_axes is not None
        assert page_slider.ancilla_toggle_axes is not None
        assert (
            page_slider.block_toggle_axes.get_position().x0
            < page_slider.wire_filter_axes.get_position().x0
        )
        assert (
            page_slider.wire_filter_axes.get_position().x0
            < page_slider.ancilla_toggle_axes.get_position().x0
        )
    finally:
        plt.close(figure)


def test_page_window_click_selection_uses_visible_page_coordinates() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    try:
        page_window = cast(Managed2DPageWindowState | None, get_page_window(figure))
        assert page_window is not None
        assert page_window.page_box is not None

        page_window.page_box.set_val("2")

        assert page_window.window_scene is not None
        assert page_window.window_scene.gates
        selected_gate = page_window.window_scene.gates[0]
        assert selected_gate.operation_id is not None

        visible_page = page_window.window_scene.pages[0]
        _dispatch_click_at_data(
            figure,
            axes,
            x=selected_gate.x + page_x_offset(visible_page, page_window.window_scene),
            y=selected_gate.y + page_y_offset(visible_page),
        )

        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id == selected_gate.operation_id
        assert any(
            gate.operation_id == selected_gate.operation_id
            and gate.visual_state is SceneVisualState.HIGHLIGHTED
            for gate in page_window.scene.gates
        )
    finally:
        plt.close(figure)


def test_page_window_wire_filter_refresh_keeps_hover_connected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    result = public_draw_quantum_circuit(
        build_wrapped_ir(),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            style={"max_page_width": 4.0},
            hover=True,
            figsize=(4.0, 3.0),
        ),
    )

    try:
        figure = result.primary_figure
        axes = result.primary_axes
        page_window = cast(Managed2DPageWindowState | None, get_page_window(figure))
        assert page_window is not None
        assert get_hover_state(axes) is not None

        page_window.toggle_wire_filter()

        assert page_window.exploration is not None
        assert page_window.exploration.wire_filter_mode is WireFilterMode.ACTIVE
        assert get_hover_state(axes) is not None
    finally:
        plt.close(figure)


def test_page_window_block_toggle_recovers_single_interleaved_collapsed_block() -> None:
    current_semantic_ir, expanded_semantic_ir = _interleaved_semantic_block_circuits()
    current_circuit = lower_semantic_circuit(current_semantic_ir)
    layout_engine = LayoutEngine()
    style = DrawStyle(max_page_width=2.6)
    scene = managed_module.compute_paged_scene(
        current_circuit,
        layout_engine,
        style,
        hover_enabled=True,
    )
    figure, axes = create_managed_figure(
        scene,
        figure_width=3.2,
        figure_height=3.0,
        use_agg=True,
    )

    try:
        managed_module.configure_page_window(
            figure=figure,
            axes=axes,
            circuit=current_circuit,
            layout_engine=layout_engine,
            renderer=MatplotlibRenderer(),
            scene=scene,
            effective_page_width=style.max_page_width,
            set_page_window=set_page_window,
            semantic_ir=current_semantic_ir,
            expanded_semantic_ir=expanded_semantic_ir,
        )
        page_window = cast(Managed2DPageWindowState | None, get_page_window(figure))
        assert page_window is not None

        page_window.select_operation("op:1")
        page_window.toggle_selected_block()
        page_window.toggle_selected_block()

        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id == "op:1"
        assert [gate.operation_id for gate in page_window.scene.gates].count("op:1") == 1
        assert [gate.label for gate in page_window.scene.gates].count("PREP") == 1
    finally:
        plt.close(figure)


def _dispatch_click_at_data(
    figure: Figure,
    axes: Axes,
    *,
    x: float,
    y: float,
) -> None:
    figure.canvas.draw()
    display_x, display_y = axes.transData.transform((x, y))
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
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Z",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Z",
                            native_kind="gate",
                            location=(2,),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Y",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Y",
                            native_kind="gate",
                            location=(3,),
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
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Z",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Z",
                            native_kind="gate",
                            location=(2, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Y",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Y",
                            native_kind="gate",
                            location=(3, 0),
                        ),
                    ),
                )
            ),
        ),
    )
    return current_semantic_ir, expanded_semantic_ir


def _semantic_filter_circuit() -> SemanticCircuitIR:
    quantum_wires = (
        WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
        WireIR(id="anc0", index=1, kind=WireKind.QUANTUM, label="anc0"),
        WireIR(id="q1", index=2, kind=WireKind.QUANTUM, label="q1"),
    )
    return SemanticCircuitIR(
        quantum_wires=quantum_wires,
        layers=(
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        target_wires=("q0",),
                        provenance=SemanticProvenanceIR(location=(0,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q1",),
                        provenance=SemanticProvenanceIR(location=(1,)),
                    ),
                )
            ),
        ),
    )


def _interleaved_semantic_block_circuits() -> tuple[SemanticCircuitIR, SemanticCircuitIR]:
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
                        name="H",
                        target_wires=("q0",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="H",
                            native_kind="gate",
                            location=(0,),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Prep",
                        label="Prep",
                        target_wires=("q0", "q1"),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Prep",
                            native_kind="composite",
                            composite_label="Prep",
                            location=(1,),
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
                            location=(2,),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Y",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Y",
                            native_kind="gate",
                            location=(3,),
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
                            location=(0,),
                        ),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        target_wires=("q0",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="H",
                            native_kind="gate",
                            decomposition_origin="Prep",
                            composite_label="Prep",
                            location=(1, 0),
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
                            location=(2,),
                        ),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="CX",
                            native_kind="gate",
                            decomposition_origin="Prep",
                            composite_label="Prep",
                            location=(1, 1),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Y",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Y",
                            native_kind="gate",
                            location=(3,),
                        ),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Z",
                        target_wires=("q1",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Z",
                            native_kind="gate",
                            decomposition_origin="Prep",
                            composite_label="Prep",
                            location=(1, 2),
                        ),
                    ),
                )
            ),
        ),
    )
    return current_semantic_ir, expanded_semantic_ir


def _semantic_long_label_block_circuits() -> tuple[SemanticCircuitIR, SemanticCircuitIR]:
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(2)
    )
    current_semantic_ir = SemanticCircuitIR(
        quantum_wires=quantum_wires,
        layers=(
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="ProbabilityFlowBlock",
                        label="ProbabilityFlowBlock",
                        target_wires=("q0", "q1"),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="ProbabilityFlowBlock",
                            native_kind="composite",
                            composite_label="ProbabilityFlowBlock",
                            location=(0,),
                        ),
                        metadata={"collapsed_block": True},
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
                        name="Hadamard",
                        target_wires=("q0",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Hadamard",
                            native_kind="gate",
                            decomposition_origin="ProbabilityFlowBlock",
                            composite_label="ProbabilityFlowBlock",
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
                            decomposition_origin="ProbabilityFlowBlock",
                            composite_label="ProbabilityFlowBlock",
                            location=(0, 1),
                        ),
                    ),
                )
            ),
        ),
    )
    return current_semantic_ir, expanded_semantic_ir


def _semantic_controls_circuits() -> tuple[SemanticCircuitIR, SemanticCircuitIR]:
    quantum_wires = (
        WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
        WireIR(id="anc0", index=1, kind=WireKind.QUANTUM, label="anc0"),
        WireIR(id="q1", index=2, kind=WireKind.QUANTUM, label="q1"),
        WireIR(id="q2", index=3, kind=WireKind.QUANTUM, label="q2"),
    )
    current_semantic_ir = SemanticCircuitIR(
        quantum_wires=quantum_wires,
        layers=(
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Prep",
                        label="Prep",
                        target_wires=("q0", "q1"),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Prep",
                            native_kind="composite",
                            composite_label="Prep",
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
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Y",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Y",
                            native_kind="gate",
                            location=(2,),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Z",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Z",
                            native_kind="gate",
                            location=(3,),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="H",
                            native_kind="gate",
                            location=(4,),
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
                            decomposition_origin="Prep",
                            composite_label="Prep",
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
                            decomposition_origin="Prep",
                            composite_label="Prep",
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
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Y",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Y",
                            native_kind="gate",
                            location=(2, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Z",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="Z",
                            native_kind="gate",
                            location=(3, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="H",
                            native_kind="gate",
                            location=(4, 0),
                        ),
                    ),
                )
            ),
        ),
    )
    return current_semantic_ir, expanded_semantic_ir


def _semantic_operation_names(circuit: SemanticCircuitIR) -> list[str]:
    return [operation.name for layer in circuit.layers for operation in layer.operations]
