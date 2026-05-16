"""Public package exports for :mod:`quantum_circuit_drawer`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from ._version import __version__
from .analysis import CircuitAnalysisResult
from .builder import CircuitBuilder
from .circuit_compare import (
    CircuitCompareConfig,
    CircuitCompareMetrics,
    CircuitCompareOptions,
    CircuitCompareResult,
    CircuitCompareSideMetrics,
)
from .config import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    UnsupportedPolicy,
)
from .diagnostics import DiagnosticSeverity, RenderDiagnostic
from .exceptions import (
    LayoutError,
    QuantumCircuitDrawerError,
    RenderingError,
    StyleValidationError,
    UnsupportedBackendError,
    UnsupportedFrameworkError,
    UnsupportedOperationError,
)
from .hover import HoverOptions
from .latex import LatexBackend, LatexMode, LatexResult
from .logging import (
    CapturedLogEntry,
    LogCapture,
    LogFormat,
    LogProfile,
    capture_logs,
    configure_logging,
)
from .presets import StylePreset
from .result import DrawResult
from .style import DrawStyle, DrawTheme
from .topology import (
    FunctionalTopology,
    HardwareTopology,
    PeriodicTopology1D,
    PeriodicTopology2D,
    grid_topology,
    honeycomb_topology,
    line_topology,
    star_topology,
    star_tree_topology,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from .config import ViewMode
    from .histogram import (
        HistogramAppearanceOptions,
        HistogramCompareConfig,
        HistogramCompareMetrics,
        HistogramCompareOptions,
        HistogramCompareResult,
        HistogramCompareSort,
        HistogramConfig,
        HistogramDataOptions,
        HistogramDrawStyle,
        HistogramKind,
        HistogramMode,
        HistogramResult,
        HistogramSort,
        HistogramStateLabelMode,
        HistogramViewOptions,
    )
    from .topology import TopologyInput, TopologyQubitMode
    from .typing import OutputPath


def draw_quantum_circuit(
    circuit: object,
    *,
    mode: DrawMode | str | None = None,
    show: bool | None = None,
    output_path: OutputPath | None = None,
    figsize: tuple[float, float] | None = None,
    framework: str | None = None,
    view: ViewMode | None = None,
    composite_mode: str | None = None,
    topology: TopologyInput | None = None,
    topology_qubits: TopologyQubitMode | None = None,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult:
    """Draw a supported circuit and return a ``DrawResult``.

    Direct kwargs are the small, common API for everyday rendering choices. Advanced
    styling, hover behavior, topology resizing, keyboard controls, unsupported
    operation policy, and adapter-specific options stay in ``config``.

    Args:
        circuit: Public ``CircuitIR``, supported framework object, OpenQASM 2/3 text,
            or ``.qasm`` / ``.qasm3`` path.
        mode: Optional direct render mode: ``"auto"``, ``"pages"``,
            ``"pages_controls"``, ``"slider"``, ``"full"``, or ``DrawMode``.
        show: Optional override for automatic display.
        output_path: Optional file path for saving rendered output.
        figsize: Optional managed figure size as ``(width, height)`` in inches.
        framework: Optional adapter name, such as ``"ir"``, ``"qiskit"``, or
            ``"qasm"``.
        view: Optional ``"2d"`` or ``"3d"`` view.
        composite_mode: Optional ``"compact"`` or ``"expand"`` composite rendering.
        topology: Optional built-in topology name or topology object for 3D views.
        topology_qubits: Optional ``"used"`` or ``"all"`` topology-node display mode.
        config: Optional advanced ``DrawConfig``. Non-``None`` direct kwargs override
            only their matching fields.
        ax: Optional caller-owned Matplotlib axes for static rendering.

    Returns:
        ``DrawResult`` with figures, axes, resolved mode, diagnostics, framework, hover
        state, interactivity state, and saved path.
    """

    from .api import draw_quantum_circuit as _draw_quantum_circuit

    kwargs: dict[str, object] = {"config": config, "ax": ax}
    if mode is not None:
        kwargs["mode"] = mode
    if show is not None:
        kwargs["show"] = show
    if output_path is not None:
        kwargs["output_path"] = output_path
    if figsize is not None:
        kwargs["figsize"] = figsize
    if framework is not None:
        kwargs["framework"] = framework
    if view is not None:
        kwargs["view"] = view
    if composite_mode is not None:
        kwargs["composite_mode"] = composite_mode
    if topology is not None:
        kwargs["topology"] = topology
    if topology_qubits is not None:
        kwargs["topology_qubits"] = topology_qubits

    return _draw_quantum_circuit(circuit, **cast(Any, kwargs))


def analyze_quantum_circuit(
    circuit: object,
    *,
    mode: DrawMode | str | None = None,
    framework: str | None = None,
    view: ViewMode | None = None,
    composite_mode: str | None = None,
    topology: TopologyInput | None = None,
    topology_qubits: TopologyQubitMode | None = None,
    config: DrawConfig | None = None,
) -> CircuitAnalysisResult:
    """Analyze a supported circuit without rendering figures.

    Direct kwargs are the small, common API for preparation choices. This function
    does not render, display, or save figures, so output options such as ``show`` and
    ``output_path`` are ignored even when present in ``config``.

    Args:
        circuit: Public ``CircuitIR``, supported framework object, OpenQASM text, or
            QASM path.
        mode: Optional preparation mode: ``"auto"``, ``"pages"``,
            ``"pages_controls"``, ``"slider"``, ``"full"``, or ``DrawMode``.
        framework: Optional adapter name, such as ``"ir"``, ``"qiskit"``, or
            ``"qasm"``.
        view: Optional ``"2d"`` or ``"3d"`` preparation view.
        composite_mode: Optional ``"compact"`` or ``"expand"`` composite handling.
        topology: Optional built-in topology name or topology object for 3D analysis.
        topology_qubits: Optional ``"used"`` or ``"all"`` topology-node mode.
        config: Optional ``DrawConfig`` used for framework, view, mode, topology, and
            adapter preparation. Display and saving options are ignored. Non-``None``
            direct kwargs override only matching render fields.

    Returns:
        ``CircuitAnalysisResult`` with resolved framework, page count, wire counts,
        operation counts, and diagnostics.
    """

    from .api import analyze_quantum_circuit as _analyze_quantum_circuit

    kwargs: dict[str, object] = {"config": config}
    if mode is not None:
        kwargs["mode"] = mode
    if framework is not None:
        kwargs["framework"] = framework
    if view is not None:
        kwargs["view"] = view
    if composite_mode is not None:
        kwargs["composite_mode"] = composite_mode
    if topology is not None:
        kwargs["topology"] = topology
    if topology_qubits is not None:
        kwargs["topology_qubits"] = topology_qubits

    return _analyze_quantum_circuit(circuit, **cast(Any, kwargs))


def circuit_to_latex(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    backend: LatexBackend | str = LatexBackend.QUANTIKZ,
    mode: LatexMode | DrawMode | str | None = None,
    framework: str | None = None,
    composite_mode: str | None = None,
) -> LatexResult:
    """Export a supported 2D circuit as LaTeX source.

    Direct kwargs are the small, common API for LaTeX export choices. The export path
    always prepares a 2D, non-displaying circuit pipeline; visual display, saving,
    topology, and 3D options stay outside this function.

    Args:
        circuit: Public ``CircuitIR``, supported framework object, OpenQASM text, or
            QASM path.
        config: Optional ``DrawConfig`` for framework and style choices. ``view`` must
            resolve to ``"2d"``.
        backend: ``LatexBackend`` or ``"quantikz"`` / ``"tikz"``.
        mode: Optional ``LatexMode``, compatible ``DrawMode``, ``"full"``, or
            ``"pages"``.
        framework: Optional adapter name, such as ``"ir"``, ``"qiskit"``, or
            ``"qasm"``.
        composite_mode: Optional ``"compact"`` or ``"expand"`` composite handling.
            Non-``None`` direct kwargs override only matching render fields.

    Returns:
        ``LatexResult`` with joined source, per-page snippets, backend, mode, page
        count, detected framework, and diagnostics.
    """

    from .api import circuit_to_latex as _circuit_to_latex

    kwargs: dict[str, object] = {
        "config": config,
        "backend": backend,
        "mode": mode,
    }
    if framework is not None:
        kwargs["framework"] = framework
    if composite_mode is not None:
        kwargs["composite_mode"] = composite_mode

    return _circuit_to_latex(circuit, **cast(Any, kwargs))


def plot_histogram(
    data: object,
    *,
    kind: HistogramKind | str | None = None,
    mode: HistogramMode | str | None = None,
    sort: HistogramSort | str | None = None,
    state_label_mode: HistogramStateLabelMode | str | None = None,
    qubits: tuple[int, ...] | None = None,
    top_k: int | None = None,
    result_index: int | None = None,
    data_key: str | None = None,
    show: bool | None = None,
    output_path: OutputPath | None = None,
    figsize: tuple[float, float] | None = None,
    config: HistogramConfig | None = None,
    ax: Axes | None = None,
) -> HistogramResult:
    """Plot counts or quasi-probability data.

    Direct kwargs are the small, common API for data selection, ordering, display, and
    saving. Advanced appearance, hover behavior, presets, themes, bar styles, and
    uniform reference lines stay in ``config``.

    Args:
        data: Mapping, framework result object, vector-like probabilities, or tuple/list
            of result payloads accepted by the histogram normalizer.
        kind: Optional ``"auto"``, ``"counts"``, ``"quasi"``, or ``HistogramKind``.
        mode: Optional ``"auto"``, ``"static"``, ``"interactive"``, or
            ``HistogramMode``.
        sort: Optional ``"state"``, ``"state_desc"``, ``"value_desc"``, or
            ``"value_asc"``.
        state_label_mode: Optional ``"binary"`` or ``"decimal"`` visible tick labels.
        qubits: Optional tuple of qubit indices for a joint marginal.
        top_k: Optional positive number of bins to keep after sorting.
        result_index: Optional payload index for result containers with several
            histograms.
        data_key: Optional Qiskit data field name.
        show: Optional override for automatic display.
        output_path: Optional file path for saving.
        figsize: Optional managed figure size as ``(width, height)`` in inches.
        config: Optional advanced ``HistogramConfig``. Non-``None`` direct kwargs
            override only matching fields.
        ax: Optional caller-owned Matplotlib axes for static plotting.

    Returns:
        ``HistogramResult`` with figure, axes, resolved kind, state labels, values,
        selected qubits, diagnostics, and saved path.
    """

    from .histogram import plot_histogram as _plot_histogram

    kwargs: dict[str, object] = {"config": config, "ax": ax}
    if kind is not None:
        kwargs["kind"] = kind
    if mode is not None:
        kwargs["mode"] = mode
    if sort is not None:
        kwargs["sort"] = sort
    if state_label_mode is not None:
        kwargs["state_label_mode"] = state_label_mode
    if qubits is not None:
        kwargs["qubits"] = qubits
    if top_k is not None:
        kwargs["top_k"] = top_k
    if result_index is not None:
        kwargs["result_index"] = result_index
    if data_key is not None:
        kwargs["data_key"] = data_key
    if show is not None:
        kwargs["show"] = show
    if output_path is not None:
        kwargs["output_path"] = output_path
    if figsize is not None:
        kwargs["figsize"] = figsize

    return _plot_histogram(data, **cast(Any, kwargs))


def compare_histograms(
    left_data: object,
    right_data: object,
    *additional_data: object,
    kind: HistogramKind | str | None = None,
    sort: HistogramCompareSort | str | None = None,
    qubits: tuple[int, ...] | None = None,
    top_k: int | None = None,
    result_index: int | None = None,
    data_key: str | None = None,
    left_label: str | None = None,
    right_label: str | None = None,
    series_labels: tuple[str, ...] | None = None,
    show: bool | None = None,
    output_path: OutputPath | None = None,
    figsize: tuple[float, float] | None = None,
    config: HistogramCompareConfig | None = None,
    ax: Axes | None = None,
) -> HistogramCompareResult:
    """Overlay two or more histogram-like datasets on aligned bins.

    Direct kwargs are the small, common API for shared data selection, ordering,
    labels, display, and saving. Hover, presets, and theme customization stay in
    ``config``.

    Args:
        left_data: First histogram-like input.
        right_data: Second histogram-like input.
        *additional_data: Optional additional distributions to draw in the same axes.
        kind: Optional ``"auto"``, ``"counts"``, ``"quasi"``, or ``HistogramKind``.
        sort: Optional ``"state"``, ``"state_desc"``, ``"delta_desc"``, or
            ``HistogramCompareSort``.
        qubits: Optional tuple of qubit indices for a joint marginal.
        top_k: Optional positive number of aligned bins to keep after sorting.
        result_index: Optional payload index for result containers with several
            histograms.
        data_key: Optional Qiskit data field name.
        left_label: Optional legend label for the first distribution.
        right_label: Optional legend label for the second distribution.
        series_labels: Optional legend labels for every distribution when comparing
            three or more series.
        show: Optional override for automatic display.
        output_path: Optional file path for saving.
        figsize: Optional managed figure size as ``(width, height)`` in inches.
        config: Optional ``HistogramCompareConfig`` for data selection, ordering,
            labels, hover, appearance, and output. Non-``None`` direct kwargs override
            only matching fields.
        ax: Optional caller-owned Matplotlib axes.

    Returns:
        ``HistogramCompareResult`` with aligned state labels, series values,
        first-two deltas, metrics, diagnostics, and saved path.
    """

    from .histogram import compare_histograms as _compare_histograms

    kwargs: dict[str, object] = {"config": config, "ax": ax}
    if kind is not None:
        kwargs["kind"] = kind
    if sort is not None:
        kwargs["sort"] = sort
    if qubits is not None:
        kwargs["qubits"] = qubits
    if top_k is not None:
        kwargs["top_k"] = top_k
    if result_index is not None:
        kwargs["result_index"] = result_index
    if data_key is not None:
        kwargs["data_key"] = data_key
    if left_label is not None:
        kwargs["left_label"] = left_label
    if right_label is not None:
        kwargs["right_label"] = right_label
    if series_labels is not None:
        kwargs["series_labels"] = series_labels
    if show is not None:
        kwargs["show"] = show
    if output_path is not None:
        kwargs["output_path"] = output_path
    if figsize is not None:
        kwargs["figsize"] = figsize

    return _compare_histograms(left_data, right_data, *additional_data, **cast(Any, kwargs))


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
    """Draw two or more circuits side by side and compare their structure.

    Direct kwargs are the small, common API for shared render, title, summary, and
    output choices. Per-side render or appearance overrides, hover, styles,
    unsupported-operation policy, and adapter-specific options stay in ``config``.

    Args:
        left_circuit: First supported circuit input.
        right_circuit: Second supported circuit input.
        *additional_circuits: Optional extra circuits for multi-circuit comparison.
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
        config: Optional ``CircuitCompareConfig`` for shared draw settings, per-side
            overrides, titles, highlighting, summary table, and output. Non-``None``
            direct kwargs override only matching common fields.
        axes: Optional caller-owned axes, one per circuit.
        summary_ax: Optional caller-owned axes for the summary table.

    Returns:
        ``CircuitCompareResult`` with shared figure, per-side draw results, structural
        metrics, titles, diagnostics, and saved path.
    """

    from .circuit_compare import compare_circuits as _compare_circuits

    kwargs: dict[str, object] = {"config": config, "axes": axes, "summary_ax": summary_ax}
    if mode is not None:
        kwargs["mode"] = mode
    if show is not None:
        kwargs["show"] = show
    if output_path is not None:
        kwargs["output_path"] = output_path
    if figsize is not None:
        kwargs["figsize"] = figsize
    if framework is not None:
        kwargs["framework"] = framework
    if view is not None:
        kwargs["view"] = view
    if composite_mode is not None:
        kwargs["composite_mode"] = composite_mode
    if left_title is not None:
        kwargs["left_title"] = left_title
    if right_title is not None:
        kwargs["right_title"] = right_title
    if titles is not None:
        kwargs["titles"] = titles
    if highlight_differences is not None:
        kwargs["highlight_differences"] = highlight_differences
    if show_summary is not None:
        kwargs["show_summary"] = show_summary

    return _compare_circuits(
        left_circuit,
        right_circuit,
        *additional_circuits,
        **cast(Any, kwargs),
    )


__all__ = [
    "CircuitBuilder",
    "CircuitAppearanceOptions",
    "CircuitAnalysisResult",
    "CapturedLogEntry",
    "CircuitCompareConfig",
    "CircuitCompareMetrics",
    "CircuitCompareOptions",
    "CircuitCompareResult",
    "CircuitCompareSideMetrics",
    "CircuitRenderOptions",
    "DiagnosticSeverity",
    "DrawConfig",
    "DrawMode",
    "DrawResult",
    "DrawSideConfig",
    "DrawStyle",
    "DrawTheme",
    "FunctionalTopology",
    "HistogramAppearanceOptions",
    "HistogramCompareConfig",
    "HistogramCompareMetrics",
    "HistogramCompareOptions",
    "HistogramCompareResult",
    "HistogramCompareSort",
    "HistogramConfig",
    "HistogramDataOptions",
    "HistogramDrawStyle",
    "HistogramKind",
    "HistogramMode",
    "HistogramResult",
    "HistogramStateLabelMode",
    "HardwareTopology",
    "HistogramSort",
    "HistogramViewOptions",
    "HoverOptions",
    "LatexBackend",
    "LatexMode",
    "LatexResult",
    "LayoutError",
    "LogCapture",
    "LogFormat",
    "LogProfile",
    "OutputOptions",
    "PeriodicTopology1D",
    "PeriodicTopology2D",
    "QuantumCircuitDrawerError",
    "RenderingError",
    "RenderDiagnostic",
    "StyleValidationError",
    "StylePreset",
    "UnsupportedBackendError",
    "UnsupportedFrameworkError",
    "UnsupportedOperationError",
    "UnsupportedPolicy",
    "__version__",
    "analyze_quantum_circuit",
    "capture_logs",
    "circuit_to_latex",
    "compare_circuits",
    "compare_histograms",
    "configure_logging",
    "draw_quantum_circuit",
    "grid_topology",
    "honeycomb_topology",
    "line_topology",
    "plot_histogram",
    "star_topology",
    "star_tree_topology",
]


def __getattr__(name: str) -> object:
    histogram_exports = {
        "HistogramAppearanceOptions",
        "HistogramCompareConfig",
        "HistogramCompareMetrics",
        "HistogramCompareOptions",
        "HistogramCompareResult",
        "HistogramCompareSort",
        "HistogramConfig",
        "HistogramDataOptions",
        "HistogramDrawStyle",
        "HistogramKind",
        "HistogramMode",
        "HistogramResult",
        "HistogramSort",
        "HistogramStateLabelMode",
        "HistogramViewOptions",
        "compare_histograms",
        "plot_histogram",
    }
    if name in histogram_exports:
        from . import histogram as histogram_module

        value = getattr(histogram_module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
