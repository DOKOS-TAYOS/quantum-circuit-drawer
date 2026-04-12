from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.artist import Artist
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch
from matplotlib.text import Text
from pytest import approx

import quantum_circuit_drawer.renderers.matplotlib_primitives as matplotlib_primitives
from quantum_circuit_drawer.ir import ClassicalConditionIR
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.renderers.matplotlib_renderer import MatplotlibRenderer
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_dense_rotation_ir, build_sample_scene


def _display_patch_ratio(figure: object, patch: object) -> float:
    renderer = figure.canvas.get_renderer()
    bounds = patch.get_window_extent(renderer=renderer).bounds
    _, _, width, height = bounds
    return width / height


def _display_bounds(figure: object, artist: object) -> tuple[float, float, float, float]:
    renderer = figure.canvas.get_renderer()
    bounds = artist.get_window_extent(renderer=renderer).bounds
    return bounds


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


def test_matplotlib_renderer_adds_artists() -> None:
    figure, axes = plt.subplots()

    scene = build_sample_scene()
    MatplotlibRenderer().render(scene, ax=axes)

    assert axes.figure is figure
    assert len(axes.patches) >= len(scene.gates) + len(scene.measurements)
    assert _line_artist_count(axes) >= len(scene.wires)
    assert {"H", "M", "q0", "q1", "c0"}.issubset({text.get_text() for text in axes.texts})


def test_matplotlib_renderer_does_not_require_pyplot_subplots(monkeypatch) -> None:
    def fail_subplots(*args, **kwargs):
        raise AssertionError("pyplot.subplots should not be used for renderer-managed figures")

    monkeypatch.setattr(plt, "subplots", fail_subplots)

    figure, axes = MatplotlibRenderer().render(build_sample_scene())

    assert axes.figure is figure
    assert axes.patches
    assert axes.lines


def test_matplotlib_renderer_draws_occluding_patches_above_lines() -> None:
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(build_sample_scene(), ax=axes)

    patch_zorders = [patch.get_zorder() for patch in axes.patches]
    background_line_zorders = _background_line_zorders(axes)

    assert patch_zorders
    assert background_line_zorders
    assert min(patch_zorders) > max(background_line_zorders)


def test_matplotlib_renderer_draws_measurement_destination_arrow_and_label() -> None:
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(build_sample_scene(), ax=axes)

    assert any(isinstance(patch, FancyArrowPatch) for patch in axes.patches)
    assert sum(text.get_text() == "c0" for text in axes.texts) >= 2


def test_matplotlib_renderer_draws_classical_condition_with_arrow_and_bottom_label() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="X",
                        target_wires=("q0",),
                        classical_conditions=(
                            ClassicalConditionIR(wire_ids=("c0",), expression="if c[0]=1"),
                        ),
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    label = next(text for text in axes.texts if text.get_text() == "if c[0]=1")

    assert abs(label.get_position()[1] - scene.wire_y_positions["c0"]) < abs(
        label.get_position()[1] - scene.wire_y_positions["q0"]
    )
    assert (
        scene.wire_y_positions["c0"] - 0.3 < label.get_position()[1] < scene.wire_y_positions["c0"]
    )
    assert any(isinstance(patch, FancyArrowPatch) for patch in axes.patches)
    assert axes.collections[-1].get_linestyle()[0][1] is None


def test_matplotlib_renderer_repeats_wire_labels_when_wrapping_pages() -> None:
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
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    )
                ]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Z", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Y", target_wires=("q1",))]
            ),
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    assert sum(text.get_text() == "q0" for text in axes.texts) == len(scene.pages)
    assert sum(text.get_text() == "q1" for text in axes.texts) == len(scene.pages)


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

    assert any(text.get_text() == "3" for text in axes.texts)


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


def test_matplotlib_renderer_reuses_page_transforms_per_artist(monkeypatch) -> None:
    figure, axes = plt.subplots()
    renderer = MatplotlibRenderer()
    gate_calls = 0
    measurement_calls = 0

    original_gate_for_page = renderer._gate_for_page
    original_measurement_for_page = renderer._measurement_for_page

    def count_gate_for_page(*args, **kwargs):
        nonlocal gate_calls
        gate_calls += 1
        return original_gate_for_page(*args, **kwargs)

    def count_measurement_for_page(*args, **kwargs):
        nonlocal measurement_calls
        measurement_calls += 1
        return original_measurement_for_page(*args, **kwargs)

    monkeypatch.setattr(renderer, "_gate_for_page", count_gate_for_page)
    monkeypatch.setattr(renderer, "_measurement_for_page", count_measurement_for_page)

    scene = build_sample_scene()
    renderer.render(scene, ax=axes)

    assert gate_calls == len(scene.gates)
    assert measurement_calls == len(scene.measurements)


