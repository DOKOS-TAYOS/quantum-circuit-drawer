from __future__ import annotations

import pytest

from quantum_circuit_drawer.plots.histogram_models import (
    HistogramCompareConfig,
    HistogramConfig,
)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"kind": "density"}, "kind must be one of: auto, counts, quasi"),
        ({"mode": "live"}, "mode must be one of: auto, static, interactive"),
        ({"sort": "weight"}, "sort must be one of: state, state_desc, value_desc, value_asc"),
        ({"draw_style": "filled"}, "draw_style must be one of: solid, outline, soft"),
        ({"state_label_mode": "hex"}, "state_label_mode must be one of: binary, decimal"),
        ({"qubits": [0, 1]}, "qubits must be a tuple of non-negative integers"),
        ({"qubits": (0, -1)}, "qubits must be a tuple of non-negative integers"),
        ({"qubits": (0, 0)}, "qubits must not contain duplicates"),
        ({"show_uniform_reference": 1}, "show_uniform_reference must be a boolean"),
        ({"hover": 1}, "hover must be a boolean"),
        ({"show": 1}, "show must be a boolean"),
        ({"figsize": (4.0,)}, "figsize must be a 2-item tuple of positive numbers"),
    ],
)
def test_histogram_config_rejects_invalid_public_values(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        HistogramConfig(**kwargs)


def test_histogram_compare_config_rejects_unknown_sort() -> None:
    with pytest.raises(ValueError, match="sort must be one of: state, state_desc, delta_desc"):
        HistogramCompareConfig(sort="weight")
