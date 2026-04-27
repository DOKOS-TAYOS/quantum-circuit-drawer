from __future__ import annotations

from typing import cast

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import proj3d  # type: ignore[import-untyped]
from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

from quantum_circuit_drawer import DrawMode
from quantum_circuit_drawer import draw_quantum_circuit as public_draw_quantum_circuit
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
from quantum_circuit_drawer.managed.exploration_2d import WireFilterMode
from quantum_circuit_drawer.managed.page_window_3d import (
    configure_3d_page_window,
    windowed_3d_page_scenes,
)
from quantum_circuit_drawer.managed.slider_3d import (
    Managed3DPageSliderState,
    configure_3d_page_slider,
)
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    create_managed_figure,
    get_page_slider,
    get_page_window,
    set_page_slider,
    set_page_window,
)
from quantum_circuit_drawer.renderers.matplotlib_renderer_3d import MatplotlibRenderer3D
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_dense_rotation_ir, build_public_draw_config, build_wrapped_ir
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


def test_3d_page_window_expanded_group_highlight_persists_without_selection() -> None:
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

        page_window.select_operation("op:0")
        page_window.toggle_selected_block()
        page_window.select_operation(None)

        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id is None
        assert any(
            gate.group_highlighted for gate in page_window.current_scene.gates if gate.operation_id
        )
        assert all(
            gate.visual_state is SceneVisualState.DEFAULT
            for gate in page_window.current_scene.gates
            if gate.operation_id is not None
        )
    finally:
        plt.close(figure)


def test_3d_page_window_expands_only_selected_fundamental_rzz_block() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_fundamental_rzz_circuits()
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

        page_window.select_operation("op:0")
        page_window.toggle_selected_block()

        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id == "op:0.0"
        assert any(gate.operation_id == "op:2" for gate in page_window.current_scene.gates)
        assert not [
            gate
            for gate in page_window.current_scene.gates
            if gate.operation_id is not None and gate.operation_id.startswith("op:2.")
        ]
        assert {"op:0.0", "op:0.1", "op:0.2"}.issubset(
            {
                gate.operation_id
                for gate in page_window.current_scene.gates
                if gate.operation_id is not None
            }
        )
    finally:
        plt.close(figure)


def test_3d_page_slider_background_drag_does_not_clear_selection() -> None:
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

        _dispatch_click_release_at_3d_point(figure, axes, selected_gate.center)

        assert page_slider.exploration.selected_operation_id == selected_gate.operation_id

        _dispatch_drag_in_axes(
            figure,
            axes,
            start=(axes.bbox.x0 + 12.0, axes.bbox.y0 + 12.0),
            end=(axes.bbox.x0 + 42.0, axes.bbox.y0 + 36.0),
        )

        assert page_slider.exploration.selected_operation_id == selected_gate.operation_id
    finally:
        plt.close(figure)


def test_3d_page_slider_background_click_clears_selection() -> None:
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

        _dispatch_click_release_at_3d_point(figure, axes, selected_gate.center)
        assert page_slider.exploration.selected_operation_id == selected_gate.operation_id

        _dispatch_click_release_in_axes(
            figure,
            axes,
            display=(axes.bbox.x0 + 12.0, axes.bbox.y0 + 12.0),
        )

        assert page_slider.exploration.selected_operation_id is None
    finally:
        plt.close(figure)


def test_3d_page_window_arrow_keys_navigate_pages_and_visible_count() -> None:
    result = public_draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    try:
        page_window = get_page_window(result.primary_figure)
        assert page_window is not None

        _dispatch_key_press(result.primary_figure, "down")
        assert page_window.visible_page_count == 2

        _dispatch_key_press(result.primary_figure, "up")
        assert page_window.visible_page_count == 1

        _dispatch_key_press(result.primary_figure, "right")
        assert page_window.start_page == 1

        _dispatch_key_press(result.primary_figure, "left")
        assert page_window.start_page == 0
    finally:
        plt.close(result.primary_figure)


