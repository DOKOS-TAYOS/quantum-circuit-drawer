"""Public package exports for quantum_circuit_drawer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

from ._version import __version__
from .exceptions import (
    LayoutError,
    QuantumCircuitDrawerError,
    RenderingError,
    StyleValidationError,
    UnsupportedBackendError,
    UnsupportedFrameworkError,
    UnsupportedOperationError,
)
from .style import DrawStyle, DrawTheme

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from .typing import LayoutEngineLike, OutputPath, RenderResult


def draw_quantum_circuit(
    circuit: object,
    framework: str | None = None,
    *,
    style: DrawStyle | Mapping[str, object] | None = None,
    layout: LayoutEngineLike | None = None,
    backend: str = "matplotlib",
    ax: Axes | None = None,
    output: OutputPath | None = None,
    show: bool = True,
    page_slider: bool = False,
    composite_mode: str = "compact",
    view: Literal["2d", "3d"] = "2d",
    topology: Literal["line", "grid", "star", "star_tree", "honeycomb"] = "line",
    direct: bool = True,
    hover: bool = False,
    **options: object,
) -> RenderResult:
    """Draw a quantum circuit from a supported framework."""

    from .api import draw_quantum_circuit as _draw_quantum_circuit

    return _draw_quantum_circuit(
        circuit,
        framework,
        style=style,
        layout=layout,
        backend=backend,
        ax=ax,
        output=output,
        show=show,
        page_slider=page_slider,
        composite_mode=composite_mode,
        view=view,
        topology=topology,
        direct=direct,
        hover=hover,
        **options,
    )


__all__ = [
    "DrawStyle",
    "DrawTheme",
    "LayoutError",
    "QuantumCircuitDrawerError",
    "RenderingError",
    "StyleValidationError",
    "UnsupportedBackendError",
    "UnsupportedFrameworkError",
    "UnsupportedOperationError",
    "__version__",
    "draw_quantum_circuit",
]
