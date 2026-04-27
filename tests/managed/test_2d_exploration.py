from __future__ import annotations

from typing import cast

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent, MouseEvent
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
from quantum_circuit_drawer.layout._layering import normalized_draw_circuit
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.layout.scene import SceneVisualState
from quantum_circuit_drawer.managed.exploration_2d import (
    WireFilterMode,
    build_exploration_catalog,
    next_selected_operation_id_for_block_action,
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


def test_simple_qiskit_if_body_operations_do_not_become_collapsible_blocks() -> None:
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(5)
    )
    classical_wires = (WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c[0]"),)
    circuit = SemanticCircuitIR(
        quantum_wires=quantum_wires,
        classical_wires=classical_wires,
        layers=(
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q4",),
                        provenance=SemanticProvenanceIR(
                            framework="qiskit",
                            native_name="x",
                            native_kind="gate",
                            location=(7, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RZ",
                        target_wires=("q3",),
                        parameters=(0.35,),
                        provenance=SemanticProvenanceIR(
                            framework="qiskit",
                            native_name="rz",
                            native_kind="gate",
                            location=(7, 1),
                        ),
                    ),
                )
            ),
        ),
    )

    catalog = build_exploration_catalog(circuit, circuit)

    assert "op:7" not in catalog.blocks
    assert catalog.block_id_by_operation_id == {}


def test_nested_location_compact_block_can_be_expanded_from_selected_operation() -> None:
    quantum_wires = (
        WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
        WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
    )
    current_semantic_ir = SemanticCircuitIR(
        quantum_wires=quantum_wires,
        layers=(
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="CircuitOperation",
                        label="CircuitOp",
                        target_wires=("q0", "q1"),
                        provenance=SemanticProvenanceIR(
                            framework="cirq",
                            native_name="CircuitOperation",
                            native_kind="composite",
                            composite_label="CircuitOperation",
                            location=(5, 0),
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
                            framework="cirq",
                            native_name="H",
                            native_kind="gate",
                            decomposition_origin="CircuitOperation",
                            composite_label="CircuitOperation",
                            location=(5, 0, 0, 0),
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
                            framework="cirq",
                            native_name="CX",
                            native_kind="gate",
                            decomposition_origin="CircuitOperation",
                            composite_label="CircuitOperation",
                            location=(5, 0, 1, 0),
                        ),
                    ),
                )
            ),
        ),
    )

    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    assert catalog.initial_collapsed_block_ids == frozenset({"op:5"})
    assert catalog.blocks["op:5"].original_collapsed_operation is not None

    expand_action = selected_block_action(
        catalog,
        selected_operation_id="op:5.0",
        collapsed_block_ids=set(catalog.initial_collapsed_block_ids),
    )
    assert expand_action is not None
    assert expand_action.action == "expand"
    assert next_selected_operation_id_for_block_action(catalog, expand_action) == "op:5.0.0.0"

    collapse_action = selected_block_action(
        catalog,
        selected_operation_id="op:5.0.0.0",
        collapsed_block_ids=set(),
    )
    assert collapse_action is not None
    assert collapse_action.action == "collapse"
    assert next_selected_operation_id_for_block_action(catalog, collapse_action) == "op:5.0"


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


def test_fundamental_decomposition_blocks_start_collapsed_and_expand_independently() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_fundamental_rzz_circuits()
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    assert catalog.initial_collapsed_block_ids == frozenset({"op:0", "op:2"})
    assert (
        selected_block_action(
            catalog,
            selected_operation_id="op:0",
            collapsed_block_ids=set(catalog.initial_collapsed_block_ids),
        )
        is not None
    )
    assert (
        selected_block_action(
            catalog,
            selected_operation_id="op:0",
            collapsed_block_ids=set(catalog.initial_collapsed_block_ids),
        ).action
        == "expand"
    )

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids={"op:2"},
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    transformed_operation_ids = [
        semantic_operation_id(operation)
        for layer in transformed.semantic_ir.layers
        for operation in layer.operations
    ]

    assert "op:2" in transformed_operation_ids
    assert not [
        operation_id
        for operation_id in transformed_operation_ids
        if operation_id.startswith("op:2.")
    ]
    assert {"op:0.0", "op:0.1", "op:0.2"}.issubset(transformed_operation_ids)


