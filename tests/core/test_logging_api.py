from __future__ import annotations

import io
import json
import logging
from typing import cast

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.figure import Figure

import quantum_circuit_drawer
import quantum_circuit_drawer.managed.rendering as managed_module
from quantum_circuit_drawer import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    analyze_quantum_circuit,
    circuit_to_latex,
    compare_circuits,
    compare_histograms,
    draw_quantum_circuit,
    plot_histogram,
)
from quantum_circuit_drawer.ir.lowering import lower_semantic_circuit
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.logging import LogFormat, configure_logging
from quantum_circuit_drawer.renderers._matplotlib_figure import (
    create_managed_figure,
    get_histogram_state,
    get_page_slider,
    get_page_window,
    get_topology_menu_state,
    set_page_slider,
    set_page_window,
)
from quantum_circuit_drawer.renderers.matplotlib_renderer import MatplotlibRenderer
from quantum_circuit_drawer.style import DrawStyle
from tests.managed.test_2d_exploration import _semantic_controls_circuits
from tests.support import (
    build_dense_rotation_ir,
    build_public_compare_config,
    build_public_draw_config,
    build_public_histogram_compare_config,
    build_public_histogram_config,
    build_sample_ir,
    build_wrapped_ir,
)


def _event_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if getattr(record, "event", None) is not None]


def _interactive_event_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        record
        for record in _event_records(caplog)
        if str(getattr(record, "event", "")).startswith("interactive.")
    ]


def _dispatch_key_press(figure: Figure, key: str) -> None:
    event = KeyEvent("key_press_event", figure.canvas, key=key)
    figure.canvas.callbacks.process("key_press_event", event)


def _dispatch_click_at_axes_center(figure: Figure, axes: Axes) -> None:
    x, y, width, height = axes.get_window_extent(renderer=figure.canvas.get_renderer()).bounds
    press_event = MouseEvent(
        "button_press_event",
        figure.canvas,
        x + (width / 2.0),
        y + (height / 2.0),
        button=1,
    )
    release_event = MouseEvent(
        "button_release_event",
        figure.canvas,
        x + (width / 2.0),
        y + (height / 2.0),
        button=1,
    )
    figure.canvas.callbacks.process("button_press_event", press_event)
    figure.canvas.callbacks.process("button_release_event", release_event)


def _dense_histogram_counts(*, bit_width: int = 7) -> dict[str, int]:
    return {
        format(index, f"0{bit_width}b"): ((index * 17) % 41) + (index % 7) + 3
        for index in range(2**bit_width)
    }


def test_public_package_exports_logging_api() -> None:
    assert quantum_circuit_drawer.configure_logging is configure_logging
    assert quantum_circuit_drawer.LogFormat is LogFormat


def test_configure_logging_is_idempotent_and_writes_human_logs() -> None:
    stream = io.StringIO()

    logger = configure_logging(
        level="DEBUG",
        stream=stream,
        logger_name="quantum_circuit_drawer.tests.logging_api",
    )
    logger.debug("first message")
    logger = configure_logging(
        level="DEBUG",
        stream=stream,
        logger_name="quantum_circuit_drawer.tests.logging_api",
    )
    logger.debug("second message")

    output_lines = [line for line in stream.getvalue().splitlines() if line.strip()]

    assert len(logger.handlers) == 1
    assert len(output_lines) == 2
    assert "first message" in output_lines[0]
    assert "second message" in output_lines[1]


def test_configure_logging_writes_json_records() -> None:
    stream = io.StringIO()
    logger = configure_logging(
        level="INFO",
        format=LogFormat.JSON,
        stream=stream,
        logger_name="quantum_circuit_drawer.tests.logging_json",
    )

    logger.warning("json message")

    payload = json.loads(stream.getvalue().strip())

    assert payload["level"] == "WARNING"
    assert payload["logger"] == "quantum_circuit_drawer.tests.logging_json"
    assert payload["message"] == "json message"
    assert "event" in payload


