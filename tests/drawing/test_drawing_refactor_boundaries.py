from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from quantum_circuit_drawer import (
    CircuitBuilder,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawResult,
    DrawSideConfig,
    OutputOptions,
)
from quantum_circuit_drawer.circuit_compare import CircuitCompareMetrics
from quantum_circuit_drawer.drawing.pipeline import prepare_draw_pipeline
from quantum_circuit_drawer.drawing.request import build_draw_request
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_sample_ir


def build_reference_compare_ir() -> object:
    return CircuitBuilder(2, 1, name="reference").h(0).cx(0, 1).measure(1, 0).build()


def build_candidate_compare_ir() -> object:
    return (
        CircuitBuilder(2, 1, name="candidate").h(0).x(1).cx(0, 1).swap(0, 1).measure(0, 0).build()
    )


def test_preparation_module_builds_prepared_draw_call() -> None:
    from quantum_circuit_drawer.drawing.preparation import prepare_draw_call

    prepared = prepare_draw_call(
        build_sample_ir(),
        config=DrawConfig(
            side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.FULL)),
            output=OutputOptions(show=False),
        ),
        ax=None,
    )

    assert prepared.resolved_config.mode is DrawMode.FULL
    assert prepared.request.ax is None
    assert prepared.pipeline.detected_framework == "ir"
    assert prepared.pipeline.draw_options.view == "2d"


def test_results_module_builds_draw_result_with_normalized_saved_path(
    sandbox_tmp_path: Path,
) -> None:
    from quantum_circuit_drawer.drawing.results import build_draw_result

    request = build_draw_request(
        circuit=build_sample_ir(),
        style=DrawStyle(),
        show=False,
    )
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )
    figure, axes = plt.subplots()
    output_path = sandbox_tmp_path / "result.png"

    result = build_draw_result(
        primary_figure=figure,
        primary_axes=axes,
        figures=(figure,),
        axes=(axes,),
        mode=DrawMode.FULL,
        page_count=1,
        diagnostics=(),
        pipeline=pipeline,
        output=output_path,
    )

    assert isinstance(result, DrawResult)
    assert result.saved_path == str(output_path.resolve())
    assert result.detected_framework == "ir"
    assert result.interactive_enabled is False

    plt.close(figure)


def test_compare_module_reports_expected_metrics() -> None:
    from quantum_circuit_drawer.drawing.compare import circuit_compare_metrics

    left_request = build_draw_request(circuit=build_reference_compare_ir(), show=False)
    left_pipeline = prepare_draw_pipeline(
        circuit=left_request.circuit,
        framework=left_request.framework,
        style=left_request.style,
        layout=left_request.layout,
        options=left_request.pipeline_options,
    )
    right_request = build_draw_request(circuit=build_candidate_compare_ir(), show=False)
    right_pipeline = prepare_draw_pipeline(
        circuit=right_request.circuit,
        framework=right_request.framework,
        style=right_request.style,
        layout=right_request.layout,
        options=right_request.pipeline_options,
    )

    metrics, diff_summary = circuit_compare_metrics(left_pipeline.ir, right_pipeline.ir)

    assert metrics == CircuitCompareMetrics(
        left_layer_count=3,
        right_layer_count=4,
        layer_delta=1,
        left_operation_count=3,
        right_operation_count=5,
        operation_delta=2,
        left_multi_qubit_count=1,
        right_multi_qubit_count=2,
        multi_qubit_delta=1,
        left_measurement_count=1,
        right_measurement_count=1,
        measurement_delta=0,
        left_swap_count=0,
        right_swap_count=1,
        swap_delta=1,
        differing_layer_count=2,
        left_only_layer_count=0,
        right_only_layer_count=1,
    )
    assert diff_summary.left_columns == (0, 2)
    assert diff_summary.right_columns == (0, 2, 3)


def test_managed_drawing_shim_reexports_new_rendering_owner() -> None:
    import quantum_circuit_drawer.managed.drawing as drawing_facade
    from quantum_circuit_drawer.managed.rendering import (
        is_3d_axes,
        render_draw_pipeline_on_axes,
        render_managed_draw_pipeline,
    )

    assert drawing_facade.render_managed_draw_pipeline is render_managed_draw_pipeline
    assert drawing_facade.render_draw_pipeline_on_axes is render_draw_pipeline_on_axes
    assert drawing_facade.is_3d_axes is is_3d_axes
