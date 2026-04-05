from __future__ import annotations

import pytest

from quantum_circuit_drawer.adapters._helpers import canonical_gate_spec
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily


@pytest.mark.parametrize(
    ("raw_name", "expected_label", "expected_family"),
    [
        ("PhaseShift", "P", CanonicalGateFamily.P),
        ("u1", "P", CanonicalGateFamily.P),
        ("U3", "U", CanonicalGateFamily.U),
        ("u2", "U2", CanonicalGateFamily.U2),
        ("Adjoint(S)", "Sdg", CanonicalGateFamily.SDG),
        ("Adjoint(T)", "Tdg", CanonicalGateFamily.TDG),
        ("Adjoint(SX)", "SXdg", CanonicalGateFamily.SXDG),
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