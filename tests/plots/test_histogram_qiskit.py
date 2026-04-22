from __future__ import annotations

from collections import Counter

import matplotlib.pyplot as plt
import pytest

from quantum_circuit_drawer import HistogramKind
from quantum_circuit_drawer.histogram import plot_histogram
from tests.support import build_public_histogram_config

pytestmark = [pytest.mark.optional, pytest.mark.integration]

pytest.importorskip("qiskit")


def _qiskit_types() -> tuple[type[object], type[object], type[object], type[object], type[object]]:
    from qiskit.primitives import SamplerResult
    from qiskit.primitives.containers import DataBin
    from qiskit.primitives.containers.bit_array import BitArray
    from qiskit.result import Counts, QuasiDistribution

    return Counts, QuasiDistribution, SamplerResult, DataBin, BitArray


def _build_sampler_result() -> object:
    from qiskit import QuantumCircuit
    from qiskit.primitives import StatevectorSampler

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()
    return StatevectorSampler().run([circuit], shots=128).result()


def test_plot_histogram_accepts_qiskit_counts() -> None:
    Counts, _, _, _, _ = _qiskit_types()

    result = plot_histogram(
        Counts({"00": 5, "11": 3}),
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("00", "11")
    assert result.values == (5.0, 3.0)

    plt.close(result.figure)


def test_plot_histogram_accepts_qiskit_quasi_distribution() -> None:
    _, QuasiDistribution, _, _, _ = _qiskit_types()

    result = plot_histogram(
        QuasiDistribution({0: 0.5, 3: -0.25}),
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.QUASI
    assert result.state_labels == ("00", "11")
    assert result.values == (0.5, -0.25)

    plt.close(result.figure)


def test_plot_histogram_accepts_sampler_result_quasi_dists() -> None:
    _, QuasiDistribution, SamplerResult, _, _ = _qiskit_types()

    sampler_result = SamplerResult(
        quasi_dists=[QuasiDistribution({0: 0.75, 1: 0.25})],
        metadata=[{}],
    )

    result = plot_histogram(
        sampler_result,
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.QUASI
    assert result.state_labels == ("0", "1")
    assert result.values == (0.75, 0.25)

    plt.close(result.figure)


def test_plot_histogram_rejects_sampler_result_index_out_of_range() -> None:
    _, QuasiDistribution, SamplerResult, _, _ = _qiskit_types()

    sampler_result = SamplerResult(
        quasi_dists=[QuasiDistribution({0: 0.75, 1: 0.25})],
        metadata=[{}],
    )

    with pytest.raises(ValueError, match="result_index 1 is out of range"):
        plot_histogram(
            sampler_result,
            config=build_public_histogram_config(show=False, result_index=1),
        )


def test_plot_histogram_accepts_qiskit_primitive_result() -> None:
    primitive_result = _build_sampler_result()

    result = plot_histogram(
        primitive_result,
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert Counter(result.state_labels) == Counter(("00", "11"))
    assert sum(result.values) == pytest.approx(128.0)

    plt.close(result.figure)


def test_plot_histogram_accepts_qiskit_sampler_pub_result() -> None:
    primitive_result = _build_sampler_result()
    sampler_pub_result = primitive_result[0]

    result = plot_histogram(
        sampler_pub_result,
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert Counter(result.state_labels) == Counter(("00", "11"))
    assert sum(result.values) == pytest.approx(128.0)

    plt.close(result.figure)


def test_plot_histogram_accepts_qiskit_bit_array() -> None:
    primitive_result = _build_sampler_result()
    bit_array = primitive_result[0].data.meas

    result = plot_histogram(
        bit_array,
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert Counter(result.state_labels) == Counter(("00", "11"))
    assert sum(result.values) == pytest.approx(128.0)

    plt.close(result.figure)


def test_plot_histogram_requires_data_key_when_data_bin_has_multiple_bit_arrays() -> None:
    _, _, _, DataBin, BitArray = _qiskit_types()

    alpha = BitArray.from_counts({"0": 4})
    beta = BitArray.from_counts({"1": 4})
    data = DataBin(alpha=alpha, beta=beta)

    with pytest.raises(ValueError, match="data_key"):
        plot_histogram(data, config=build_public_histogram_config(show=False))


def test_plot_histogram_uses_data_key_to_select_bit_array_from_data_bin() -> None:
    _, _, _, DataBin, BitArray = _qiskit_types()

    alpha = BitArray.from_counts({"0": 4})
    beta = BitArray.from_counts({"1": 4})
    data = DataBin(alpha=alpha, beta=beta)

    result = plot_histogram(
        data,
        config=build_public_histogram_config(show=False, data_key="beta"),
    )

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("1",)
    assert result.values == (4.0,)

    plt.close(result.figure)
