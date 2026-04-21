"""Stable entrypoint for interactive histogram helpers."""

from __future__ import annotations

from .histogram_interactive_state import (
    HistogramInteractiveState,
    attach_histogram_interactivity,
)

__all__ = ["HistogramInteractiveState", "attach_histogram_interactivity"]
