# ruff: noqa: F403, F405
from matplotlib.collections import PatchCollection
from matplotlib.colors import to_hex

import quantum_circuit_drawer.renderers._matplotlib_axes as matplotlib_axes_module
from quantum_circuit_drawer.layout.scene import SceneGroupHighlight
from tests._matplotlib_renderer_support import *


def test_matplotlib_renderer_adds_artists() -> None:
    figure, axes = plt.subplots()

    scene = build_sample_scene()
    MatplotlibRenderer().render(scene, ax=axes)

    assert axes.figure is figure
    assert len(axes.patches) >= len(scene.gates) + len(scene.measurements)
    assert _line_artist_count(axes) >= len(scene.wires)
    assert {"H", "M", "q0", "q1", "c0"}.issubset(_normalized_axis_text_values(axes))


def test_matplotlib_renderer_does_not_require_pyplot_subplots(monkeypatch) -> None:
    def fail_subplots(*args, **kwargs):
        raise AssertionError("pyplot.subplots should not be used for renderer-managed figures")

    monkeypatch.setattr(plt, "subplots", fail_subplots)

    figure, axes = MatplotlibRenderer().render(build_sample_scene())

    assert axes.figure is figure
    assert_axes_contains_circuit_artists(axes, expected_texts={"H", "M", "q0", "q1", "c0"})
    assert_figure_has_visible_content(figure)


def test_matplotlib_renderer_draws_occluding_patches_above_lines() -> None:
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(build_sample_scene(), ax=axes)

    patch_zorders = [patch.get_zorder() for patch in axes.patches]
    background_line_zorders = _background_line_zorders(axes)

    assert patch_zorders
    assert background_line_zorders
    assert min(patch_zorders) > max(background_line_zorders)


def test_matplotlib_renderer_projects_pages_without_relying_on_dense_page_indexes() -> None:
    style = DrawStyle(show_wire_labels=False)
    scene = LayoutScene(
        width=style.margin_left + style.gate_width + style.margin_right,
        height=style.margin_top + style.gate_height + style.margin_bottom,
        page_height=style.margin_top + style.gate_height + style.margin_bottom,
        style=style,
        wires=(
            SceneWire(
                id="q0",
                label="q0",
                kind=WireKind.QUANTUM,
                y=style.margin_top,
                x_start=style.margin_left,
                x_end=style.margin_left + style.gate_width,
            ),
        ),
        gates=(
            SceneGate(
                column=0,
                x=style.margin_left + (style.gate_width / 2.0),
                y=style.margin_top,
                width=style.gate_width,
                height=style.gate_height,
                label="X",
                subtitle=None,
                kind=OperationKind.GATE,
            ),
        ),
        gate_annotations=(),
        controls=(),
        connections=(),
        swaps=(),
        barriers=(),
        measurements=(),
        texts=(),
        wire_fold_markers=(),
        pages=(
            ScenePage(
                index=7,
                start_column=0,
                end_column=0,
                content_x_start=style.margin_left,
                content_x_end=style.margin_left + style.gate_width,
                content_width=style.gate_width,
                y_offset=0.0,
            ),
        ),
        hover=HoverOptions(enabled=False),
        wire_y_positions={"q0": style.margin_top},
    )

    projected_pages = MatplotlibRenderer()._project_pages(scene)

    assert len(projected_pages) == 1
    assert projected_pages[0].gates == scene.gates
    assert projected_pages[0].barriers == ()


