from __future__ import annotations

import io
import json
import logging

import matplotlib.pyplot as plt
import pytest

import quantum_circuit_drawer
from quantum_circuit_drawer import (
    DrawConfig,
    OutputOptions,
    analyze_quantum_circuit,
    circuit_to_latex,
    compare_circuits,
    compare_histograms,
    draw_quantum_circuit,
    plot_histogram,
)
from quantum_circuit_drawer.logging import LogFormat, configure_logging
from tests.support import (
    build_public_compare_config,
    build_public_histogram_compare_config,
    build_public_histogram_config,
    build_sample_ir,
)


def _event_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if getattr(record, "event", None) is not None]


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
