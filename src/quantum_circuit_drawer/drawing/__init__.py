"""Internal drawing compatibility facade.

This package remains importable for compatibility, but it is not part of the stable public extension contract.
"""

from .api import draw_quantum_circuit
from .pages import single_page_scene, single_page_scenes
from .pipeline import PreparedDrawPipeline, coerce_pipeline_options, prepare_draw_pipeline
from .request import DrawPipelineOptions, DrawRequest, build_draw_request, validate_draw_request
from .runtime import RuntimeContext, detect_runtime_context, resolve_draw_config

__all__ = [
    "DrawPipelineOptions",
    "DrawRequest",
    "PreparedDrawPipeline",
    "RuntimeContext",
    "build_draw_request",
    "coerce_pipeline_options",
    "detect_runtime_context",
    "draw_quantum_circuit",
    "prepare_draw_pipeline",
    "resolve_draw_config",
    "single_page_scene",
    "single_page_scenes",
    "validate_draw_request",
]
