"""Public API orchestration for drawing supported circuit objects."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ..circuit_compare import CircuitCompareConfig, CircuitCompareMetrics, CircuitCompareResult
from ..config import DrawConfig, DrawMode, ResolvedDrawConfig
from ..diagnostics import RenderDiagnostic
from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..renderers._render_support import (
    backend_supports_interaction,
    figure_backend_name,
    save_rendered_figure,
)
from ..result import DrawResult
from .pages import single_page_scenes
from .pipeline import prepare_draw_pipeline
from .request import DrawRequest, build_draw_request, validate_draw_request
from .runtime import resolve_draw_config

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..layout.scene import LayoutScene
    from ..layout.scene_3d import LayoutScene3D
    from ..renderers.base import BaseRenderer
    from ..typing import LayoutEngineLike, OutputPath
    from .pipeline import PreparedDrawPipeline

logger = logging.getLogger(__name__)

_INTERACTIVE_COMPARE_MODES = frozenset({DrawMode.SLIDER, DrawMode.PAGES_CONTROLS})


@dataclass(frozen=True, slots=True)
class _PreparedDrawCall:
    resolved_config: ResolvedDrawConfig
    request: DrawRequest
    pipeline: PreparedDrawPipeline
    diagnostics: tuple[RenderDiagnostic, ...]


def draw_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult:
    """Draw a supported circuit with the current public API contract.

    The function resolves the runtime-dependent default mode, validates
    interactive constraints, prepares the pipeline, and returns one
    normalized ``DrawResult`` for every rendering path.
    """
    prepared = _prepare_draw_call(circuit, config=config, ax=ax)
    resolved_config = prepared.resolved_config
    request = prepared.request
    pipeline = prepared.pipeline

    if request.ax is None:
        if resolved_config.mode is DrawMode.PAGES and request.pipeline_options.view == "2d":
            return _render_managed_2d_pages_result(
                pipeline,
                output=request.output,
                show=request.show,
                figsize=request.figsize,
                page_slider=request.page_slider,
                page_window=request.page_window,
                mode=resolved_config.mode,
                diagnostics=prepared.diagnostics,
            )
        if resolved_config.mode is DrawMode.PAGES and request.pipeline_options.view == "3d":
            return _render_managed_3d_pages_result(
                pipeline,
                output=request.output,
                show=request.show,
                figsize=request.figsize,
                mode=resolved_config.mode,
                diagnostics=prepared.diagnostics,
            )
        if (
            resolved_config.mode is DrawMode.PAGES_CONTROLS
            and request.pipeline_options.view == "3d"
        ):
            return _render_managed_3d_page_controls_result(
                pipeline,
                output=request.output,
                show=request.show,
                figsize=request.figsize,
                mode=resolved_config.mode,
                diagnostics=prepared.diagnostics,
            )
        figure, axes = _render_managed_draw_pipeline(
            pipeline,
            output=request.output,
            show=request.show,
            figsize=request.figsize,
            page_slider=request.page_slider,
            page_window=request.page_window,
        )
        return _build_draw_result(
            primary_figure=figure,
            primary_axes=axes,
            figures=(figure,),
            axes=(axes,),
            mode=resolved_config.mode,
            page_count=_page_count_for_pipeline(pipeline, mode=resolved_config.mode),
            diagnostics=prepared.diagnostics,
            pipeline=pipeline,
            output=request.output,
        )

    if request.pipeline_options.view == "3d" and not _is_3d_axes(request.ax):
        raise ValueError("view='3d' requires a 3D Matplotlib axes")
    logger.debug("Rendering scene on caller-managed Matplotlib axes")
    axes = _render_draw_pipeline_on_axes(
        pipeline,
        axes=request.ax,
        output=request.output,
    )
    figure = cast("Figure", axes.figure)
    return _build_draw_result(
        primary_figure=figure,
        primary_axes=axes,
        figures=(figure,),
        axes=(axes,),
        mode=resolved_config.mode,
        page_count=_page_count_for_pipeline(pipeline, mode=resolved_config.mode),
        diagnostics=prepared.diagnostics,
        pipeline=pipeline,
        output=request.output,
    )


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
        figure = _shared_figure_for_compare_axes(left_axes, right_axes)

    normalized_left_config = _normalize_compare_draw_config(left_config, side_label="left")
    normalized_right_config = _normalize_compare_draw_config(right_config, side_label="right")
    left_prepared = _prepare_draw_call(left_circuit, config=normalized_left_config, ax=left_axes)
    right_prepared = _prepare_draw_call(
        right_circuit,
        config=normalized_right_config,
        ax=right_axes,
    )

    rendered_left_axes = _render_draw_pipeline_on_axes(
        left_prepared.pipeline,
        axes=left_axes,
        output=None,
        respect_precomputed_scene=True,
    )
    rendered_right_axes = _render_draw_pipeline_on_axes(
        right_prepared.pipeline,
        axes=right_axes,
        output=None,
        respect_precomputed_scene=True,
    )
    shared_figure = figure

    metrics, diff_summary = _circuit_compare_metrics(
        left_prepared.pipeline.ir,
        right_prepared.pipeline.ir,
    )
    if resolved_compare_config.highlight_differences:
        _highlight_compare_columns(
            rendered_left_axes,
            cast("LayoutScene", left_prepared.pipeline.paged_scene),
            diff_summary.left_columns,
        )
        _highlight_compare_columns(
            rendered_right_axes,
            cast("LayoutScene", right_prepared.pipeline.paged_scene),
            diff_summary.right_columns,
        )

    _apply_compare_titles(
        left_axes=rendered_left_axes,
        right_axes=rendered_right_axes,
        config=resolved_compare_config,
        metrics=metrics,
    )
    if resolved_compare_config.output_path is not None:
        save_rendered_figure(shared_figure, resolved_compare_config.output_path)
    from ..renderers._render_support import show_figure_if_supported

    if resolved_compare_config.show:
        show_figure_if_supported(shared_figure, show=True)

    left_result = _build_draw_result(
        primary_figure=shared_figure,
        primary_axes=rendered_left_axes,
        figures=(shared_figure,),
        axes=(rendered_left_axes,),
        mode=left_prepared.resolved_config.mode,
        page_count=1,
        diagnostics=left_prepared.diagnostics,
        pipeline=left_prepared.pipeline,
        output=None,
    )
    right_result = _build_draw_result(
        primary_figure=shared_figure,
        primary_axes=rendered_right_axes,
        figures=(shared_figure,),
        axes=(rendered_right_axes,),
        mode=right_prepared.resolved_config.mode,
        page_count=1,
        diagnostics=right_prepared.diagnostics,
        pipeline=right_prepared.pipeline,
        output=None,
    )
    return CircuitCompareResult(
        figure=shared_figure,
        axes=(rendered_left_axes, rendered_right_axes),
        left_result=left_result,
        right_result=right_result,
        metrics=metrics,
        diagnostics=(),
        saved_path=_normalized_saved_path(resolved_compare_config.output_path),
    )


def _prepare_draw_call(
    circuit: object,
    *,
    config: DrawConfig | None,
    ax: Axes | None,
) -> _PreparedDrawCall:
    resolved_config = resolve_draw_config(config, ax=ax)
    if not resolved_config.interactive_mode_allowed:
        raise ValueError(
            f"mode={resolved_config.mode.value!r} requires a notebook widget backend "
            "such as nbagg, ipympl, or widget"
        )
    if ax is not None and resolved_config.mode in _INTERACTIVE_COMPARE_MODES:
        raise ValueError(
            f"mode={resolved_config.mode.value!r} requires a Matplotlib-managed figure "
            "and cannot be used with ax"
        )

    request = build_draw_request(
        circuit=circuit,
        framework=resolved_config.config.framework,
        style=resolved_config.config.style,
        layout=resolved_config.config.layout,
        backend=resolved_config.config.backend,
        ax=ax,
        output=resolved_config.config.output_path,
        show=resolved_config.config.show,
        figsize=resolved_config.config.figsize,
        page_slider=resolved_config.mode is DrawMode.SLIDER,
        page_window=(
            resolved_config.mode is DrawMode.PAGES_CONTROLS and resolved_config.config.view == "2d"
        ),
        composite_mode=resolved_config.config.composite_mode,
        view=resolved_config.config.view,
        topology=resolved_config.config.topology,
        topology_menu=resolved_config.config.topology_menu,
        direct=resolved_config.config.direct,
        hover=resolved_config.config.hover,
        render_mode=resolved_config.mode.value,
        unsupported_policy=resolved_config.config.unsupported_policy,
    )
    validate_draw_request(request)
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )
    pipeline = _pipeline_for_resolved_mode(pipeline, mode=resolved_config.mode)
    diagnostics = _combined_draw_diagnostics(
        resolved_config.diagnostics,
        request.diagnostics,
        pipeline.diagnostics,
    )
    return _PreparedDrawCall(
        resolved_config=resolved_config,
        request=request,
        pipeline=pipeline,
        diagnostics=diagnostics,
    )


def _build_draw_result(
    *,
    primary_figure: Figure,
    primary_axes: Axes,
    figures: tuple[Figure, ...],
    axes: tuple[Axes, ...],
    mode: DrawMode,
    page_count: int,
    diagnostics: tuple[RenderDiagnostic, ...],
    pipeline: PreparedDrawPipeline,
    output: OutputPath | None,
) -> DrawResult:
    hover_enabled = pipeline.draw_options.hover.enabled
    return DrawResult(
        primary_figure=primary_figure,
        primary_axes=primary_axes,
        figures=figures,
        axes=axes,
        mode=mode,
        page_count=page_count,
        diagnostics=diagnostics,
        detected_framework=pipeline.detected_framework,
        interactive_enabled=_interactive_enabled_for_result(
            figure=primary_figure,
            mode=mode,
            pipeline=pipeline,
        ),
        hover_enabled=hover_enabled,
        saved_path=_normalized_saved_path(output),
    )


@dataclass(frozen=True, slots=True)
class _CircuitCompareDiffSummary:
    left_columns: tuple[int, ...]
    right_columns: tuple[int, ...]


def _normalize_compare_draw_config(
    config: DrawConfig | None,
    *,
    side_label: str,
) -> DrawConfig:
    resolved_config = DrawConfig(show=False) if config is None else config
    if resolved_config.view != "2d":
        raise ValueError(
            f"compare_circuits only supports 2D rendering; {side_label}_config.view must be '2d'"
        )
    if resolved_config.mode in _INTERACTIVE_COMPARE_MODES:
        raise ValueError("compare_circuits does not support slider or page-control modes in v1")
    return replace(
        resolved_config,
        mode=DrawMode.FULL,
        view="2d",
        show=False,
        output_path=None,
        topology_menu=False,
    )


def _shared_figure_for_compare_axes(left_axes: Axes, right_axes: Axes) -> Figure:
    left_figure = cast("Figure", left_axes.figure)
    right_figure = cast("Figure", right_axes.figure)
    if left_figure is not right_figure:
        raise ValueError("compare_circuits requires both axes to belong to the same figure")
    return left_figure


def _interactive_enabled_for_result(
    *,
    figure: Figure,
    mode: DrawMode,
    pipeline: PreparedDrawPipeline,
) -> bool:
    if not backend_supports_interaction(figure_backend_name(figure)):
        return False
    if mode in _INTERACTIVE_COMPARE_MODES:
        return True
    if pipeline.draw_options.hover.enabled:
        return True
    return pipeline.draw_options.view == "3d"


def _normalized_saved_path(output: object) -> str | None:
    if output is None:
        return None
    return str(Path(output).resolve())


def _circuit_compare_metrics(
    left_ir: CircuitIR,
    right_ir: CircuitIR,
) -> tuple[CircuitCompareMetrics, _CircuitCompareDiffSummary]:
    left_layer_signatures = tuple(_layer_signature(left_ir, layer) for layer in left_ir.layers)
    right_layer_signatures = tuple(_layer_signature(right_ir, layer) for layer in right_ir.layers)
    common_layer_count = min(len(left_layer_signatures), len(right_layer_signatures))
    differing_layer_indices = tuple(
        layer_index
        for layer_index in range(common_layer_count)
        if left_layer_signatures[layer_index] != right_layer_signatures[layer_index]
    )
    left_only_layer_indices = tuple(range(common_layer_count, len(left_layer_signatures)))
    right_only_layer_indices = tuple(range(common_layer_count, len(right_layer_signatures)))
    left_stats = _circuit_stats(left_ir)
    right_stats = _circuit_stats(right_ir)
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
    return metrics, _CircuitCompareDiffSummary(
        left_columns=tuple((*differing_layer_indices, *left_only_layer_indices)),
        right_columns=tuple((*differing_layer_indices, *right_only_layer_indices)),
    )


@dataclass(frozen=True, slots=True)
class _CircuitStats:
    layer_count: int
    operation_count: int
    multi_qubit_count: int
    measurement_count: int
    swap_count: int


def _circuit_stats(circuit: CircuitIR) -> _CircuitStats:
    operations = tuple(operation for layer in circuit.layers for operation in layer.operations)
    return _CircuitStats(
        layer_count=len(circuit.layers),
        operation_count=len(operations),
        multi_qubit_count=sum(
            1 for operation in operations if _is_multi_qubit_operation(operation)
        ),
        measurement_count=sum(
            1 for operation in operations if operation.kind is OperationKind.MEASUREMENT
        ),
        swap_count=sum(1 for operation in operations if operation.kind is OperationKind.SWAP),
    )


def _is_multi_qubit_operation(operation: OperationIR | MeasurementIR) -> bool:
    quantum_wire_ids = tuple(dict.fromkeys((*operation.control_wires, *operation.target_wires)))
    if operation.kind is OperationKind.MEASUREMENT:
        return len(tuple(operation.target_wires)) > 1
    if operation.kind is OperationKind.BARRIER:
        return False
    return len(quantum_wire_ids) > 1


def _layer_signature(
    circuit: CircuitIR,
    layer: LayerIR,
) -> tuple[tuple[object, ...], ...]:
    wire_indices = {wire.id: wire.index for wire in circuit.all_wires}
    return tuple(_operation_signature(operation, wire_indices) for operation in layer.operations)


def _operation_signature(
    operation: OperationIR | MeasurementIR,
    wire_indices: dict[str, int],
) -> tuple[object, ...]:
    measurement_target = (
        wire_indices.get(operation.classical_target, operation.classical_target)
        if isinstance(operation, MeasurementIR)
        else None
    )
    return (
        operation.kind,
        operation.canonical_family,
        operation.name,
        tuple(operation.parameters),
        tuple(wire_indices[wire_id] for wire_id in operation.target_wires),
        tuple(wire_indices[wire_id] for wire_id in operation.control_wires),
        measurement_target,
    )


def _highlight_compare_columns(
    axes: Axes,
    scene: LayoutScene,
    columns: tuple[int, ...],
) -> None:
    if not columns:
        return
    column_spans = _scene_column_spans(scene)
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


def _scene_column_spans(scene: LayoutScene) -> dict[int, tuple[float, float]]:
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


def _apply_compare_titles(
    *,
    left_axes: Axes,
    right_axes: Axes,
    config: CircuitCompareConfig,
    metrics: CircuitCompareMetrics,
) -> None:
    left_axes.set_title(config.left_title)
    right_axes.set_title(config.right_title)
    if not config.show_summary:
        return
    summary_figure = cast("Figure", left_axes.figure)
    summary_figure.suptitle(
        (
            f"Layers {metrics.left_layer_count}->{metrics.right_layer_count} "
            f"(Δ {metrics.layer_delta:+d}) | "
            f"Ops {metrics.left_operation_count}->{metrics.right_operation_count} "
            f"(Δ {metrics.operation_delta:+d}) | "
            f"2Q {metrics.left_multi_qubit_count}->{metrics.right_multi_qubit_count} "
            f"(Δ {metrics.multi_qubit_delta:+d}) | "
            f"SWAP {metrics.left_swap_count}->{metrics.right_swap_count} "
            f"(Δ {metrics.swap_delta:+d}) | "
            f"Meas {metrics.left_measurement_count}->{metrics.right_measurement_count} "
            f"(Δ {metrics.measurement_delta:+d})"
        ),
        fontsize=11.0,
    )


def _combined_draw_diagnostics(
    *diagnostic_groups: tuple[RenderDiagnostic, ...],
) -> tuple[RenderDiagnostic, ...]:
    diagnostics: list[RenderDiagnostic] = []
    for diagnostic_group in diagnostic_groups:
        diagnostics.extend(diagnostic_group)
    return tuple(diagnostics)


def _pipeline_for_resolved_mode(
    pipeline: PreparedDrawPipeline,
    *,
    mode: DrawMode,
) -> PreparedDrawPipeline:
    if mode is not DrawMode.FULL:
        return pipeline
    if pipeline.draw_options.view != "2d":
        return pipeline

    from ..managed.drawing import build_continuous_slider_scene

    layout_engine = cast("LayoutEngineLike", pipeline.layout_engine)
    continuous_scene = build_continuous_slider_scene(
        pipeline.ir,
        layout_engine,
        pipeline.normalized_style,
        hover_enabled=pipeline.draw_options.hover.enabled,
    )
    continuous_scene.hover = getattr(pipeline.paged_scene, "hover", continuous_scene.hover)
    return replace(pipeline, paged_scene=continuous_scene)


def _render_managed_draw_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    page_slider: bool,
    page_window: bool,
    respect_precomputed_scene: bool = False,
) -> tuple[Figure, Axes]:
    from ..managed.drawing import render_managed_draw_pipeline

    return render_managed_draw_pipeline(
        pipeline,
        output=output,
        show=show,
        figsize=figsize,
        page_slider=page_slider,
        page_window=page_window,
        respect_precomputed_scene=respect_precomputed_scene,
    )


def _render_managed_2d_pages_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    page_slider: bool,
    page_window: bool,
    mode: DrawMode,
    diagnostics: tuple[RenderDiagnostic, ...],
) -> DrawResult:
    adapted_scene = _page_window_adapted_2d_scene(pipeline, figsize=figsize)
    adapted_pipeline = replace(pipeline, paged_scene=adapted_scene)
    page_scenes = single_page_scenes(adapted_scene)

    if output is not None:
        saved_figure, _ = _render_managed_draw_pipeline(
            adapted_pipeline,
            output=output,
            show=False,
            figsize=figsize,
            page_slider=page_slider,
            page_window=page_window,
        )
        try:
            import matplotlib.pyplot as plt

            plt.close(saved_figure)
        except Exception:  # pragma: no cover - close should be best-effort only
            pass

    figures: list[Figure] = []
    axes_list: list[Axes] = []
    for page_scene in page_scenes:
        page_pipeline = replace(adapted_pipeline, paged_scene=page_scene)
        figure, axes = _render_managed_draw_pipeline(
            page_pipeline,
            output=None,
            show=show,
            figsize=figsize,
            page_slider=False,
            page_window=False,
            respect_precomputed_scene=True,
        )
        figures.append(figure)
        axes_list.append(axes)

    return _build_draw_result(
        primary_figure=figures[0],
        primary_axes=axes_list[0],
        figures=tuple(figures),
        axes=tuple(axes_list),
        mode=mode,
        page_count=len(page_scenes),
        diagnostics=diagnostics,
        pipeline=pipeline,
        output=output,
    )


def _render_managed_3d_pages_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    mode: DrawMode,
    diagnostics: tuple[RenderDiagnostic, ...],
) -> DrawResult:
    page_scenes = _windowed_3d_scenes(pipeline, figsize=figsize)

    if output is not None:
        _save_clean_3d_pages_output(
            page_scenes,
            renderer=pipeline.renderer,
            output=output,
            figsize=figsize,
        )

    figures: list[Figure] = []
    axes_list: list[Axes] = []
    for page_scene in page_scenes:
        page_pipeline = replace(pipeline, paged_scene=page_scene)
        figure, axes = _render_managed_draw_pipeline(
            page_pipeline,
            output=None,
            show=show,
            figsize=figsize,
            page_slider=False,
            page_window=False,
        )
        figures.append(figure)
        axes_list.append(axes)

    return _build_draw_result(
        primary_figure=figures[0],
        primary_axes=axes_list[0],
        figures=tuple(figures),
        axes=tuple(axes_list),
        mode=mode,
        page_count=len(page_scenes),
        diagnostics=diagnostics,
        pipeline=pipeline,
        output=output,
    )


def _render_managed_3d_page_controls_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    mode: DrawMode,
    diagnostics: tuple[RenderDiagnostic, ...],
) -> DrawResult:
    from ..managed.page_window_3d import configure_3d_page_window
    from ..managed.topology_menu import attach_topology_menu
    from ..renderers._matplotlib_figure import create_managed_figure, set_page_window
    from ..renderers._render_support import (
        should_use_managed_agg_canvas,
        show_figure_if_supported,
    )

    page_scenes = _windowed_3d_scenes(pipeline, figsize=figsize)
    if output is not None:
        _save_clean_3d_pages_output(
            page_scenes,
            renderer=pipeline.renderer,
            output=output,
            figsize=figsize,
        )

    scene_3d = page_scenes[0]
    use_agg_canvas = should_use_managed_agg_canvas(
        show=show,
        output=None,
        prefer_offscreen_when_hidden=not scene_3d.hover_enabled,
    )
    figure_width, figure_height = figsize or (
        max(4.6, scene_3d.width * 0.95),
        max(2.1, scene_3d.height * 0.72) + 1.0,
    )
    figure, axes = create_managed_figure(
        scene_3d,
        figure_width=figure_width,
        figure_height=figure_height,
        use_agg=use_agg_canvas,
        projection="3d",
    )
    page_window = configure_3d_page_window(
        figure=figure,
        axes=axes,
        pipeline=pipeline,
        page_scenes=page_scenes,
        set_page_window=set_page_window,
    )
    primary_axes = page_window.display_axes[0]
    if pipeline.draw_options.topology_menu and not use_agg_canvas:
        attach_topology_menu(figure=figure, axes=primary_axes, pipeline=pipeline)
    show_figure_if_supported(figure, show=show)
    return _build_draw_result(
        primary_figure=figure,
        primary_axes=primary_axes,
        figures=(figure,),
        axes=(primary_axes,),
        mode=mode,
        page_count=len(page_scenes),
        diagnostics=diagnostics,
        pipeline=pipeline,
        output=output,
    )


def _page_count_for_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    mode: DrawMode,
) -> int:
    if pipeline.draw_options.view != "3d":
        return len(getattr(pipeline.paged_scene, "pages", ()) or ())
    if mode is DrawMode.FULL:
        return 1
    return len(_windowed_3d_scenes(pipeline))


def _page_window_adapted_2d_scene(
    pipeline: PreparedDrawPipeline,
    *,
    figsize: tuple[float, float] | None,
) -> LayoutScene:
    from ..layout.engine import LayoutEngine
    from ..managed.drawing import page_window_adaptive_paged_scene
    from ..renderers._matplotlib_figure import create_managed_figure

    if pipeline.draw_options.view == "2d":
        initial_scene = cast("LayoutScene", pipeline.paged_scene)
        layout_engine = cast("LayoutEngineLike", pipeline.layout_engine)
    else:
        layout_engine = LayoutEngine()
        initial_scene = layout_engine.compute(pipeline.ir, pipeline.normalized_style)
        initial_scene.hover = pipeline.draw_options.hover

    figure_width, figure_height = figsize or (
        max(4.6, initial_scene.width * 0.95),
        max(2.1, initial_scene.page_height * 0.72),
    )
    figure, axes = create_managed_figure(
        initial_scene,
        figure_width=figure_width,
        figure_height=figure_height,
        use_agg=True,
    )
    try:
        adapted_scene, _ = page_window_adaptive_paged_scene(
            pipeline.ir,
            layout_engine,
            pipeline.normalized_style,
            axes,
            hover_enabled=initial_scene.hover.enabled,
            initial_scene=initial_scene,
            visible_page_count=1,
        )
    finally:
        figure.clear()

    adapted_scene.hover = initial_scene.hover
    return adapted_scene


def _windowed_3d_scenes(
    pipeline: PreparedDrawPipeline,
    *,
    figsize: tuple[float, float] | None = None,
) -> tuple[LayoutScene3D, ...]:
    from ..managed.page_window_3d import windowed_3d_page_scenes

    return windowed_3d_page_scenes(pipeline, figure_size=figsize)


def _save_clean_3d_pages_output(
    page_scenes: tuple[LayoutScene3D, ...],
    *,
    renderer: BaseRenderer,
    output: OutputPath,
    figsize: tuple[float, float] | None,
) -> None:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    from ..renderers._render_support import save_rendered_figure
    from ..renderers.matplotlib_renderer_3d import _MANAGED_3D_VIEWPORT_BOUNDS_ATTR

    first_scene = page_scenes[0]
    page_count = len(page_scenes)
    figure = Figure(
        figsize=figsize
        or (
            max(4.6, first_scene.width * 0.95),
            max(2.1, first_scene.height * 0.72) * page_count,
        )
    )
    FigureCanvasAgg(figure)
    figure.patch.set_facecolor(first_scene.style.theme.figure_facecolor)
    top = 0.98
    bottom = 0.02
    left = 0.02
    width = 0.96
    total_height = top - bottom
    gap = 0.02
    subplot_height = (total_height - (gap * max(0, page_count - 1))) / float(page_count)

    for page_index, page_scene in enumerate(page_scenes):
        subplot_bottom = bottom + ((page_count - page_index - 1) * (subplot_height + gap))
        axes = figure.add_axes((left, subplot_bottom, width, subplot_height), projection="3d")
        pipeline_bounds = (left, subplot_bottom, width, subplot_height)
        setattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, pipeline_bounds)
        renderer.render(page_scene, ax=axes)

    save_rendered_figure(figure, output)


def _render_draw_pipeline_on_axes(
    pipeline: PreparedDrawPipeline,
    *,
    axes: Axes,
    output: OutputPath | None,
    respect_precomputed_scene: bool = False,
) -> Axes:
    from ..managed.drawing import render_draw_pipeline_on_axes

    return render_draw_pipeline_on_axes(
        pipeline,
        axes=axes,
        output=output,
        respect_precomputed_scene=respect_precomputed_scene,
    )


def _is_3d_axes(ax: Axes) -> bool:
    from ..managed.drawing import is_3d_axes

    return is_3d_axes(ax)
