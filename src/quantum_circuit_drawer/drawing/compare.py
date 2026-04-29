"""Circuit comparison helpers for the public drawing API."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.transforms import blended_transform_factory

from .._logging import (
    duration_ms,
    emit_render_diagnostics,
    log_event,
    logged_api_call,
    push_log_context,
)
from ..circuit_compare import (
    CircuitCompareConfig,
    CircuitCompareMetrics,
    CircuitCompareResult,
    CircuitCompareSideMetrics,
)
from ..config import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
)
from ..ir.circuit import CircuitIR
from ..ir.operations import OperationKind
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
    from .preparation import PreparedDrawCall


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
_SUMMARY_BEST_COLOR = "#16a34a"
_SUMMARY_WORST_COLOR = "#dc2626"
logger = logging.getLogger(__name__)


def compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *additional_circuits: object,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, ...] | None = None,
    summary_ax: Axes | None = None,
) -> CircuitCompareResult:
    """Render two or more circuits side by side and return structural comparison data."""

    with logged_api_call(logger, api="compare_circuits") as started_at:
        resolved_compare_config = config or CircuitCompareConfig()
        if axes is not None and resolved_compare_config.figsize is not None:
            raise ValueError("figsize cannot be used with axes in compare_circuits")
        if axes is None and summary_ax is not None:
            raise ValueError("summary_ax can only be used with caller-managed compare axes")

        circuits = (left_circuit, right_circuit, *additional_circuits)
        titles = resolve_compare_titles(resolved_compare_config, circuit_count=len(circuits))
        if axes is not None and len(axes) != len(circuits):
            raise ValueError(
                "compare_circuits requires one axes object for each circuit when axes are provided"
            )

        normalized_side_configs = tuple(
            normalize_compare_draw_config(
                merge_compare_side_config(resolved_compare_config, side_label=_side_label(index)),
                side_label=_side_label(index),
                auto_mode=DrawMode.FULL if axes is not None else DrawMode.PAGES_CONTROLS,
            )
            for index in range(len(circuits))
        )
        uses_non_full_compare_mode = any(
            normalized_side_config.mode is not DrawMode.FULL
            for normalized_side_config in normalized_side_configs
        )
        if axes is not None and uses_non_full_compare_mode:
            raise ValueError(
                "compare_circuits managed modes require separate Matplotlib-managed figures "
                "and cannot be used with axes"
            )
        if axes is None:
            result = _compare_circuits_with_managed_side_figures(
                circuits,
                config=resolved_compare_config,
                side_configs=normalized_side_configs,
                titles=titles,
            )
        else:
            figure = shared_figure_for_compare_axes(
                *((*axes, summary_ax) if summary_ax is not None else axes)
            )
            prepared_calls = tuple(
                _prepare_compare_draw_call(
                    circuit,
                    config=side_config,
                    ax=side_axes,
                    scope=_side_label(index),
                )
                for index, (circuit, side_config, side_axes) in enumerate(
                    zip(
                        circuits,
                        normalized_side_configs,
                        axes,
                        strict=True,
                    )
                )
            )
            rendered_axes = tuple(
                _render_compare_axes(
                    prepared,
                    axes=side_axes,
                    scope=_side_label(index),
                )
                for index, (prepared, side_axes) in enumerate(
                    zip(prepared_calls, axes, strict=True)
                )
            )
            metrics, diff_summary = circuit_compare_metrics(
                prepared_calls[0].pipeline.ir,
                prepared_calls[1].pipeline.ir,
                left_semantic=prepared_calls[0].pipeline.semantic_ir,
                right_semantic=prepared_calls[1].pipeline.semantic_ir,
            )
            if resolved_compare_config.highlight_differences and len(circuits) == 2:
                highlight_compare_columns(
                    rendered_axes[0],
                    cast("LayoutScene", prepared_calls[0].pipeline.paged_scene),
                    diff_summary.left_columns,
                )
                highlight_compare_columns(
                    rendered_axes[1],
                    cast("LayoutScene", prepared_calls[1].pipeline.paged_scene),
                    diff_summary.right_columns,
                )
            side_metrics = tuple(
                circuit_compare_side_metrics(
                    title=title,
                    circuit=prepared.pipeline.semantic_ir,
                )
                for title, prepared in zip(titles, prepared_calls, strict=True)
            )

            apply_compare_titles(
                axes=rendered_axes,
                summary_ax=summary_ax,
                config=resolved_compare_config,
                metrics=metrics,
                side_metrics=side_metrics,
                titles=titles,
                text_color=prepared_calls[0].pipeline.normalized_style.theme.text_color,
                summary_facecolor=(
                    prepared_calls[0].pipeline.normalized_style.theme.ui_surface_facecolor
                    or prepared_calls[0].pipeline.normalized_style.theme.axes_facecolor
                ),
            )
            if resolved_compare_config.output_path is not None:
                save_rendered_figure(figure, resolved_compare_config.output_path)
            if resolved_compare_config.show:
                show_figure_if_supported(figure, show=True)

            side_results = tuple(
                build_draw_result(
                    primary_figure=figure,
                    primary_axes=rendered_axis,
                    figures=(figure,),
                    axes=(rendered_axis,),
                    mode=prepared.resolved_config.mode,
                    page_count=1,
                    diagnostics=prepared.diagnostics,
                    pipeline=prepared.pipeline,
                    output=None,
                )
                for prepared, rendered_axis in zip(prepared_calls, rendered_axes, strict=True)
            )
            result = CircuitCompareResult(
                figure=figure,
                axes=rendered_axes,
                left_result=side_results[0],
                right_result=side_results[1],
                metrics=metrics,
                side_results=side_results,
                side_metrics=side_metrics,
                titles=titles,
                summary_axes=summary_ax,
                diagnostics=(),
                saved_path=normalized_saved_path(resolved_compare_config.output_path),
            )

        with push_log_context(scope=None):
            emit_render_diagnostics(logger, result.diagnostics)
            if result.saved_path is not None:
                log_event(
                    logger,
                    logging.INFO,
                    "output.saved",
                    "Saved circuit comparison output.",
                    output_path=result.saved_path,
                )
            log_event(
                logger,
                logging.INFO,
                "api.completed",
                "Completed compare_circuits.",
                duration_ms=duration_ms(started_at),
                side_count=len(result.side_results or (result.left_result, result.right_result)),
                diagnostic_count=len(result.diagnostics),
                saved_path=result.saved_path,
            )
            return result


def _compare_circuits_with_managed_side_figures(
    circuits: tuple[object, ...],
    *,
    config: CircuitCompareConfig,
    side_configs: tuple[DrawConfig, ...],
    titles: tuple[str, ...],
) -> CircuitCompareResult:
    """Render managed compare modes as normal side figures plus one summary figure."""

    configured_sides = tuple(
        _with_compare_side_output(side_config, compare_config=config)
        for side_config in side_configs
    )
    prepared_calls = tuple(
        _prepare_compare_draw_call(
            circuit,
            config=side_config,
            ax=None,
            scope=_side_label(index),
        )
        for index, (circuit, side_config) in enumerate(zip(circuits, configured_sides, strict=True))
    )
    metrics, _diff_summary = circuit_compare_metrics(
        prepared_calls[0].pipeline.ir,
        prepared_calls[1].pipeline.ir,
        left_semantic=prepared_calls[0].pipeline.semantic_ir,
        right_semantic=prepared_calls[1].pipeline.semantic_ir,
    )
    side_metrics = tuple(
        circuit_compare_side_metrics(
            title=title,
            circuit=prepared.pipeline.semantic_ir,
        )
        for title, prepared in zip(titles, prepared_calls, strict=True)
    )
    side_results = tuple(
        _draw_compare_side_result(
            prepared,
            scope=_side_label(index),
        )
        for index, prepared in enumerate(prepared_calls)
    )
    left_text_color = prepared_calls[0].pipeline.normalized_style.theme.text_color
    for side_result, title in zip(side_results, titles, strict=True):
        _apply_window_titles_to_draw_result(side_result, title)

    summary_figure = _build_compare_summary_figure(
        config=config,
        metrics=metrics,
        side_metrics=side_metrics,
        titles=titles,
        text_color=left_text_color,
        card_facecolor=(
            prepared_calls[0].pipeline.normalized_style.theme.ui_surface_facecolor
            or prepared_calls[0].pipeline.normalized_style.theme.axes_facecolor
        ),
        figure_facecolor=prepared_calls[0].pipeline.normalized_style.theme.figure_facecolor,
    )
    if config.output_path is not None and config.show_summary:
        save_rendered_figure(summary_figure, config.output_path)
    if config.show:
        show_figure_if_supported(
            summary_figure if config.show_summary else side_results[0].primary_figure,
            show=True,
        )

    return CircuitCompareResult(
        figure=summary_figure,
        axes=tuple(side_result.primary_axes for side_result in side_results),
        left_result=side_results[0],
        right_result=side_results[1],
        metrics=metrics,
        side_results=side_results,
        side_metrics=side_metrics,
        titles=titles,
        diagnostics=combined_draw_diagnostics(
            *(prepared.diagnostics for prepared in prepared_calls),
        ),
        saved_path=(
            normalized_saved_path(config.output_path)
            if config.output_path is not None and config.show_summary
            else None
        ),
    )


def _prepare_compare_draw_call(
    circuit: object,
    *,
    config: DrawConfig,
    ax: Axes | None,
    scope: str,
) -> PreparedDrawCall:
    with push_log_context(scope=scope):
        return prepare_draw_call(circuit, config=config, ax=ax)


def _render_compare_axes(
    prepared: PreparedDrawCall,
    *,
    axes: Axes,
    scope: str,
) -> Axes:
    with push_log_context(
        scope=scope,
        view=prepared.resolved_config.config.view,
        mode=prepared.resolved_config.mode.value,
        framework=prepared.pipeline.detected_framework,
        backend=prepared.resolved_config.config.backend,
    ):
        rendered_axes = render_draw_pipeline_on_axes(
            prepared.pipeline,
            axes=axes,
            output=None,
            respect_precomputed_scene=True,
        )
        log_event(
            logger,
            logging.INFO,
            "render.completed",
            "Completed circuit comparison side rendering.",
            page_count=1,
            managed=False,
            saved_path=None,
        )
        return rendered_axes


def _draw_compare_side_result(
    prepared: PreparedDrawCall,
    *,
    scope: str,
) -> DrawResult:
    with push_log_context(scope=scope):
        return draw_result_from_prepared_call(prepared, defer_show=True)


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
    side_metrics: tuple[CircuitCompareSideMetrics, ...],
    titles: tuple[str, ...],
    text_color: str,
    card_facecolor: str,
    figure_facecolor: str,
) -> Figure:
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=_summary_figure_size(len(side_metrics)))
    figure.patch.set_facecolor(figure_facecolor)
    if config.show_summary:
        _add_compare_summary_card(
            figure=figure,
            metrics=metrics,
            side_metrics=side_metrics,
            titles=titles,
            text_color=text_color,
            card_facecolor=card_facecolor,
            bounds=_SUMMARY_FIGURE_CARD_BOUNDS,
        )
    return figure


def _summary_figure_size(side_count: int) -> tuple[float, float]:
    if side_count <= 2:
        return _SUMMARY_FIGURE_SIZE
    return (max(_SUMMARY_FIGURE_SIZE[0], 2.8 + (side_count * 1.2)), _SUMMARY_FIGURE_SIZE[1])


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
                adapter_options=config.adapter_options,
            ),
            appearance=CircuitAppearanceOptions(
                preset=config.preset,
                style=config.style,
                hover=config.hover,
            ),
        ),
        output=OutputOptions(show=False),
    )


def resolve_compare_titles(
    config: CircuitCompareConfig,
    *,
    circuit_count: int,
) -> tuple[str, ...]:
    """Resolve user-facing titles for every compared circuit."""

    if circuit_count < 2:
        raise ValueError("compare_circuits requires at least two circuits")
    if config.titles is not None:
        if len(config.titles) != circuit_count:
            raise ValueError("compare.titles must contain one title for each compared circuit")
        return config.titles
    return (
        config.left_title,
        config.right_title,
        *(f"Circuit {index}" for index in range(3, circuit_count + 1)),
    )


def _side_label(index: int) -> str:
    if index == 0:
        return "left"
    if index == 1:
        return "right"
    return f"circuit {index + 1}"


def merge_compare_side_config(
    config: CircuitCompareConfig,
    *,
    side_label: str,
) -> DrawConfig:
    """Build one per-side draw config from shared options and block overrides."""

    render_override = None
    appearance_override = None
    if side_label == "left":
        render_override = config.left_render
        appearance_override = config.left_appearance
    elif side_label == "right":
        render_override = config.right_render
        appearance_override = config.right_appearance
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


def shared_figure_for_compare_axes(*axes: Axes) -> Figure:
    """Return the shared figure for caller-managed compare axes."""

    if not axes:
        raise ValueError("compare_circuits requires at least one axes object")
    first_figure = cast("Figure", axes[0].figure)
    if any(cast("Figure", side_axes.figure) is not first_figure for side_axes in axes[1:]):
        raise ValueError("compare_circuits requires all axes to belong to the same figure")
    return first_figure


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


def circuit_compare_side_metrics(
    *,
    title: str,
    circuit: SemanticCircuitIR,
) -> CircuitCompareSideMetrics:
    """Build public per-circuit metrics for summary tables."""

    stats = semantic_circuit_stats(circuit)
    return CircuitCompareSideMetrics(
        title=title,
        layer_count=stats.layer_count,
        operation_count=stats.operation_count,
        multi_qubit_count=stats.multi_qubit_count,
        measurement_count=stats.measurement_count,
        swap_count=stats.swap_count,
    )


def is_multi_qubit_semantic_operation(operation: SemanticOperationIR) -> bool:
    """Return whether one semantic operation spans multiple quantum wires."""

    quantum_wire_ids = tuple(dict.fromkeys((*operation.control_wires, *operation.target_wires)))
    if operation.kind is OperationKind.MEASUREMENT:
        return len(tuple(operation.target_wires)) > 1
    if operation.kind is OperationKind.BARRIER:
        return False
    return len(quantum_wire_ids) > 1


def semantic_layer_signature(
    circuit: SemanticCircuitIR,
    layer: SemanticLayerIR,
) -> tuple[tuple[object, ...], ...]:
    """Build a stable signature for one semantic IR layer."""

    wire_indices = {wire.id: wire.index for wire in circuit.all_wires}
    return tuple(
        semantic_operation_signature(operation, wire_indices) for operation in layer.operations
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
    axes: tuple[Axes, ...],
    summary_ax: Axes | None = None,
    config: CircuitCompareConfig,
    metrics: CircuitCompareMetrics,
    side_metrics: tuple[CircuitCompareSideMetrics, ...],
    titles: tuple[str, ...],
    text_color: str,
    summary_facecolor: str,
) -> None:
    """Apply per-side titles and the shared comparison summary card."""

    summary_figure = cast("Figure", axes[0].figure)
    _set_figure_window_title(summary_figure, " vs ".join(titles))
    _clear_compare_summary_artifacts(summary_figure)
    suptitle = getattr(summary_figure, "_suptitle", None)
    if suptitle is not None:
        suptitle.remove()
        setattr(summary_figure, "_suptitle", None)
    if not config.show_summary:
        return

    if summary_ax is not None:
        summary_ax.clear()
        summary_ax.axis("off")

    _add_compare_summary_card(
        figure=summary_figure,
        metrics=metrics,
        side_metrics=side_metrics,
        titles=titles,
        text_color=text_color,
        card_facecolor=summary_facecolor,
        bounds=(
            _summary_axes_card_bounds(summary_ax)
            if summary_ax is not None
            else _SUMMARY_CARD_BOUNDS
        ),
    )


def _summary_axes_card_bounds(summary_ax: Axes) -> tuple[float, float, float, float]:
    bounds = summary_ax.get_position()
    horizontal_padding = min(0.012, bounds.width * 0.04)
    vertical_padding = min(0.012, bounds.height * 0.08)
    return (
        bounds.x0 + horizontal_padding,
        bounds.y0 + vertical_padding,
        max(0.01, bounds.width - (2.0 * horizontal_padding)),
        max(0.01, bounds.height - (2.0 * vertical_padding)),
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
    side_metrics: tuple[CircuitCompareSideMetrics, ...],
    titles: tuple[str, ...],
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

    if len(side_metrics) > 2:
        _add_multi_compare_summary_rows(
            figure=figure,
            side_metrics=side_metrics,
            titles=titles,
            text_color=text_color,
            bounds=bounds,
        )
        return

    _add_two_compare_summary_rows(
        figure=figure,
        metrics=metrics,
        text_color=text_color,
        bounds=bounds,
    )


def _add_two_compare_summary_rows(
    *,
    figure: Figure,
    metrics: CircuitCompareMetrics,
    text_color: str,
    bounds: tuple[float, float, float, float],
) -> None:
    card_x, card_y, card_width, card_height = bounds
    header_y = card_y + card_height - _summary_header_offset(card_height)
    metric_x = card_x + _SUMMARY_CARD_PADDING_X
    left_x = card_x + (card_width * 0.56)
    right_x = card_x + (card_width * 0.74)
    delta_x = card_x + (card_width * 0.9)
    header_fontsize, row_fontsize = _summary_font_sizes(card_height)

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
            fontsize=header_fontsize,
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
    row_bottom_y = card_y + _summary_row_bottom_padding(card_height)
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
                fontsize=row_fontsize,
            )
            artist.set_gid("circuit-compare-summary-row")


def _add_multi_compare_summary_rows(
    *,
    figure: Figure,
    side_metrics: tuple[CircuitCompareSideMetrics, ...],
    titles: tuple[str, ...],
    text_color: str,
    bounds: tuple[float, float, float, float],
) -> None:
    card_x, card_y, card_width, card_height = bounds
    header_y = card_y + card_height - _summary_header_offset(card_height)
    metric_x = card_x + _SUMMARY_CARD_PADDING_X
    side_count = len(side_metrics)
    outer_padding = max(_SUMMARY_CARD_PADDING_X, min(0.03, card_width * 0.04))
    metric_column_width = min(card_width * 0.24, max(card_width * 0.17, 0.16))
    data_left_x = metric_x + metric_column_width
    data_right_x = card_x + card_width - outer_padding
    header_fontsize, row_fontsize = _summary_font_sizes(
        card_height,
        multi=True,
        side_count=side_count,
    )
    slot_width = max(0.01, (data_right_x - data_left_x) / float(max(1, side_count)))
    value_x_positions = tuple(
        data_left_x + ((index + 0.5) * slot_width) for index in range(side_count)
    )

    header_specs = (
        ("Metric", metric_x, "left", header_fontsize),
        *(
            (_short_summary_title(title), x_position, "center", max(7.4, header_fontsize - 1.0))
            for title, x_position in zip(titles, value_x_positions, strict=True)
        ),
    )
    for text, x_position, alignment, fontsize in header_specs:
        artist = figure.text(
            x_position,
            header_y,
            text,
            color=text_color,
            ha=alignment,
            va="center",
            fontsize=fontsize,
            fontweight="bold",
        )
        artist.set_gid("circuit-compare-summary-header")

    rows = _multi_compare_summary_rows(side_metrics)
    row_bottom_y = card_y + _summary_row_bottom_padding(card_height)
    row_spacing = (header_y - row_bottom_y) / float(len(rows))
    for row_index, (label, values) in enumerate(rows):
        row_y = header_y - ((row_index + 1) * row_spacing)
        label_artist = figure.text(
            metric_x,
            row_y,
            label,
            color=text_color,
            ha="left",
            va="center",
            fontsize=row_fontsize,
        )
        label_artist.set_gid("circuit-compare-summary-row")
        for value_index, (value, x_position) in enumerate(
            zip(values, value_x_positions, strict=True)
        ):
            artist = figure.text(
                x_position,
                row_y,
                str(value),
                color=_summary_value_color(values, value_index, fallback=text_color),
                ha="center",
                va="center",
                fontsize=row_fontsize,
            )
            artist.set_gid("circuit-compare-summary-row")


def _summary_header_offset(card_height: float) -> float:
    return min(_SUMMARY_CARD_HEADER_OFFSET, max(0.018, card_height * 0.16))


def _summary_row_bottom_padding(card_height: float) -> float:
    return min(_SUMMARY_CARD_ROW_BOTTOM_PADDING, max(0.014, card_height * 0.14))


def _summary_font_sizes(
    card_height: float,
    *,
    multi: bool = False,
    side_count: int = 2,
) -> tuple[float, float]:
    if card_height < 0.18:
        header_fontsize, row_fontsize = (8.2, 7.6) if multi else (8.8, 8.0)
    elif card_height < 0.28:
        header_fontsize, row_fontsize = (9.2, 8.5) if multi else (9.8, 8.9)
    else:
        header_fontsize, row_fontsize = (10.5, 9.4) if multi else (11.0, 10.0)

    if multi and side_count > 3:
        shrink = min(1.2, 0.3 * float(side_count - 3))
        header_fontsize -= shrink
        row_fontsize -= min(0.6, 0.15 * float(side_count - 3))
    return (header_fontsize, row_fontsize)


def _multi_compare_summary_rows(
    side_metrics: tuple[CircuitCompareSideMetrics, ...],
) -> tuple[tuple[str, tuple[int, ...]], ...]:
    return (
        ("Layers", tuple(metrics.layer_count for metrics in side_metrics)),
        ("Ops", tuple(metrics.operation_count for metrics in side_metrics)),
        ("2Q", tuple(metrics.multi_qubit_count for metrics in side_metrics)),
        ("SWAP", tuple(metrics.swap_count for metrics in side_metrics)),
        ("Measurements", tuple(metrics.measurement_count for metrics in side_metrics)),
    )


def _summary_value_color(
    values: tuple[int, ...],
    value_index: int,
    *,
    fallback: str,
) -> str:
    lowest_value = min(values)
    highest_value = max(values)
    if lowest_value == highest_value:
        return fallback
    if values[value_index] == lowest_value:
        return _SUMMARY_BEST_COLOR
    if values[value_index] == highest_value:
        return _SUMMARY_WORST_COLOR
    return fallback


def _short_summary_title(title: str) -> str:
    normalized_title = title.strip() or "Circuit"
    if len(normalized_title) <= 13:
        return normalized_title
    return f"{normalized_title[:10]}..."
