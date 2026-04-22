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
    assert "compact output boxes" in frameworks_reference
    assert "materialized `.qtape`, `.tape`, or `._tape`" in troubleshooting_reference
    assert "does not call `construct()`" in troubleshooting_reference
    assert "compact output boxes" in troubleshooting_reference
    assert "wrappers with a materialized tape" in installation_reference


def test_pennylane_docs_describe_deterministic_composite_observable_fallbacks() -> None:
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")

    assert "deterministic class-based or native-type fallback labels" in frameworks_reference
    assert "deterministic fallback labels instead of a vague generic box name" in (
        troubleshooting_reference
    )


def test_framework_docs_describe_semantic_consolidation_scope_for_current_and_future_backends() -> (
    None
):
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")
    changelog_reference = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "All built-in framework adapters now use the richer semantic adapter path." in (
        frameworks_reference
    )
    assert "legacy `to_ir(...)` route remains a supported extension point" in (frameworks_reference)
    assert "all built-in framework adapters use the richer semantic-adapter path internally" in (
        troubleshooting_reference
    )
    assert "Migrated the Qiskit adapter onto the shared semantic path" in changelog_reference


def test_qiskit_docs_describe_compact_control_flow_support() -> None:
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")

    assert "compact native boxes for `if_else`, `switch_case`, `for_loop`, and `while_loop`" in (
        frameworks_reference
    )
    assert "does not execute branches or unroll loops for display" in troubleshooting_reference


def test_myqlm_docs_describe_break_and_classic_classical_box_support() -> None:
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")

    assert "drawable `BREAK` / `CLASSIC` classical boxes" in frameworks_reference
    assert "raw native formula is preserved instead of raising" in frameworks_reference
    assert "compact classical `BREAK` / `CLASSIC` boxes" in troubleshooting_reference
    assert "raw formula in hover instead of raising" in troubleshooting_reference


def test_myqlm_docs_describe_quantum_reset_metadata_and_classical_only_limit() -> None:
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")
    changelog_reference = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "quantum resets keep drawing even when MyQLM attaches extra classical metadata" in (
        frameworks_reference
    )
    assert (
        "classical-only resets without qubit targets still remain outside the supported subset"
        in (frameworks_reference)
    )
    assert "qubit-targeted `RESET` operations keep rendering as quantum resets" in (
        troubleshooting_reference
    )
    assert "classical-only reset" in troubleshooting_reference
    assert "transversal compatibility polish" in changelog_reference


def test_cudaq_docs_describe_controlled_swap_support() -> None:
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")

    assert "Controlled `swap` now renders as a compact controlled `SWAP` box" in (
        frameworks_reference
    )
    assert "controlled `swap` as a compact controlled `SWAP` box" in troubleshooting_reference
    assert "CUDA-Q now supports `reset`" in troubleshooting_reference
    assert "controlled `swap`" in troubleshooting_reference


def test_cudaq_docs_describe_structured_control_flow_support() -> None:
    frameworks_reference = Path("docs/frameworks.md").read_text(encoding="utf-8")
    troubleshooting_reference = Path("docs/troubleshooting.md").read_text(encoding="utf-8")

    assert (
        "Structured `cc.if`, `scf.if`, `scf.for`, and `cc.loop` now render as compact descriptive boxes"
        in (frameworks_reference)
    )
    assert "structured control flow (`cc.if`, `scf.if`, `scf.for`, `cc.loop`)" in (
        troubleshooting_reference
    )
    assert "does not execute branches or unroll loops for display" in troubleshooting_reference


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
