"""Structured diagnostics returned by public rendering APIs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ._validation import validate_str as _validate_str


class DiagnosticSeverity(StrEnum):
    """Severity levels attached to non-fatal diagnostics.

    Values:
        ``INFO`` records useful context, such as an automatic mode resolution.
        ``WARNING`` records a recoverable issue that the caller may want to surface,
        such as a fallback or ignored display request.
    """

    INFO = "info"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class RenderDiagnostic:
    """A non-fatal message returned with draw, histogram, and comparison results.

    Attributes:
        code: Stable machine-readable identifier for the condition.
        message: Human-readable explanation intended for logs or user interfaces.
        severity: ``DiagnosticSeverity.INFO`` or ``DiagnosticSeverity.WARNING``.
    """

    code: str
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.INFO

    def __post_init__(self) -> None:
        _validate_str("code", self.code)
        _validate_str("message", self.message)
        object.__setattr__(self, "severity", _normalize_diagnostic_severity(self.severity))


def _normalize_diagnostic_severity(value: object) -> DiagnosticSeverity:
    try:
        return value if isinstance(value, DiagnosticSeverity) else DiagnosticSeverity(str(value))
    except ValueError as exc:
        choices = ", ".join(severity.value for severity in DiagnosticSeverity)
        raise ValueError(f"severity must be one of: {choices}") from exc
