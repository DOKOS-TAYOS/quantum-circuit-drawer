"""Public APIs and result types for side-by-side circuit comparison."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from ._validation import (
    validate_bool as _validate_bool,
)
from ._validation import (
    validate_instance as _validate_instance,
)
from ._validation import (
    validate_str_tuple as _validate_str_tuple,
)
from .config import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawSideConfig,
    OutputOptions,
    validate_output_options,
)
from .export.figures import save_matplotlib_figure
from .result import DrawResult, _resolved_output_path, diagnostics_to_dicts
from .typing import OutputPath

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .diagnostics import RenderDiagnostic


@dataclass(frozen=True, slots=True)
class CircuitCompareOptions:
    """Public comparison-only controls for ``compare_circuits``."""

    left_title: str = "Left"
    right_title: str = "Right"
    highlight_differences: bool = True
    show_summary: bool = True
    titles: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        _validate_bool("highlight_differences", self.highlight_differences)
        _validate_bool("show_summary", self.show_summary)
        if self.titles is not None:
            _validate_str_tuple("titles", self.titles)


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
    def titles(self) -> tuple[str, ...] | None:
        return self.compare.titles

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
class CircuitCompareSideMetrics:
    """Per-circuit metrics used by multi-circuit comparison summaries."""

    title: str
    layer_count: int
    operation_count: int
    multi_qubit_count: int
    measurement_count: int
    swap_count: int


@dataclass(frozen=True, slots=True)
class CircuitCompareResult:
    """Returned comparison figure plus nested per-side draw results."""

    figure: Figure
    axes: tuple[Axes, ...]
    left_result: DrawResult
    right_result: DrawResult
    metrics: CircuitCompareMetrics
    side_results: tuple[DrawResult, ...] = ()
    side_metrics: tuple[CircuitCompareSideMetrics, ...] = ()
    titles: tuple[str, ...] = ()
    summary_axes: Axes | None = None
    diagnostics: tuple[RenderDiagnostic, ...] = ()
    saved_path: str | None = None

    def save(self, path: OutputPath) -> str:
        """Save the comparison figure and return the absolute saved path."""

        save_matplotlib_figure(self.figure, path)
        return _resolved_output_path(path)

    def to_dict(self) -> dict[str, object]:
        """Return comparison metadata without Matplotlib figure or axes objects."""

        return {
            "left_result": self.left_result.to_dict(),
            "right_result": self.right_result.to_dict(),
            "side_results": tuple(result.to_dict() for result in self._resolved_side_results()),
            "metrics": asdict(self.metrics),
            "side_metrics": tuple(asdict(metrics) for metrics in self.side_metrics),
            "titles": self._resolved_titles(),
            "diagnostics": diagnostics_to_dicts(self.diagnostics),
            "saved_path": self.saved_path,
        }

    def _resolved_side_results(self) -> tuple[DrawResult, ...]:
        return self.side_results or (self.left_result, self.right_result)

    def _resolved_titles(self) -> tuple[str, ...]:
        if self.titles:
            return self.titles
        if self.side_metrics:
            return tuple(metrics.title for metrics in self.side_metrics)
        return ()


def compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *additional_circuits: object,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, ...] | None = None,
    summary_ax: Axes | None = None,
) -> CircuitCompareResult:
    """Render two or more circuits side by side and return structural comparison data."""

    from .drawing.api import compare_circuits as _compare_circuits

    return _compare_circuits(
        left_circuit,
        right_circuit,
        *additional_circuits,
        config=config,
        axes=axes,
        summary_ax=summary_ax,
    )


__all__ = [
    "CircuitCompareConfig",
    "CircuitCompareMetrics",
    "CircuitCompareOptions",
    "CircuitCompareResult",
    "CircuitCompareSideMetrics",
    "compare_circuits",
]
