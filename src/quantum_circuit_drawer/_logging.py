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
_HUMAN_CONTEXT_PRIORITY = (
    "request_id",
    "session_id",
    "api",
    "scope",
    "surface",
    "interaction_source",
)
_CONTEXT_FIELDS = (
    "request_id",
    "api",
    "view",
    "mode",
    "framework",
    "backend",
    "scope",
    "session_id",
    "surface",
)
_STANDARD_RECORD_ATTRS = frozenset(stdlib_logging.makeLogRecord({}).__dict__)
_REQUEST_CONTEXT = ContextVar("quantum_circuit_drawer_request_context", default=None)
_INTERACTIVE_CONTEXT = ContextVar("quantum_circuit_drawer_interactive_context", default=None)


class LogFormat(StrEnum):
    """Supported output formats for ``configure_logging``."""

    HUMAN = "human"
    JSON = "json"


class LogProfile(StrEnum):
    """Supported verbosity profiles for ``configure_logging``."""

    SUMMARY = "summary"
    DETAIL = "detail"
    INTERACTIVE = "interactive"


@dataclass(frozen=True, slots=True)
class _RequestLogContext:
    request_id: str
    api: str | None = None
    view: str | None = None
    mode: str | None = None
    framework: str | None = None
    backend: str | None = None
    scope: str | None = None


@dataclass(frozen=True, slots=True)
class InteractiveLogSession:
    request_id: str
    session_id: str
    surface: str
    api: str | None = None
    view: str | None = None
    mode: str | None = None
    framework: str | None = None
    backend: str | None = None
    scope: str | None = None


class InteractionSource(StrEnum):
    """Supported origins for interactive state transitions."""

    KEYBOARD = "keyboard"
    BUTTON = "button"
    SLIDER = "slider"
    TEXTBOX = "textbox"
    RADIO = "radio"
    MOUSE = "mouse"
    PROGRAMMATIC = "programmatic"


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
            for field, value in _ordered_custom_record_fields(record).items()
            if value is not None and field != "event"
        ]
        line = " ".join((*pieces, *context_parts, message))
        if record.exc_info:
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
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)


class _LogProfileFilter(stdlib_logging.Filter):
    """Filter structured package events according to one configured profile."""

    def __init__(self, profile: LogProfile) -> None:
        super().__init__()
        self._profile = profile

    def filter(self, record: stdlib_logging.LogRecord) -> bool:
        if record.levelno >= stdlib_logging.WARNING:
            return True
        event = getattr(record, "event", None)
        if not isinstance(event, str) or not event:
            return True
        if self._profile is LogProfile.INTERACTIVE:
            return True
        if self._profile is LogProfile.DETAIL:
            return not event.startswith("interactive.")
        return event.startswith("api.") or event == "diagnostic.emitted" or event == "output.saved"


def configure_logging(
    *,
    level: int | str = "INFO",
    format: LogFormat | str = LogFormat.HUMAN,
    profile: LogProfile | str = LogProfile.INTERACTIVE,
    stream: TextIO | None = None,
    logger_name: str = _PACKAGE_LOGGER_NAME,
) -> stdlib_logging.Logger:
    """Configure one package logger with one managed stream handler and profile filter."""

    logger = stdlib_logging.getLogger(logger_name)
    _remove_managed_handlers(logger)

    handler = stdlib_logging.StreamHandler(stream)
    handler.setLevel(_normalize_log_level(level))
    handler.setFormatter(_formatter_for_format(format))
    handler.addFilter(_LogProfileFilter(_normalize_log_profile(profile)))
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


def current_interactive_log_session() -> InteractiveLogSession | None:
    """Return the current interactive session context, if any."""

    return _INTERACTIVE_CONTEXT.get()


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
def push_interactive_log_session(
    session: InteractiveLogSession,
) -> Iterator[InteractiveLogSession]:
    """Temporarily activate one interactive log session."""

    token = _INTERACTIVE_CONTEXT.set(session)
    try:
        yield session
    finally:
        _INTERACTIVE_CONTEXT.reset(token)


