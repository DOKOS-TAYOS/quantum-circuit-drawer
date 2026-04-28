from __future__ import annotations

import numpy as np
import pytest

from quantum_circuit_drawer.utils.formatting import (
    format_gate_name,
    format_gate_name_mathtext,
    format_gate_text_block,
    format_parameter,
    format_parameter_text,
    format_parameter_text_mathtext,
    format_parameters,
    format_visible_label,
    format_visible_label_mathtext,
)


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("Sdg", "Sdg"),
        ("SXdg", "SXdg"),
        ("iSWAP", "iSWAP"),
        ("u2", "U2"),
        ("rx", "RX"),
        ("PROBABILITY", "Prob"),
        ("PROB", "Prob"),
        ("PROBS", "Prob"),
        ("EXPVAL", "ExpVal"),
        ("COUNTS", "Counts"),
        ("IF", "if"),
        ("IF/ELSE", "if/else"),
        ("SWITCH", "switch"),
        ("WHILE", "while"),
        ("FOR", "for"),
        ("LOOP", "loop"),
        ("Circuit - 42", "circuit 42"),
        ("CircuitOperation", "CircuitOp"),
        ("controlled-swap", "controlled-swap"),
    ],
)
def test_format_gate_name_normalizes_expected_labels(raw_name: str, expected: str) -> None:
    assert format_gate_name(raw_name) == expected


def test_format_parameter_formats_real_numbers_and_numpy_scalars() -> None:
    assert format_parameter(3) == "3"
    assert format_parameter(3.125) == "3.12"
    assert format_parameter(np.float64(2.0)) == "2"
    assert format_parameter("theta") == "theta"


def test_format_parameters_joins_formatted_values() -> None:
    assert format_parameters([np.float64(2.0), 0.125, "phi"]) == "2, 0.125, phi"


def test_format_gate_name_mathtext_wraps_upright_gate_labels() -> None:
    assert format_gate_name_mathtext("rzz") == r"$\mathrm{RZZ}$"
    assert format_gate_name_mathtext("iswap") == r"$\mathrm{iSWAP}$"


def test_format_parameter_text_mathtext_formats_numeric_and_symbolic_values() -> None:
    assert format_parameter_text_mathtext("0.125") == r"$0.125$"
    assert format_parameter_text_mathtext("theta, phi") == r"$\theta, \phi$"


def test_format_visible_label_mathtext_escapes_generic_circuit_text() -> None:
    assert format_visible_label_mathtext("q0") == r"$\mathrm{q0}$"
    assert format_visible_label_mathtext("if c[0]=1") == r"$\mathrm{if\ c[0]=1}$"


def test_format_visible_label_auto_keeps_generic_circuit_text_plain() -> None:
    assert format_visible_label("q0", use_mathtext="auto") == "q0"
    assert format_visible_label("if c[0]=1", use_mathtext="auto") == "if c[0]=1"


def test_format_parameter_text_auto_formats_symbolic_parameters_only() -> None:
    assert format_parameter_text("theta, phi", use_mathtext="auto") == r"$\theta, \phi$"
    assert format_parameter_text("0.125", use_mathtext="auto") == "0.125"


def test_format_gate_text_block_auto_keeps_gate_label_plain_and_formats_symbolic_subtitle() -> None:
    assert format_gate_text_block("RX", "theta", use_mathtext="auto") == "RX\n$\\theta$"
    assert format_gate_text_block("RX", "0.5", use_mathtext="auto") == "RX\n0.5"
