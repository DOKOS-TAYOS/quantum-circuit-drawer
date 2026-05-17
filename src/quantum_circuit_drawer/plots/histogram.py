"""Public histogram plotting APIs for single and comparison histograms."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, TypeVar

from .._ipython_display import close_figures_in_pyplot
from .._logging import (
    duration_ms,
    emit_render_diagnostics,
    log_event,
    logged_api_call,
    push_log_context,
)
from ..diagnostics import DiagnosticSeverity, RenderDiagnostic
from ..drawing.results import normalized_saved_path
from ..drawing.runtime import (
    detect_runtime_context,
    show_requested_without_interactive_backend_diagnostics,
)
from ..style.theme import resolve_theme
from .histogram_compare import (
    attach_histogram_compare_hover,
    attach_histogram_compare_legend_toggle,
    build_compare_metrics,
    draw_histogram_compare_axes,
    ordered_comparison_state_labels,
    resolve_comparison_kind,
)
from .histogram_models import (
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
    _normalize_compare_sort,
    _normalize_kind,
    _normalize_mode,
    _normalize_sort,
    _normalize_state_label_mode,
)
from .histogram_normalize import normalize_histogram_data
from .histogram_render import (
    apply_bit_order,
    apply_joint_marginal,
    display_labels_for_states,
    display_state_label,
    draw_histogram_axes,
    order_histogram_values,
    resolve_figure_and_axes,
    resolved_histogram_bit_width,
    resolved_histogram_y_limits,
    save_histogram_if_requested,
    uniform_reference_value,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from ..typing import OutputPath

logger = logging.getLogger(__name__)
_HistogramDisplayResultT = TypeVar(
    "_HistogramDisplayResultT",
    HistogramResult,
    HistogramCompareResult,
)


def plot_histogram(
    data: object,
    *,
    kind: HistogramKind | str | None = None,
    mode: HistogramMode | str | None = None,
    sort: HistogramSort | str | None = None,
    state_label_mode: HistogramStateLabelMode | str | None = None,
    reverse_bits: bool | None = None,
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
        reverse_bits: Optional override that reverses each bitstring before marginal
            selection, sorting, and decimal conversion.
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

    with logged_api_call(logger, api="plot_histogram") as started_at:
        resolved_config = _merge_histogram_config(
            config,
            kind=kind,
            mode=mode,
            sort=sort,
            state_label_mode=state_label_mode,
            reverse_bits=reverse_bits,
            qubits=qubits,
            top_k=top_k,
            result_index=result_index,
            data_key=data_key,
            show=show,
            output_path=output_path,
            figsize=figsize,
        )
        if ax is not None and resolved_config.figsize is not None:
            raise ValueError("figsize cannot be used with ax")
        runtime_context = detect_runtime_context()
        resolved_mode = _resolve_histogram_mode(
            resolved_config.mode,
            runtime_context=runtime_context,
            ax=ax,
            show=resolved_config.show,
        )
        diagnostics: list[RenderDiagnostic] = []
        with push_log_context(mode=resolved_mode.value, backend=runtime_context.pyplot_backend):
            log_event(
                logger,
                logging.INFO,
                "runtime.resolved",
                "Resolved histogram runtime configuration.",
                caller_axes=ax is not None,
                notebook_backend_active=runtime_context.notebook_backend_active,
            )
            if resolved_config.mode is HistogramMode.AUTO:
                diagnostics.append(
                    RenderDiagnostic(
                        code="auto_mode_resolved",
                        message=f"Resolved histogram mode {resolved_mode.value!r} from mode='auto'.",
                        severity=DiagnosticSeverity.INFO,
                    )
                )
                if runtime_context.is_notebook and not runtime_context.notebook_backend_active:
                    diagnostics.append(
                        RenderDiagnostic(
                            code="histogram_auto_mode_fallback_static",
                            message=(
                                "Fell back to static histogram mode because the notebook backend is not "
                                "widget-interactive."
                            ),
                            severity=DiagnosticSeverity.INFO,
                        )
                    )
            diagnostics.extend(
                show_requested_without_interactive_backend_diagnostics(
                    show=resolved_config.show,
                    runtime_context=runtime_context,
                    caller_axes=ax,
                )
            )
            if (
                resolved_mode is HistogramMode.INTERACTIVE
                and runtime_context.is_notebook
                and not runtime_context.notebook_backend_active
            ):
                raise ValueError(
                    "mode='interactive' requires a notebook widget backend such as nbagg, ipympl, or widget"
                )
            if ax is not None and resolved_mode is HistogramMode.INTERACTIVE:
                raise ValueError(
                    "mode='interactive' requires a Matplotlib-managed figure and cannot be used with ax"
                )

            normalized = normalize_histogram_data(
                data,
                requested_kind=resolved_config.kind,
                result_index=resolved_config.result_index,
                data_key=resolved_config.data_key,
            )
            base_values_by_state = apply_bit_order(
                normalized.values_by_state,
                reverse_bits=resolved_config.reverse_bits,
            )
            values_by_state = apply_joint_marginal(
                base_values_by_state,
                qubits=resolved_config.qubits,
                bit_width=normalized.bit_width,
            )
            theme = resolve_theme(resolved_config.theme)
            uniform_reference = uniform_reference_value(
                values_by_state,
                kind=normalized.kind,
                bit_width=resolved_histogram_bit_width(
                    bit_width=normalized.bit_width,
                    qubits=resolved_config.qubits,
                ),
                show_uniform_reference=resolved_config.show_uniform_reference,
            )
            ordered_values_by_state = order_histogram_values(
                values_by_state,
                sort=resolved_config.sort,
                top_k=resolved_config.top_k,
            )
            state_labels = tuple(ordered_values_by_state)
            values = tuple(float(value) for value in ordered_values_by_state.values())
            figure, axes = resolve_figure_and_axes(ax=ax, figsize=resolved_config.figsize)

            if resolved_mode is HistogramMode.INTERACTIVE:
                from .histogram_interactive import attach_histogram_interactivity

                attach_histogram_interactivity(
                    figure=figure,
                    axes=axes,
                    values_by_state=base_values_by_state,
                    bit_width=normalized.bit_width,
                    kind=normalized.kind,
                    config=resolved_config,
                )
            else:
                draw_histogram_axes(
                    figure=figure,
                    axes=axes,
                    state_labels=state_labels,
                    display_labels=display_labels_for_states(
                        state_labels,
                        mode=resolved_config.state_label_mode,
                    ),
                    values=values,
                    kind=normalized.kind,
                    theme=theme,
                    draw_style=resolved_config.draw_style,
                    uniform_reference_value=uniform_reference,
                    thin_xlabels=False,
                )
                save_histogram_if_requested(figure, output_path=resolved_config.output_path)
            if resolved_config.show and not runtime_context.is_notebook:
                from ..renderers._render_support import show_figure_if_supported

                show_figure_if_supported(figure, show=True)

            result = HistogramResult(
                figure=figure,
                axes=axes,
                kind=normalized.kind,
                state_labels=state_labels,
                values=values,
                qubits=resolved_config.qubits,
                diagnostics=tuple(diagnostics),
                saved_path=normalized_saved_path(resolved_config.output_path),
            )
            result = _with_histogram_notebook_output_policy(
                result,
                runtime_context=runtime_context,
                show=resolved_config.show,
            )
            log_event(
                logger,
                logging.INFO,
                "render.completed",
                "Completed histogram rendering.",
                histogram_kind=result.kind.value,
                state_count=len(result.state_labels),
                saved_path=result.saved_path,
            )
            emit_render_diagnostics(logger, result.diagnostics)
            if result.saved_path is not None:
                log_event(
                    logger,
                    logging.INFO,
                    "output.saved",
                    "Saved histogram output.",
                    output_path=result.saved_path,
                )
            log_event(
                logger,
                logging.INFO,
                "api.completed",
                "Completed plot_histogram.",
                duration_ms=duration_ms(started_at),
                histogram_kind=result.kind.value,
                state_count=len(result.state_labels),
                diagnostic_count=len(result.diagnostics),
                saved_path=result.saved_path,
            )
            return result


def _merge_histogram_config(
    config: HistogramConfig | None,
    *,
    kind: HistogramKind | str | None = None,
    mode: HistogramMode | str | None = None,
    sort: HistogramSort | str | None = None,
    state_label_mode: HistogramStateLabelMode | str | None = None,
    reverse_bits: bool | None = None,
    qubits: tuple[int, ...] | None = None,
    top_k: int | None = None,
    result_index: int | None = None,
    data_key: str | None = None,
    show: bool | None = None,
    output_path: OutputPath | None = None,
    figsize: tuple[float, float] | None = None,
) -> HistogramConfig:
    resolved_config = HistogramConfig() if config is None else config

    data_options = resolved_config.data
    if (
        kind is not None
        or top_k is not None
        or qubits is not None
        or reverse_bits is not None
        or result_index is not None
        or data_key is not None
    ):
        data_options = replace(
            data_options,
            kind=data_options.kind if kind is None else _normalize_kind(kind),
            top_k=data_options.top_k if top_k is None else top_k,
            qubits=data_options.qubits if qubits is None else qubits,
            reverse_bits=data_options.reverse_bits if reverse_bits is None else reverse_bits,
            result_index=data_options.result_index if result_index is None else result_index,
            data_key=data_options.data_key if data_key is None else data_key,
        )

    view_options = resolved_config.view
    if mode is not None or sort is not None or state_label_mode is not None:
        view_options = replace(
            view_options,
            mode=view_options.mode if mode is None else _normalize_mode(mode),
            sort=view_options.sort if sort is None else _normalize_sort(sort),
            state_label_mode=(
                view_options.state_label_mode
                if state_label_mode is None
                else _normalize_state_label_mode(state_label_mode)
            ),
        )

    output_options = resolved_config.output
    if show is not None or output_path is not None or figsize is not None:
        output_options = replace(
            output_options,
            show=output_options.show if show is None else show,
            output_path=output_options.output_path if output_path is None else output_path,
            figsize=output_options.figsize if figsize is None else figsize,
        )

    if (
        data_options is resolved_config.data
        and view_options is resolved_config.view
        and output_options is resolved_config.output
    ):
        return resolved_config
    return replace(
        resolved_config,
        data=data_options,
        view=view_options,
        output=output_options,
    )


def compare_histograms(
    left_data: object,
    right_data: object,
    *additional_data: object,
    kind: HistogramKind | str | None = None,
    sort: HistogramCompareSort | str | None = None,
    reverse_bits: bool | None = None,
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
        reverse_bits: Optional override that reverses each bitstring before marginal
            selection and comparison ordering.
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
        config: Optional ``HistogramCompareConfig`` for shared data selection, ordering,
            labels, hover, appearance, and output. Non-``None`` direct kwargs override
            only matching fields.
        ax: Optional caller-owned Matplotlib axes. Interactive histogram controls are
            not used for comparison plots.

    Returns:
        ``HistogramCompareResult`` with aligned state labels, series values,
        first-two deltas, metrics, selected qubits, diagnostics, and saved path.
    """

    with logged_api_call(logger, api="compare_histograms") as started_at:
        resolved_config = _merge_histogram_compare_config(
            config,
            kind=kind,
            sort=sort,
            reverse_bits=reverse_bits,
            qubits=qubits,
            top_k=top_k,
            result_index=result_index,
            data_key=data_key,
            left_label=left_label,
            right_label=right_label,
            series_labels=series_labels,
            show=show,
            output_path=output_path,
            figsize=figsize,
        )
        if ax is not None and resolved_config.figsize is not None:
            raise ValueError("figsize cannot be used with ax")
        runtime_context = detect_runtime_context()
        diagnostics = list(
            show_requested_without_interactive_backend_diagnostics(
                show=resolved_config.show,
                runtime_context=runtime_context,
                caller_axes=ax,
            )
        )
        with push_log_context(backend=runtime_context.pyplot_backend):
            log_event(
                logger,
                logging.INFO,
                "runtime.resolved",
                "Resolved histogram comparison runtime configuration.",
                caller_axes=ax is not None,
                notebook_backend_active=runtime_context.notebook_backend_active,
            )
            data_series = (left_data, right_data, *additional_data)
            series_labels = _resolve_compare_series_labels(
                resolved_config,
                series_count=len(data_series),
            )
            normalized_series = tuple(
                normalize_histogram_data(
                    data,
                    requested_kind=resolved_config.kind,
                    result_index=resolved_config.result_index,
                    data_key=resolved_config.data_key,
                )
                for data in data_series
            )
            values_by_state_series = tuple(
                apply_joint_marginal(
                    apply_bit_order(
                        normalized.values_by_state,
                        reverse_bits=resolved_config.reverse_bits,
                    ),
                    qubits=resolved_config.qubits,
                    bit_width=normalized.bit_width,
                )
                for normalized in normalized_series
            )
            comparison_kind = resolve_comparison_kind(
                requested_kind=resolved_config.kind,
                series_kinds=tuple(normalized.kind for normalized in normalized_series),
            )
            ordered_state_labels = ordered_comparison_state_labels(
                values_by_state_series=values_by_state_series,
                sort=resolved_config.sort,
                top_k=resolved_config.top_k,
            )
            series_values = tuple(
                tuple(
                    float(values_by_state.get(state_label, 0.0))
                    for state_label in ordered_state_labels
                )
                for values_by_state in values_by_state_series
            )
            left_values = series_values[0]
            right_values = series_values[1]
            delta_values = tuple(
                float(left_value - right_value)
                for left_value, right_value in zip(left_values, right_values, strict=True)
            )
            metrics = build_compare_metrics(delta_values)

            figure, axes = resolve_figure_and_axes(ax=ax, figsize=resolved_config.figsize)
            theme = resolve_theme(resolved_config.theme)
            artists = draw_histogram_compare_axes(
                figure=figure,
                axes=axes,
                state_labels=ordered_state_labels,
                series_values=series_values,
                kind=comparison_kind,
                theme=theme,
                series_labels=series_labels,
            )
            if resolved_config.hover:
                attach_histogram_compare_hover(
                    axes,
                    artists=artists,
                    state_labels=ordered_state_labels,
                    series_values=series_values,
                    kind=comparison_kind,
                    theme=theme,
                    series_labels=series_labels,
                )
            attach_histogram_compare_legend_toggle(
                axes,
                artists=artists,
                series_values=series_values,
                kind=comparison_kind,
            )
            save_histogram_if_requested(figure, output_path=resolved_config.output_path)
            if resolved_config.show and not runtime_context.is_notebook:
                from ..renderers._render_support import show_figure_if_supported

                show_figure_if_supported(figure, show=True)

            result = HistogramCompareResult(
                figure=figure,
                axes=axes,
                kind=comparison_kind,
                state_labels=ordered_state_labels,
                left_values=left_values,
                right_values=right_values,
                delta_values=delta_values,
                metrics=metrics,
                qubits=resolved_config.qubits,
                series_labels=series_labels,
                series_values=series_values,
                diagnostics=tuple(diagnostics),
                saved_path=normalized_saved_path(resolved_config.output_path),
            )
            result = _with_histogram_notebook_output_policy(
                result,
                runtime_context=runtime_context,
                show=resolved_config.show,
            )
            series_count = len(result.series_values or (result.left_values, result.right_values))
            log_event(
                logger,
                logging.INFO,
                "render.completed",
                "Completed histogram comparison rendering.",
                histogram_kind=result.kind.value,
                state_count=len(result.state_labels),
                series_count=series_count,
                saved_path=result.saved_path,
            )
            emit_render_diagnostics(logger, result.diagnostics)
            if result.saved_path is not None:
                log_event(
                    logger,
                    logging.INFO,
                    "output.saved",
                    "Saved histogram comparison output.",
                    output_path=result.saved_path,
                )
            log_event(
                logger,
                logging.INFO,
                "api.completed",
                "Completed compare_histograms.",
                duration_ms=duration_ms(started_at),
                histogram_kind=result.kind.value,
                state_count=len(result.state_labels),
                series_count=series_count,
                diagnostic_count=len(result.diagnostics),
                saved_path=result.saved_path,
            )
            return result


