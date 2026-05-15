"""Structured diagnostics returned by public rendering APIs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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
