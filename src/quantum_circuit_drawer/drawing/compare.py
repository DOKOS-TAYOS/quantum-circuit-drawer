"""Circuit comparison helpers for the public drawing API."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from ..circuit_compare import CircuitCompareConfig, CircuitCompareMetrics, CircuitCompareResult
from ..config import DrawConfig, DrawMode
from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..managed.rendering import render_draw_pipeline_on_axes
from ..renderers._render_support import save_rendered_figure, show_figure_if_supported
from .preparation import INTERACTIVE_COMPARE_MODES, prepare_draw_call
from .results import build_draw_result, normalized_saved_path

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..layout.scene import LayoutScene


@dataclass(frozen=True, slots=True)
class CircuitCompareDiffSummary:
    """Column-level diff summary for visual comparison overlays."""

    left_columns: tuple[int, ...]
    right_columns: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _CircuitStats:
    layer_count: int
    operation_count: int
    multi_qubit_count: int
    measurement_count: int
    swap_count: int


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

    resolved_compare_config = config or CircuitCompareConfig()
    if axes is not None and resolved_compare_config.figsize is not None:
        raise ValueError("figsize cannot be used with axes in compare_circuits")

    left_axes: Axes
    right_axes: Axes
    if axes is None:
        import matplotlib.pyplot as plt

        figure, created_axes = plt.subplots(1, 2, figsize=resolved_compare_config.figsize)
        left_axes, right_axes = tuple(created_axes)
    else:
        left_axes, right_axes = axes
        figure = shared_figure_for_compare_axes(left_axes, right_axes)

    normalized_left_config = normalize_compare_draw_config(left_config, side_label="left")
    normalized_right_config = normalize_compare_draw_config(right_config, side_label="right")
    left_prepared = prepare_draw_call(left_circuit, config=normalized_left_config, ax=left_axes)
    right_prepared = prepare_draw_call(
        right_circuit,
        config=normalized_right_config,
        ax=right_axes,
    )

    rendered_left_axes = render_draw_pipeline_on_axes(
        left_prepared.pipeline,
        axes=left_axes,
        output=None,
        respect_precomputed_scene=True,
    )
    rendered_right_axes = render_draw_pipeline_on_axes(
        right_prepared.pipeline,
        axes=right_axes,
        output=None,
        respect_precomputed_scene=True,
    )
    metrics, diff_summary = circuit_compare_metrics(
        left_prepared.pipeline.ir,
        right_prepared.pipeline.ir,
    )
    if resolved_compare_config.highlight_differences:
        highlight_compare_columns(
            rendered_left_axes,
            cast("LayoutScene", left_prepared.pipeline.paged_scene),
            diff_summary.left_columns,
        )
        highlight_compare_columns(
            rendered_right_axes,
            cast("LayoutScene", right_prepared.pipeline.paged_scene),
            diff_summary.right_columns,
        )

    apply_compare_titles(
        left_axes=rendered_left_axes,
        right_axes=rendered_right_axes,
        config=resolved_compare_config,
        metrics=metrics,
    )
    if resolved_compare_config.output_path is not None:
        save_rendered_figure(figure, resolved_compare_config.output_path)
    if resolved_compare_config.show:
        show_figure_if_supported(figure, show=True)

    left_result = build_draw_result(
        primary_figure=figure,
        primary_axes=rendered_left_axes,
        figures=(figure,),
        axes=(rendered_left_axes,),
        mode=left_prepared.resolved_config.mode,
        page_count=1,
        diagnostics=left_prepared.diagnostics,
        pipeline=left_prepared.pipeline,
        output=None,
    )
    right_result = build_draw_result(
        primary_figure=figure,
        primary_axes=rendered_right_axes,
        figures=(figure,),
        axes=(rendered_right_axes,),
        mode=right_prepared.resolved_config.mode,
        page_count=1,
        diagnostics=right_prepared.diagnostics,
        pipeline=right_prepared.pipeline,
        output=None,
    )
    return CircuitCompareResult(
        figure=figure,
        axes=(rendered_left_axes, rendered_right_axes),
        left_result=left_result,
        right_result=right_result,
        metrics=metrics,
        diagnostics=(),
        saved_path=normalized_saved_path(resolved_compare_config.output_path),
    )


def normalize_compare_draw_config(
    config: DrawConfig | None,
    *,
    side_label: str,
) -> DrawConfig:
    """Normalize one per-side draw config for public circuit comparison."""

    resolved_config = DrawConfig(show=False) if config is None else config
    if resolved_config.view != "2d":
        raise ValueError(
            f"compare_circuits only supports 2D rendering; {side_label}_config.view must be '2d'"
        )
    if resolved_config.mode in INTERACTIVE_COMPARE_MODES:
        raise ValueError("compare_circuits does not support slider or page-control modes in v1")
    return replace(
        resolved_config,
        mode=DrawMode.FULL,
        view="2d",
        show=False,
        output_path=None,
        topology_menu=False,
    )


def shared_figure_for_compare_axes(left_axes: Axes, right_axes: Axes) -> Figure:
    """Return the shared figure for caller-managed compare axes."""

    left_figure = cast("Figure", left_axes.figure)
    right_figure = cast("Figure", right_axes.figure)
    if left_figure is not right_figure:
        raise ValueError("compare_circuits requires both axes to belong to the same figure")
    return left_figure


def circuit_compare_metrics(
    left_ir: CircuitIR,
    right_ir: CircuitIR,
) -> tuple[CircuitCompareMetrics, CircuitCompareDiffSummary]:
    """Compute comparison metrics and differing layer indices for two circuits."""

    left_layer_signatures = tuple(layer_signature(left_ir, layer) for layer in left_ir.layers)
    right_layer_signatures = tuple(layer_signature(right_ir, layer) for layer in right_ir.layers)
    common_layer_count = min(len(left_layer_signatures), len(right_layer_signatures))
    differing_layer_indices = tuple(
        layer_index
        for layer_index in range(common_layer_count)
        if left_layer_signatures[layer_index] != right_layer_signatures[layer_index]
    )
    left_only_layer_indices = tuple(range(common_layer_count, len(left_layer_signatures)))
    right_only_layer_indices = tuple(range(common_layer_count, len(right_layer_signatures)))
    left_stats = circuit_stats(left_ir)
    right_stats = circuit_stats(right_ir)
    metrics = CircuitCompareMetrics(
        left_layer_count=left_stats.layer_count,
        right_layer_count=right_stats.layer_count,
        layer_delta=right_stats.layer_count - left_stats.layer_count,
        left_operation_count=left_stats.operation_count,
        right_operation_count=right_stats.operation_count,
        operation_delta=right_stats.operation_count - left_stats.operation_count,
        left_multi_qubit_count=left_stats.multi_qubit_count,
        right_multi_qubit_count=right_stats.multi_qubit_count,
        multi_qubit_delta=right_stats.multi_qubit_count - left_stats.multi_qubit_count,
        left_measurement_count=left_stats.measurement_count,
        right_measurement_count=right_stats.measurement_count,
        measurement_delta=right_stats.measurement_count - left_stats.measurement_count,
        left_swap_count=left_stats.swap_count,
        right_swap_count=right_stats.swap_count,
        swap_delta=right_stats.swap_count - left_stats.swap_count,
        differing_layer_count=len(differing_layer_indices),
        left_only_layer_count=len(left_only_layer_indices),
        right_only_layer_count=len(right_only_layer_indices),
    )
    return metrics, CircuitCompareDiffSummary(
        left_columns=tuple((*differing_layer_indices, *left_only_layer_indices)),
        right_columns=tuple((*differing_layer_indices, *right_only_layer_indices)),
    )


def circuit_stats(circuit: CircuitIR) -> _CircuitStats:
    """Compute aggregate circuit statistics for comparison output."""

    operations = tuple(operation for layer in circuit.layers for operation in layer.operations)
    return _CircuitStats(
        layer_count=len(circuit.layers),
        operation_count=len(operations),
        multi_qubit_count=sum(1 for operation in operations if is_multi_qubit_operation(operation)),
        measurement_count=sum(
            1 for operation in operations if operation.kind is OperationKind.MEASUREMENT
        ),
        swap_count=sum(1 for operation in operations if operation.kind is OperationKind.SWAP),
    )


def is_multi_qubit_operation(operation: OperationIR | MeasurementIR) -> bool:
    """Return whether one operation spans multiple quantum wires."""

    quantum_wire_ids = tuple(dict.fromkeys((*operation.control_wires, *operation.target_wires)))
    if operation.kind is OperationKind.MEASUREMENT:
        return len(tuple(operation.target_wires)) > 1
    if operation.kind is OperationKind.BARRIER:
        return False
    return len(quantum_wire_ids) > 1


def layer_signature(
    circuit: CircuitIR,
    layer: LayerIR,
) -> tuple[tuple[object, ...], ...]:
    """Build a stable signature for one layer of IR operations."""

    wire_indices = {wire.id: wire.index for wire in circuit.all_wires}
    return tuple(operation_signature(operation, wire_indices) for operation in layer.operations)


def operation_signature(
    operation: OperationIR | MeasurementIR,
    wire_indices: dict[str, int],
) -> tuple[object, ...]:
    """Build a stable signature for one operation."""

    measurement_target: int | str | None
    if isinstance(operation, MeasurementIR):
        classical_target = operation.classical_target
        if classical_target is None:
            measurement_target = None
        else:
            measurement_target = wire_indices.get(classical_target, classical_target)
    else:
        measurement_target = None
    return (
        operation.kind,
        operation.canonical_family,
        operation.name,
        tuple(operation.parameters),
        tuple(wire_indices[wire_id] for wire_id in operation.target_wires),
        tuple(wire_indices[wire_id] for wire_id in operation.control_wires),
        measurement_target,
    )


def highlight_compare_columns(
    axes: Axes,
    scene: LayoutScene,
    columns: tuple[int, ...],
) -> None:
    """Draw visual diff bands for the provided column indices."""

    if not columns:
        return
    column_spans = scene_column_spans(scene)
    facecolor = "#f59e0b"
    for column in columns:
        column_span = column_spans.get(column)
        if column_span is None:
            continue
        band = axes.axvspan(
            column_span[0],
            column_span[1],
            color=facecolor,
            alpha=0.09,
            zorder=0.1,
            linewidth=0.0,
        )
        band.set_gid("circuit-compare-diff-band")


def scene_column_spans(scene: LayoutScene) -> dict[int, tuple[float, float]]:
    """Return x-axis spans for each rendered circuit column."""

    column_positions: dict[int, list[float]] = {}
    for collection in (
        scene.gates,
        scene.gate_annotations,
        scene.controls,
        scene.connections,
        scene.swaps,
        scene.barriers,
        scene.measurements,
    ):
        for item in collection:
            column_positions.setdefault(item.column, []).append(float(item.x))
    if not column_positions:
        return {}
    sorted_columns = sorted(column_positions)
    column_centers = {
        column: sum(x_positions) / float(len(x_positions))
        for column, x_positions in column_positions.items()
    }
    default_half_width = (scene.style.gate_width + scene.style.layer_spacing) / 2.0
    spans: dict[int, tuple[float, float]] = {}
    for index, column in enumerate(sorted_columns):
        center = column_centers[column]
        previous_center = column_centers[sorted_columns[index - 1]] if index > 0 else None
        next_center = (
            column_centers[sorted_columns[index + 1]] if index + 1 < len(sorted_columns) else None
        )
        left_bound = (
            (previous_center + center) / 2.0
            if previous_center is not None
            else center - default_half_width
        )
        right_bound = (
            (center + next_center) / 2.0 if next_center is not None else center + default_half_width
        )
        spans[column] = (left_bound, right_bound)
    return spans


def apply_compare_titles(
    *,
    left_axes: Axes,
    right_axes: Axes,
    config: CircuitCompareConfig,
    metrics: CircuitCompareMetrics,
) -> None:
    """Apply per-side titles and the shared comparison summary."""

    left_axes.set_title(config.left_title)
    right_axes.set_title(config.right_title)
    if not config.show_summary:
        return
    summary_figure = cast("Figure", left_axes.figure)
    summary_figure.suptitle(
        (
            f"Layers {metrics.left_layer_count}->{metrics.right_layer_count} "
            f"(\u0394 {metrics.layer_delta:+d}) | "
            f"Ops {metrics.left_operation_count}->{metrics.right_operation_count} "
            f"(\u0394 {metrics.operation_delta:+d}) | "
            f"2Q {metrics.left_multi_qubit_count}->{metrics.right_multi_qubit_count} "
            f"(\u0394 {metrics.multi_qubit_delta:+d}) | "
            f"SWAP {metrics.left_swap_count}->{metrics.right_swap_count} "
            f"(\u0394 {metrics.swap_delta:+d}) | "
            f"Meas {metrics.left_measurement_count}->{metrics.right_measurement_count} "
            f"(\u0394 {metrics.measurement_delta:+d})"
        ),
        fontsize=11.0,
    )
