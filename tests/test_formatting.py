from __future__ import annotations

from quantum_circuit_drawer.utils.formatting import format_gate_name


def test_format_gate_name_preserves_compact_canonical_gate_labels() -> None:
    assert format_gate_name("Sdg") == "Sdg"
    assert format_gate_name("SXdg") == "SXdg"
    assert format_gate_name("iSWAP") == "iSWAP"
    assert format_gate_name("u2") == "U2"