def _merge_histogram_compare_config(
    config: HistogramCompareConfig | None,
    *,
    kind: HistogramKind | str | None = None,
    sort: HistogramCompareSort | str | None = None,
    reverse_bits: bool | None = None,
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
) -> HistogramCompareConfig:
    resolved_config = HistogramCompareConfig() if config is None else config

    data_options = resolved_config.data
    if (
        kind is not None
        or top_k is not None
        or qubits is not None
        or reverse_bits is not None
        or result_index is not None
        or data_key is not None
    ):
        data_options = replace(
            data_options,
            kind=data_options.kind if kind is None else _normalize_kind(kind),
            top_k=data_options.top_k if top_k is None else top_k,
            qubits=data_options.qubits if qubits is None else qubits,
            reverse_bits=data_options.reverse_bits if reverse_bits is None else reverse_bits,
            result_index=data_options.result_index if result_index is None else result_index,
            data_key=data_options.data_key if data_key is None else data_key,
        )

    compare_options = resolved_config.compare
    if (
        sort is not None
        or left_label is not None
        or right_label is not None
        or series_labels is not None
    ):
        compare_options = replace(
            compare_options,
            sort=compare_options.sort if sort is None else _normalize_compare_sort(sort),
            left_label=compare_options.left_label if left_label is None else left_label,
            right_label=compare_options.right_label if right_label is None else right_label,
            series_labels=(
                compare_options.series_labels if series_labels is None else series_labels
            ),
        )

    output_options = resolved_config.output
    if show is not None or output_path is not None or figsize is not None:
        output_options = replace(
            output_options,
            show=output_options.show if show is None else show,
            output_path=output_options.output_path if output_path is None else output_path,
            figsize=output_options.figsize if figsize is None else figsize,
        )

    if (
        data_options is resolved_config.data
        and compare_options is resolved_config.compare
        and output_options is resolved_config.output
    ):
        return resolved_config
    return replace(
        resolved_config,
        data=data_options,
        compare=compare_options,
        output=output_options,
    )


