from __future__ import annotations

from collections.abc import Mapping

import pytest

from quantum_circuit_drawer.diagnostics import DiagnosticSeverity, RenderDiagnostic
from quantum_circuit_drawer.drawing.pipeline import prepare_draw_pipeline, resolve_layout_engine
from quantum_circuit_drawer.drawing.request import DrawPipelineOptions, build_draw_request
from quantum_circuit_drawer.exceptions import LayoutError
from quantum_circuit_drawer.hover import HoverOptions
from quantum_circuit_drawer.ir.circuit import CircuitIR
from quantum_circuit_drawer.ir.operations import OperationKind
from quantum_circuit_drawer.ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
)
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout import LayoutEngine
from quantum_circuit_drawer.layout.scene import LayoutScene
from quantum_circuit_drawer.style import DrawStyle
from tests.support import build_sample_ir


def _hover_payload_count(scene: object) -> int:
    return sum(
        1
        for item in (
            *scene.gates,
            *scene.controls,
            *scene.connections,
            *scene.swaps,
            *scene.measurements,
        )
        if getattr(item, "hover_data", None) is not None
    )


class _CapturingAdapter:
    def __init__(self, ir: CircuitIR) -> None:
        self._ir = ir
        self.calls: list[dict[str, object]] = []

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        self.calls.append({"circuit": circuit, "options": dict(options or {})})
        return self._ir


class _LegacyFallbackAdapter(_CapturingAdapter):
    framework_name = "legacy_demo"

    def __init__(self, ir: CircuitIR) -> None:
        super().__init__(ir)
        self.semantic_calls: list[dict[str, object]] = []

    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR | None:
        self.semantic_calls.append({"circuit": circuit, "options": dict(options or {})})
        return None


class _SemanticCapturingAdapter:
    framework_name = "semantic_demo"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        del circuit, options
        raise AssertionError("legacy to_ir() should not run for semantic adapters")

    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR:
        self.calls.append({"circuit": circuit, "options": dict(options or {})})
        return SemanticCircuitIR(
            quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0")],
            layers=[
                SemanticLayerIR(
                    operations=[
                        SemanticOperationIR(
                            kind=OperationKind.GATE,
                            name="H",
                            target_wires=("q0",),
                            annotations=("native: semantic_demo",),
                            hover_details=("group: semantic_layer[0]",),
                        )
                    ],
                    metadata={"native_group": "semantic_layer[0]"},
                )
            ],
            metadata={"framework": self.framework_name},
            diagnostics=(
                RenderDiagnostic(
                    code="semantic_demo_info",
                    message="semantic adapter path used",
                    severity=DiagnosticSeverity.INFO,
                ),
            ),
        )


class _SemanticMetadataDuplicatingAdapter(_SemanticCapturingAdapter):
    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR:
        semantic_ir = super().to_semantic_ir(circuit, options=options)
        duplicate_diagnostic = semantic_ir.diagnostics[0]
        semantic_ir.metadata["diagnostics"] = (duplicate_diagnostic,)
        return semantic_ir


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
    import quantum_circuit_drawer.drawing.pipeline as pipeline_module
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
        extra={"precision": 3, "page_slider": True, "explicit_matrices": False},
    )

    assert options.to_mapping()["hover"] == HoverOptions(show_matrix="always")
    assert options.adapter_options() == {
        "composite_mode": "expand",
        "precision": 3,
        "page_slider": True,
        "explicit_matrices": False,
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


def test_build_draw_request_disables_2d_hover_for_notebook_backend_show_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("matplotlib.pyplot.get_backend", lambda: "nbagg")

    request = build_draw_request(
        circuit=build_sample_ir(),
        hover=HoverOptions(),
        show=False,
    )

    assert request.pipeline_options.hover.enabled is False


def test_build_draw_request_disables_explicit_matrices_when_effective_hover_is_disabled() -> None:
    request = build_draw_request(
        circuit=build_sample_ir(),
        hover=HoverOptions(),
        show=False,
    )

    assert request.pipeline_options.hover.enabled is False
    assert request.pipeline_options.adapter_options()["explicit_matrices"] is False


def test_build_draw_request_keeps_explicit_matrices_true_when_explicitly_requested() -> None:
    request = build_draw_request(
        circuit=build_sample_ir(),
        hover=HoverOptions(),
        show=False,
        explicit_matrices=True,
    )

    assert request.pipeline_options.hover.enabled is False
    assert request.pipeline_options.adapter_options()["explicit_matrices"] is True


def test_build_draw_request_preserves_explicit_matrices_false_when_hover_stays_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.request.pyplot_backend_supports_interaction",
        lambda: True,
    )

    request = build_draw_request(
        circuit=build_sample_ir(),
        hover=HoverOptions(),
        show=True,
        explicit_matrices=False,
    )

    assert request.pipeline_options.hover.enabled is True
    assert request.pipeline_options.adapter_options()["explicit_matrices"] is False


