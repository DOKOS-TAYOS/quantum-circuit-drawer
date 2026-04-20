# ruff: noqa: F403, F405
import quantum_circuit_drawer.renderers._matplotlib_hover as matplotlib_hover_module
from quantum_circuit_drawer.layout.scene import SceneHoverData
from tests._matplotlib_renderer_support import *


def test_draw_quantum_circuit_2d_interactive_hover_adds_rich_annotation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        _single_gate_with_matrix_ir(),
        hover=HoverOptions(show_matrix="always"),
    )
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    _dispatch_motion_event(figure, axes, gate_patch)
    annotation = next(text for text in axes.texts if isinstance(text, Annotation))

    assert annotation.get_visible() is True
    assert "X" in annotation.get_text()
    assert "qubits: q0" in annotation.get_text().lower()
    assert "matrix: 2 x 2" in annotation.get_text().lower()
    assert "[[" in annotation.get_text()


def test_draw_quantum_circuit_2d_measurement_hover_reports_destination_bit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        _single_measurement_ir(classical_label="alpha", bit_label="alpha[1]"),
        hover=HoverOptions(show_matrix="never"),
    )
    figure.canvas.draw()

    measurement_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    _dispatch_motion_event(figure, axes, measurement_patch)
    annotation = next(text for text in axes.texts if isinstance(text, Annotation))

    assert "qubits: q0" in annotation.get_text().lower()
    assert "bits: alpha[1]" in annotation.get_text().lower()


def test_draw_quantum_circuit_2d_hover_annotation_stays_plain_with_mathtext_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        _single_gate_with_matrix_ir(),
        hover=HoverOptions(show_matrix="never"),
    )
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    _dispatch_motion_event(figure, axes, gate_patch)
    annotation = next(text for text in axes.texts if isinstance(text, Annotation))

    assert "$" not in annotation.get_text()
    assert "x" in annotation.get_text().lower()


def test_draw_quantum_circuit_2d_hover_covers_control_and_target_artists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(build_sample_ir(), hover=True)
    figure.canvas.draw()

    annotation = next(text for text in axes.texts if isinstance(text, Annotation))
    ellipse_collections = _ellipse_collections(axes)
    control_collection = min(
        ellipse_collections, key=lambda collection: min(collection.get_widths())
    )
    x_target_collection = max(
        ellipse_collections, key=lambda collection: max(collection.get_widths())
    )

    _dispatch_motion_event(figure, axes, control_collection)
    control_text = annotation.get_text()
    _dispatch_motion_event(figure, axes, x_target_collection)

    assert annotation.get_visible() is True
    assert control_text == annotation.get_text()


def test_draw_quantum_circuit_2d_hover_falls_back_to_static_labels_when_noninteractive() -> None:
    _, axes = draw_quantum_circuit(build_sample_ir(), hover=True, show=False)

    assert not any(isinstance(text, Annotation) for text in axes.texts)


def test_draw_quantum_circuit_2d_hover_respects_never_matrix_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        _single_gate_with_matrix_ir(),
        hover=HoverOptions(show_matrix="never"),
    )
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    _dispatch_motion_event(figure, axes, gate_patch)
    annotation = next(text for text in axes.texts if isinstance(text, Annotation))

    assert "[[" not in annotation.get_text()


def test_draw_quantum_circuit_2d_hover_hides_visual_size_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(_single_gate_with_matrix_ir(), hover=True)
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    _dispatch_motion_event(figure, axes, gate_patch)
    annotation = next(text for text in axes.texts if isinstance(text, Annotation))

    assert "size:" not in annotation.get_text().lower()


def test_draw_quantum_circuit_2d_hover_uses_canonical_matrix_fallback_when_missing_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        _single_gate_without_matrix_ir(),
        hover=HoverOptions(show_matrix="always"),
    )
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    _dispatch_motion_event(figure, axes, gate_patch)
    annotation = next(text for text in axes.texts if isinstance(text, Annotation))

    assert "matrix: 2 x 2" in annotation.get_text().lower()
    assert "[[" in annotation.get_text()


