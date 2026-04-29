"""Preparation helpers for draw-call orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from .._logging import log_event, push_log_context
from ..config import DrawConfig, DrawMode, ResolvedDrawConfig
from ..diagnostics import RenderDiagnostic
from ..managed.viewport import build_continuous_slider_scene
from .pipeline import PreparedDrawPipeline, prepare_draw_pipeline
from .request import DrawRequest, build_draw_request, validate_draw_request
from .results import combined_draw_diagnostics
from .runtime import resolve_draw_config

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from ..typing import LayoutEngineLike

INTERACTIVE_COMPARE_MODES = frozenset({DrawMode.SLIDER, DrawMode.PAGES_CONTROLS})
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedDrawCall:
    """Resolved inputs and pipeline for one public draw invocation."""

    resolved_config: ResolvedDrawConfig
    request: DrawRequest
    pipeline: PreparedDrawPipeline
    diagnostics: tuple[RenderDiagnostic, ...]


def prepare_draw_call(
    circuit: object,
    *,
    config: DrawConfig | None,
    ax: Axes | None,
) -> PreparedDrawCall:
    """Resolve one public draw call into validated rendering inputs."""

    resolved_config = resolve_draw_config(config, ax=ax)
    with push_log_context(
        view=resolved_config.config.view,
        mode=resolved_config.mode.value,
        framework=resolved_config.config.framework,
        backend=resolved_config.config.backend,
    ):
        log_event(
            logger,
            logging.INFO,
            "runtime.resolved",
            "Resolved draw runtime configuration.",
            interactive_mode_allowed=resolved_config.interactive_mode_allowed,
            notebook_backend_active=resolved_config.notebook_backend_active,
            caller_axes=ax is not None,
        )
    if not resolved_config.interactive_mode_allowed:
        raise ValueError(
            f"mode={resolved_config.mode.value!r} requires a notebook widget backend "
            "such as nbagg, ipympl, or widget"
        )
    if ax is not None and resolved_config.mode in INTERACTIVE_COMPARE_MODES:
        raise ValueError(
            f"mode={resolved_config.mode.value!r} requires a Matplotlib-managed figure "
            "and cannot be used with ax"
        )

    adapter_options = _adapter_options_for_draw_call(resolved_config)
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
        topology_qubits=resolved_config.config.topology_qubits,
        topology_resize=resolved_config.config.topology_resize,
        topology_menu=resolved_config.config.topology_menu,
        direct=resolved_config.config.direct,
        keyboard_shortcuts=resolved_config.config.keyboard_shortcuts,
        double_click_toggle=resolved_config.config.double_click_toggle,
        hover=resolved_config.config.hover,
        **adapter_options,
    )
    validate_draw_request(request)
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )
    pipeline = pipeline_for_resolved_mode(pipeline, mode=resolved_config.mode)
    diagnostics = combined_draw_diagnostics(
        resolved_config.diagnostics,
        request.diagnostics,
        pipeline.diagnostics,
    )
    return PreparedDrawCall(
        resolved_config=resolved_config,
        request=request,
        pipeline=pipeline,
        diagnostics=diagnostics,
    )


def _adapter_options_for_draw_call(resolved_config: ResolvedDrawConfig) -> dict[str, object]:
    """Return adapter options plus internal draw policies for one call."""

    adapter_options = dict(resolved_config.config.adapter_options)
    adapter_options["render_mode"] = resolved_config.mode.value
    adapter_options["unsupported_policy"] = resolved_config.config.unsupported_policy
    return adapter_options


def pipeline_for_resolved_mode(
    pipeline: PreparedDrawPipeline,
    *,
    mode: DrawMode,
) -> PreparedDrawPipeline:
    """Adapt one prepared pipeline for the resolved public draw mode."""

    if mode is not DrawMode.FULL:
        return pipeline
    if pipeline.draw_options.view != "2d":
        return pipeline

    layout_engine = cast("LayoutEngineLike", pipeline.layout_engine)
    continuous_scene = build_continuous_slider_scene(
        pipeline.ir,
        layout_engine,
        pipeline.normalized_style,
        hover_enabled=pipeline.draw_options.hover.enabled,
    )
    continuous_scene.hover = getattr(pipeline.paged_scene, "hover", continuous_scene.hover)
    return replace(pipeline, paged_scene=continuous_scene)
