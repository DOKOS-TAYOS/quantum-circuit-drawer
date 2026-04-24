from __future__ import annotations

import numpy as np
import pytest

from quantum_circuit_drawer.utils.formatting import (
    format_gate_name,
    format_gate_name_mathtext,
    format_parameter,
    format_parameter_text_mathtext,
    format_parameters,
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
