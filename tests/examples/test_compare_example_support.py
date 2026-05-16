from __future__ import annotations

import importlib
from importlib.util import find_spec
from types import SimpleNamespace

import pytest


def test_compare_histograms_ideal_vs_sampled_demo_uses_delta_sort(monkeypatch) -> None:
    module = importlib.import_module("examples.compare_histograms_ideal_vs_sampled")
    ideal, sampled = module.build_inputs()
    captured: dict[str, object] = {}

    monkeypatch.setattr(module, "_parse_args", lambda: (None, False))
    monkeypatch.setattr(
        module,
        "compare_histograms",
        lambda *data, **kwargs: captured.update({"data": data, **kwargs}) or SimpleNamespace(),
    )
    monkeypatch.setattr(module, "release_rendered_result", lambda result: None)

    module.main()

    assert set(ideal) == set(sampled)
    assert captured["left_label"] == "Ideal"
    assert captured["right_label"] == "Sampled"
    assert captured["sort"] == "delta_desc"


def test_compare_histograms_multi_series_demo_labels_all_series(monkeypatch) -> None:
    module = importlib.import_module("examples.compare_histograms_multi_series")
    series = module.build_inputs()
    captured: dict[str, object] = {}

    monkeypatch.setattr(module, "_parse_args", lambda: (None, False))
    monkeypatch.setattr(
        module,
        "compare_histograms",
        lambda *data, **kwargs: captured.update({"data": data, **kwargs}) or SimpleNamespace(),
    )
    monkeypatch.setattr(module, "release_rendered_result", lambda result: None)

    module.main()

    assert len(series) == 4
    assert captured["top_k"] == 8
    assert captured["series_labels"] == (
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
    config = module.build_config()

    assert circuit.num_qubits == 3
    assert circuit.num_clbits == 3
    assert config.shared.appearance.hover.enabled is True


def test_compare_circuits_multi_transpile_demo_exposes_four_titles() -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the multi-transpile builder test")

    module = importlib.import_module("examples.compare_circuits_multi_transpile")
    circuit = module.build_source_circuit()
    config = module.build_config()

    assert circuit.num_qubits == 4
    assert config.shared.appearance.hover.enabled is True
