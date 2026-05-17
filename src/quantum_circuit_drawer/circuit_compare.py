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
    validate_str as _validate_str,
)
from ._validation import (
    validate_str_tuple as _validate_str_tuple,
)
from .config import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    ViewMode,
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
    """Comparison-only presentation controls for ``compare_circuits(...)``.

    Attributes:
        left_title: Default title for the first circuit when ``titles`` is not given.
        right_title: Default title for the second circuit when ``titles`` is not given.
        highlight_differences: Whether differing columns are visually highlighted in
            the side-by-side render.
        show_summary: Whether to include the summary table axes when the comparison
            owns the Matplotlib figure.
        titles: Optional title for every compared circuit. Use this when comparing
            three or more circuits or when the default left/right labels are not enough.
    """

    left_title: str = "Left"
    right_title: str = "Right"
    highlight_differences: bool = True
    show_summary: bool = True
    titles: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        _validate_str("left_title", self.left_title)
        _validate_str("right_title", self.right_title)
        _validate_bool("highlight_differences", self.highlight_differences)
        _validate_bool("show_summary", self.show_summary)
        if self.titles is not None:
            _validate_str_tuple("titles", self.titles)


@dataclass(frozen=True, slots=True)
class CircuitCompareConfig:
    """Advanced configuration object for ``compare_circuits(...)``.

    Attributes:
        shared: Base ``DrawSideConfig`` applied to every compared circuit.
        left_render: Optional render override for the first circuit.
        right_render: Optional render override for the second circuit.
        left_appearance: Optional appearance override for the first circuit.
        right_appearance: Optional appearance override for the second circuit.
        compare: ``CircuitCompareOptions`` controlling titles, highlighting, and the
            summary table.
        output: ``OutputOptions`` controlling display, saving, and managed figure size.
            Direct kwargs on ``compare_circuits(...)`` override only matching common
            fields when they are not ``None``.
    """

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
    """Structural metrics comparing the first two normalized circuits.

    Attributes:
        left_layer_count: Layer count for the first circuit.
        right_layer_count: Layer count for the second circuit.
        layer_delta: ``right_layer_count - left_layer_count``.
        left_operation_count: Operation count for the first circuit.
        right_operation_count: Operation count for the second circuit.
        operation_delta: ``right_operation_count - left_operation_count``.
        left_multi_qubit_count: Multi-qubit operation count for the first circuit.
        right_multi_qubit_count: Multi-qubit operation count for the second circuit.
        multi_qubit_delta: Difference in multi-qubit operation counts.
        left_measurement_count: Measurement count for the first circuit.
        right_measurement_count: Measurement count for the second circuit.
        measurement_delta: Difference in measurement counts.
        left_swap_count: Swap count for the first circuit.
        right_swap_count: Swap count for the second circuit.
        swap_delta: Difference in swap counts.
        differing_layer_count: Count of aligned layer positions with different
            semantic signatures.
        left_only_layer_count: Layers that only exist in the first circuit.
        right_only_layer_count: Layers that only exist in the second circuit.
    """

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
    """Per-circuit summary row used by multi-circuit comparisons.

    Attributes:
        title: Display title for this circuit.
        layer_count: Number of normalized layers.
        operation_count: Total number of operations.
        multi_qubit_count: Operations touching more than one quantum wire.
        measurement_count: Measurement operation count.
        swap_count: Swap operation count.
    """

    title: str
    layer_count: int
    operation_count: int
    multi_qubit_count: int
    measurement_count: int
    swap_count: int


@dataclass(frozen=True, slots=True)
class CircuitCompareResult:
    """Result returned by ``compare_circuits(...)``.

    Attributes:
        figure: Shared Matplotlib figure containing the side-by-side comparison.
        axes: Circuit axes, one per compared circuit.
        left_result: ``DrawResult`` for the first circuit.
        right_result: ``DrawResult`` for the second circuit.
        metrics: Structural metrics for the first two circuits.
        side_results: ``DrawResult`` objects for all circuits when comparing more than
            two inputs.
        side_metrics: Summary metrics for every compared circuit.
        titles: Resolved display titles.
        summary_axes: Optional axes containing the comparison summary table.
        diagnostics: Combined non-fatal diagnostics from all compared circuits.
        saved_path: Absolute saved path when ``output_path`` was used.
    """

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
        """Save the comparison figure to disk.

        Args:
            path: Destination image path accepted by Matplotlib.

        Returns:
            The absolute path written.
        """

        save_matplotlib_figure(self.figure, path)
        return _resolved_output_path(path)

    def to_dict(self) -> dict[str, object]:
        """Return comparison metadata without Matplotlib objects.

        Returns:
            A JSON-friendly dictionary containing nested draw-result metadata, metrics,
            titles, diagnostics, and saved path.
        """

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
    mode: DrawMode | str | None = None,
    show: bool | None = None,
    output_path: OutputPath | None = None,
    figsize: tuple[float, float] | None = None,
    framework: str | None = None,
    view: ViewMode | None = None,
    composite_mode: str | None = None,
    left_title: str | None = None,
    right_title: str | None = None,
    titles: tuple[str, ...] | None = None,
    highlight_differences: bool | None = None,
    show_summary: bool | None = None,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, ...] | None = None,
    summary_ax: Axes | None = None,
) -> CircuitCompareResult:
    """Render circuits side by side and return structural comparison data.

    Direct kwargs are the small, common API for shared render, title, summary, and
    output choices. Per-side render or appearance overrides, hover, styles,
    unsupported-operation policy, and adapter-specific options stay in ``config``.

    Args:
        left_circuit: First supported circuit input.
        right_circuit: Second supported circuit input.
        *additional_circuits: Optional extra circuits to include in the same comparison.
        mode: Optional shared render mode: ``"auto"``, ``"pages"``,
            ``"pages_controls"``, ``"slider"``, ``"full"``, or ``DrawMode``.
        show: Optional override for automatic display.
        output_path: Optional file path for saving the comparison summary or static
            side-by-side figure.
        figsize: Optional managed side-figure size as ``(width, height)`` in inches.
        framework: Optional shared adapter name, such as ``"ir"``, ``"qiskit"``, or
            ``"qasm"``.
        view: Optional shared view. Circuit comparison currently supports ``"2d"``.
        composite_mode: Optional ``"compact"`` or ``"expand"`` composite rendering.
        left_title: Optional display title for the first circuit.
        right_title: Optional display title for the second circuit.
        titles: Optional title for every compared circuit.
        highlight_differences: Optional override for diff markers in static comparison.
        show_summary: Optional override for the managed summary figure/card.
        config: Optional ``CircuitCompareConfig`` for shared render settings,
            per-side overrides, titles, highlighting, summary table, and output.
            Non-``None`` direct kwargs override only matching common fields.
        axes: Optional caller-owned axes, one per circuit. Do not combine with a
            managed ``figsize``.
        summary_ax: Optional caller-owned axes for the summary table.

    Returns:
        ``CircuitCompareResult`` with the shared figure, per-side ``DrawResult``
        objects, metrics, diagnostics, and saved path.
    """

    from .drawing.api import compare_circuits as _compare_circuits

    return _compare_circuits(
        left_circuit,
        right_circuit,
        *additional_circuits,
        mode=mode,
        show=show,
        output_path=output_path,
        figsize=figsize,
        framework=framework,
        view=view,
        composite_mode=composite_mode,
        left_title=left_title,
        right_title=right_title,
        titles=titles,
        highlight_differences=highlight_differences,
        show_summary=show_summary,
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