def test_matplotlib_renderer_draws_classical_bus_marker_and_size() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        classical_wires=[
            WireIR(
                id="c",
                index=0,
                kind=WireKind.CLASSICAL,
                label="c",
                metadata={"bundle_size": 3},
            )
        ],
        layers=[
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c",
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    assert any(normalize_rendered_text(text.get_text()) == "3" for text in axes.texts)


def test_matplotlib_renderer_draws_measurement_pointer_downward() -> None:
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(build_sample_scene(), ax=axes)

    angled_lines = [
        line
        for line in axes.lines
        if len(line.get_xdata()) == 2
        and line.get_xdata()[0] != line.get_xdata()[1]
        and abs(line.get_xdata()[1] - line.get_xdata()[0]) < 0.5
    ]

    assert angled_lines
    assert any(line.get_ydata()[1] > line.get_ydata()[0] for line in angled_lines)


def test_matplotlib_renderer_batches_dense_wire_segments_into_collections() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(4)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        canonical_family=CanonicalGateFamily.X,
                        target_wires=(f"q{(layer_index + 1) % 4}",),
                        control_wires=(f"q{layer_index % 4}",),
                    )
                ]
            )
            for layer_index in range(16)
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    segmented_collections = [
        collection
        for collection in axes.collections
        if hasattr(collection, "get_segments") and len(collection.get_segments()) >= 8
    ]

    assert segmented_collections
    assert len(axes.lines) <= 2


def test_matplotlib_renderer_draws_one_horizontal_wire_segment_per_quantum_wire() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(3)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",)),
                    OperationIR(kind=OperationKind.GATE, name="Z", target_wires=("q1",)),
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RZ",
                        canonical_family=CanonicalGateFamily.RZ,
                        target_wires=("q2",),
                        parameters=(0.5,),
                    ),
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="Y", target_wires=("q0",)),
                    OperationIR(kind=OperationKind.GATE, name="S", target_wires=("q1",)),
                    OperationIR(kind=OperationKind.GATE, name="T", target_wires=("q2",)),
                ]
            ),
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    horizontal_segment_collections = [
        collection
        for collection in axes.collections
        if hasattr(collection, "get_segments")
        and len(collection.get_segments()) == len(scene.wires)
        and all(segment[0][1] == approx(segment[1][1]) for segment in collection.get_segments())
    ]

    assert len(scene.wires) == 3
    assert horizontal_segment_collections
    first_gate_left = min(gate.x - (gate.width / 2.0) for gate in scene.gates)
    last_gate_right = max(gate.x + (gate.width / 2.0) for gate in scene.gates)
    for rendered_segment, wire in zip(
        horizontal_segment_collections[0].get_segments(),
        scene.wires,
        strict=True,
    ):
        assert rendered_segment[0][0] < first_gate_left
        assert rendered_segment[0][1] == approx(wire.y)
        assert rendered_segment[1][0] > last_gate_right
        assert rendered_segment[1][1] == approx(wire.y)


def test_matplotlib_renderer_extends_horizontal_wire_segments_before_and_after_each_page() -> None:
    scene = LayoutEngine().compute(build_wrapped_ir(), DrawStyle(max_page_width=4.0))
    figure, axes = plt.subplots()
    renderer = MatplotlibRenderer()

    renderer.render(scene, ax=axes)

    horizontal_segment_collections = [
        collection
        for collection in axes.collections
        if hasattr(collection, "get_segments")
        and len(collection.get_segments()) == len(scene.wires)
        and all(segment[0][1] == approx(segment[1][1]) for segment in collection.get_segments())
    ]
    projected_pages = renderer._project_pages(scene)

    assert len(horizontal_segment_collections) == len(scene.pages)
    for collection, page, projected_page in zip(
        horizontal_segment_collections,
        scene.pages,
        projected_pages,
        strict=True,
    ):
        x_offset = renderer._page_x_offset(page, scene)
        first_gate_left = min(
            gate.x + x_offset - (gate.width / 2.0) for gate in projected_page.gates
        )
        last_gate_right = max(
            gate.x + x_offset + (gate.width / 2.0) for gate in projected_page.gates
        )
        for rendered_segment in collection.get_segments():
            assert rendered_segment[0][0] < first_gate_left
            assert rendered_segment[1][0] > last_gate_right


