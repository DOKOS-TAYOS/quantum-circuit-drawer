from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from quantum_circuit_drawer.adapters.cudaq_adapter import CudaqAdapter
from quantum_circuit_drawer.adapters.registry import get_adapter
from quantum_circuit_drawer.drawing import __doc__ as drawing_doc
from quantum_circuit_drawer.exceptions import UnsupportedFrameworkError
from quantum_circuit_drawer.managed import __doc__ as managed_doc
from quantum_circuit_drawer.plots import __doc__ as plots_doc

_SUPPORT_MATRIX_PATHS: tuple[Path, ...] = (
    Path("README.md"),
    Path("docs/installation.md"),
    Path("docs/frameworks.md"),
    Path("docs/troubleshooting.md"),
)


@pytest.mark.parametrize("path", _SUPPORT_MATRIX_PATHS)
def test_support_matrix_docs_publish_the_release_support_levels(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert "Support matrix" in text
    assert "Internal IR" in text
    assert "Qiskit" in text
    assert "Cirq" in text
    assert "PennyLane" in text
    assert "MyQLM" in text
    assert "CUDA-Q" in text
    assert "Strong support" in text
    assert "Best-effort on native Windows" in text
    assert "Scoped adapter + contract support" in text
    assert "Linux/WSL2 only" in text


def test_internal_packages_docstrings_mark_compatibility_only_facades() -> None:
    for module_doc in (drawing_doc, managed_doc, plots_doc):
        assert module_doc is not None
        assert "compatibility facade" in module_doc
        assert "not part of the stable public extension contract" in module_doc


def test_api_and_extension_docs_freeze_internal_facades_outside_public_contract() -> None:
    api_reference = Path("docs/api.md").read_text(encoding="utf-8")
    extensions_reference = Path("docs/extensions.md").read_text(encoding="utf-8")

    assert "Internal compatibility facades" in api_reference
    assert "`quantum_circuit_drawer.ir`" in api_reference
    assert "`lower_semantic_circuit(...)`" in api_reference
    assert "`quantum_circuit_drawer.drawing`" in api_reference
    assert "`quantum_circuit_drawer.managed`" in api_reference
    assert "`quantum_circuit_drawer.plots`" in api_reference
    assert "compatibility facades" in extensions_reference
    assert "not stable extension points" in extensions_reference
    assert "`to_semantic_ir(..., options)` is optional" in extensions_reference
    assert "`lower_semantic_circuit(...)`" in extensions_reference


def test_pennylane_docs_describe_materialized_wrapper_contract() -> None:
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")
    installation_reference = Path("docs/installation.md").read_text(encoding="utf-8")

    assert "materialized `.qtape`, `.tape`, or `._tape`" in frameworks_reference
    assert "does not call `construct()`" in frameworks_reference
    assert "materialized `.qtape`, `.tape`, or `._tape`" in troubleshooting_reference
    assert "does not call `construct()`" in troubleshooting_reference
    assert "wrappers with a materialized tape" in installation_reference


def test_framework_docs_describe_semantic_consolidation_scope_for_current_and_future_backends() -> (
    None
):
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")
    changelog_reference = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "Cirq and PennyLane currently use the richer semantic adapter path." in (
        frameworks_reference
    )
    assert "MyQLM and CUDA-Q continue through the legacy `to_ir(...)` path in this phase." in (
        frameworks_reference
    )
    assert "future semantic migrations" in frameworks_reference
    assert "legacy adapter path" in troubleshooting_reference
    assert "future semantic migrations for MyQLM and CUDA-Q" in changelog_reference


def test_draw_quantum_circuit_reports_cudaq_windows_platform_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_registry = SimpleNamespace(
        get=lambda framework_name: CudaqAdapter(),
        detect_framework_name_from_registered=lambda circuit, *, exclude_framework=None: None,
    )

    monkeypatch.setattr(
        "quantum_circuit_drawer.adapters.registry.registry",
        fake_registry,
    )
    monkeypatch.setattr(
        "quantum_circuit_drawer.adapters.cudaq_adapter.extract_dependency_types",
        lambda module_name, attribute_paths: (),
    )
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"CUDA-Q support is Linux/WSL2-only.*native Windows.*WSL2 or Linux",
    ):
        get_adapter(object(), framework="cudaq")
