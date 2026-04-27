"""Public histogram plotting APIs for single and comparison histograms."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..diagnostics import DiagnosticSeverity, RenderDiagnostic
from ..drawing.results import normalized_saved_path
from ..drawing.runtime import detect_runtime_context
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
)
from .histogram_normalize import normalize_histogram_data
from .histogram_render import (
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


def plot_histogram(
    data: object,
    *,
    config: HistogramConfig | None = None,
    ax: Axes | None = None,
) -> HistogramResult:
    """Plot a histogram from counts or quasi-probability data."""

    resolved_config = config or HistogramConfig()
    if ax is not None and resolved_config.figsize is not None:
        raise ValueError("figsize cannot be used with ax")
    runtime_context = detect_runtime_context()
    resolved_mode = _resolve_histogram_mode(
        resolved_config.mode,
        runtime_context=runtime_context,
        ax=ax,
    )
    diagnostics: list[RenderDiagnostic] = []
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
    values_by_state = apply_joint_marginal(
        normalized.values_by_state,
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
            values_by_state=normalized.values_by_state,
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
    if resolved_config.show:
        from ..renderers._render_support import show_figure_if_supported

        show_figure_if_supported(figure, show=True)

    return HistogramResult(
        figure=figure,
        axes=axes,
        kind=normalized.kind,
        state_labels=state_labels,
        values=values,
        qubits=resolved_config.qubits,
        diagnostics=tuple(diagnostics),
        saved_path=normalized_saved_path(resolved_config.output_path),
    )


def compare_histograms(
    left_data: object,
    right_data: object,
    *additional_data: object,
    config: HistogramCompareConfig | None = None,
    ax: Axes | None = None,
) -> HistogramCompareResult:
    """Overlay two or more histograms on the same bins and return aligned values."""

    resolved_config = config or HistogramCompareConfig()
    if ax is not None and resolved_config.figsize is not None:
        raise ValueError("figsize cannot be used with ax")

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
            normalized.values_by_state,
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
        tuple(float(values_by_state.get(state_label, 0.0)) for state_label in ordered_state_labels)
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
    if resolved_config.show:
        from ..renderers._render_support import show_figure_if_supported

        show_figure_if_supported(figure, show=True)

    return HistogramCompareResult(
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
        diagnostics=(),
        saved_path=normalized_saved_path(resolved_config.output_path),
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


def _resolve_histogram_mode(
    mode: HistogramMode,
    *,
    runtime_context: object,
    ax: Axes | None,
) -> HistogramMode:
    if mode is not HistogramMode.AUTO:
        return mode
    if ax is not None:
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