def test_transform_semantic_circuit_keeps_expanded_block_before_following_operation() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_fundamental_rzz_circuits()
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=set(),
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    transformed_operation_ids = [
        semantic_operation_id(operation)
        for layer in transformed.semantic_ir.layers
        for operation in layer.operations
    ]

    assert transformed_operation_ids.index("op:0.1") < transformed_operation_ids.index("op:1")
    assert transformed_operation_ids.index("op:0.2") < transformed_operation_ids.index("op:1")


def test_transform_semantic_circuit_expands_block_without_crossing_prior_operation() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_block_after_cnot_circuits()
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    collapsed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids={"op:2"},
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    expanded = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=set(),
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )

    collapsed_columns = _normalized_operation_columns(collapsed.semantic_ir)
    expanded_columns = _normalized_operation_columns(expanded.semantic_ir)

    assert collapsed_columns["op:1"] < collapsed_columns["op:2"]
    assert expanded_columns["op:1"] < expanded_columns["op:2.0"]
    assert expanded_columns["op:1"] < expanded_columns["op:2.1"]


def test_transform_semantic_circuit_keeps_independent_late_wires_in_place_when_expanding() -> None:
    current_semantic_ir, expanded_semantic_ir = (
        _semantic_block_after_cnot_with_independent_late_wires()
    )
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    collapsed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids={"op:2"},
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    expanded = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=set(),
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    recollapsed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids={"op:2"},
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )

    collapsed_columns = _normalized_operation_columns(collapsed.semantic_ir)
    expanded_columns = _normalized_operation_columns(expanded.semantic_ir)
    recollapsed_columns = _normalized_operation_columns(recollapsed.semantic_ir)

    assert expanded_columns["op:1"] < expanded_columns["op:2.0"]
    assert expanded_columns["op:1"] < expanded_columns["op:2.1"]
    assert expanded_columns["op:5"] == collapsed_columns["op:5"] == recollapsed_columns["op:5"]
    assert expanded_columns["op:6"] == collapsed_columns["op:6"] == recollapsed_columns["op:6"]
    assert expanded_columns["op:7"] == collapsed_columns["op:7"] == recollapsed_columns["op:7"]


def test_transform_semantic_circuit_keeps_terminal_outputs_after_expanded_blocks() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_terminal_collision_circuits()
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=set(),
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )

    assert _semantic_operation_names(transformed.semantic_ir)[-1] == "PROBS"


def test_transform_semantic_circuit_collapses_measure_block_after_prior_operations() -> None:
    semantic_ir = _semantic_measure_block_with_late_visual_layers()
    catalog = build_exploration_catalog(semantic_ir, semantic_ir)

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids={"op:3"},
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )

    assert _semantic_operation_names(transformed.semantic_ir) == [
        "H",
        "X",
        "Y",
        "MEASURE",
    ]


def test_block_actions_expand_and_recollapse_multiple_blocks_independently() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_fundamental_rzz_circuits()
    catalog = build_exploration_catalog(current_semantic_ir, expanded_semantic_ir)
    collapsed_block_ids = set(catalog.initial_collapsed_block_ids)

    first_expand = selected_block_action(
        catalog,
        selected_operation_id="op:0",
        collapsed_block_ids=collapsed_block_ids,
    )
    assert first_expand is not None
    assert first_expand.action == "expand"
    collapsed_block_ids.discard(first_expand.block_id)
    assert next_selected_operation_id_for_block_action(catalog, first_expand) == "op:0.0"

    second_expand = selected_block_action(
        catalog,
        selected_operation_id="op:2",
        collapsed_block_ids=collapsed_block_ids,
    )
    assert second_expand is not None
    assert second_expand.action == "expand"
    collapsed_block_ids.discard(second_expand.block_id)
    assert next_selected_operation_id_for_block_action(catalog, second_expand) == "op:2.0"

    expanded = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=collapsed_block_ids,
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    expanded_operation_ids = {
        semantic_operation_id(operation)
        for layer in expanded.semantic_ir.layers
        for operation in layer.operations
    }
    assert {"op:0.0", "op:0.1", "op:0.2", "op:2.0", "op:2.1", "op:2.2"}.issubset(
        expanded_operation_ids
    )

    first_collapse = selected_block_action(
        catalog,
        selected_operation_id="op:0.0",
        collapsed_block_ids=collapsed_block_ids,
    )
    assert first_collapse is not None
    assert first_collapse.action == "collapse"
    collapsed_block_ids.add(first_collapse.block_id)
    assert next_selected_operation_id_for_block_action(catalog, first_collapse) == "op:0"

    second_collapse = selected_block_action(
        catalog,
        selected_operation_id="op:2.0",
        collapsed_block_ids=collapsed_block_ids,
    )
    assert second_collapse is not None
    assert second_collapse.action == "collapse"
    collapsed_block_ids.add(second_collapse.block_id)
    assert next_selected_operation_id_for_block_action(catalog, second_collapse) == "op:2"

    recollapsed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids=collapsed_block_ids,
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    assert {"RZZ", "H"} == set(_semantic_operation_names(recollapsed.semantic_ir))


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
        assert {"H", "X"}.issubset({gate.label for gate in page_slider.scene.gates})
        assert page_slider.exploration.transformed_semantic_ir is not None
        assert {"H", "X", "Z"}.issubset(
            set(_semantic_operation_names(page_slider.exploration.transformed_semantic_ir))
        )
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