def test_matplotlib_renderer_renders_large_wrapped_scene_without_errors() -> None:
    quantum_wires = [
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(6)
    ]
    layers = [
        LayerIR(
            operations=[
                OperationIR(
                    kind=OperationKind.GATE,
                    name="RX" if layer_index % 2 else "H",
                    target_wires=(f"q{layer_index % 6}",),
                    parameters=(0.5,) if layer_index % 2 else (),
                ),
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name="X",
                    target_wires=(f"q{(layer_index + 1) % 6}",),
                    control_wires=(f"q{layer_index % 6}",),
                ),
            ]
        )
        for layer_index in range(18)
    ]
    circuit = CircuitIR(quantum_wires=quantum_wires, layers=layers)
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    assert len(scene.pages) > 1
    assert sum(normalize_rendered_text(text.get_text()) == "q0" for text in axes.texts) == len(
        scene.pages
    )
    assert any(normalize_rendered_text(text.get_text()) == "RX\n0.5" for text in axes.texts)
    assert any(normalize_rendered_text(text.get_text()) == "H" for text in axes.texts)
    assert axes.get_xlim() == approx((0.0, scene.width))


def test_matplotlib_renderer_keeps_compact_gate_boxes_square_on_wide_axes() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots(figsize=(12, 2))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))

    assert _display_patch_ratio(figure, gate_patch) == approx(1.0, rel=0.04)


def test_matplotlib_renderer_batches_cx_target_and_control_markers_into_collections() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
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
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots(figsize=(12, 2))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    ellipse_collections = _ellipse_collections(axes)

    assert len(ellipse_collections) >= 2
    assert all(
        widths == approx(heights)
        for collection in ellipse_collections
        for widths, heights in zip(
            collection.get_widths(),
            collection.get_heights(),
            strict=True,
        )
    )
    assert not any(isinstance(patch, Circle) for patch in axes.patches)


def test_matplotlib_renderer_batches_gate_boxes_into_patch_collections() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index in range(3)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",)),
                    OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q1",)),
                    OperationIR(kind=OperationKind.GATE, name="Z", target_wires=("q2",)),
                ]
            ),
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="S", target_wires=("q0",)),
                    OperationIR(kind=OperationKind.GATE, name="T", target_wires=("q1",)),
                    OperationIR(kind=OperationKind.GATE, name="Y", target_wires=("q2",)),
                ]
            ),
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    patch_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, PatchCollection)
        and len(collection.get_paths()) >= len(scene.gates)
    ]

    assert len(scene.gates) == 6
    assert patch_collections
    assert len([patch for patch in axes.patches if isinstance(patch, FancyBboxPatch)]) < len(
        scene.gates
    )


def test_matplotlib_renderer_batches_measurement_boxes_into_patch_collections() -> None:
    scene = LayoutEngine().compute(_measurement_register_ir(measurement_count=4), DrawStyle())
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    patch_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, PatchCollection)
        and len(collection.get_paths()) >= len(scene.measurements)
    ]

    assert len(scene.measurements) == 4
    assert patch_collections


def test_matplotlib_renderer_batches_group_highlights_into_patch_collection() -> None:
    scene = build_sample_scene()
    scene.group_highlights = (
        SceneGroupHighlight(column=0, x=1.4, y=1.0, width=0.8, height=0.8),
        SceneGroupHighlight(column=0, x=2.4, y=2.0, width=0.9, height=0.9),
    )
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    highlight_collections = [
        collection
        for collection in axes.collections
        if isinstance(collection, PatchCollection)
        and getattr(collection, "get_gid", lambda: None)() == "decomposition-group-highlight"
    ]

    assert highlight_collections
    assert max(len(collection.get_paths()) for collection in highlight_collections) == 2


def test_matplotlib_renderer_draws_open_controls_as_hollow_ellipses() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
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
                        control_values=((0,),),
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots(figsize=(12, 2))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    open_control_collections = [
        collection
        for collection in _ellipse_collections(axes)
        if min(collection.get_widths()) == approx(scene.style.control_radius * 2.0)
        and to_hex(collection.get_facecolors()[0], keep_alpha=False)
        == to_hex(scene.style.theme.axes_facecolor, keep_alpha=False)
        and to_hex(collection.get_edgecolors()[0], keep_alpha=False)
        == to_hex(scene.style.theme.control_color or scene.style.theme.wire_color, keep_alpha=False)
    ]

    assert open_control_collections


