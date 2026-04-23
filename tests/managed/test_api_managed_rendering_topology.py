# ruff: noqa: F403, F405
from tests._api_managed_rendering_support import *


def test_draw_quantum_circuit_3d_uses_agg_canvas_for_hidden_non_hover_render_on_interactive_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.renderers._matplotlib_figure as figure_support

    captured_use_agg: list[bool] = []
    original_create_managed_figure = figure_support.create_managed_figure

    def capture_create_managed_figure(*args: object, **kwargs: object) -> tuple[Figure, object]:
        captured_use_agg.append(bool(kwargs.get("use_agg", False)))
        return original_create_managed_figure(*args, **kwargs)

    monkeypatch.setattr(plt, "get_backend", lambda: "TkAgg")
    monkeypatch.setattr(figure_support, "create_managed_figure", capture_create_managed_figure)

    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        show=False,
    )

    assert axes.figure is figure
    assert captured_use_agg == [True]
    assert isinstance(figure.canvas, FigureCanvasAgg)
    plt.close(figure)


def test_draw_quantum_circuit_3d_keeps_interactive_canvas_for_hidden_hover_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.renderers._matplotlib_figure as figure_support

    captured_use_agg: list[bool] = []
    original_create_managed_figure = figure_support.create_managed_figure

    def capture_create_managed_figure(*args: object, **kwargs: object) -> tuple[Figure, object]:
        captured_use_agg.append(bool(kwargs.get("use_agg", False)))
        return original_create_managed_figure(*args, **kwargs)

    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)
    monkeypatch.setattr(figure_support, "create_managed_figure", capture_create_managed_figure)

    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        hover=True,
        show=False,
    )

    assert axes.figure is figure
    assert captured_use_agg == [False]
    plt.close(figure)


def test_draw_quantum_circuit_attaches_lower_left_dark_topology_radio_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
    )
    menu_state = get_topology_menu_state(figure)

    assert axes.figure is figure
    assert menu_state is not None
    assert menu_state.active_topology == "line"
    assert menu_state.valid_topologies == ("line", "star")
    assert menu_state.menu_axes is not None
    assert menu_state.radio is not None
    assert tuple(menu_state.menu_axes.get_position().bounds) == pytest.approx(
        (0.035, 0.06, 0.17, 0.21),
        abs=1e-3,
    )
    assert menu_state.menu_axes.get_facecolor() == pytest.approx(mcolors.to_rgba("#171221"))
    assert menu_state.menu_axes.spines["left"].get_edgecolor() == pytest.approx(
        mcolors.to_rgba("#352a45")
    )
    assert menu_state.radio.value_selected == "line"
    assert [label.get_text() for label in menu_state.radio.labels] == [
        "line",
        "grid",
        "star",
        "star_tree",
        "honeycomb",
    ]
    plt.close(figure)


def test_draw_quantum_circuit_skips_topology_menu_for_caller_managed_3d_axes() -> None:
    figure = plt.figure()
    axes = figure.add_subplot(111, projection="3d")

    draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
        ax=axes,
    )

    assert get_topology_menu_state(figure) is None
    plt.close(figure)


def test_topology_menu_redraws_same_axes_with_new_valid_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, axes = draw_quantum_circuit(
        build_dense_rotation_ir(layer_count=2, wire_count=4),
        view="3d",
        topology="line",
        topology_menu=True,
    )
    menu_state = get_topology_menu_state(figure)

    assert menu_state is not None
    menu_state.select_topology("grid")

    assert menu_state.active_topology == "grid"
    assert menu_state.axes is axes
    assert menu_state.scene.topology.name == "grid"
    plt.close(figure)


def test_topology_menu_keeps_invalid_topologies_visible_but_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, _ = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
    )
    menu_state = get_topology_menu_state(figure)

    assert menu_state is not None
    assert menu_state.is_enabled("line") is True
    assert menu_state.is_enabled("grid") is False
    assert set(menu_state.topologies) == {"line", "grid", "star", "star_tree", "honeycomb"}

    menu_state.select_topology("grid")

    assert menu_state.active_topology == "line"
    plt.close(figure)


def test_topology_menu_reverts_invalid_radio_selection_to_active_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plt, "get_backend", lambda: "QtAgg")
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: None)

    figure, _ = draw_quantum_circuit(
        build_sample_ir(),
        view="3d",
        topology="line",
        topology_menu=True,
    )
    menu_state = get_topology_menu_state(figure)

    assert menu_state is not None
    assert menu_state.radio is not None

    menu_state.select_topology("grid")

    assert menu_state.active_topology == "line"
    assert menu_state.radio.value_selected == "line"
    assert menu_state.radio.labels[1].get_color() != menu_state.radio.labels[0].get_color()
    plt.close(figure)