def test_draw_quantum_circuit_logs_structured_events_with_shared_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(output=OutputOptions(show=False)),
    )

    event_records = _event_records(caplog)
    events = {record.event for record in event_records}
    request_ids = {record.request_id for record in event_records}

    assert {
        "api.start",
        "runtime.resolved",
        "adapter.resolved",
        "ir.resolved",
        "layout.completed",
        "render.completed",
        "api.completed",
    }.issubset(events)
    assert len(request_ids) == 1
    assert all(record.api == "draw_quantum_circuit" for record in event_records)

    completed_record = next(record for record in event_records if record.event == "api.completed")
    assert completed_record.duration_ms >= 0.0
    assert completed_record.page_count >= 1
    plt.close(result.primary_figure)


def test_draw_quantum_circuit_logs_diagnostics_once(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from quantum_circuit_drawer.drawing.runtime import RuntimeContext

    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )
    caplog.set_level("INFO", logger="quantum_circuit_drawer")

    result = draw_quantum_circuit(build_sample_ir(), config=DrawConfig(output=OutputOptions()))

    diagnostic_records = [
        record for record in _event_records(caplog) if record.event == "diagnostic.emitted"
    ]

    assert [record.diagnostic_code for record in diagnostic_records] == [
        "auto_mode_resolved",
        "show_requested_without_interactive_backend",
    ]
    plt.close(result.primary_figure)


def test_draw_quantum_circuit_logs_api_failed_once_for_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_prepare_draw_call(*args: object, **kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.preparation.prepare_draw_call",
        fail_prepare_draw_call,
    )
    caplog.set_level("ERROR", logger="quantum_circuit_drawer")

    with pytest.raises(RuntimeError, match="boom"):
        draw_quantum_circuit(build_sample_ir(), config=DrawConfig(output=OutputOptions(show=False)))

    failed_records = [record for record in _event_records(caplog) if record.event == "api.failed"]

    assert len(failed_records) == 1
    assert failed_records[0].api == "draw_quantum_circuit"
    assert failed_records[0].exc_info is not None


def test_analyze_quantum_circuit_logs_structured_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="quantum_circuit_drawer")

    analyze_quantum_circuit(build_sample_ir(), config=DrawConfig(output=OutputOptions(show=False)))

    event_records = _event_records(caplog)
    events = {record.event for record in event_records}

    assert {"api.start", "runtime.resolved", "layout.completed", "api.completed"}.issubset(events)
    assert len({record.request_id for record in event_records}) == 1
    assert all(record.api == "analyze_quantum_circuit" for record in event_records)


def test_circuit_to_latex_logs_structured_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="quantum_circuit_drawer")

    result = circuit_to_latex(build_sample_ir(), mode="full")

    event_records = _event_records(caplog)
    events = {record.event for record in event_records}

    assert {"api.start", "runtime.resolved", "layout.completed", "api.completed"}.issubset(events)
    assert len({record.request_id for record in event_records}) == 1
    assert all(record.api == "circuit_to_latex" for record in event_records)
    assert result.page_count == 1


def test_plot_histogram_logs_structured_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="quantum_circuit_drawer")

    result = plot_histogram(
        {"00": 5, "11": 3},
        config=build_public_histogram_config(show=False),
    )

    event_records = _event_records(caplog)
    events = {record.event for record in event_records}

    assert {"api.start", "runtime.resolved", "render.completed", "api.completed"}.issubset(events)
    assert len({record.request_id for record in event_records}) == 1
    assert all(record.api == "plot_histogram" for record in event_records)
    plt.close(result.figure)


def test_compare_histograms_logs_structured_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="quantum_circuit_drawer")

    result = compare_histograms(
        {"00": 5, "11": 3},
        {"00": 4, "11": 4},
        config=build_public_histogram_compare_config(show=False),
    )

    event_records = _event_records(caplog)
    events = {record.event for record in event_records}

    assert {"api.start", "runtime.resolved", "render.completed", "api.completed"}.issubset(events)
    assert len({record.request_id for record in event_records}) == 1
    assert all(record.api == "compare_histograms" for record in event_records)
    plt.close(result.figure)


