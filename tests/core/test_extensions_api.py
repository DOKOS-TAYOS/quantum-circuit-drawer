from __future__ import annotations

import importlib

import matplotlib.pyplot as plt
import pytest

import quantum_circuit_drawer.adapters as adapters_api
from quantum_circuit_drawer import DrawMode, draw_quantum_circuit
from quantum_circuit_drawer.adapters.base import BaseAdapter
from quantum_circuit_drawer.adapters.registry import AdapterRegistry
from quantum_circuit_drawer.exceptions import LayoutError
from quantum_circuit_drawer.ir.circuit import CircuitIR
from quantum_circuit_drawer.ir.semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
)
from quantum_circuit_drawer.layout import LayoutEngine, LayoutEngine3D
from quantum_circuit_drawer.layout.scene import LayoutScene
from quantum_circuit_drawer.layout.scene_3d import LayoutScene3D
from quantum_circuit_drawer.style import DrawStyle
from quantum_circuit_drawer.typing import LayoutEngine3DLike, LayoutEngineLike
from tests.support import (
    assert_figure_has_visible_content,
    build_public_draw_config,
    build_sample_ir,
)


class _CustomCircuit:
    pass


class _ExtensionAdapter(BaseAdapter):
    framework_name = "extension_demo"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return isinstance(circuit, _CustomCircuit)

    def to_ir(self, circuit: object, options: dict[str, object] | None = None) -> CircuitIR:
        del circuit, options
        return build_sample_ir()


class _ReplacementExtensionAdapter(_ExtensionAdapter):
    pass


class _SemanticExtensionAdapter(BaseAdapter):
    framework_name = "semantic_extension_demo"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return isinstance(circuit, _CustomCircuit)

    def to_ir(self, circuit: object, options: dict[str, object] | None = None) -> CircuitIR:
        del circuit, options
        raise AssertionError("legacy to_ir() should not be used for semantic adapters")

    def to_semantic_ir(
        self,
        circuit: object,
        options: dict[str, object] | None = None,
    ) -> SemanticCircuitIR:
        del circuit, options
        sample_ir = build_sample_ir()
        return SemanticCircuitIR(
            quantum_wires=sample_ir.quantum_wires,
            classical_wires=sample_ir.classical_wires,
            layers=[
                SemanticLayerIR(
                    operations=[
                        SemanticOperationIR(
                            kind=operation.kind,
                            name=operation.name,
                            target_wires=operation.target_wires,
                            control_wires=operation.control_wires,
                            classical_conditions=operation.classical_conditions,
                            parameters=operation.parameters,
                            label=operation.label,
                            canonical_family=operation.canonical_family,
                            classical_target=getattr(operation, "classical_target", None),
                            annotations=("native: semantic_extension_demo",),
                        )
                        for operation in layer.operations
                    ],
                    metadata=layer.metadata,
                )
                for layer in sample_ir.layers
            ],
            name=sample_ir.name,
            metadata={"framework": "semantic_extension_demo"},
        )


class _EmptyNameAdapter(BaseAdapter):
    framework_name = ""

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return False

    def to_ir(self, circuit: object, options: dict[str, object] | None = None) -> CircuitIR:
        del circuit, options
        return build_sample_ir()


class _ExampleLayout2D(LayoutEngineLike):
    def compute(self, circuit: CircuitIR, style: DrawStyle) -> LayoutScene:
        return LayoutEngine().compute(circuit, style)


class _ExampleLayout3D(LayoutEngine3DLike):
    def compute(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        topology_name: object,
        direct: bool,
        hover_enabled: bool,
    ) -> LayoutScene3D:
        return LayoutEngine3D().compute(
            circuit,
            style,
            topology_name=topology_name,
            direct=direct,
            hover_enabled=hover_enabled,
        )


def test_adapters_module_exports_public_extension_helpers() -> None:
    assert adapters_api.BaseAdapter is BaseAdapter
    assert adapters_api.AdapterRegistry is AdapterRegistry
    assert callable(adapters_api.register_adapter)
    assert callable(adapters_api.unregister_adapter)
    assert callable(adapters_api.available_frameworks)
    assert callable(adapters_api.detect_framework_name)


def test_register_adapter_adds_and_removes_framework_on_global_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    monkeypatch.setattr(registry_module, "registry", registry)

    adapters_api.register_adapter(_ExtensionAdapter)

    assert "extension_demo" in adapters_api.available_frameworks()
    assert adapters_api.detect_framework_name(_CustomCircuit()) == "extension_demo"

    adapters_api.unregister_adapter("extension_demo")

    assert "extension_demo" not in adapters_api.available_frameworks()


