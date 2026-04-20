"""Compatibility facade for managed topology-menu helpers."""

from __future__ import annotations

from .managed import topology_menu as _impl

__all__ = [name for name in dir(_impl) if not name.startswith("__")]

globals().update({name: getattr(_impl, name) for name in __all__})
