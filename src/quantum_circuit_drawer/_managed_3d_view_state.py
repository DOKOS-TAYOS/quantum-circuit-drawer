"""Compatibility facade for managed 3D view-state helpers."""

from __future__ import annotations

from .managed.view_state_3d import (
    _MANAGED_3D_FIXED_VIEW_STATE_ATTR,
    TYPE_CHECKING,
    Managed3DFixedViewState,
    _axis_pair,
    _axis_triplet,
    annotations,
    capture_managed_3d_view_state,
    dataclass,
)

__all__ = [
    "Managed3DFixedViewState",
    "TYPE_CHECKING",
    "_MANAGED_3D_FIXED_VIEW_STATE_ATTR",
    "_axis_pair",
    "_axis_triplet",
    "annotations",
    "capture_managed_3d_view_state",
    "dataclass",
]
