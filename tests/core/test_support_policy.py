from __future__ import annotations

import re
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
_PUBLIC_DOC_PATHS: tuple[Path, ...] = (Path("README.md"), *tuple(sorted(Path("docs").glob("*.md"))))
_LOCAL_MARKDOWN_DOC_PATHS: tuple[Path, ...] = (
    Path("README.md"),
    Path("CHANGELOG.md"),
    Path("examples/README.md"),
    *tuple(sorted(Path("docs").glob("*.md"))),
)
_LOCAL_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _markdown_heading_slug(value: str) -> str:
    normalized = re.sub(r"`([^`]+)`", r"\1", value.strip().lower())
    normalized = re.sub(r"<[^>]+>", "", normalized)
    normalized = re.sub(r"[^a-z0-9\s_-]+", "", normalized)
    return re.sub(r"\s+", "-", normalized.strip())


def _markdown_anchors(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _MARKDOWN_HEADING_PATTERN.match(line)
        if match is None:
            continue
        base_anchor = _markdown_heading_slug(match.group(2))
        duplicate_count = counts.get(base_anchor, 0)
        counts[base_anchor] = duplicate_count + 1
        anchors.add(base_anchor if duplicate_count == 0 else f"{base_anchor}-{duplicate_count}")
    return anchors


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


def test_public_docs_describe_openqasm_text_and_file_support() -> None:
    docs_by_path = {
        path: path.read_text(encoding="utf-8")
        for path in (
            Path("README.md"),
            Path("docs/getting-started.md"),
            Path("docs/user-guide.md"),
            Path("docs/api.md"),
            Path("docs/frameworks.md"),
            Path("docs/recipes.md"),
            Path("docs/troubleshooting.md"),
            Path("examples/README.md"),
        )
    }

    for path, text in docs_by_path.items():
        assert "OpenQASM" in text, f"{path} does not mention OpenQASM"
        assert ".qasm" in text, f"{path} does not mention .qasm files"

    combined_text = "\n".join(docs_by_path.values())
    assert 'framework="qasm"' in combined_text
    assert "quantum-circuit-drawer[qiskit]" in combined_text
    assert "OPENQASM" in combined_text


def test_public_markdown_links_reference_existing_local_anchors() -> None:
    headings_by_path = {path: _markdown_anchors(path) for path in _LOCAL_MARKDOWN_DOC_PATHS}
    failures: list[str] = []

    for source_path in _LOCAL_MARKDOWN_DOC_PATHS:
        source_text = source_path.read_text(encoding="utf-8")
        for raw_link in _LOCAL_MARKDOWN_LINK_PATTERN.findall(source_text):
            target, _, anchor = raw_link.partition("#")
            if "://" in target or target.startswith("mailto:"):
                continue
            target_path = source_path if target == "" else (source_path.parent / target)
            normalized_target = target_path.resolve().relative_to(Path.cwd().resolve())
            if normalized_target.suffix.lower() != ".md":
                continue
            if normalized_target not in headings_by_path:
                failures.append(f"{source_path}: {raw_link} points to a missing Markdown file")
                continue
            if anchor and anchor not in headings_by_path[normalized_target]:
                failures.append(f"{source_path}: {raw_link} points to missing anchor #{anchor}")

    assert failures == []


def test_internal_packages_docstrings_mark_compatibility_only_facades() -> None:
    for module_doc in (drawing_doc, managed_doc, plots_doc):
        assert module_doc is not None
        assert "compatibility facade" in module_doc
        assert "not part of the stable public extension contract" in module_doc


@pytest.mark.parametrize("path", _PUBLIC_DOC_PATHS)
def test_public_docs_do_not_use_flat_drawconfig_shortcuts(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    forbidden_patterns = (
        r"DrawConfig\s*\(\s*mode\s*=",
        r"DrawConfig\s*\(\s*view\s*=",
        r"DrawConfig\s*\(\s*show\s*=",
        r"DrawConfig\s*\(\s*hover\s*=",
        r"DrawConfig\s*\(\s*topology_menu\s*=",
    )

    for pattern in forbidden_patterns:
        assert re.search(pattern, text, flags=re.MULTILINE) is None, (
            f"{path} still documents the old flat DrawConfig API via pattern: {pattern}"
        )


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