def test_compare_circuits_logs_structured_events_and_side_scopes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="quantum_circuit_drawer")

    result = compare_circuits(
        build_sample_ir(),
        build_sample_ir(),
        config=build_public_compare_config(show=False),
    )

    event_records = _event_records(caplog)
    side_scope_records = [record for record in event_records if getattr(record, "scope", None)]

    assert {"api.start", "api.completed"}.issubset({record.event for record in event_records})
    assert len({record.request_id for record in event_records}) == 1
    assert all(record.api == "compare_circuits" for record in event_records)
    assert {record.scope for record in side_scope_records} >= {"left", "right"}
    for side_result in result.side_results:
        plt.close(side_result.primary_figure)
    plt.close(result.figure)


def test_draw_quantum_circuit_logs_interactive_2d_slider_events_with_session_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")
    current_semantic_ir, _ = _semantic_controls_circuits()
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
    )
    page_slider = cast(object | None, get_page_slider(figure))

    assert page_slider is not None
    assert getattr(page_slider, "help_button_axes", None) is not None

    page_slider.select_operation("op:0")
    page_slider.show_start_column(1)
    page_slider.toggle_selected_block()
    page_slider.toggle_wire_filter()
    page_slider.toggle_ancillas()
    _dispatch_click_at_axes_center(figure, page_slider.help_button_axes)

    event_records = _interactive_event_records(caplog)
    events = {record.event for record in event_records}

    assert {
        "interactive.session.started",
        "interactive.viewport.changed",
        "interactive.selection.changed",
        "interactive.block.changed",
        "interactive.wire_filter.changed",
        "interactive.ancillas.changed",
        "interactive.help_toggled",
    }.issubset(events)
    assert len({record.request_id for record in event_records}) == 1
    assert len({record.session_id for record in event_records}) == 1
    assert all(record.surface == "2d_slider" for record in event_records)
    assert {"programmatic", "button"} <= {record.interaction_source for record in event_records}

    plt.close(figure)


def test_draw_quantum_circuit_logs_interactive_2d_page_window_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")
    current_semantic_ir, _ = _semantic_controls_circuits()
    current_circuit = lower_semantic_circuit(current_semantic_ir)
    layout_engine = LayoutEngine()
    style = DrawStyle(max_page_width=1.8)
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
        expanded_semantic_ir=current_semantic_ir,
    )
    page_window = cast(object | None, get_page_window(figure))

    assert page_window is not None

    page_window.step_page(1)
    page_window.step_visible_pages(1)
    page_window.select_operation("op:0")
    page_window.toggle_wire_filter()
    page_window.reset_exploration_view()

    event_records = _interactive_event_records(caplog)
    events = {record.event for record in event_records}

    assert {
        "interactive.session.started",
        "interactive.viewport.changed",
        "interactive.selection.changed",
        "interactive.wire_filter.changed",
        "interactive.view.reset",
    }.issubset(events)
    assert len({record.request_id for record in event_records}) == 1
    assert len({record.session_id for record in event_records}) == 1
    assert all(record.surface == "2d_page_window" for record in event_records)

    plt.close(figure)