def test_synthetic_collapsed_long_label_block_scales_to_visible_text() -> None:
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
    assert scene.gates[0].width > DrawStyle().gate_width


def test_synthetic_collapsed_block_rounds_numeric_parameters_in_visible_label() -> None:
    expanded_semantic_ir = _semantic_parameterized_long_label_block_circuit()
    catalog = build_exploration_catalog(expanded_semantic_ir, expanded_semantic_ir)

    transformed = transform_semantic_circuit(
        catalog,
        collapsed_block_ids={"op:0"},
        wire_filter_mode=WireFilterMode.ALL,
        show_ancillas=True,
    )
    scene = LayoutEngine().compute(lower_semantic_circuit(transformed.semantic_ir), DrawStyle())

    assert len(scene.gates) == 1
    assert scene.gates[0].label == "LongRotation(theta=3.142, beta=-0.123)"


def test_block_action_labels_round_numeric_parameters_like_collapsed_blocks() -> None:
    expanded_semantic_ir = _semantic_parameterized_long_label_block_circuit()
    catalog = build_exploration_catalog(expanded_semantic_ir, expanded_semantic_ir)

    expand_action = selected_block_action(
        catalog,
        selected_operation_id="op:0",
        collapsed_block_ids={"op:0"},
    )
    collapse_action = selected_block_action(
        catalog,
        selected_operation_id="op:0.0",
        collapsed_block_ids=set(),
    )

    assert expand_action is not None
    assert expand_action.label == "Expand LongRotation(theta=3.142, beta=-0.123)"
    assert collapse_action is not None
    assert collapse_action.label == "Collapse LongRotation(theta=3.142, beta=-0.123)"


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


def test_page_window_arrow_keys_navigate_pages_and_visible_count() -> None:
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

        _dispatch_key_press(figure, "down")
        assert page_window.visible_page_count == 2

        _dispatch_key_press(figure, "up")
        assert page_window.visible_page_count == 1

        _dispatch_key_press(figure, "right")
        assert page_window.start_page == 1

        _dispatch_key_press(figure, "left")
        assert page_window.start_page == 0
    finally:
        plt.close(figure)


def test_page_window_additional_shortcuts_navigate_and_clear_selection() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=18, wire_count=4),
        style={"max_page_width": 4.0},
        figsize=(4.0, 3.0),
        page_window=True,
        show=False,
    )

    try:
        page_window = cast(Managed2DPageWindowState | None, get_page_window(figure))
        assert page_window is not None

        _dispatch_key_press(figure, "down")
        assert page_window.visible_page_count == 2

        _dispatch_key_press(figure, "pagedown")
        forward_start_page = page_window.start_page
        assert forward_start_page > 0

        _dispatch_key_press(figure, "pageup")
        assert page_window.start_page < forward_start_page

        _dispatch_key_press(figure, "end")
        assert page_window.start_page == page_window.total_pages - 1

        _dispatch_key_press(figure, "home")
        assert page_window.start_page == 0

        _dispatch_key_press(figure, "up")
        assert page_window.visible_page_count == 1

        _dispatch_key_press(figure, "+")
        assert page_window.visible_page_count == 2

        _dispatch_key_press(figure, "-")
        assert page_window.visible_page_count == 1

        page_window.select_operation("op:0")
        assert page_window.exploration is not None

        _dispatch_key_press(figure, "escape")
        assert page_window.exploration.selected_operation_id is None
    finally:
        plt.close(figure)


