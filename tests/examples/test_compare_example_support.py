from __future__ import annotations

import importlib
from importlib.util import find_spec

import pytest


def test_compare_histograms_ideal_vs_sampled_demo_uses_delta_sort() -> None:
    module = importlib.import_module("examples.compare_histograms_ideal_vs_sampled")
    ideal, sampled = module.build_inputs()
    config = module.build_config(output=None, show=False)

    assert set(ideal) == set(sampled)
    assert config.compare.left_label == "Ideal"
    assert config.compare.right_label == "Sampled"
    assert config.compare.sort.value == "delta_desc"


def test_compare_histograms_multi_series_demo_labels_all_series() -> None:
    module = importlib.import_module("examples.compare_histograms_multi_series")
    series = module.build_inputs()
    config = module.build_config(output=None, show=False)

    assert len(series) == 4
    assert config.data.top_k == 8
    assert config.compare.series_labels == (
        "Ideal",
        "Noisy sim",
        "Hardware raw",
        "Mitigated",
    )


def test_compare_circuits_qiskit_transpile_demo_enables_hover() -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the compare-circuits builder test")

    module = importlib.import_module("examples.compare_circuits_qiskit_transpile")
    circuit = module.build_source_circuit()
    config = module.build_config(output=None, show=False)

    assert circuit.num_qubits == 3
    assert circuit.num_clbits == 3
    assert config.shared.appearance.hover.enabled is True
    assert config.compare.left_title == "Original"
    assert config.compare.right_title == "Transpiled"


def test_compare_circuits_multi_transpile_demo_exposes_four_titles() -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the multi-transpile builder test")

    module = importlib.import_module("examples.compare_circuits_multi_transpile")
    circuit = module.build_source_circuit()
    config = module.build_config(output=None, show=False)

    assert circuit.num_qubits == 4
    assert config.shared.appearance.hover.enabled is True
    assert config.compare.titles == ("Source", "Opt level 0", "Opt level 1", "Opt level 3")
