from __future__ import annotations

from collections.abc import Mapping

import pytest

from quantum_circuit_drawer._draw_pipeline import prepare_draw_pipeline, resolve_layout_engine
from quantum_circuit_drawer._draw_request import DrawPipelineOptions, build_draw_request
from quantum_circuit_drawer.exceptions import LayoutError
from quantum_circuit_drawer.hover import HoverOptions
from quantum_circuit_drawer.ir.circuit import CircuitIR
from quantum_circuit_drawer.layout import LayoutEngine
from quantum_circuit_drawer.layout.scene import LayoutScene
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_sample_ir


class _CapturingAdapter:
    def __init__(self, ir: CircuitIR) -> None:
        self._ir = ir
        self.calls: list[dict[str, object]] = []

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        self.calls.append({"circuit": circuit, "options": dict(options or {})})
        return self._ir


class _CapturingLayout:
    def __init__(self) -> None:
        self.calls: list[tuple[CircuitIR, DrawStyle]] = []

    def compute(self, circuit_ir: CircuitIR, style: DrawStyle) -> LayoutScene:
        self.calls.append((circuit_ir, style))
        return LayoutEngine().compute(circuit_ir, style)


def test_prepare_draw_pipeline_exposes_runtime_components_only() -> None:
    pipeline = prepare_draw_pipeline(
        circuit=build_sample_ir(),
        framework="ir",
        style={"theme": "dark"},
        layout=None,
        options={},
    )

    assert pipeline.normalized_style.theme.name == "dark"
    assert pipeline.ir.quantum_wire_count == 2
    assert isinstance(pipeline.layout_engine, LayoutEngine)
    assert pipeline.renderer.backend_name == "matplotlib"
    assert pipeline.paged_scene.pages
    assert not hasattr(pipeline, "adapter")


def test_prepare_draw_pipeline_forwards_options_and_uses_custom_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = pytest.importorskip("quantum_circuit_drawer.adapters.registry")
    circuit = build_sample_ir()
    adapter = _CapturingAdapter(circuit)
    layout = _CapturingLayout()

    monkeypatch.setattr(registry_module, "get_adapter", lambda *args: adapter)

    pipeline = prepare_draw_pipeline(
        circuit={"kind": "input"},
        framework="custom",
        style={"theme": "paper", "font_size": 10.0},
        layout=layout,
        options={"precision": 3, "page_slider": True},
    )

    assert adapter.calls == [
        {
            "circuit": {"kind": "input"},
            "options": {"composite_mode": "compact", "precision": 3, "page_slider": True},
        }
    ]
    assert pipeline.layout_engine is layout
    assert layout.calls[0][0] is circuit
    assert layout.calls[0][1].theme.name == "paper"
    assert layout.calls[0][1].font_size == 10.0


def test_prepare_draw_pipeline_normalizes_style_once_for_default_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer._draw_pipeline as pipeline_module
    import quantum_circuit_drawer.layout.engine as engine_module

    normalize_style_calls = 0
    original_pipeline_normalize_style = pipeline_module.normalize_style
    original_engine_normalize_style = engine_module.normalize_style

    def count_pipeline_normalize_style(style: DrawStyle | Mapping[str, object] | None) -> DrawStyle:
        nonlocal normalize_style_calls
        normalize_style_calls += 1
        return original_pipeline_normalize_style(style)

    def count_engine_normalize_style(style: DrawStyle) -> DrawStyle:
        nonlocal normalize_style_calls
        normalize_style_calls += 1
        return original_engine_normalize_style(style)

    monkeypatch.setattr(pipeline_module, "normalize_style", count_pipeline_normalize_style)
    monkeypatch.setattr(engine_module, "normalize_style", count_engine_normalize_style)

    prepare_draw_pipeline(
        circuit=build_sample_ir(),
        framework="ir",
        style={"theme": "dark"},
        layout=None,
        options={},
    )

    assert normalize_style_calls == 1


def test_draw_pipeline_options_keep_adapter_options_separate_from_view_controls() -> None:
    options = DrawPipelineOptions(
        composite_mode="expand",
        view="3d",
        topology="grid",
        direct=False,
        hover=HoverOptions(show_matrix="always"),
        extra={"precision": 3, "page_slider": True},
    )

    assert options.to_mapping()["hover"] == HoverOptions(show_matrix="always")
    assert options.adapter_options() == {
        "composite_mode": "expand",
        "precision": 3,
        "page_slider": True,
    }


def test_build_draw_request_disables_hover_when_not_interactive() -> None:
    request = build_draw_request(
        circuit=build_sample_ir(),
        hover=HoverOptions(),
        view="3d",
        show=False,
    )

    assert request.pipeline_options.hover.enabled is False
    assert request.pipeline_options.view == "3d"


def test_build_draw_request_keeps_figsize_out_of_pipeline_adapter_options() -> None:
    request = build_draw_request(circuit=build_sample_ir(), figsize=(8.0, 3.0))

    assert request.figsize == (8.0, 3.0)
    assert "figsize" not in request.pipeline_options.adapter_options()


def test_build_draw_request_normalizes_hover_mapping_for_2d_view() -> None:
    request = build_draw_request(
        circuit=build_sample_ir(),
        hover={"show_matrix": "always", "matrix_max_qubits": 1},
        show=False,
    )

    assert request.pipeline_options.hover == HoverOptions(
        enabled=False,
        show_matrix="always",
        matrix_max_qubits=1,
    )


def test_resolve_layout_engine_returns_default_layout_engine_for_none() -> None:
    assert isinstance(resolve_layout_engine(None), LayoutEngine)


def test_resolve_layout_engine_returns_layout_engine_instances_unchanged() -> None:
    layout_engine = LayoutEngine()

    assert resolve_layout_engine(layout_engine) is layout_engine


def test_resolve_layout_engine_accepts_layout_like_objects() -> None:
    layout_like = _CapturingLayout()

    assert resolve_layout_engine(layout_like) is layout_like


def test_resolve_layout_engine_rejects_objects_without_compute() -> None:
    with pytest.raises(LayoutError, match="layout must be None or expose a compute"):
        resolve_layout_engine(object())
