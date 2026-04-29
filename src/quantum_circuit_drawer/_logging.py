"""Shared logging helpers for public and internal package events."""

from __future__ import annotations

import json
import logging as stdlib_logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from os import PathLike
from time import perf_counter
from typing import TextIO
from uuid import uuid4

from ._compat import StrEnum
from .diagnostics import DiagnosticSeverity, RenderDiagnostic

_PACKAGE_LOGGER_NAME = "quantum_circuit_drawer"
_CONTEXT_FIELDS = (
    "request_id",
    "api",
    "view",
    "mode",
    "framework",
    "backend",
    "scope",
)
_STANDARD_RECORD_ATTRS = frozenset(stdlib_logging.makeLogRecord({}).__dict__)
_REQUEST_CONTEXT = ContextVar("quantum_circuit_drawer_request_context", default=None)


class LogFormat(StrEnum):
    """Supported output formats for ``configure_logging``."""

    HUMAN = "human"
    JSON = "json"


@dataclass(frozen=True, slots=True)
class _RequestLogContext:
    request_id: str
    api: str | None = None
    view: str | None = None
    mode: str | None = None
    framework: str | None = None
    backend: str | None = None
    scope: str | None = None


class _HumanLogFormatter(stdlib_logging.Formatter):
    """Readable line formatter for package logs."""

    def format(self, record: stdlib_logging.LogRecord) -> str:
        message = record.getMessage()
        event = getattr(record, "event", None)
        pieces = [record.levelname, record.name]
        if isinstance(event, str) and event:
            pieces.append(f"[{event}]")

        context_parts = [
            f"{field}={value}"
            for field, value in _custom_record_fields(record).items()
            if value is not None and field != "event"
        ]
        line = " ".join((*pieces, *context_parts, message))
        if record.exc_info is not None:
            return f"{line}\n{self.formatException(record.exc_info)}"
        return line