def test_matplotlib_renderer_draws_canonical_cx_without_gate_box_text() -> None:
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
    figure, axes = plt.subplots()

    MatplotlibRenderer().render(scene, ax=axes)

    assert not any(isinstance(patch, FancyBboxPatch) for patch in axes.patches)
    assert sum(isinstance(patch, Circle) for patch in axes.patches) >= 2
    assert not any(text.get_text() == "X" for text in axes.texts)


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
    assert sum(text.get_text() == "q0" for text in axes.texts) == len(scene.pages)
    assert any(text.get_text() == "RX" for text in axes.texts)
    assert any(text.get_text() == "H" for text in axes.texts)
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


def test_matplotlib_renderer_keeps_cx_target_and_control_circular_on_wide_axes() -> None:
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

    circles = [patch for patch in axes.patches if isinstance(patch, Circle)]
    rendered_ratios = sorted(_display_patch_ratio(figure, patch) for patch in circles)

    assert len(rendered_ratios) >= 2
    assert rendered_ratios[0] == approx(1.0, rel=0.04)
    assert rendered_ratios[-1] == approx(1.0, rel=0.04)


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

    annotation_texts = [text.get_text() for text in axes.texts if text.get_text() in {"0", "1"}]

    assert len(scene.pages) > 1
    assert annotation_texts == ["0", "1"]


def test_matplotlib_renderer_keeps_four_letter_gate_label_inside_box() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="SWAP", target_wires=("q0",))]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle())
    figure, axes = plt.subplots(figsize=(2.5, 2.0))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    gate_text = next(text for text in axes.texts if text.get_text() == "SWAP")
    patch_x, _, patch_width, _ = _display_bounds(figure, gate_patch)
    text_x, _, text_width, _ = _display_bounds(figure, gate_text)

    assert text_x >= patch_x
    assert text_x + text_width <= patch_x + patch_width


def test_matplotlib_renderer_keeps_four_letter_labels_inside_boxes_on_wrapped_managed_figures() -> (
    None
):
    quantum_wires = [
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
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
            for layer_index in range(20)
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(max_page_width=4.0))

    figure, axes = MatplotlibRenderer().render(scene)
    figure.canvas.draw()

    gate_patches = sorted(
        (patch for patch in axes.patches if isinstance(patch, FancyBboxPatch)),
        key=lambda patch: patch.get_y(),
    )
    gate_texts = sorted(
        (text for text in axes.texts if text.get_text() == "SWAP"),
        key=lambda text: text.get_position()[1],
    )

    assert len(gate_patches) == len(gate_texts) == 20

    for gate_patch, gate_text in zip(gate_patches, gate_texts, strict=True):
        patch_x, _, patch_width, _ = _display_bounds(figure, gate_patch)
        text_x, _, text_width, _ = _display_bounds(figure, gate_text)

        assert text_x >= patch_x
        assert text_x + text_width <= patch_x + patch_width


def test_matplotlib_renderer_keeps_four_letter_labels_inside_boxes_on_narrow_wrapped_figures() -> (
    None
):
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

    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    gate_text = next(text for text in axes.texts if text.get_text() == "SWAP")
    patch_x, _, patch_width, _ = _display_bounds(figure, gate_patch)
    text_x, _, text_width, _ = _display_bounds(figure, gate_text)

    assert text_x >= patch_x
    assert text_x + text_width <= patch_x + patch_width


def test_matplotlib_renderer_keeps_rotation_label_stack_inside_small_gate_box() -> None:
    circuit = CircuitIR(
        quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RX",
                        target_wires=("q0",),
                        parameters=(1.2345,),
                    )
                ]
            )
        ],
    )
    scene = LayoutEngine().compute(circuit, DrawStyle(show_params=True))
    figure, axes = plt.subplots(figsize=(1.35, 1.6))

    MatplotlibRenderer().render(scene, ax=axes)
    figure.canvas.draw()

    gate = scene.gates[0]
    gate_patch = next(patch for patch in axes.patches if isinstance(patch, FancyBboxPatch))
    label_text = next(text for text in axes.texts if text.get_text() == gate.label)
    subtitle_text = next(text for text in axes.texts if text.get_text() == gate.subtitle)

    patch_x, patch_y, patch_width, patch_height = _display_bounds(figure, gate_patch)
    label_x, label_y, label_width, label_height = _display_bounds(figure, label_text)
    subtitle_x, subtitle_y, subtitle_width, subtitle_height = _display_bounds(figure, subtitle_text)

    text_left = min(label_x, subtitle_x)
    text_top = min(label_y, subtitle_y)
    text_right = max(label_x + label_width, subtitle_x + subtitle_width)
    text_bottom = max(label_y + label_height, subtitle_y + subtitle_height)
    tolerance_pixels = 1.0

    assert text_left >= patch_x - tolerance_pixels
    assert text_right <= patch_x + patch_width + tolerance_pixels
    assert text_top >= patch_y - tolerance_pixels
    assert text_bottom <= patch_y + patch_height + tolerance_pixels


