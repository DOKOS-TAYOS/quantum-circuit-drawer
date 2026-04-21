# ruff: noqa: F403, F405
from tests._api_managed_rendering_support import *


def test_draw_quantum_circuit_adds_managed_3d_page_slider_for_column_navigation() -> None:
    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        view="3d",
        topology="line",
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    page_slider = get_page_slider(figure)

    assert axes.figure is figure
    assert page_slider is not None
    assert page_slider.window_size < 12
    assert page_slider.horizontal_slider is not None
    assert page_slider.vertical_slider is None
    assert page_slider.start_column == 0

    horizontal_slider = page_slider.horizontal_slider
    assert horizontal_slider is not None
    horizontal_slider.set_val(horizontal_slider.valmax)

    assert page_slider.start_column == page_slider.max_start_column
    assert page_slider.start_column in page_slider.scene_cache
    plt.close(figure)


def test_draw_quantum_circuit_3d_page_slider_adapts_window_size_to_figure_width() -> None:
    narrow_figure, _ = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=4),
        view="3d",
        topology="line",
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
        figsize=(3.2, 12.0),
    )
    wide_figure, _ = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=24, wire_count=4),
        view="3d",
        topology="line",
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
        figsize=(12.0, 4.0),
    )

    narrow_slider = get_page_slider(narrow_figure)
    wide_slider = get_page_slider(wide_figure)

    assert narrow_slider is not None
    assert wide_slider is not None
    assert wide_slider.window_size > narrow_slider.window_size
    assert wide_slider.max_start_column < narrow_slider.max_start_column

    plt.close(narrow_figure)
    plt.close(wide_figure)


def test_draw_quantum_circuit_3d_page_slider_keeps_window_when_switching_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=12, wire_count=4),
        view="3d",
        topology="line",
        topology_menu=True,
        style={"max_page_width": 4.0},
        page_slider=True,
    )
    page_slider = get_page_slider(figure)
    menu_state = get_topology_menu_state(figure)

    assert page_slider is not None
    assert menu_state is not None
    horizontal_slider = page_slider.horizontal_slider
    assert horizontal_slider is not None

    horizontal_slider.set_val(min(horizontal_slider.valmax, 2.0))
    preserved_start_column = page_slider.start_column
    menu_state.select_topology("grid")

    assert menu_state.axes is axes
    assert page_slider.start_column == preserved_start_column
    assert page_slider.current_scene.topology.name == "grid"
    plt.close(figure)