def test_page_window_tab_shortcuts_traverse_visible_expandable_blocks() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_fundamental_rzz_circuits()
    current_circuit = lower_semantic_circuit(current_semantic_ir)
    layout_engine = LayoutEngine()
    style = DrawStyle(max_page_width=8.0)
    scene = managed_module.compute_paged_scene(
        current_circuit,
        layout_engine,
        style,
        hover_enabled=True,
    )
    figure, axes = create_managed_figure(
        scene,
        figure_width=2.2,
        figure_height=2.0,
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
        assert page_window.exploration is not None

        _dispatch_key_press(figure, "tab")
        assert page_window.exploration.selected_operation_id == "op:0"

        _dispatch_key_press(figure, "tab")
        assert page_window.exploration.selected_operation_id == "op:2"

        _dispatch_key_press(figure, "shift+tab")
        assert page_window.exploration.selected_operation_id == "op:0"
    finally:
        plt.close(figure)


def test_slider_arrow_keys_move_horizontal_and_vertical_windows() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.max_start_column > 0
        assert page_slider.max_start_row > 0

        _dispatch_key_press(figure, "right")
        assert page_slider.start_column == 1

        _dispatch_key_press(figure, "down")
        assert page_slider.start_row == 1

        _dispatch_key_press(figure, "left")
        assert page_slider.start_column == 0

        _dispatch_key_press(figure, "up")
        assert page_slider.start_row == 0
    finally:
        plt.close(figure)


def test_slider_additional_shortcuts_navigate_and_adjust_visible_wires() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=24),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.max_start_column > 0
        assert page_slider.max_start_row > 0

        _dispatch_key_press(figure, "pagedown")
        assert page_slider.start_column > 0

        _dispatch_key_press(figure, "pageup")
        assert page_slider.start_column == 0

        _dispatch_key_press(figure, "end")
        assert page_slider.start_column == page_slider.max_start_column

        _dispatch_key_press(figure, "home")
        assert page_slider.start_column == 0

        visible_qubits = page_slider.visible_qubits
        _dispatch_key_press(figure, "+")
        assert page_slider.visible_qubits == min(visible_qubits + 1, page_slider.total_visible_rows)

        _dispatch_key_press(figure, "-")
        assert page_slider.visible_qubits == visible_qubits
    finally:
        plt.close(figure)


def test_slider_tab_shortcuts_traverse_visible_expandable_blocks_and_clear_selection() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_controls_circuits()
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
        figure_width=2.2,
        figure_height=2.0,
        use_agg=True,
    )

    try:
        managed_module.configure_page_slider(
            figure=figure,
            axes=axes,
            scene=scene,
            viewport_width=1.0,
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
        assert page_slider.exploration is not None

        _dispatch_key_press(figure, "tab")
        assert page_slider.exploration.selected_operation_id == "op:0"

        _dispatch_key_press(figure, "escape")
        assert page_slider.exploration.selected_operation_id is None
    finally:
        plt.close(figure)


def test_slider_enter_toggles_selected_block() -> None:
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
        _dispatch_key_press(figure, "enter")
        assert page_slider.exploration is not None
        assert page_slider.exploration.selected_operation_id == "op:0.0"

        _dispatch_key_press(figure, " ")
        assert page_slider.exploration.selected_operation_id == "op:0"
    finally:
        plt.close(figure)


def test_page_window_double_click_toggles_clicked_block() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_block_circuits()
    current_circuit = lower_semantic_circuit(current_semantic_ir)
    layout_engine = LayoutEngine()
    style = DrawStyle(max_page_width=3.0)
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
        selected_gate = next(
            gate for gate in page_window.window_scene.gates if gate.operation_id == "op:0"
        )
        visible_page = page_window.window_scene.pages[0]

        _dispatch_click_at_data(
            figure,
            axes,
            x=selected_gate.x + page_x_offset(visible_page, page_window.window_scene),
            y=selected_gate.y + page_y_offset(visible_page),
            dblclick=True,
        )
        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id == "op:0.0"

        selected_gate = next(
            gate for gate in page_window.window_scene.gates if gate.operation_id == "op:0.0"
        )
        visible_page = page_window.window_scene.pages[0]
        _dispatch_click_at_data(
            figure,
            axes,
            x=selected_gate.x + page_x_offset(visible_page, page_window.window_scene),
            y=selected_gate.y + page_y_offset(visible_page),
            dblclick=True,
        )
        assert page_window.exploration.selected_operation_id == "op:0"
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


def test_public_managed_interaction_flags_disable_keyboard_and_double_click() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_block_circuits()
    result = public_draw_quantum_circuit(
        lower_semantic_circuit(current_semantic_ir),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            style={"max_page_width": 3.0},
            hover=True,
            show=False,
            keyboard_shortcuts=False,
            double_click_toggle=False,
        ),
    )

    try:
        figure = result.primary_figure
        axes = result.primary_axes
        page_window = cast(Managed2DPageWindowState | None, get_page_window(figure))
        assert page_window is not None

        _dispatch_key_press(figure, "right")
        assert page_window.start_page == 0

        selected_gate = next(
            gate for gate in page_window.window_scene.gates if gate.operation_id == "op:0"
        )
        visible_page = page_window.window_scene.pages[0]
        _dispatch_click_at_data(
            figure,
            axes,
            x=selected_gate.x + page_x_offset(visible_page, page_window.window_scene),
            y=selected_gate.y + page_y_offset(visible_page),
            dblclick=True,
        )

        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id == "op:0"
    finally:
        plt.close(result.primary_figure)


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
    dblclick: bool = False,
) -> None:
    figure.canvas.draw()
    display_x, display_y = axes.transData.transform((x, y))
    event = MouseEvent(
        "button_press_event",
        figure.canvas,
        float(display_x),
        float(display_y),
        button=1,
        dblclick=dblclick,
    )
    figure.canvas.callbacks.process("button_press_event", event)