def test_matplotlib_renderer_uses_distinct_measurement_fill_in_dark_theme() -> None:
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(build_sample_scene(), ax=axes)

    box_patches = [patch for patch in axes.patches if isinstance(patch, FancyBboxPatch)]

    assert len(box_patches) == 2
    assert box_patches[0].get_facecolor() != box_patches[1].get_facecolor()


def test_matplotlib_renderer_projects_gate_annotations_only_on_matching_page() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q1",))]
            ),
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
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=2.0, show_wire_labels=False))
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    annotation_texts = [
        normalize_rendered_text(text.get_text())
        for text in axes.texts
        if normalize_rendered_text(text.get_text()) in {"0", "1"}
    ]

    assert len(scene.pages) > 1
    assert annotation_texts == ["0", "1"]


def test_matplotlib_renderer_reuses_projected_pages_across_repeated_renders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=24),
        DrawStyle(max_page_width=4.0, show_params=True),
    )
    figure, axes = plt.subplots(figsize=(2.1, 18.0))
    renderer = MatplotlibRenderer()
    project_calls = 0
    original_project_pages = matplotlib_renderer_module.project_pages

    def count_project_pages(scene_to_project: LayoutScene) -> object:
        nonlocal project_calls
        project_calls += 1
        return original_project_pages(scene_to_project)

    monkeypatch.setattr(matplotlib_renderer_module, "project_pages", count_project_pages)

    renderer.render(scene, ax=axes)
    axes.clear()
    renderer.render(scene, ax=axes)

    assert project_calls == 1
    plt.close(figure)


def test_add_patch_artist_skips_clip_path_when_fast_path_available(
    monkeypatch: object,
) -> None:
    figure, axes = plt.subplots()
    clip_path_calls = 0
    original_set_clip_path = Artist.set_clip_path

    def count_set_clip_path(self: Artist, path: object, transform: object = None) -> object:
        nonlocal clip_path_calls
        clip_path_calls += 1
        return original_set_clip_path(self, path, transform)

    monkeypatch.setattr(Artist, "set_clip_path", count_set_clip_path)
    patch = FancyBboxPatch((0.1, 0.1), 1.0, 1.0)

    matplotlib_primitives._add_patch_artist(axes, patch)

    assert patch in axes.patches
    assert clip_path_calls == 0


def test_add_patch_artist_falls_back_to_add_artist_when_fast_path_unavailable(
    monkeypatch: object,
) -> None:
    figure, axes = plt.subplots()
    fallback_calls = 0
    original_add_artist = axes.add_artist

    def count_add_artist(artist: object) -> object:
        nonlocal fallback_calls
        fallback_calls += 1
        return original_add_artist(artist)

    monkeypatch.setattr(
        matplotlib_axes_module,
        "_supports_fast_patch_artist_path",
        lambda _: False,
    )
    monkeypatch.setattr(axes, "add_artist", count_add_artist)
    patch = FancyBboxPatch((0.1, 0.1), 1.0, 1.0)

    matplotlib_primitives._add_patch_artist(axes, patch)

    assert fallback_calls == 1
    assert patch in axes.patches


def test_matplotlib_renderer_keeps_large_wrapped_artists_within_axes_bounds() -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=24),
        DrawStyle(max_page_width=4.0, show_params=True),
    )

    figure, axes = MatplotlibRenderer().render(scene)
    figure.canvas.draw()

    assert _outside_axes_artist_count(figure, axes, axes.texts) == 0
    assert _outside_axes_artist_count(figure, axes, axes.patches) == 0


def test_matplotlib_renderer_keeps_narrow_wrapped_artists_within_axes_bounds() -> None:
    quantum_wires = [
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=str(index))
        for index in range(4)
    ]
    circuit = CircuitIR(
        quantum_wires=quantum_wires,
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="SWAP",
                        target_wires=(f"q{layer_index % 4}",),
                    )
                ]
            )
            for layer_index in range(24)
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
    figure, axes = plt.subplots(figsize=(2.1, 18.0))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    assert _outside_axes_artist_count(figure, axes, axes.texts) == 0
    assert _outside_axes_artist_count(figure, axes, axes.patches) == 0
