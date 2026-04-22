"""Public APIs and result types for side-by-side circuit comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .config import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawSideConfig,
    OutputOptions,
    validate_output_options,
)
from .result import DrawResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .diagnostics import RenderDiagnostic
    from .typing import OutputPath


@dataclass(frozen=True, slots=True)
class CircuitCompareOptions:
    """Public comparison-only controls for ``compare_circuits``."""

    left_title: str = "Left"
    right_title: str = "Right"
    highlight_differences: bool = True
    show_summary: bool = True

    def __post_init__(self) -> None:
        _validate_bool("highlight_differences", self.highlight_differences)
        _validate_bool("show_summary", self.show_summary)


@dataclass(frozen=True, slots=True)
class CircuitCompareConfig:
    """Public configuration for ``compare_circuits``."""

    shared: DrawSideConfig = field(default_factory=DrawSideConfig)
    left_render: CircuitRenderOptions | None = None
    right_render: CircuitRenderOptions | None = None
    left_appearance: CircuitAppearanceOptions | None = None
    right_appearance: CircuitAppearanceOptions | None = None
    compare: CircuitCompareOptions = field(default_factory=CircuitCompareOptions)
    output: OutputOptions = field(default_factory=OutputOptions)

    def __post_init__(self) -> None:
        _validate_instance("shared", self.shared, DrawSideConfig)
        if self.left_render is not None:
            _validate_instance("left_render", self.left_render, CircuitRenderOptions)
        if self.right_render is not None:
            _validate_instance("right_render", self.right_render, CircuitRenderOptions)
        if self.left_appearance is not None:
            _validate_instance(
                "left_appearance",
                self.left_appearance,
                CircuitAppearanceOptions,
            )
        if self.right_appearance is not None:
            _validate_instance(
                "right_appearance",
                self.right_appearance,
                CircuitAppearanceOptions,
            )
        _validate_instance("compare", self.compare, CircuitCompareOptions)
        validate_output_options(self.output)

    @property
    def left_title(self) -> str:
        return self.compare.left_title

    @property
    def right_title(self) -> str:
        return self.compare.right_title

    @property
    def highlight_differences(self) -> bool:
        return self.compare.highlight_differences

    @property
    def show_summary(self) -> bool:
        return self.compare.show_summary

    @property
    def show(self) -> bool:
        return self.output.show

    @property
    def output_path(self) -> OutputPath | None:
        return self.output.output_path

    @property
    def figsize(self) -> tuple[float, float] | None:
        return self.output.figsize


@dataclass(frozen=True, slots=True)
class CircuitCompareMetrics:
    """Comparison metrics derived from two normalized circuit IRs."""

    left_layer_count: int
    right_layer_count: int
    layer_delta: int
    left_operation_count: int
    right_operation_count: int
    operation_delta: int
    left_multi_qubit_count: int
    right_multi_qubit_count: int
    multi_qubit_delta: int
    left_measurement_count: int
    right_measurement_count: int
    measurement_delta: int
    left_swap_count: int
    right_swap_count: int
    swap_delta: int
    differing_layer_count: int
    left_only_layer_count: int
    right_only_layer_count: int


@dataclass(frozen=True, slots=True)
class CircuitCompareResult:
    """Returned comparison figure plus nested per-side draw results."""

    figure: Figure
    axes: tuple[Axes, Axes]
    left_result: DrawResult
    right_result: DrawResult
    metrics: CircuitCompareMetrics
    diagnostics: tuple[RenderDiagnostic, ...] = ()
    saved_path: str | None = None


def compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, Axes] | None = None,
) -> CircuitCompareResult:
    """Render two circuits side by side and return structural comparison data."""

    from .drawing.api import compare_circuits as _compare_circuits

    return _compare_circuits(
        left_circuit,
        right_circuit,
        config=config,
        axes=axes,
    )


def _validate_bool(name: str, value: object) -> None:
    if isinstance(value, bool):
        return
    raise ValueError(f"{name} must be a boolean")


def _validate_instance(name: str, value: object, expected_type: type[object]) -> None:
    if isinstance(value, expected_type):
        return
    raise TypeError(f"{name} must be a {expected_type.__name__}")


__all__ = [
    "CircuitCompareConfig",
    "CircuitCompareMetrics",
    "CircuitCompareOptions",
    "CircuitCompareResult",
    "compare_circuits",
]
