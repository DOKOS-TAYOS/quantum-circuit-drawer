"""Compatibility facade for managed page-window helpers."""

from __future__ import annotations

from .managed import page_window as _impl

__all__ = [name for name in dir(_impl) if not name.startswith("__")]

globals().update({name: getattr(_impl, name) for name in __all__})