def test_build_draw_request_keeps_figsize_out_of_pipeline_adapter_options() -> None:
    request = build_draw_request(circuit=build_sample_ir(), figsize=(8.0, 3.0))

    assert request.figsize == (8.0, 3.0)
    assert "figsize" not in request.pipeline_options.adapter_options()


def test_build_draw_request_rejects_boolean_figsize_entries() -> None:
    with pytest.raises(ValueError, match="figsize must be a 2-item tuple of positive numbers"):
        build_draw_request(circuit=build_sample_ir(), figsize=(True, 3.0))


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


def test_prepare_draw_pipeline_omits_2d_hover_metadata_when_hover_is_disabled() -> None:
    pipeline = prepare_draw_pipeline(
        circuit=build_sample_ir(),
        framework="ir",
        style=None,
        layout=None,
        options={"hover": HoverOptions(enabled=False)},
    )

    assert _hover_payload_count(pipeline.paged_scene) == 0


def test_prepare_draw_pipeline_keeps_2d_hover_metadata_when_hover_is_enabled() -> None:
    pipeline = prepare_draw_pipeline(
        circuit=build_sample_ir(),
        framework="ir",
        style=None,
        layout=None,
        options={"hover": HoverOptions()},
    )

    assert _hover_payload_count(pipeline.paged_scene) > 0


def test_prepare_draw_pipeline_uses_ir_fast_path_without_registry_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.adapters.registry as registry_module

    monkeypatch.setattr(
        registry_module,
        "get_adapter",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("get_adapter should not run")),
    )

    pipeline = prepare_draw_pipeline(
        circuit=build_sample_ir(),
        framework="ir",
        style=None,
        layout=None,
        options={},
    )

    assert pipeline.ir.quantum_wire_count == 2


def test_prepare_draw_pipeline_falls_back_to_legacy_adapter_when_semantic_ir_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.adapters.registry as registry_module

    legacy_ir = build_sample_ir()
    legacy_ir.metadata["framework"] = "legacy_demo"
    adapter = _LegacyFallbackAdapter(legacy_ir)
    monkeypatch.setattr(registry_module, "get_adapter", lambda *args, **kwargs: adapter)

    pipeline = prepare_draw_pipeline(
        circuit={"kind": "legacy"},
        framework="legacy_demo",
        style=None,
        layout=None,
        options={"explicit_matrices": False},
    )

    assert adapter.semantic_calls == [
        {
            "circuit": {"kind": "legacy"},
            "options": {"composite_mode": "compact", "explicit_matrices": False},
        },
        {
            "circuit": {"kind": "legacy"},
            "options": {"composite_mode": "expand", "explicit_matrices": False},
        },
    ]
    assert adapter.calls == [
        {
            "circuit": {"kind": "legacy"},
            "options": {"composite_mode": "compact", "explicit_matrices": False},
        }
    ]
    assert pipeline.detected_framework == "legacy_demo"
    assert pipeline.ir.metadata["framework"] == "legacy_demo"
    assert pipeline.semantic_ir.metadata["framework"] == "legacy_demo"


def test_prepare_draw_pipeline_prefers_semantic_adapter_path_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.adapters.registry as registry_module

    adapter = _SemanticCapturingAdapter()
    monkeypatch.setattr(registry_module, "get_adapter", lambda *args, **kwargs: adapter)

    pipeline = prepare_draw_pipeline(
        circuit={"kind": "semantic"},
        framework="semantic_demo",
        style=None,
        layout=None,
        options={"explicit_matrices": True},
    )

    assert adapter.calls == [
        {
            "circuit": {"kind": "semantic"},
            "options": {"composite_mode": "compact", "explicit_matrices": True},
        },
        {
            "circuit": {"kind": "semantic"},
            "options": {"composite_mode": "expand", "explicit_matrices": True},
        },
    ]
    assert pipeline.detected_framework == "semantic_demo"
    assert pipeline.semantic_ir.metadata["framework"] == "semantic_demo"
    assert pipeline.ir.metadata["framework"] == "semantic_demo"
    assert pipeline.ir.layers[0].metadata["native_group"] == "semantic_layer[0]"
    assert pipeline.ir.layers[0].operations[0].metadata["native_annotations"] == (
        "native: semantic_demo",
    )
    assert pipeline.diagnostics[0].code == "semantic_demo_info"


def test_prepare_draw_pipeline_deduplicates_semantic_diagnostics_from_field_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quantum_circuit_drawer.adapters.registry as registry_module

    adapter = _SemanticMetadataDuplicatingAdapter()
    monkeypatch.setattr(registry_module, "get_adapter", lambda *args, **kwargs: adapter)

    pipeline = prepare_draw_pipeline(
        circuit={"kind": "semantic"},
        framework="semantic_demo",
        style=None,
        layout=None,
        options={},
    )

    assert [diagnostic.code for diagnostic in pipeline.diagnostics] == ["semantic_demo_info"]
