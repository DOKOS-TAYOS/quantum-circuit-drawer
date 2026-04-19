from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

_MANAGED_3D_FIXED_VIEW_STATE_ATTR = "_quantum_circuit_drawer_managed_3d_fixed_view_state"

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class Managed3DFixedViewState:
    """Typed camera and axis state reused across managed 3D redraws."""

    elev: float
    azim: float
    roll: float | None
    x_limits: tuple[float, float]
    y_limits: tuple[float, float]
    z_limits: tuple[float, float]
    raw_box_aspect: tuple[float, float, float] | None


def capture_managed_3d_view_state(axes: Axes3D) -> Managed3DFixedViewState:
    """Capture the mutable 3D camera and bounds state from one axes."""

    roll_value = getattr(axes, "roll", None)
    raw_box_aspect = _axis_triplet(getattr(axes, "_box_aspect", None))
    return Managed3DFixedViewState(
        elev=float(getattr(axes, "elev", 18.0)),
        azim=float(getattr(axes, "azim", -55.0)),
        roll=None if roll_value is None else float(roll_value),
        x_limits=_axis_pair(axes.get_xlim3d()),
        y_limits=_axis_pair(axes.get_ylim3d()),
        z_limits=_axis_pair(axes.get_zlim3d()),
        raw_box_aspect=raw_box_aspect,
    )


def _axis_pair(values: object) -> tuple[float, float]:
    if not hasattr(values, "__iter__"):
        raise TypeError("3D axis limits must be iterable")
    pair = tuple(float(value) for value in values)
    if len(pair) != 2:
        raise ValueError("3D axis limits must contain exactly two values")
    return (pair[0], pair[1])


def _axis_triplet(values: object) -> tuple[float, float, float] | None:
    if not hasattr(values, "__iter__"):
        return None
    triplet = tuple(float(value) for value in values)
    if len(triplet) != 3:
        return None
    return triplet