def test_gate_text_fitting_context_matches_existing_font_fit_for_wrapped_subtitles() -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=24),
        DrawStyle(max_page_width=4.0, show_params=True),
    )
    figure, axes = plt.subplots(figsize=(2.1, 18.0))
    gate = next(gate for gate in scene.gates if gate.subtitle == "0.5")

    matplotlib_primitives.prepare_axes(axes, scene)
    context = matplotlib_primitives._build_gate_text_fitting_context(axes, scene)
    cache: dict[tuple[str, float, float], float] = {}

    label_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=context,
        width=gate.width,
        text=gate.label,
        default_font_size=scene.style.font_size,
        cache=cache,
    )
    subtitle_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=context,
        width=gate.width,
        text=gate.subtitle or "",
        default_font_size=scene.style.font_size * 0.78,
        cache=cache,
    )

    assert len(scene.pages) > 1
    assert label_size == approx(
        matplotlib_primitives._fit_gate_text_font_size(
            ax=axes,
            scene=scene,
            width=gate.width,
            text=gate.label,
            default_font_size=scene.style.font_size,
        )
    )
    assert subtitle_size == approx(
        matplotlib_primitives._fit_gate_text_font_size(
            ax=axes,
            scene=scene,
            width=gate.width,
            text=gate.subtitle or "",
            default_font_size=scene.style.font_size * 0.78,
        )
    )


def test_gate_text_fitting_context_caches_repeated_inputs(monkeypatch) -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=8),
        DrawStyle(show_params=True),
    )
    figure, axes = plt.subplots(figsize=(2.5, 4.0))
    gate = scene.gates[0]
    text_size_calls = 0

    matplotlib_primitives.prepare_axes(axes, scene)
    context = matplotlib_primitives._build_gate_text_fitting_context(axes, scene)
    original_text_size = matplotlib_primitives._text_size_in_points

    def count_text_size(text: str) -> tuple[float, float]:
        nonlocal text_size_calls
        text_size_calls += 1
        return original_text_size(text)

    monkeypatch.setattr(matplotlib_primitives, "_text_size_in_points", count_text_size)

    cache: dict[tuple[str, float, float | None, float], float] = {}
    first_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=context,
        width=gate.width,
        height=gate.height * 0.555,
        text=gate.label,
        default_font_size=scene.style.font_size,
        cache=cache,
    )
    second_size = matplotlib_primitives._fit_gate_text_font_size_with_context(
        context=context,
        width=gate.width,
        height=gate.height * 0.555,
        text=gate.label,
        default_font_size=scene.style.font_size,
        cache=cache,
    )

    assert first_size == approx(second_size)
    assert text_size_calls == 1
    assert cache == {
        (gate.label, gate.width, gate.height * 0.555, scene.style.font_size): first_size
    }


def test_matplotlib_renderer_reuses_gate_text_context_per_wrapped_page(monkeypatch) -> None:
    scene = LayoutEngine().compute(
        build_dense_rotation_ir(layer_count=24),
        DrawStyle(max_page_width=4.0, show_params=True),
    )
    figure, axes = plt.subplots(figsize=(2.1, 18.0))
    viewport_calls = 0
    original_get_viewport_width = matplotlib_primitives.get_viewport_width

    def count_viewport_width(*args, **kwargs) -> float:
        nonlocal viewport_calls
        viewport_calls += 1
        return original_get_viewport_width(*args, **kwargs)

    monkeypatch.setattr(matplotlib_primitives, "get_viewport_width", count_viewport_width)

    MatplotlibRenderer().render(scene, ax=axes)

    assert len(scene.pages) > 1
    assert 0 < viewport_calls <= len(scene.pages)


def test_add_text_artist_skips_clip_path_when_fast_path_available(
    monkeypatch: object,
) -> None:
    figure, axes = plt.subplots()
    clip_path_calls = 0
    original_set_clip_path = Text.set_clip_path

    def count_set_clip_path(self: Text, path: object, transform: object = None) -> object:
        nonlocal clip_path_calls
        clip_path_calls += 1
        return original_set_clip_path(self, path, transform)

    monkeypatch.setattr(Text, "set_clip_path", count_set_clip_path)

    text_artist = matplotlib_primitives._add_text_artist(
        axes,
        0.5,
        0.5,
        "H",
        ha="center",
        va="center",
        fontsize=12.0,
    )

    assert text_artist in axes.texts
    assert clip_path_calls == 0


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


def test_add_text_artist_falls_back_to_axes_text_when_fast_path_unavailable(
    monkeypatch: object,
) -> None:
    figure, axes = plt.subplots()
    fallback_calls = 0
    original_axes_text = axes.text

    def count_axes_text(*args: object, **kwargs: object) -> Text:
        nonlocal fallback_calls
        fallback_calls += 1
        return original_axes_text(*args, **kwargs)

    monkeypatch.setattr(
        matplotlib_primitives,
        "_supports_fast_text_artist_path",
        lambda _: False,
    )
    monkeypatch.setattr(axes, "text", count_axes_text)

    text_artist = matplotlib_primitives._add_text_artist(
        axes,
        0.5,
        0.5,
        "fallback",
        fontsize=12.0,
    )

    assert fallback_calls == 1
    assert text_artist in axes.texts


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
        matplotlib_primitives,
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
