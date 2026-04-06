from __future__ import annotations

import numpy as np
import pytest

from quantum_circuit_drawer.utils.formatting import (
    format_gate_name,
    format_parameter,
    format_parameters,
)


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("Sdg", "Sdg"),
        ("SXdg", "SXdg"),
        ("iSWAP", "iSWAP"),
        ("u2", "U2"),
        ("rx", "RX"),
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
