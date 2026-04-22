"""Compatibility facade for runtime context helpers."""

from __future__ import annotations

from .drawing.runtime import (
    _INTERACTIVE_DRAW_MODES,
    NOTEBOOK_INTERACTIVE_BACKENDS,
    TYPE_CHECKING,
    DiagnosticSeverity,
    DrawConfig,
    DrawMode,
    RenderDiagnostic,
    ResolvedDrawConfig,
    RuntimeContext,
    _resolve_draw_mode,
    _resolve_ipython_shell,
    _running_inside_notebook,
    annotations,
    builtins,
    dataclass,
    detect_runtime_context,
    lru_cache,
    pyplot_backend_name,
    resolve_draw_config,
    sys,
)

__all__ = [
    "DiagnosticSeverity",
    "DrawConfig",
    "DrawMode",
    "NOTEBOOK_INTERACTIVE_BACKENDS",
    "RenderDiagnostic",
    "ResolvedDrawConfig",
    "RuntimeContext",
    "TYPE_CHECKING",
    "_INTERACTIVE_DRAW_MODES",
    "_resolve_draw_mode",
    "_resolve_ipython_shell",
    "_running_inside_notebook",
    "annotations",
    "builtins",
    "dataclass",
    "detect_runtime_context",
    "lru_cache",
    "pyplot_backend_name",
    "resolve_draw_config",
    "sys",
]