def _dispatch_key_press(figure: Figure, key: str) -> None:
    event = KeyEvent(
        "key_press_event",
        figure.canvas,
        key=key,
    )
    figure.canvas.callbacks.process("key_press_event", event)


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


def _semantic_block_after_cnot_circuits() -> tuple[SemanticCircuitIR, SemanticCircuitIR]:
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
                        provenance=SemanticProvenanceIR(location=(0,)),
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
                        provenance=SemanticProvenanceIR(location=(1,)),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Circuit - 42",
                        label="circuit 42",
                        target_wires=("q0", "q1", "q2"),
                        provenance=SemanticProvenanceIR(
                            native_kind="composite",
                            composite_label="Circuit - 42",
                            location=(2,),
                        ),
                        metadata={"collapsed_block": True},
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q1",),
                        provenance=SemanticProvenanceIR(location=(3,)),
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
                        provenance=SemanticProvenanceIR(location=(0,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            decomposition_origin="Circuit - 42",
                            composite_label="Circuit - 42",
                            location=(2, 0),
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
                        provenance=SemanticProvenanceIR(location=(1,)),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="P",
                        target_wires=("q1",),
                        control_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            decomposition_origin="Circuit - 42",
                            composite_label="Circuit - 42",
                            location=(2, 1),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q1",),
                        provenance=SemanticProvenanceIR(location=(3,)),
                    ),
                )
            ),
        ),
    )
    return current_semantic_ir, expanded_semantic_ir