def create_interactive_log_session(
    *,
    surface: str,
    request_id: str | None = None,
    api: str | None = None,
    view: str | None = None,
    mode: str | None = None,
    framework: str | None = None,
    backend: str | None = None,
    scope: str | None = None,
    session_id: str | None = None,
) -> InteractiveLogSession:
    """Create one interactive log session, inheriting the current request when present."""

    current = current_log_context()
    return InteractiveLogSession(
        request_id=_resolved_context_field(
            explicit_value=request_id,
            current_value=current.request_id if current is not None else None,
            fallback=uuid4().hex,
        ),
        session_id=_resolved_context_field(
            explicit_value=session_id,
            current_value=None,
            fallback=uuid4().hex,
        ),
        surface=_resolved_context_field(
            explicit_value=surface,
            current_value=None,
            fallback="interactive",
        ),
        api=_optional_context_field(api, current.api if current is not None else None),
        view=_optional_context_field(view, current.view if current is not None else None),
        mode=_optional_context_field(mode, current.mode if current is not None else None),
        framework=_optional_context_field(
            framework,
            current.framework if current is not None else None,
        ),
        backend=_optional_context_field(
            backend,
            current.backend if current is not None else None,
        ),
        scope=_optional_context_field(scope, current.scope if current is not None else None),
    )


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
    interactive_session = current_interactive_log_session()
    if interactive_session is not None:
        extra.update(asdict(interactive_session))
    extra["event"] = event
    for field_name, value in fields.items():
        extra[field_name] = _normalize_log_value(value)
    logger.log(level, message, *args, extra=extra, exc_info=exc_info)


def log_interaction(
    logger: stdlib_logging.Logger,
    level: int,
    event: str,
    message: str,
    *,
    session: InteractiveLogSession,
    source: InteractionSource | str,
    exc_info: bool | BaseException | tuple[type[BaseException], BaseException, object] = False,
    **fields: object,
) -> None:
    """Emit one interactive package event under the provided persistent session."""

    with push_interactive_log_session(session):
        log_event(
            logger,
            level,
            event,
            message,
            exc_info=exc_info,
            interaction_source=_normalize_interaction_source(source),
            **fields,
        )


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


def _normalize_log_profile(value: LogProfile | str) -> LogProfile:
    try:
        return value if isinstance(value, LogProfile) else LogProfile(str(value).lower())
    except ValueError as exc:
        choices = ", ".join(item.value for item in LogProfile)
        raise ValueError(f"profile must be one of: {choices}") from exc


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


def _ordered_custom_record_fields(record: stdlib_logging.LogRecord) -> dict[str, object]:
    custom_fields = _custom_record_fields(record)
    ordered_fields: dict[str, object] = {}
    for field_name in _HUMAN_CONTEXT_PRIORITY:
        if field_name in custom_fields:
            ordered_fields[field_name] = custom_fields.pop(field_name)
    ordered_fields.update(custom_fields)
    return ordered_fields


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


def _optional_context_field(explicit_value: str | None, current_value: str | None) -> str | None:
    if explicit_value is not None:
        normalized_value = _normalize_log_value(explicit_value)
        return None if normalized_value is None else str(normalized_value)
    if current_value is None:
        return None
    normalized_value = _normalize_log_value(current_value)
    return None if normalized_value is None else str(normalized_value)


def _resolved_context_field(
    *,
    explicit_value: str | None,
    current_value: str | None,
    fallback: str,
) -> str:
    return _optional_context_field(explicit_value, current_value) or fallback


def _normalize_interaction_source(value: InteractionSource | str) -> str:
    if isinstance(value, InteractionSource):
        return value.value
    return str(_normalize_log_value(value))


package_logger()


__all__ = [
    "InteractionSource",
    "InteractiveLogSession",
    "LogFormat",
    "LogProfile",
    "configure_logging",
    "create_interactive_log_session",
    "current_log_context",
    "current_interactive_log_session",
    "duration_ms",
    "emit_render_diagnostics",
    "log_event",
    "log_interaction",
    "logged_api_call",
    "package_logger",
    "push_interactive_log_session",
    "push_log_context",
]
