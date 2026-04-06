from __future__ import annotations

import builtins
import sys
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer.adapters._helpers import (
    build_classical_register,
    canonical_gate_spec,
    extract_dependency_types,
    load_optional_dependency,
    sequential_bit_labels,
)
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily


def test_load_optional_dependency_returns_none_when_module_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "missing_quantum_dep":
            raise ModuleNotFoundError(name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert load_optional_dependency("missing_quantum_dep") is None


def test_load_optional_dependency_rejects_imports_that_do_not_register_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "ghost_dep":
            return ModuleType("ghost_dep")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.delitem(sys.modules, "ghost_dep", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match="optional dependency 'ghost_dep' was not loaded"):
        load_optional_dependency("ghost_dep")


def test_extract_dependency_types_returns_only_available_runtime_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    top_level = type("TopLevelType", (), {})
    nested = type("NestedType", (), {})
    fake_module = ModuleType("fake_quantum_module")
    fake_module.TopLevelType = top_level
    fake_module.namespace = SimpleNamespace(NestedType=nested, not_a_type=SimpleNamespace())

    monkeypatch.setitem(sys.modules, "fake_quantum_module", fake_module)

    assert extract_dependency_types(
        "fake_quantum_module",
        ("TopLevelType", "namespace.NestedType", "namespace.missing", "namespace.not_a_type"),
    ) == (top_level, nested)


def test_sequential_bit_labels_build_expected_labels() -> None:
    assert sequential_bit_labels(3, label="alpha") == ("alpha[0]", "alpha[1]", "alpha[2]")


def test_build_classical_register_handles_empty_and_non_empty_bit_labels() -> None:
    assert build_classical_register(()) == ([], ())

    wires, bit_targets = build_classical_register(("beta[0]", "beta[1]"), label="beta")

    assert len(wires) == 1
    assert wires[0].label == "beta"
    assert wires[0].metadata["bundle_size"] == 2
    assert bit_targets == (("c0", "beta[0]"), ("c0", "beta[1]"))


@pytest.mark.parametrize(
    ("raw_name", "expected_label", "expected_family"),
    [
        ("PhaseShift", "P", CanonicalGateFamily.P),
        ("u1", "P", CanonicalGateFamily.P),
        ("U3", "U", CanonicalGateFamily.U),
        ("u2", "U2", CanonicalGateFamily.U2),
        ("Identity", "I", CanonicalGateFamily.I),
        ("id", "I", CanonicalGateFamily.I),
        ("ResetChannel", "RESET", CanonicalGateFamily.RESET),
        ("delay", "DELAY", CanonicalGateFamily.DELAY),
        ("Adjoint(S)", "Sdg", CanonicalGateFamily.SDG),
        ("Adjoint(T)", "Tdg", CanonicalGateFamily.TDG),
        ("Adjoint(SX)", "SXdg", CanonicalGateFamily.SXDG),
        ("RXXGate", "RXX", CanonicalGateFamily.RXX),
        ("RYYGate", "RYY", CanonicalGateFamily.RYY),
        ("RZZGate", "RZZ", CanonicalGateFamily.RZZ),
        ("RZXGate", "RZX", CanonicalGateFamily.RZX),
        ("FSimGate", "FSIM", CanonicalGateFamily.FSIM),
        ("ECRGate", "ECR", CanonicalGateFamily.ECR),
        ("iswap", "iSWAP", CanonicalGateFamily.ISWAP),
    ],
)
def test_canonical_gate_spec_maps_additional_gate_aliases(
    raw_name: str,
    expected_label: str,
    expected_family: CanonicalGateFamily,
) -> None:
    canonical_gate = canonical_gate_spec(raw_name)

    assert canonical_gate.label == expected_label
    assert canonical_gate.family is expected_family


def test_canonical_gate_spec_compacts_unknown_gate_names() -> None:
    canonical_gate = canonical_gate_spec("MySuperLongGate")

    assert canonical_gate.label == "MYSUPE"
    assert canonical_gate.family is CanonicalGateFamily.CUSTOM
