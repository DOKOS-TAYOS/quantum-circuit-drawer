"""Public API orchestration for drawing supported circuit objects."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from .._logging import (
    duration_ms,
    emit_render_diagnostics,
    log_event,
    logged_api_call,
    push_log_context,
)
from ..circuit_compare import CircuitCompareConfig, CircuitCompareResult
from ..config import DrawConfig
from ..renderers._render_support import figure_backend_name as _figure_backend_name
from ..result import DrawResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from ..config import DrawMode, ViewMode
    from ..topology import TopologyInput, TopologyQubitMode
    from ..typing import OutputPath

# Kept as a lightweight compatibility alias for tests and internal monkeypatching.
figure_backend_name = _figure_backend_name
logger = logging.getLogger(__name__)


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
    """Draw a supported circuit and return normalized figure handles.

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
        ``DrawResult`` with figure and axes handles, resolved mode, page count,
        diagnostics, detected framework, interactivity state, hover state, and saved
        path.
    """

    from .managed_modes import draw_result_from_prepared_call
    from .preparation import prepare_draw_call

    with logged_api_call(logger, api="draw_quantum_circuit") as started_at:
        resolved_config = _merge_draw_config(
            config,
            mode=mode,
            show=show,
            output_path=output_path,
            figsize=figsize,
            framework=framework,
            view=view,
            composite_mode=composite_mode,
            topology=topology,
            topology_qubits=topology_qubits,
        )
        prepared = prepare_draw_call(circuit, config=resolved_config, ax=ax)
        with push_log_context(
            view=prepared.resolved_config.config.view,
            mode=prepared.resolved_config.mode.value,
            framework=prepared.pipeline.detected_framework,
            backend=prepared.resolved_config.config.backend,
        ):
            result = draw_result_from_prepared_call(
                prepared,
                defer_show=prepared.resolved_config.is_notebook,
            )
            emit_render_diagnostics(logger, result.diagnostics)
            if result.saved_path is not None:
                log_event(
                    logger,
                    logging.INFO,
                    "output.saved",
                    "Saved rendered circuit output.",
                    output_path=result.saved_path,
                )
            log_event(
                logger,
                logging.INFO,
                "api.completed",
                "Completed draw_quantum_circuit.",
                duration_ms=duration_ms(started_at),
                page_count=result.page_count,
                detected_framework=result.detected_framework,
                interactive_enabled=result.interactive_enabled,
                hover_enabled=result.hover_enabled,
                diagnostic_count=len(result.diagnostics),
                saved_path=result.saved_path,
            )
            return result


def _merge_draw_config(
    config: DrawConfig | None,
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
) -> DrawConfig:
    resolved_config = DrawConfig() if config is None else config

    render_options = resolved_config.side.render
    if (
        mode is not None
        or framework is not None
        or view is not None
        or composite_mode is not None
        or topology is not None
        or topology_qubits is not None
    ):
        render_options = replace(
            render_options,
            framework=render_options.framework if framework is None else framework,
            view=render_options.view if view is None else view,
            mode=render_options.mode if mode is None else mode,
            composite_mode=(
                render_options.composite_mode if composite_mode is None else composite_mode
            ),
            topology=render_options.topology if topology is None else topology,
            topology_qubits=(
                render_options.topology_qubits if topology_qubits is None else topology_qubits
            ),
        )

    side_config = resolved_config.side
    if render_options is not resolved_config.side.render:
        side_config = replace(side_config, render=render_options)

    output_options = resolved_config.output
    if show is not None or output_path is not None or figsize is not None:
        output_options = replace(
            output_options,
            show=output_options.show if show is None else show,
            output_path=output_options.output_path if output_path is None else output_path,
            figsize=output_options.figsize if figsize is None else figsize,
        )

    if side_config is resolved_config.side and output_options is resolved_config.output:
        return resolved_config
    return replace(resolved_config, side=side_config, output=output_options)


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
        ``CircuitCompareResult`` with shared figure, per-side results, structural
        metrics, diagnostics, and saved path.
    """

    from .compare import compare_circuits as _compare_circuits

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
