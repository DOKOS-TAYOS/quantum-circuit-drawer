from __future__ import annotations

from tests.support import build_sample_ir


def test_prepare_draw_pipeline_exposes_only_runtime_components() -> None:
    from quantum_circuit_drawer._draw_pipeline import prepare_draw_pipeline

    pipeline = prepare_draw_pipeline(
        circuit=build_sample_ir(),
        framework="ir",
        style={"theme": "dark"},
        layout=None,
        options={},
    )

    assert pipeline.normalized_style.theme.name == "dark"
    assert pipeline.ir.quantum_wire_count == 2
    assert pipeline.layout_engine is not None
    assert pipeline.renderer.backend_name == "matplotlib"
    assert pipeline.paged_scene.pages
    assert not hasattr(pipeline, "adapter")