def _semantic_block_after_cnot_with_independent_late_wires() -> tuple[
    SemanticCircuitIR, SemanticCircuitIR
]:
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(5)
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
                        provenance=SemanticProvenanceIR(location=(0,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q3",),
                        provenance=SemanticProvenanceIR(location=(5,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q4",),
                        provenance=SemanticProvenanceIR(location=(6,)),
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
                        provenance=SemanticProvenanceIR(location=(1,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="Z",
                        target_wires=("q4",),
                        control_wires=("q3",),
                        provenance=SemanticProvenanceIR(location=(7,)),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="Circuit - 42",
                        label="circuit 42",
                        target_wires=("q0", "q1", "q2"),
                        provenance=SemanticProvenanceIR(
                            native_kind="composite",
                            composite_label="Circuit - 42",
                            location=(2,),
                        ),
                        metadata={"collapsed_block": True},
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q1",),
                        provenance=SemanticProvenanceIR(location=(3,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(location=(4,)),
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
                        provenance=SemanticProvenanceIR(location=(0,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            decomposition_origin="Circuit - 42",
                            composite_label="Circuit - 42",
                            location=(2, 0),
                        ),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q3",),
                        provenance=SemanticProvenanceIR(location=(5,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q4",),
                        provenance=SemanticProvenanceIR(location=(6,)),
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
                        provenance=SemanticProvenanceIR(location=(1,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="Z",
                        target_wires=("q4",),
                        control_wires=("q3",),
                        provenance=SemanticProvenanceIR(location=(7,)),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="P",
                        target_wires=("q1",),
                        control_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            decomposition_origin="Circuit - 42",
                            composite_label="Circuit - 42",
                            location=(2, 1),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q1",),
                        provenance=SemanticProvenanceIR(location=(3,)),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RY",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(location=(4,)),
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


def _semantic_parameterized_long_label_block_circuit() -> SemanticCircuitIR:
    label = "LongRotation(theta=3.14159265, beta=-0.123456)"
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(2)
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
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="H",
                            native_kind="gate",
                            decomposition_origin=label,
                            composite_label=label,
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
                            decomposition_origin=label,
                            composite_label=label,
                            location=(0, 1),
                        ),
                    ),
                )
            ),
        ),
    )


def _semantic_terminal_collision_circuits() -> tuple[SemanticCircuitIR, SemanticCircuitIR]:
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
                        name="RZZ",
                        target_wires=("q0", "q1"),
                        parameters=(0.7,),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="RZZ",
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
                        name="PROBS",
                        target_wires=("q0", "q1"),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="ProbabilityMP",
                            native_kind="probs",
                            location=(0,),
                        ),
                        metadata={"pennylane_terminal_kind": "probs"},
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
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(1, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RZ",
                        target_wires=("q1",),
                        parameters=(0.7,),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="RZ",
                            native_kind="gate",
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(1, 1),
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
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(1, 2),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="PROBS",
                        target_wires=("q0", "q1"),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="ProbabilityMP",
                            native_kind="probs",
                            location=(0,),
                        ),
                        metadata={"pennylane_terminal_kind": "probs"},
                    ),
                )
            ),
        ),
    )
    return current_semantic_ir, expanded_semantic_ir


def _semantic_measure_block_with_late_visual_layers() -> SemanticCircuitIR:
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(3)
    )
    classical_wires = tuple(
        WireIR(id=f"c{index}", index=index, kind=WireKind.CLASSICAL, label=f"c[{index}]")
        for index in range(3)
    )
    return SemanticCircuitIR(
        quantum_wires=quantum_wires,
        classical_wires=classical_wires,
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
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="MEASURE",
                            native_kind="measurement",
                            location=(3, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q1",),
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
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q1",),
                        classical_target="c1",
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="MEASURE",
                            native_kind="measurement",
                            location=(3, 1),
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
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q2",),
                        classical_target="c2",
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="MEASURE",
                            native_kind="measurement",
                            location=(3, 2),
                        ),
                    ),
                )
            ),
        ),
    )


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


def _semantic_fundamental_rzz_circuits() -> tuple[SemanticCircuitIR, SemanticCircuitIR]:
    quantum_wires = tuple(
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(4)
    )
    current_semantic_ir = SemanticCircuitIR(
        quantum_wires=quantum_wires,
        layers=(
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RZZ",
                        target_wires=("q0", "q1"),
                        parameters=(0.5,),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="RZZ",
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
                        name="H",
                        target_wires=("q1",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="H",
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
                        name="RZZ",
                        target_wires=("q2", "q3"),
                        parameters=(0.5,),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="RZZ",
                            native_kind="gate",
                            location=(2,),
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
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="CX",
                            native_kind="gate",
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(0, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RZ",
                        target_wires=("q1",),
                        parameters=(0.5,),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="RZ",
                            native_kind="gate",
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(0, 1),
                        ),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="H",
                        target_wires=("q1",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="H",
                            native_kind="gate",
                            location=(1,),
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
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(0, 2),
                        ),
                    ),
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q3",),
                        control_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="CX",
                            native_kind="gate",
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(2, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RZ",
                        target_wires=("q3",),
                        parameters=(0.5,),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="RZ",
                            native_kind="gate",
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(2, 1),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q3",),
                        control_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="CX",
                            native_kind="gate",
                            decomposition_origin="RZZ",
                            composite_label="RZZ",
                            location=(2, 2),
                        ),
                    ),
                )
            ),
        ),
    )
    return current_semantic_ir, expanded_semantic_ir


def _semantic_operation_names(circuit: SemanticCircuitIR) -> list[str]:
    return [operation.name for layer in circuit.layers for operation in layer.operations]


def _normalized_operation_columns(circuit: SemanticCircuitIR) -> dict[str, int]:
    normalized = normalized_draw_circuit(lower_semantic_circuit(circuit))
    return {
        semantic_operation_id(operation): layer_index
        for layer_index, layer in enumerate(normalized.layers)
        for operation in layer.operations
    }