def _resolve_compare_series_labels(
    config: HistogramCompareConfig,
    *,
    series_count: int,
) -> tuple[str, ...]:
    if series_count < 2:
        raise ValueError("compare_histograms requires at least two data series")
    if config.series_labels is not None:
        if len(config.series_labels) != series_count:
            raise ValueError(
                "compare.series_labels must contain one label for each histogram series"
            )
        return config.series_labels
    return (
        config.left_label,
        config.right_label,
        *(f"Series {index}" for index in range(3, series_count + 1)),
    )


def _with_histogram_notebook_output_policy(
    result: _HistogramDisplayResultT,
    *,
    runtime_context: object,
    show: bool,
) -> _HistogramDisplayResultT:
    """Apply notebook display flags while preserving the returned result object."""

    if not getattr(runtime_context, "is_notebook", False):
        return result
    if not show:
        close_figures_in_pyplot((result.figure,))
    return replace(
        result,
        _ipython_display_enabled=show,
        _ipython_close_after_display=not getattr(
            runtime_context,
            "notebook_backend_active",
            False,
        ),
    )


def _resolve_histogram_mode(
    mode: HistogramMode,
    *,
    runtime_context: object,
    ax: Axes | None,
    show: bool,
) -> HistogramMode:
    if mode is not HistogramMode.AUTO:
        return mode
    if ax is not None:
        return HistogramMode.STATIC
    if not show:
        return HistogramMode.STATIC
    if getattr(runtime_context, "is_notebook", False):
        if getattr(runtime_context, "notebook_backend_active", False):
            return HistogramMode.INTERACTIVE
        return HistogramMode.STATIC
    return HistogramMode.INTERACTIVE


_normalize_histogram_data = normalize_histogram_data
_apply_joint_marginal = apply_joint_marginal
_display_labels_for_states = display_labels_for_states
_display_state_label = display_state_label
_draw_histogram_axes = draw_histogram_axes
_draw_histogram_compare_axes = draw_histogram_compare_axes
_order_histogram_values = order_histogram_values
_resolved_histogram_bit_width = resolved_histogram_bit_width
_resolved_histogram_y_limits = resolved_histogram_y_limits
_save_histogram_if_requested = save_histogram_if_requested
_uniform_reference_value = uniform_reference_value


__all__ = [
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
]
