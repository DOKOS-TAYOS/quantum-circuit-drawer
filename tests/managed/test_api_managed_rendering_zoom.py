# ruff: noqa: F403, F405
from tests._api_managed_rendering_support import *


def test_draw_quantum_circuit_configures_zoom_text_scaling_once_per_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0
    original_configure_zoom = managed_module.configure_zoom_text_scaling

    def capture_configure_zoom(*args: object, **kwargs: object) -> None:
        nonlocal call_count
        call_count += 1
        original_configure_zoom(*args, **kwargs)

    monkeypatch.setattr(managed_module, "configure_zoom_text_scaling", capture_configure_zoom)

    figure, _ = draw_quantum_circuit(build_sample_ir(), show=False)

    assert call_count == 1
    plt.close(figure)


def test_draw_quantum_circuit_rescales_2d_text_when_zooming() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))

    draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12),
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    gate_label = _text_artist_by_text(axes, "RX\n0.5")
    initial_font_size = gate_label.get_fontsize()

    axes.set_xlim(0.0, 2.5)
    axes.set_ylim(3.5, 0.0)
    figure.canvas.draw()

    assert gate_label.get_fontsize() > initial_font_size

    plt.close(figure)


def test_draw_quantum_circuit_rescales_all_2d_text_when_zooming() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))

    draw_quantum_circuit(
        _zoom_text_scaling_ir(),
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    tracked_labels = ("RZZ\n0.7", "M", "q0", "q1", "c", "0", "1", "dest", "23")
    initial_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}

    axes.set_xlim(0.0, 2.5)
    axes.set_ylim(3.5, 0.0)
    figure.canvas.draw()

    for label in tracked_labels:
        assert _font_size_by_text(axes, label) > initial_font_sizes[label]

    plt.close(figure)


def test_draw_quantum_circuit_updates_gate_text_immediately_when_zoom_changes() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))

    draw_quantum_circuit(
        _zoom_text_scaling_ir(),
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    tracked_labels = ("RZZ\n0.7", "M", "q0", "q1", "c", "0", "1", "dest", "23")
    initial_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}

    axes.set_xlim(0.0, 2.5)
    axes.set_ylim(3.5, 0.0)
    immediate_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}
    figure.canvas.draw()
    drawn_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}

    for label in tracked_labels:
        assert immediate_font_sizes[label] > initial_font_sizes[label]
        assert immediate_font_sizes[label] == pytest.approx(
            drawn_font_sizes[label],
            rel=1e-3,
            abs=1e-3,
        )

    plt.close(figure)


def test_draw_quantum_circuit_updates_gate_text_without_waiting_for_draw_idle() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))

    draw_quantum_circuit(
        _zoom_text_scaling_ir(),
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    tracked_labels = ("RZZ\n0.7", "M", "q0", "q1", "c", "0", "1", "dest", "23")
    initial_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}

    original_draw_idle = figure.canvas.draw_idle

    def suppress_draw_idle() -> None:
        return None

    figure.canvas.draw_idle = suppress_draw_idle  # type: ignore[method-assign]
    try:
        axes.set_xlim(0.0, 2.5)
        axes.set_ylim(3.5, 0.0)
    finally:
        figure.canvas.draw_idle = original_draw_idle  # type: ignore[method-assign]

    updated_font_sizes = {label: _font_size_by_text(axes, label) for label in tracked_labels}

    for label in tracked_labels:
        assert updated_font_sizes[label] > initial_font_sizes[label]

    plt.close(figure)


def test_draw_quantum_circuit_fits_zoom_scaled_text_to_reference_boxes() -> None:
    figure, axes = plt.subplots(figsize=(8.0, 3.0))
    circuit = _zoom_text_scaling_ir()
    style = DrawStyle(max_page_width=12.0)
    scene = LayoutEngine().compute(circuit, style)

    draw_quantum_circuit(
        circuit,
        style={"max_page_width": 12.0},
        ax=axes,
    )
    figure.canvas.draw()

    axes.set_xlim(0.0, 2.5)
    axes.set_ylim(3.5, 0.0)

    full_gate_box_labels = ("q0", "q1", "c")
    half_gate_box_labels = ("M", "dest", "0", "1", "23")

    for label in full_gate_box_labels:
        assert _font_size_by_text(axes, label) == pytest.approx(
            _expected_box_fitted_font_size(
                axes,
                scene,
                text=label,
                width=scene.style.gate_width,
                height=scene.style.gate_height,
                height_fraction=matplotlib_primitives._SINGLE_LINE_HEIGHT_FRACTION,
            ),
            rel=1e-3,
            abs=1e-3,
        )

    for label in half_gate_box_labels:
        assert _font_size_by_text(axes, label) == pytest.approx(
            _expected_box_fitted_font_size(
                axes,
                scene,
                text=label,
                width=scene.style.gate_width * 0.5,
                height=scene.style.gate_height * 0.5,
                height_fraction=1.0,
            ),
            rel=1e-3,
            abs=1e-3,
        )

    plt.close(figure)
