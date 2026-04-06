from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch
from pytest import approx

from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.renderers.matplotlib_renderer import MatplotlibRenderer
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_sample_scene


def _display_patch_ratio(figure: object, patch: object) -> float:
    renderer = figure.canvas.get_renderer()
    bounds = patch.get_window_extent(renderer=renderer).bounds
    _, _, width, height = bounds
    return width / height


def _display_bounds(figure: object, artist: object) -> tuple[float, float, float, float]:
    renderer = figure.canvas.get_renderer()
    bounds = artist.get_window_extent(renderer=renderer).bounds
    return bounds


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