def test_draw_quantum_circuit_logs_interactive_3d_topology_events_with_shared_session(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")
    monkeypatch.setattr(
        "quantum_circuit_drawer.renderers._render_support.should_use_managed_agg_canvas",
        lambda **_kwargs: False,
    )

    result = draw_quantum_circuit(
        build_wrapped_ir(),
        config=build_public_draw_config(
            mode=DrawMode.PAGES_CONTROLS,
            view="3d",
            topology="line",
            topology_menu=True,
            show=False,
        ),
    )

    page_window = cast(object | None, get_page_window(result.primary_figure))
    menu_state = cast(object | None, get_topology_menu_state(result.primary_figure))

    assert page_window is not None
    assert menu_state is not None
    assert getattr(menu_state, "radio", None) is not None

    menu_state.radio.set_active(menu_state.topologies.index("grid"))
    _dispatch_key_press(result.primary_figure, "shift+t")

    event_records = _interactive_event_records(caplog)
    topology_records = [
        record for record in event_records if record.event == "interactive.topology.changed"
    ]

    assert {record.interaction_source for record in topology_records} >= {"radio", "keyboard"}
    assert len({record.request_id for record in event_records}) == 1
    assert len({record.session_id for record in event_records}) == 1
    assert all(record.surface == "3d_page_window" for record in topology_records)

    plt.close(result.primary_figure)


def test_plot_histogram_logs_interactive_events_and_invalid_input(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")

    result = plot_histogram(
        _dense_histogram_counts(),
        config=build_public_histogram_config(
            mode="interactive",
            show=False,
            figsize=(8.0, 4.0),
        ),
    )

    state = cast(object | None, get_histogram_state(result.figure))

    assert state is not None
    assert getattr(state, "help_button_axes", None) is not None

    state.cycle_sort()
    state.toggle_label_mode()
    state.toggle_kind()
    state.toggle_slider()
    state.set_window_start(1)
    _dispatch_key_press(result.figure, "u")
    state.submit_marginal_text("0,2,5")
    state.submit_marginal_text("0, bad")
    _dispatch_click_at_axes_center(result.figure, state.help_button_axes)

    event_records = _interactive_event_records(caplog)
    events = {record.event for record in event_records}

    assert {
        "interactive.session.started",
        "interactive.sort.changed",
        "interactive.label_mode.changed",
        "interactive.kind.changed",
        "interactive.slider_visibility.changed",
        "interactive.window.changed",
        "interactive.uniform_reference.changed",
        "interactive.marginal.changed",
        "interactive.input.invalid",
        "interactive.help_toggled",
    }.issubset(events)
    assert len({record.request_id for record in event_records}) == 1
    assert len({record.session_id for record in event_records}) == 1
    assert all(record.surface == "histogram" for record in event_records)
    invalid_records = [
        record for record in event_records if record.event == "interactive.input.invalid"
    ]
    assert invalid_records
    assert all(record.levelname == "WARNING" for record in invalid_records)

    plt.close(result.figure)


def test_compare_circuits_interactive_logs_keep_scope_and_distinct_sessions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")

    config = build_public_compare_config(
        show=False,
        shared=DrawSideConfig(
            render=CircuitRenderOptions(
                mode=DrawMode.PAGES_CONTROLS,
                view="2d",
            ),
            appearance=CircuitAppearanceOptions(
                style={"max_page_width": 4.0},
            ),
        ),
    )
    result = compare_circuits(
        build_dense_rotation_ir(layer_count=18, wire_count=4),
        build_dense_rotation_ir(layer_count=18, wire_count=4),
        config=config,
    )

    left_state = cast(object | None, get_page_window(result.side_results[0].primary_figure))
    right_state = cast(object | None, get_page_window(result.side_results[1].primary_figure))

    assert left_state is not None
    assert right_state is not None

    left_state.step_page(1)
    right_state.step_page(1)

    event_records = _interactive_event_records(caplog)
    viewport_records = [
        record for record in event_records if record.event == "interactive.viewport.changed"
    ]

    assert len({record.request_id for record in viewport_records}) == 1
    assert {record.scope for record in viewport_records} >= {"left", "right"}
    left_session_ids = {record.session_id for record in viewport_records if record.scope == "left"}
    right_session_ids = {
        record.session_id for record in viewport_records if record.scope == "right"
    }
    assert left_session_ids
    assert right_session_ids
    assert left_session_ids.isdisjoint(right_session_ids)

    for side_result in result.side_results:
        plt.close(side_result.primary_figure)
    plt.close(result.figure)