def test_draw_quantum_circuit_2d_hover_reports_controlled_gate_matrix_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(build_sample_ir(), hover=HoverOptions(show_matrix="never"))
    figure.canvas.draw()

    annotation = next(text for text in axes.texts if isinstance(text, Annotation))
    ellipse_collections = _ellipse_collections(axes)
    control_collection = min(
        ellipse_collections, key=lambda collection: min(collection.get_widths())
    )

    _dispatch_motion_event(figure, axes, control_collection)

    assert "matrix: 4 x 4" in annotation.get_text().lower()
    assert "qubits: q0, q1" in annotation.get_text().lower()


def test_draw_quantum_circuit_2d_hover_only_redraws_on_target_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(build_sample_ir(), hover=True)
    figure.canvas.draw()

    redraw_count = 0
    original_draw_idle = figure.canvas.draw_idle

    def count_draw_idle() -> None:
        nonlocal redraw_count
        redraw_count += 1
        original_draw_idle()

    monkeypatch.setattr(figure.canvas, "draw_idle", count_draw_idle)

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    measurement_patch = max(
        (patch for patch in axes.patches if isinstance(patch, FancyBboxPatch)),
        key=lambda patch: patch.get_y(),
    )
    axes_bounds = axes.get_window_extent(renderer=figure.canvas.get_renderer())

    _dispatch_motion_event(figure, axes, gate_patch)
    assert redraw_count == 1

    _dispatch_motion_event(figure, axes, gate_patch)
    _dispatch_motion_event(figure, axes, gate_patch)
    assert redraw_count == 1

    _dispatch_motion_event(figure, axes, measurement_patch)
    assert redraw_count == 2

    _dispatch_motion_event_at(figure, axes_bounds.x0 + 4.0, axes_bounds.y0 + 4.0)
    assert redraw_count == 3

    _dispatch_motion_event_at(figure, axes_bounds.x0 + 4.0, axes_bounds.y0 + 4.0)
    assert redraw_count == 3


def test_matplotlib_hover_does_not_fill_gap_between_connected_targets() -> None:
    hover_data = SceneHoverData(
        key="controlled-x",
        name="CX",
        qubit_labels=("q0", "q1"),
        other_wire_labels=(),
        matrix=None,
        matrix_dimension=4,
        gate_x=0.0,
        gate_y=0.0,
        gate_width=1.0,
        gate_height=1.0,
    )
    hover_targets: list[matplotlib_hover_module._HoverTarget2D] = []

    matplotlib_hover_module.add_hover_target(
        hover_targets,
        hover_data,
        x_min=0.0,
        x_max=1.0,
        y_min=0.0,
        y_max=1.0,
    )
    matplotlib_hover_module.add_hover_target(
        hover_targets,
        hover_data,
        x_min=0.45,
        x_max=0.55,
        y_min=1.0,
        y_max=4.0,
    )
    matplotlib_hover_module.add_hover_target(
        hover_targets,
        hover_data,
        x_min=0.0,
        x_max=1.0,
        y_min=4.0,
        y_max=5.0,
    )

    hover_boxes = matplotlib_hover_module._build_hover_boxes(hover_targets)

    assert matplotlib_hover_module._resolve_hover_box(hover_boxes, x=0.1, y=2.5) is None
    assert matplotlib_hover_module._resolve_hover_box(hover_boxes, x=0.5, y=2.5) is not None


