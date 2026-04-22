from __future__ import annotations

from collections.abc import Callable

import pytest

from quantum_circuit_drawer import OutputOptions
from quantum_circuit_drawer.plots.histogram_models import (
    HistogramAppearanceOptions,
    HistogramCompareConfig,
    HistogramCompareOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramViewOptions,
)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: HistogramConfig(data=HistogramDataOptions(kind="density")),  # type: ignore[arg-type]
            "kind must be one of: auto, counts, quasi",
        ),
        (
            lambda: HistogramConfig(view=HistogramViewOptions(mode="live")),  # type: ignore[arg-type]
            "mode must be one of: auto, static, interactive",
        ),
        (
            lambda: HistogramConfig(view=HistogramViewOptions(sort="weight")),  # type: ignore[arg-type]
            "sort must be one of: state, state_desc, value_desc, value_asc",
        ),
        (
            lambda: HistogramConfig(
                appearance=HistogramAppearanceOptions(draw_style="filled")  # type: ignore[arg-type]
            ),
            "draw_style must be one of: solid, outline, soft",
        ),
        (
            lambda: HistogramConfig(
                view=HistogramViewOptions(state_label_mode="hex")  # type: ignore[arg-type]
            ),
            "state_label_mode must be one of: binary, decimal",
        ),
        (
            lambda: HistogramConfig(data=HistogramDataOptions(qubits=[0, 1])),  # type: ignore[arg-type]
            "qubits must be a tuple of non-negative integers",
        ),
        (
            lambda: HistogramConfig(data=HistogramDataOptions(qubits=(0, -1))),
            "qubits must be a tuple of non-negative integers",
        ),
        (
            lambda: HistogramConfig(data=HistogramDataOptions(qubits=(0, 0))),
            "qubits must not contain duplicates",
        ),
        (
            lambda: HistogramConfig(
                appearance=HistogramAppearanceOptions(show_uniform_reference=1)  # type: ignore[arg-type]
            ),
            "show_uniform_reference must be a boolean",
        ),
        (
            lambda: HistogramConfig(
                appearance=HistogramAppearanceOptions(hover=1)  # type: ignore[arg-type]
            ),
            "hover must be a boolean",
        ),
        (
            lambda: HistogramConfig(output=OutputOptions(show=1)),  # type: ignore[arg-type]
            "show must be a boolean",
        ),
        (
            lambda: HistogramConfig(output=OutputOptions(figsize=(4.0,))),
            "figsize must be a 2-item tuple of positive numbers",
        ),
    ],
)
def test_histogram_config_rejects_invalid_public_values(
    factory: Callable[[], object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


def test_histogram_compare_config_rejects_unknown_sort() -> None:
    with pytest.raises(ValueError, match="sort must be one of: state, state_desc, delta_desc"):
        HistogramCompareConfig(compare=HistogramCompareOptions(sort="weight"))  # type: ignore[arg-type]


def test_histogram_compare_config_rejects_non_boolean_hover() -> None:
    with pytest.raises(ValueError, match="hover must be a boolean"):
        HistogramCompareConfig(compare=HistogramCompareOptions(hover=1))  # type: ignore[arg-type]