def test_3d_page_window_additional_shortcuts_navigate_and_clear_selection() -> None:
    result = public_draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=36, wire_count=4),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            style={"max_page_width": 4.0},
            show=False,
        ),
    )

    try:
        page_window = get_page_window(result.primary_figure)
        assert page_window is not None

        _dispatch_key_press(result.primary_figure, "down")
        assert page_window.visible_page_count == 2

        _dispatch_key_press(result.primary_figure, "pagedown")
        forward_start_page = page_window.start_page
        assert forward_start_page > 0

        _dispatch_key_press(result.primary_figure, "pageup")
        assert page_window.start_page < forward_start_page

        _dispatch_key_press(result.primary_figure, "end")
        assert page_window.start_page == page_window.total_pages - 1

        _dispatch_key_press(result.primary_figure, "home")
        assert page_window.start_page == 0

        _dispatch_key_press(result.primary_figure, "up")
        assert page_window.visible_page_count == 1

        _dispatch_key_press(result.primary_figure, "+")
        assert page_window.visible_page_count == 2

        _dispatch_key_press(result.primary_figure, "-")
        assert page_window.visible_page_count == 1

        page_window.select_operation("op:0")
        assert page_window.exploration is not None

        _dispatch_key_press(result.primary_figure, "escape")
        assert page_window.exploration.selected_operation_id is None
    finally:
        plt.close(result.primary_figure)


def test_3d_page_window_tab_shortcuts_traverse_visible_expandable_blocks() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_fundamental_rzz_circuits()
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
        assert page_window.exploration is not None

        _dispatch_key_press(figure, "tab")
        assert page_window.exploration.selected_operation_id == "op:0"

        _dispatch_key_press(figure, "tab")
        assert page_window.exploration.selected_operation_id == "op:2"

        _dispatch_key_press(figure, "shift+tab")
        assert page_window.exploration.selected_operation_id == "op:0"
    finally:
        plt.close(figure)


def test_3d_page_window_zero_shortcut_resets_exploration_state() -> None:
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
        assert page_window.exploration is not None

        page_window.select_operation("op:0")
        page_window.toggle_selected_block()
        page_window.toggle_wire_filter()
        page_window.toggle_ancillas()

        assert page_window.exploration.selected_operation_id is not None
        assert page_window.exploration.collapsed_block_ids == set()
        assert page_window.exploration.wire_filter_mode is WireFilterMode.ACTIVE
        assert page_window.exploration.show_ancillas is False

        _dispatch_key_press(figure, "0")

        assert page_window.exploration.selected_operation_id is None
        assert page_window.exploration.collapsed_block_ids == set(
            page_window.exploration.catalog.initial_collapsed_block_ids
        )
        assert page_window.exploration.wire_filter_mode is WireFilterMode.ALL
        assert page_window.exploration.show_ancillas is True
    finally:
        plt.close(figure)


def test_3d_slider_arrow_keys_move_horizontal_window_only() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed3DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.max_start_column > 0

        _dispatch_key_press(figure, "right")
        assert page_slider.start_column == 1

        _dispatch_key_press(figure, "up")
        assert page_slider.start_column == 1

        _dispatch_key_press(figure, "left")
        assert page_slider.start_column == 0
    finally:
        plt.close(figure)


def test_3d_slider_additional_shortcuts_navigate_and_ignore_plus_minus() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=4),
        view="3d",
        topology="line",
        topology_menu=True,
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed3DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.max_start_column > 0

        _dispatch_key_press(figure, "pagedown")
        forward_start_column = page_slider.start_column
        assert forward_start_column > 0

        _dispatch_key_press(figure, "pageup")
        assert page_slider.start_column < forward_start_column

        _dispatch_key_press(figure, "end")
        assert page_slider.start_column == page_slider.max_start_column

        _dispatch_key_press(figure, "home")
        assert page_slider.start_column == 0

        _dispatch_key_press(figure, "+")
        assert page_slider.start_column == 0

        _dispatch_key_press(figure, "-")
        assert page_slider.start_column == 0
    finally:
        plt.close(figure)


def test_3d_slider_tab_shortcuts_select_expandable_blocks_and_clear_selection() -> None:
    current_semantic_ir, expanded_semantic_ir = _semantic_controls_circuits()
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
    figure, axes = create_managed_figure(
        initial_scene,
        figure_width=3.2,
        figure_height=2.4,
        use_agg=True,
        projection="3d",
    )

    try:
        page_slider = configure_3d_page_slider(
            figure=figure,
            axes=axes,
            pipeline=pipeline,
            set_page_slider=set_page_slider,
        )
        assert page_slider is not None
        assert page_slider.exploration is not None

        _dispatch_key_press(figure, "tab")
        assert page_slider.exploration.selected_operation_id == "op:0"

        _dispatch_key_press(figure, "escape")
        assert page_slider.exploration.selected_operation_id is None
    finally:
        plt.close(figure)


