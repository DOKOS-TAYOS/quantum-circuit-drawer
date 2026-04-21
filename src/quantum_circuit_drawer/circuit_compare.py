"""Public APIs and result types for side-by-side circuit comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .result import DrawResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .config import DrawConfig
    from .diagnostics import RenderDiagnostic
    from .typing import OutputPath


@dataclass(frozen=True, slots=True)
class CircuitCompareConfig:
    """Public configuration for ``compare_circuits``."""

    left_title: str = "Left"
    right_title: str = "Right"
    highlight_differences: bool = True
    show_summary: bool = True
    show: bool = True
    output_path: OutputPath | None = None
    figsize: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        self._validate_bool("highlight_differences", self.highlight_differences)
        self._validate_bool("show_summary", self.show_summary)
        self._validate_bool("show", self.show)
        self._validate_figsize(self.figsize)

    @staticmethod
    def _validate_bool(name: str, value: object) -> None:
        if isinstance(value, bool):
            return
        raise ValueError(f"{name} must be a boolean")

    @staticmethod
    def _validate_figsize(value: tuple[float, float] | None) -> None:
        if value is None:
            return
        if not isinstance(value, tuple | list) or len(value) != 2:
            raise ValueError("figsize must be a 2-item tuple of positive numbers")
        width, height = value
        if not _is_positive_dimension(width) or not _is_positive_dimension(height):
            raise ValueError("figsize must be a 2-item tuple of positive numbers")


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
    left_config: DrawConfig | None = None,
    right_config: DrawConfig | None = None,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, Axes] | None = None,
) -> CircuitCompareResult:
    """Render two circuits side by side and return structural comparison data."""

    from .drawing.api import compare_circuits as _compare_circuits

    return _compare_circuits(
        left_circuit,
        right_circuit,
        left_config=left_config,
        right_config=right_config,
        config=config,
        axes=axes,
    )


def _is_positive_dimension(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and float(value) > 0.0
