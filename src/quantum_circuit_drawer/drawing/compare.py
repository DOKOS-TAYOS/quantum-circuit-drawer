"""Circuit comparison helpers for the public drawing API."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.transforms import blended_transform_factory

from ..circuit_compare import CircuitCompareConfig, CircuitCompareMetrics, CircuitCompareResult
from ..config import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
)
from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
    semantic_operation_signature,
)
from ..managed.rendering import render_draw_pipeline_on_axes
from ..renderers._render_support import save_rendered_figure, show_figure_if_supported
from .managed_modes import draw_result_from_prepared_call
from .preparation import prepare_draw_call
from .results import build_draw_result, combined_draw_diagnostics, normalized_saved_path

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..layout.scene import LayoutScene
    from ..result import DrawResult


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


_SUMMARY_CARD_BOUNDS = (0.31, 0.58, 0.38, 0.34)
_SUMMARY_FIGURE_CARD_BOUNDS = (0.06, 0.1, 0.88, 0.8)
_SUMMARY_FIGURE_SIZE = (3.8, 2.8)
_SUMMARY_CARD_PADDING_X = 0.02
_SUMMARY_CARD_HEADER_OFFSET = 0.065
_SUMMARY_CARD_ROW_BOTTOM_PADDING = 0.12


def compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, Axes] | None = None,
) -> CircuitCompareResult:
    """Render two circuits side by side and return structural comparison data."""

    resolved_compare_config = config or CircuitCompareConfig()
    if axes is not None and resolved_compare_config.figsize is not None:
        raise ValueError("figsize cannot be used with axes in compare_circuits")

    normalized_left_config = normalize_compare_draw_config(
        merge_compare_side_config(resolved_compare_config, side_label="left"),
        side_label="left",
        auto_mode=DrawMode.FULL if axes is not None else DrawMode.PAGES_CONTROLS,
    )
    normalized_right_config = normalize_compare_draw_config(
        merge_compare_side_config(resolved_compare_config, side_label="right"),
        side_label="right",
        auto_mode=DrawMode.FULL if axes is not None else DrawMode.PAGES_CONTROLS,
    )
    uses_non_full_compare_mode = (
        normalized_left_config.mode is not DrawMode.FULL
        or normalized_right_config.mode is not DrawMode.FULL
    )
    if axes is not None and uses_non_full_compare_mode:
        raise ValueError(
            "compare_circuits managed modes require separate Matplotlib-managed figures "
            "and cannot be used with axes"
        )
    if axes is None:
        return _compare_circuits_with_managed_side_figures(
            left_circuit,
            right_circuit,
            config=resolved_compare_config,
            left_config=normalized_left_config,
            right_config=normalized_right_config,
        )

    left_axes: Axes
    right_axes: Axes
    if axes is None:
        import matplotlib.pyplot as plt

        figure, created_axes = plt.subplots(1, 2, figsize=resolved_compare_config.figsize)
        left_axes, right_axes = tuple(created_axes)
    else:
        left_axes, right_axes = axes
        figure = shared_figure_for_compare_axes(left_axes, right_axes)

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
        left_semantic=left_prepared.pipeline.semantic_ir,
        right_semantic=right_prepared.pipeline.semantic_ir,
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
        left_text_color=left_prepared.pipeline.normalized_style.theme.text_color,
        right_text_color=right_prepared.pipeline.normalized_style.theme.text_color,
        summary_facecolor=left_prepared.pipeline.normalized_style.theme.ui_surface_facecolor
        or left_prepared.pipeline.normalized_style.theme.axes_facecolor,
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


def _compare_circuits_with_managed_side_figures(
    left_circuit: object,
    right_circuit: object,
    *,
    config: CircuitCompareConfig,
    left_config: DrawConfig,
    right_config: DrawConfig,
) -> CircuitCompareResult:
    """Render managed compare modes as two normal side figures plus one summary figure."""

    left_config = _with_compare_side_output(left_config, compare_config=config)
    right_config = _with_compare_side_output(right_config, compare_config=config)
    left_prepared = prepare_draw_call(left_circuit, config=left_config, ax=None)
    right_prepared = prepare_draw_call(right_circuit, config=right_config, ax=None)
    metrics, _diff_summary = circuit_compare_metrics(
        left_prepared.pipeline.ir,
        right_prepared.pipeline.ir,
        left_semantic=left_prepared.pipeline.semantic_ir,
        right_semantic=right_prepared.pipeline.semantic_ir,
    )
    left_result = draw_result_from_prepared_call(left_prepared, defer_show=True)
    right_result = draw_result_from_prepared_call(right_prepared, defer_show=True)
    left_text_color = left_prepared.pipeline.normalized_style.theme.text_color
    _apply_window_titles_to_draw_result(left_result, config.left_title)
    _apply_window_titles_to_draw_result(right_result, config.right_title)

    summary_figure = _build_compare_summary_figure(
        config=config,
        metrics=metrics,
        text_color=left_text_color,
        card_facecolor=(
            left_prepared.pipeline.normalized_style.theme.ui_surface_facecolor
            or left_prepared.pipeline.normalized_style.theme.axes_facecolor
        ),
        figure_facecolor=left_prepared.pipeline.normalized_style.theme.figure_facecolor,
    )
    if config.output_path is not None and config.show_summary:
        save_rendered_figure(summary_figure, config.output_path)
    if config.show:
        show_figure_if_supported(
            summary_figure if config.show_summary else left_result.primary_figure,
            show=True,
        )

    return CircuitCompareResult(
        figure=summary_figure,
        axes=(left_result.primary_axes, right_result.primary_axes),
        left_result=left_result,
        right_result=right_result,
        metrics=metrics,
        diagnostics=combined_draw_diagnostics(
            left_prepared.diagnostics,
            right_prepared.diagnostics,
        ),
        saved_path=(
            normalized_saved_path(config.output_path)
            if config.output_path is not None and config.show_summary
            else None
        ),
    )


def _with_compare_side_output(
    config: DrawConfig,
    *,
    compare_config: CircuitCompareConfig,
) -> DrawConfig:
    return replace(
        config,
        output=OutputOptions(
            show=compare_config.show or config.hover.enabled,
            output_path=None,
            figsize=compare_config.figsize,
        ),
    )


def _apply_window_titles_to_draw_result(
    result: DrawResult,
    title: str,
) -> None:
    total_figures = len(result.figures)
    for figure_index, figure in enumerate(result.figures, start=1):
        figure_title = (
            title if total_figures == 1 else f"{title} - page {figure_index}/{total_figures}"
        )
        _set_figure_window_title(figure, figure_title)


def _set_figure_window_title(figure: Figure, title: str) -> None:
    set_label = getattr(figure, "set_label", None)
    if callable(set_label):
        set_label(title)

    canvas = getattr(figure, "canvas", None)
    manager = getattr(canvas, "manager", None)
    set_window_title = getattr(manager, "set_window_title", None)
    if callable(set_window_title):
        set_window_title(title)


def _build_compare_summary_figure(
    *,
    config: CircuitCompareConfig,
    metrics: CircuitCompareMetrics,
    text_color: str,
    card_facecolor: str,
    figure_facecolor: str,
) -> Figure:
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=_SUMMARY_FIGURE_SIZE)
    figure.patch.set_facecolor(figure_facecolor)
    if config.show_summary:
        _add_compare_summary_card(
            figure=figure,
            metrics=metrics,
            text_color=text_color,
            card_facecolor=card_facecolor,
            bounds=_SUMMARY_FIGURE_CARD_BOUNDS,
        )
    return figure


def normalize_compare_draw_config(
    config: DrawConfig,
    *,
    side_label: str,
    auto_mode: DrawMode = DrawMode.FULL,
) -> DrawConfig:
    """Normalize one per-side draw config for public circuit comparison."""

    if config.view != "2d":
        raise ValueError(
            f"compare_circuits only supports 2D rendering; {side_label}_render.view must be '2d'"
        )
    mode = auto_mode if config.mode is DrawMode.AUTO else config.mode
    return DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                framework=config.framework,
                backend=config.backend,
                layout=config.layout,
                view="2d",
                mode=mode,
                composite_mode=config.composite_mode,
                topology=config.topology,
                topology_qubits=config.topology_qubits,
                topology_resize=config.topology_resize,
                topology_menu=False,
                direct=config.direct,
                unsupported_policy=config.unsupported_policy,
            ),
            appearance=CircuitAppearanceOptions(
                preset=config.preset,
                style=config.style,
                hover=config.hover,
            ),
        ),
        output=OutputOptions(show=False),
    )


def merge_compare_side_config(
    config: CircuitCompareConfig,
    *,
    side_label: str,
) -> DrawConfig:
    """Build one per-side draw config from shared options and block overrides."""

    render_override = config.left_render if side_label == "left" else config.right_render
    appearance_override = (
        config.left_appearance if side_label == "left" else config.right_appearance
    )
    resolved_render = config.shared.render if render_override is None else render_override
    resolved_appearance = (
        config.shared.appearance if appearance_override is None else appearance_override
    )
    return DrawConfig(
        side=DrawSideConfig(
            render=resolved_render,
            appearance=resolved_appearance,
        ),
        output=OutputOptions(show=False),
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
    *,
    left_semantic: SemanticCircuitIR | None = None,
    right_semantic: SemanticCircuitIR | None = None,
) -> tuple[CircuitCompareMetrics, CircuitCompareDiffSummary]:
    """Compute comparison metrics and differing layer indices for two circuits."""

    resolved_left_semantic = left_semantic or _semantic_from_ir(left_ir)
    resolved_right_semantic = right_semantic or _semantic_from_ir(right_ir)
    left_layer_signatures = tuple(
        semantic_layer_signature(resolved_left_semantic, layer)
        for layer in resolved_left_semantic.layers
    )
    right_layer_signatures = tuple(
        semantic_layer_signature(resolved_right_semantic, layer)
        for layer in resolved_right_semantic.layers
    )
    common_layer_count = min(len(left_layer_signatures), len(right_layer_signatures))
    differing_layer_indices = tuple(
        layer_index
        for layer_index in range(common_layer_count)
        if left_layer_signatures[layer_index] != right_layer_signatures[layer_index]
    )
    left_only_layer_indices = tuple(range(common_layer_count, len(left_layer_signatures)))
    right_only_layer_indices = tuple(range(common_layer_count, len(right_layer_signatures)))
    left_stats = semantic_circuit_stats(resolved_left_semantic)
    right_stats = semantic_circuit_stats(resolved_right_semantic)
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


def semantic_circuit_stats(circuit: SemanticCircuitIR) -> _CircuitStats:
    """Compute aggregate statistics for semantic-circuit comparison output."""

    operations = tuple(operation for layer in circuit.layers for operation in layer.operations)
    return _CircuitStats(
        layer_count=len(circuit.layers),
        operation_count=len(operations),
        multi_qubit_count=sum(
            1 for operation in operations if is_multi_qubit_semantic_operation(operation)
        ),
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


def is_multi_qubit_semantic_operation(operation: SemanticOperationIR) -> bool:
    """Return whether one semantic operation spans multiple quantum wires."""

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


def semantic_layer_signature(
    circuit: SemanticCircuitIR,
    layer: SemanticLayerIR,
) -> tuple[tuple[object, ...], ...]:
    """Build a stable signature for one semantic IR layer."""

    wire_indices = {wire.id: wire.index for wire in circuit.all_wires}
    return tuple(
        semantic_operation_signature(operation, wire_indices) for operation in layer.operations
    )


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
        tuple(tuple(int(value) for value in entry) for entry in operation.control_values),
        measurement_target,
    )


def _semantic_from_ir(circuit: CircuitIR) -> SemanticCircuitIR:
    from ..ir.lowering import semantic_circuit_from_circuit_ir

    return semantic_circuit_from_circuit_ir(circuit)


def highlight_compare_columns(
    axes: Axes,
    scene: LayoutScene,
    columns: tuple[int, ...],
) -> None:
    """Draw thin top markers for the provided differing column indices."""

    if not columns:
        return
    column_spans = scene_column_spans(scene)
    facecolor = scene.style.theme.accent_color
    marker_transform = blended_transform_factory(axes.transData, axes.transAxes)
    for column in columns:
        column_span = column_spans.get(column)
        if column_span is None:
            continue
        marker = Rectangle(
            (column_span[0], 0.982),
            column_span[1] - column_span[0],
            0.018,
            transform=marker_transform,
            facecolor=facecolor,
            edgecolor="none",
            alpha=0.1,
            zorder=6.0,
            clip_on=False,
        )
        marker.set_gid("circuit-compare-diff-marker")
        axes.add_patch(marker)


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
    left_text_color: str,
    right_text_color: str,
    summary_facecolor: str,
) -> None:
    """Apply per-side titles and the shared comparison summary card."""

    del right_text_color
    summary_figure = cast("Figure", left_axes.figure)
    _set_figure_window_title(summary_figure, f"{config.left_title} vs {config.right_title}")
    _clear_compare_summary_artifacts(summary_figure)
    suptitle = getattr(summary_figure, "_suptitle", None)
    if suptitle is not None:
        suptitle.remove()
        setattr(summary_figure, "_suptitle", None)
    if not config.show_summary:
        return

    _add_compare_summary_card(
        figure=summary_figure,
        metrics=metrics,
        text_color=left_text_color,
        card_facecolor=summary_facecolor,
    )


def _clear_compare_summary_artifacts(figure: Figure) -> None:
    figure.patches[:] = [
        patch
        for patch in figure.patches
        if getattr(patch, "get_gid", lambda: None)() != "circuit-compare-summary-card"
    ]
    for text in tuple(figure.texts):
        if getattr(text, "get_gid", lambda: None)() not in {
            "circuit-compare-summary-header",
            "circuit-compare-summary-row",
        }:
            continue
        text.remove()


def _add_compare_summary_card(
    *,
    figure: Figure,
    metrics: CircuitCompareMetrics,
    text_color: str,
    card_facecolor: str,
    bounds: tuple[float, float, float, float] = _SUMMARY_CARD_BOUNDS,
) -> None:
    card_x, card_y, card_width, card_height = bounds
    card = FancyBboxPatch(
        (card_x, card_y),
        card_width,
        card_height,
        boxstyle="round,pad=0.008,rounding_size=0.01",
        transform=figure.transFigure,
        facecolor=card_facecolor,
        edgecolor=text_color,
        linewidth=0.8,
        alpha=0.94,
    )
    card.set_gid("circuit-compare-summary-card")
    figure.patches.append(card)

    header_y = card_y + card_height - _SUMMARY_CARD_HEADER_OFFSET
    metric_x = card_x + _SUMMARY_CARD_PADDING_X
    left_x = card_x + (card_width * 0.56)
    right_x = card_x + (card_width * 0.74)
    delta_x = card_x + (card_width * 0.9)

    for text, x_position, alignment in (
        ("Metric", metric_x, "left"),
        ("Left", left_x, "center"),
        ("Right", right_x, "center"),
        ("\u0394", delta_x, "center"),
    ):
        artist = figure.text(
            x_position,
            header_y,
            text,
            color=text_color,
            ha=alignment,
            va="center",
            fontsize=11.0,
            fontweight="bold",
        )
        artist.set_gid("circuit-compare-summary-header")

    rows = (
        ("Layers", metrics.left_layer_count, metrics.right_layer_count, metrics.layer_delta),
        (
            "Ops",
            metrics.left_operation_count,
            metrics.right_operation_count,
            metrics.operation_delta,
        ),
        (
            "2Q",
            metrics.left_multi_qubit_count,
            metrics.right_multi_qubit_count,
            metrics.multi_qubit_delta,
        ),
        ("SWAP", metrics.left_swap_count, metrics.right_swap_count, metrics.swap_delta),
        (
            "Measurements",
            metrics.left_measurement_count,
            metrics.right_measurement_count,
            metrics.measurement_delta,
        ),
    )
    row_bottom_y = card_y + min(_SUMMARY_CARD_ROW_BOTTOM_PADDING, card_height * 0.22)
    row_spacing = (header_y - row_bottom_y) / float(len(rows))

    for row_index, (label, left_value, right_value, delta_value) in enumerate(rows):
        row_y = header_y - ((row_index + 1) * row_spacing)
        for text, x_position, alignment in (
            (label, metric_x, "left"),
            (str(left_value), left_x, "center"),
            (str(right_value), right_x, "center"),
            (f"{int(delta_value):+d}", delta_x, "center"),
        ):
            artist = figure.text(
                x_position,
                row_y,
                text,
                color=text_color,
                ha=alignment,
                va="center",
                fontsize=10.0,
            )
            artist.set_gid("circuit-compare-summary-row")
