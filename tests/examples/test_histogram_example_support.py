from __future__ import annotations

import importlib

from quantum_circuit_drawer import HistogramDrawStyle, HistogramKind, HistogramSort


def test_histogram_binary_order_demo_uses_full_counts_payload() -> None:
    module = importlib.import_module("examples.histogram_binary_order")
    counts = module.build_counts_data()
    config = module.build_config(output=None, show=False)

    assert len(counts) == 16
    assert counts["0000"] == 41
    assert counts["1111"] == 95
    assert config.data.kind is HistogramKind.COUNTS
    assert config.view.sort is HistogramSort.STATE


def test_histogram_interactive_large_demo_covers_full_seven_bit_space() -> None:
    module = importlib.import_module("examples.histogram_interactive_large")
    counts = module.build_counts_data()
    config = module.build_config(output=None, show=False)

    assert len(counts) == 128
    assert counts["0000000"] >= 3
    assert counts["1111111"] >= 3
    assert config.appearance.show_uniform_reference is True


def test_histogram_quasi_demo_uses_negative_values_and_soft_style() -> None:
    module = importlib.import_module("examples.histogram_quasi")
    distribution = module.build_quasi_distribution()
    config = module.build_config(output=None, show=False)

    assert any(value < 0 for value in distribution.values())
    assert config.data.kind is HistogramKind.QUASI
    assert config.appearance.draw_style is HistogramDrawStyle.SOFT


def test_histogram_result_index_demo_selects_the_second_payload() -> None:
    module = importlib.import_module("examples.histogram_result_index")
    payload = module.build_payload()
    config = module.build_config(output=None, show=False)

    assert len(payload) == 3
    assert payload[1]["11"] == 23
    assert config.data.result_index == 1