def test_3d_slider_zero_shortcut_resets_exploration_state() -> None:
    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
        page_slider=True,
        show=False,
    )

    try:
        page_slider = cast(Managed3DPageSliderState | None, get_page_slider(figure))
        assert page_slider is not None
        assert page_slider.exploration is not None

        selected_gate = next(gate for gate in page_slider.current_scene.gates if gate.operation_id)
        assert selected_gate.operation_id is not None

        page_slider.select_operation(selected_gate.operation_id)
        page_slider.toggle_wire_filter()
        page_slider.toggle_ancillas()

        assert page_slider.exploration.selected_operation_id is not None
        assert page_slider.exploration.wire_filter_mode is WireFilterMode.ACTIVE
        assert page_slider.exploration.show_ancillas is False

        _dispatch_key_press(figure, "0")

        assert page_slider.exploration.selected_operation_id is None
        assert page_slider.exploration.collapsed_block_ids == set(
            page_slider.exploration.catalog.initial_collapsed_block_ids
        )
        assert page_slider.exploration.wire_filter_mode is WireFilterMode.ALL
        assert page_slider.exploration.show_ancillas is True
    finally:
        plt.close(figure)


def test_3d_page_window_enter_toggles_selected_block() -> None:
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
        assert page_window.exploration is not None

        page_window.select_operation("op:0")
        _dispatch_key_press(figure, "enter")

        assert page_window.exploration.selected_operation_id == "op:0.0"
    finally:
        plt.close(figure)


def test_3d_page_window_double_click_toggles_clicked_block() -> None:
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

        _dispatch_click_release_at_3d_point(
            figure, display_axes, selected_gate.center, dblclick=True
        )

        assert page_window.exploration is not None
        assert page_window.exploration.selected_operation_id == "op:0.0"

        expanded_gate = next(
            gate for gate in page_window.current_scene.gates if gate.operation_id == "op:0.0"
        )
        _dispatch_click_release_at_3d_point(
            figure, display_axes, expanded_gate.center, dblclick=True
        )

        assert page_window.exploration.selected_operation_id == "op:0"
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
    _dispatch_click_release_in_axes(
        figure,
        axes,
        display=(float(display_x), float(display_y)),
    )


def _dispatch_click_release_at_3d_point(
    figure: Figure,
    axes: Axes3D,
    point: object,
    dblclick: bool = False,
) -> None:
    figure.canvas.draw()
    projected_x, projected_y, _ = proj3d.proj_transform(
        float(getattr(point, "x")),
        float(getattr(point, "y")),
        float(getattr(point, "z")),
        axes.get_proj(),
    )
    display_x, display_y = axes.transData.transform((projected_x, projected_y))
    _dispatch_click_release_in_axes(
        figure,
        axes,
        display=(float(display_x), float(display_y)),
        dblclick=dblclick,
    )


def _dispatch_click_release_in_axes(
    figure: Figure,
    axes: Axes3D,
    *,
    display: tuple[float, float],
    dblclick: bool = False,
) -> None:
    press_event = MouseEvent(
        "button_press_event",
        figure.canvas,
        display[0],
        display[1],
        button=1,
        dblclick=dblclick,
    )
    figure.canvas.callbacks.process("button_press_event", press_event)
    release_event = MouseEvent(
        "button_release_event",
        figure.canvas,
        display[0],
        display[1],
        button=1,
        dblclick=dblclick,
    )
    figure.canvas.callbacks.process("button_release_event", release_event)


def _dispatch_drag_in_axes(
    figure: Figure,
    axes: Axes3D,
    *,
    start: tuple[float, float],
    end: tuple[float, float],
) -> None:
    press_event = MouseEvent(
        "button_press_event",
        figure.canvas,
        start[0],
        start[1],
        button=1,
    )
    figure.canvas.callbacks.process("button_press_event", press_event)
    release_event = MouseEvent(
        "button_release_event",
        figure.canvas,
        end[0],
        end[1],
        button=1,
    )
    figure.canvas.callbacks.process("button_release_event", release_event)


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
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="S",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="S",
                            native_kind="gate",
                            location=(5,),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="T",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="T",
                            native_kind="gate",
                            location=(6,),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RX",
                        target_wires=("q2",),
                        parameters=(0.25,),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="RX",
                            native_kind="gate",
                            location=(7,),
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
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="S",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="S",
                            native_kind="gate",
                            location=(5, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="T",
                        target_wires=("q2",),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="T",
                            native_kind="gate",
                            location=(6, 0),
                        ),
                    ),
                )
            ),
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=OperationKind.GATE,
                        name="RX",
                        target_wires=("q2",),
                        parameters=(0.25,),
                        provenance=SemanticProvenanceIR(
                            framework="demo",
                            native_name="RX",
                            native_kind="gate",
                            location=(7, 0),
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