def test_register_adapter_requires_replace_for_duplicate_framework(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    monkeypatch.setattr(registry_module, "registry", registry)

    adapters_api.register_adapter(_ExtensionAdapter)

    with pytest.raises(ValueError, match="framework 'extension_demo' is already registered"):
        adapters_api.register_adapter(_ReplacementExtensionAdapter)


def test_register_adapter_replace_true_swaps_existing_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    monkeypatch.setattr(registry_module, "registry", registry)
    adapters_api.register_adapter(_ExtensionAdapter)

    adapters_api.register_adapter(_ReplacementExtensionAdapter, replace=True)

    assert isinstance(registry.get("extension_demo"), _ReplacementExtensionAdapter)


def test_unregister_adapter_missing_ok_prevents_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    monkeypatch.setattr(registry_module, "registry", registry)

    adapters_api.unregister_adapter("missing_framework", missing_ok=True)


def test_register_adapter_validates_type_and_framework_name() -> None:
    with pytest.raises(TypeError, match="must be a BaseAdapter subclass"):
        AdapterRegistry().register(object)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="framework_name must be a non-empty string"):
        AdapterRegistry().register(_EmptyNameAdapter)


def test_registering_custom_adapter_before_first_lookup_keeps_builtins_available() -> None:
    registry = AdapterRegistry()

    registry.register(_ExtensionAdapter)

    assert registry.available_frameworks() == (
        "extension_demo",
        "ir",
        "qiskit",
        "cirq",
        "pennylane",
        "myqlm",
        "cudaq",
    )


def test_registering_builtin_name_without_replace_fails_even_before_defaults_loaded() -> None:
    registry = AdapterRegistry()

    with pytest.raises(ValueError, match="framework 'qiskit' is already registered"):
        registry.register(_BuiltinNamedAdapter)


class _BuiltinNamedAdapter(BaseAdapter):
    framework_name = "qiskit"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return False

    def to_ir(self, circuit: object, options: dict[str, object] | None = None) -> CircuitIR:
        del circuit, options
        return build_sample_ir()


def test_custom_adapter_draws_via_explicit_framework(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    monkeypatch.setattr(registry_module, "registry", registry)
    adapters_api.register_adapter(_ExtensionAdapter)

    result = draw_quantum_circuit(
        _CustomCircuit(),
        config=build_public_draw_config(
            framework="extension_demo",
            mode=DrawMode.FULL,
            show=False,
        ),
    )

    assert result.detected_framework == "extension_demo"
    assert_figure_has_visible_content(result.primary_figure)

    plt.close(result.primary_figure)


def test_custom_semantic_adapter_draws_via_explicit_framework(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    monkeypatch.setattr(registry_module, "registry", registry)
    adapters_api.register_adapter(_SemanticExtensionAdapter)

    result = draw_quantum_circuit(
        _CustomCircuit(),
        config=build_public_draw_config(
            framework="semantic_extension_demo",
            mode=DrawMode.FULL,
            show=False,
        ),
    )

    assert result.detected_framework == "semantic_extension_demo"
    assert_figure_has_visible_content(result.primary_figure)

    plt.close(result.primary_figure)


def test_custom_layout_2d_is_accepted_through_draw_config() -> None:
    result = draw_quantum_circuit(
        build_sample_ir(),
        config=build_public_draw_config(
            layout=_ExampleLayout2D(),
            mode=DrawMode.FULL,
            show=False,
        ),
    )

    assert_figure_has_visible_content(result.primary_figure)

    plt.close(result.primary_figure)


def test_custom_layout_3d_is_accepted_through_draw_config() -> None:
    result = draw_quantum_circuit(
        build_sample_ir(),
        config=build_public_draw_config(
            layout=_ExampleLayout3D(),
            view="3d",
            mode=DrawMode.FULL,
            show=False,
        ),
    )

    assert_figure_has_visible_content(result.primary_figure)

    plt.close(result.primary_figure)


def test_invalid_custom_layout_3d_still_fails_with_clear_error() -> None:
    with pytest.raises(LayoutError, match="layout must be None or expose a compute"):
        draw_quantum_circuit(
            build_sample_ir(),
            config=build_public_draw_config(
                layout=object(),
                view="3d",
                mode=DrawMode.FULL,
                show=False,
            ),
        )
