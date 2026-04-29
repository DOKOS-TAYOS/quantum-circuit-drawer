"""Public API orchestration for drawing supported circuit objects."""

from __future__ import annotations

import logging
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

# Kept as a lightweight compatibility alias for tests and internal monkeypatching.
figure_backend_name = _figure_backend_name
logger = logging.getLogger(__name__)


def draw_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult:
    """Draw a supported circuit with the current public API contract."""

    from .managed_modes import draw_result_from_prepared_call
    from .preparation import prepare_draw_call

    with logged_api_call(logger, api="draw_quantum_circuit") as started_at:
        prepared = prepare_draw_call(circuit, config=config, ax=ax)
        with push_log_context(
            view=prepared.resolved_config.config.view,
            mode=prepared.resolved_config.mode.value,
            framework=prepared.pipeline.detected_framework,
            backend=prepared.resolved_config.config.backend,
        ):
            result = draw_result_from_prepared_call(prepared)
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


def compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *additional_circuits: object,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, ...] | None = None,
    summary_ax: Axes | None = None,
) -> CircuitCompareResult:
    """Render two or more circuits side by side and return structural comparison data."""

    from .compare import compare_circuits as _compare_circuits

    return _compare_circuits(
        left_circuit,
        right_circuit,
        *additional_circuits,
        config=config,
        axes=axes,
        summary_ax=summary_ax,
    )