def test_draw_quantum_circuit_2d_hover_connection_hitbox_stays_near_visible_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    circuit_ir = _adjacent_cnot_and_box_gates_ir()
    scene = LayoutEngine().compute(circuit_ir, DrawStyle())
    projected_page = MatplotlibRenderer()._project_pages(scene)[0]
    connection = next(
        scene_connection
        for scene_connection in projected_page.connections
        if scene_connection.hover_data is not None and scene_connection.hover_data.name == "CNOT"
    )
    right_column_left_edge = min(
        gate.x - (gate.width / 2.0) for gate in projected_page.gates if gate.x > connection.x
    )
    right_column_gate_ys = sorted(gate.y for gate in projected_page.gates if gate.x > connection.x)
    probe_data_x = (connection.x + right_column_left_edge) / 2.0
    probe_data_y = (right_column_gate_ys[1] + right_column_gate_ys[2]) / 2.0

    figure, axes = draw_quantum_circuit(circuit_ir, hover=True)
    try:
        figure.canvas.draw()

        annotation = next(text for text in axes.texts if isinstance(text, Annotation))
        probe_x, probe_y = axes.transData.transform((probe_data_x, probe_data_y))

        _dispatch_motion_event_at(figure, float(probe_x), float(probe_y))

        assert annotation.get_visible() is False
    finally:
        plt.close(figure)


def test_matplotlib_renderer_hover_keeps_batch_draws_for_hoverable_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine().compute(_hover_batching_ir(), DrawStyle())
    figure, axes = plt.subplots()
    singleton_calls = {
        "controls": 0,
        "swaps": 0,
        "connections": 0,
        "x_target_circles": 0,
        "x_target_segments": 0,
    }

    original_draw_controls = matplotlib_renderer_module.draw_controls
    original_draw_swaps = matplotlib_renderer_module.draw_swaps
    original_draw_connections = matplotlib_renderer_module.draw_connections
    original_draw_x_target_circles = matplotlib_renderer_module.draw_x_target_circles
    original_draw_x_target_segments = matplotlib_renderer_module.draw_x_target_segments

    def count_controls(*args: object, **kwargs: object) -> object:
        controls = args[1]
        if len(controls) == 1:
            singleton_calls["controls"] += 1
        return original_draw_controls(*args, **kwargs)

    def count_swaps(*args: object, **kwargs: object) -> object:
        swaps = args[1]
        if len(swaps) == 1:
            singleton_calls["swaps"] += 1
        return original_draw_swaps(*args, **kwargs)

    def count_connections(*args: object, **kwargs: object) -> object:
        connections = args[1]
        if len(connections) == 1:
            singleton_calls["connections"] += 1
        return original_draw_connections(*args, **kwargs)

    def count_x_target_circles(*args: object, **kwargs: object) -> object:
        gates = args[1]
        if len(gates) == 1:
            singleton_calls["x_target_circles"] += 1
        return original_draw_x_target_circles(*args, **kwargs)

    def count_x_target_segments(*args: object, **kwargs: object) -> object:
        gates = args[1]
        if len(gates) == 1:
            singleton_calls["x_target_segments"] += 1
        return original_draw_x_target_segments(*args, **kwargs)

    monkeypatch.setattr(matplotlib_renderer_module, "draw_controls", count_controls)
    monkeypatch.setattr(matplotlib_renderer_module, "draw_swaps", count_swaps)
    monkeypatch.setattr(matplotlib_renderer_module, "draw_connections", count_connections)
    monkeypatch.setattr(matplotlib_renderer_module, "draw_x_target_circles", count_x_target_circles)
    monkeypatch.setattr(
        matplotlib_renderer_module,
        "draw_x_target_segments",
        count_x_target_segments,
    )

    MatplotlibRenderer().render(scene, ax=axes)

    assert singleton_calls == {
        "controls": 0,
        "swaps": 0,
        "connections": 0,
        "x_target_circles": 0,
        "x_target_segments": 0,
    }


def _adjacent_cnot_and_box_gates_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(8)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        canonical_family=CanonicalGateFamily.X,
                        target_wires=("q7",),
                        control_wires=("q2",),
                    )
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q3",)),
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q4",)),
                    OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q5",)),
                    OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q6",)),
                ]
            ),
        ],
    )