class _JsonLogFormatter(stdlib_logging.Formatter):
    """JSON formatter for machine-readable package logs."""

    def format(self, record: stdlib_logging.LogRecord) -> str:
        payload = {
            "event": getattr(record, "event", None),
            **{field: getattr(record, field, None) for field in _CONTEXT_FIELDS},
        }
        payload.update(_custom_record_fields(record))
        payload.update(
            {
                "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        )
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def configure_logging(
    *,
    level: int | str = "INFO",
    format: LogFormat | str = LogFormat.HUMAN,
    stream: TextIO | None = None,
    logger_name: str = _PACKAGE_LOGGER_NAME,
) -> stdlib_logging.Logger:
    """Configure one package logger with a single managed stream handler."""

    logger = stdlib_logging.getLogger(logger_name)
    _remove_managed_handlers(logger)

    handler = stdlib_logging.StreamHandler(stream)
    handler.setLevel(_normalize_log_level(level))
    handler.setFormatter(_formatter_for_format(format))
    setattr(handler, "_quantum_circuit_drawer_handler_type", "configured")
    logger.addHandler(handler)
    logger.setLevel(_normalize_log_level(level))
    return logger


def package_logger() -> stdlib_logging.Logger:
    """Return the package root logger with a default null handler installed."""

    logger = stdlib_logging.getLogger(_PACKAGE_LOGGER_NAME)
    if not any(
        getattr(handler, "_quantum_circuit_drawer_handler_type", None) == "null"
        for handler in logger.handlers
    ):
        null_handler = stdlib_logging.NullHandler()
        setattr(null_handler, "_quantum_circuit_drawer_handler_type", "null")
        logger.addHandler(null_handler)
    return logger


def current_log_context() -> _RequestLogContext | None:
    """Return the current request-scoped log context, if any."""

    return _REQUEST_CONTEXT.get()


@contextmanager
def push_log_context(**values: object) -> Iterator[_RequestLogContext]:
    """Temporarily enrich the current request log context."""

    current = current_log_context()
    payload = {} if current is None else asdict(current)
    for key, value in values.items():
        if value is None:
            continue
        payload[key] = _normalize_log_value(value)
    payload.setdefault("request_id", uuid4().hex)
    next_context = _RequestLogContext(**payload)
    token = _REQUEST_CONTEXT.set(next_context)
    try:
        yield next_context
    finally:
        _REQUEST_CONTEXT.reset(token)


@contextmanager
def logged_api_call(
    logger: stdlib_logging.Logger,
    *,
    api: str,
) -> Iterator[float]:
    """Log one public API call start and unexpected failure."""

    with push_log_context(api=api):
        log_event(logger, stdlib_logging.INFO, "api.start", "Starting %s.", api)
        started_at = perf_counter()
        try:
            yield started_at
        except Exception:
            log_event(
                logger,
                stdlib_logging.ERROR,
                "api.failed",
                "%s failed.",
                api,
                exc_info=True,
            )
            raise


def log_event(
    logger: stdlib_logging.Logger,
    level: int,
    event: str,
    message: str,
    *args: object,
    exc_info: bool | BaseException | tuple[type[BaseException], BaseException, object] = False,
    **fields: object,
) -> None:
    """Emit one structured package log event."""

    extra: dict[str, object] = {field: None for field in _CONTEXT_FIELDS}
    current = current_log_context()
    if current is not None:
        extra.update(asdict(current))
    extra["event"] = event
    for field_name, value in fields.items():
        extra[field_name] = _normalize_log_value(value)
    logger.log(level, message, *args, extra=extra, exc_info=exc_info)


def emit_render_diagnostics(
    logger: stdlib_logging.Logger,
    diagnostics: tuple[RenderDiagnostic, ...],
) -> None:
    """Emit final public diagnostics into the logger exactly once."""

    emitted: set[tuple[str, str, str]] = set()
    for diagnostic in diagnostics:
        key = (diagnostic.code, diagnostic.message, diagnostic.severity.value)
        if key in emitted:
            continue
        emitted.add(key)
        level = (
            stdlib_logging.WARNING
            if diagnostic.severity is DiagnosticSeverity.WARNING
            else stdlib_logging.INFO
        )
        log_event(
            logger,
            level,
            "diagnostic.emitted",
            diagnostic.message,
            diagnostic_code=diagnostic.code,
            severity=diagnostic.severity.value,
        )


def duration_ms(started_at: float) -> float:
    """Return elapsed wall time in milliseconds."""

    return (perf_counter() - started_at) * 1000.0


def _remove_managed_handlers(logger: stdlib_logging.Logger) -> None:
    managed_handlers = [
        handler
        for handler in logger.handlers
        if getattr(handler, "_quantum_circuit_drawer_handler_type", None) == "configured"
    ]
    for handler in managed_handlers:
        logger.removeHandler(handler)


def _formatter_for_format(value: LogFormat | str) -> stdlib_logging.Formatter:
    normalized_format = _normalize_log_format(value)
    if normalized_format is LogFormat.JSON:
        return _JsonLogFormatter()
    return _HumanLogFormatter()


def _normalize_log_format(value: LogFormat | str) -> LogFormat:
    try:
        return value if isinstance(value, LogFormat) else LogFormat(str(value).lower())
    except ValueError as exc:
        choices = ", ".join(item.value for item in LogFormat)
        raise ValueError(f"format must be one of: {choices}") from exc


def _normalize_log_level(value: int | str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized_value = value.strip().upper()
        level_mapping = stdlib_logging.getLevelNamesMapping()
        if normalized_value in level_mapping:
            return int(level_mapping[normalized_value])
    raise ValueError("level must be an integer or a valid logging level name")


def _custom_record_fields(record: stdlib_logging.LogRecord) -> dict[str, object]:
    return {
        key: _normalize_log_value(value)
        for key, value in record.__dict__.items()
        if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_")
    }


def _normalize_log_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, PathLike):
        return str(value)
    if isinstance(value, tuple):
        return tuple(_normalize_log_value(item) for item in value)
    if isinstance(value, list):
        return [_normalize_log_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _normalize_log_value(item) for key, item in value.items()}
    return value


package_logger()


__all__ = [
    "LogFormat",
    "configure_logging",
    "current_log_context",
    "duration_ms",
    "emit_render_diagnostics",
    "log_event",
    "logged_api_call",
    "package_logger",
    "push_log_context",
]
