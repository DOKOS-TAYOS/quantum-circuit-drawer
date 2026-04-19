"""Default values for the public drawing style configuration."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from numbers import Real
from typing import TypedDict, Unpack

from .theme import DrawTheme, resolve_theme

DEFAULT_LINE_WIDTH = 1.6


class DrawStyleChanges(TypedDict, total=False):
    font_size: float
    wire_spacing: float
    layer_spacing: float
    gate_width: float
    gate_height: float
    line_width: float | None
    wire_line_width: float | None
    classical_wire_line_width: float | None
    gate_edge_line_width: float | None
    barrier_line_width: float | None
    measurement_line_width: float | None
    connection_line_width: float | None
    topology_edge_line_width: float | None
    control_radius: float
    show_params: bool
    show_wire_labels: bool
    use_mathtext: bool
    theme: DrawTheme
    margin_left: float
    margin_right: float
    margin_top: float
    margin_bottom: float
    label_margin: float
    classical_wire_gap: float
    swap_marker_size: float
    max_page_width: float
    page_vertical_gap: float


@dataclass(slots=True)
class DrawStyle:
    """Typed style configuration accepted by ``style=...``.

    ``DrawStyle`` mirrors the user-facing style options documented for the
    public API. Instances are typically passed directly or produced by
    ``normalize_style(...)`` after validating a mapping.
    """

    font_size: float = 12.0
    wire_spacing: float = 1.2
    layer_spacing: float = 0.45
    gate_width: float = 0.72
    gate_height: float = 0.72
    line_width: float | None = None
    wire_line_width: float | None = None
    classical_wire_line_width: float | None = None
    gate_edge_line_width: float | None = None
    barrier_line_width: float | None = None
    measurement_line_width: float | None = None
    connection_line_width: float | None = None
    topology_edge_line_width: float | None = None
    control_radius: float = 0.08
    show_params: bool = True
    show_wire_labels: bool = True
    use_mathtext: bool = True
    theme: DrawTheme = field(default_factory=lambda: resolve_theme(None))
    margin_left: float = 0.85
    margin_right: float = 0.35
    margin_top: float = 0.8
    margin_bottom: float = 0.8
    label_margin: float = 0.18
    classical_wire_gap: float = 0.75
    swap_marker_size: float = 0.14
    max_page_width: float = 20.0
    page_vertical_gap: float = 1.8
    _line_width_is_default: bool = field(default=True, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.line_width is None:
            self.line_width = DEFAULT_LINE_WIDTH
            self._line_width_is_default = True
            return
        self._line_width_is_default = False


def replace_draw_style(style: DrawStyle, /, **changes: Unpack[DrawStyleChanges]) -> DrawStyle:
    """Return a ``DrawStyle`` replacement while preserving line-width provenance."""

    if "line_width" in changes:
        line_width_change = changes["line_width"]
    else:
        line_width_change = style.line_width
    if line_width_change is None:
        changes["line_width"] = DEFAULT_LINE_WIDTH
        line_width_is_default = True
    elif not isinstance(line_width_change, Real) or float(line_width_change) <= 0.0:
        raise ValueError("line_width must be a positive number")
    else:
        line_width_is_default = False if "line_width" in changes else style._line_width_is_default

    for field_name in (
        "wire_line_width",
        "classical_wire_line_width",
        "gate_edge_line_width",
        "barrier_line_width",
        "measurement_line_width",
        "connection_line_width",
        "topology_edge_line_width",
    ):
        if field_name not in changes:
            continue
        line_width_value = changes[field_name]
        if line_width_value is None:
            continue
        if not isinstance(line_width_value, Real) or float(line_width_value) <= 0.0:
            raise ValueError(f"{field_name} must be a positive number or None")

    replaced_style = replace(style, **changes)
    replaced_style._line_width_is_default = line_width_is_default
    return replaced_style


def uses_default_line_width(style: DrawStyle) -> bool:
    """Return whether ``style.line_width`` still comes from the library default."""

    return style._line_width_is_default


def resolved_line_width(style: DrawStyle) -> float:
    """Return a non-optional validated line width."""

    line_width = style.line_width
    assert line_width is not None
    return float(line_width)


def resolved_wire_line_width(style: DrawStyle) -> float:
    """Return the resolved quantum-wire stroke width."""

    return _resolved_family_line_width(style.wire_line_width, fallback=resolved_line_width(style))


def resolved_classical_wire_line_width(style: DrawStyle) -> float:
    """Return the resolved classical-wire stroke width."""

    return _resolved_family_line_width(
        style.classical_wire_line_width,
        fallback=resolved_line_width(style) * 0.9,
    )


def resolved_gate_edge_line_width(style: DrawStyle) -> float:
    """Return the resolved gate-edge stroke width."""

    return _resolved_family_line_width(
        style.gate_edge_line_width, fallback=resolved_line_width(style)
    )


def resolved_barrier_line_width(style: DrawStyle) -> float:
    """Return the resolved barrier stroke width."""

    return _resolved_family_line_width(
        style.barrier_line_width, fallback=resolved_line_width(style)
    )


def resolved_measurement_line_width(style: DrawStyle) -> float:
    """Return the resolved measurement stroke width."""

    return _resolved_family_line_width(
        style.measurement_line_width,
        fallback=resolved_line_width(style),
    )


def resolved_connection_line_width(style: DrawStyle) -> float:
    """Return the resolved connection stroke width."""

    return _resolved_family_line_width(
        style.connection_line_width,
        fallback=resolved_line_width(style),
    )


def resolved_topology_edge_line_width(style: DrawStyle) -> float:
    """Return the resolved topology-edge stroke width."""

    return _resolved_family_line_width(
        style.topology_edge_line_width,
        fallback=resolved_line_width(style) * 0.6,
    )


def _resolved_family_line_width(value: float | None, *, fallback: float) -> float:
    if value is None:
        return float(fallback)
    return float(value)
