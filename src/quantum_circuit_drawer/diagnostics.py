"""Structured diagnostics returned by public rendering APIs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DiagnosticSeverity(StrEnum):
    """Severity levels for non-fatal rendering diagnostics."""

    INFO = "info"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class RenderDiagnostic:
    """A structured diagnostic emitted during rendering or normalization."""

    code: str
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.INFO
