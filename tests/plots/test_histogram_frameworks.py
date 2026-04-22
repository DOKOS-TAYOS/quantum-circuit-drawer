from __future__ import annotations

import matplotlib.pyplot as plt

from quantum_circuit_drawer import HistogramKind
from quantum_circuit_drawer.histogram import plot_histogram
from tests.support import build_public_histogram_config


class FakeCudaqSampleResult:
    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts
        self.register_names = ["__global__"]

    def items(self) -> list[tuple[str, int]]:
        return list(self._counts.items())


class FakeCirqResult:
    def __init__(self, measurements: dict[str, list[list[int]]]) -> None:
        self.measurements = measurements


class FakeMyQLMState:
    def __init__(self, value: int) -> None:
        self.value = value


class FakeMyQLMSample:
    def __init__(self, *, state: object, probability: float) -> None:
        self.state = state
        self.probability = probability


class FakeMyQLMResult:
    def __init__(self, *, raw_data: tuple[FakeMyQLMSample, ...], nbqbits: int) -> None:
        self.raw_data = raw_data
        self.nbqbits = nbqbits


def test_plot_histogram_accepts_cudaq_sample_result_like_objects() -> None:
    result = plot_histogram(
        FakeCudaqSampleResult({"00": 6, "11": 2}),
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("00", "11")
    assert result.values == (6.0, 2.0)

    plt.close(result.figure)


def test_plot_histogram_accepts_cirq_like_measurement_results_with_multiple_registers() -> None:
    result = plot_histogram(
        FakeCirqResult(
            measurements={
                "alpha": [[0, 1], [1, 0], [1, 0]],
                "beta": [[1], [0], [0]],
            }
        ),
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("01 1", "10 0")
    assert result.values == (1.0, 2.0)

    plt.close(result.figure)


def test_plot_histogram_accepts_probability_vectors_from_framework_outputs() -> None:
    result = plot_histogram(
        [0.125, 0.375, 0.25, 0.25],
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.QUASI
    assert result.state_labels == ("00", "01", "10", "11")
    assert result.values == (0.125, 0.375, 0.25, 0.25)

    plt.close(result.figure)


def test_plot_histogram_accepts_single_wire_sample_vectors_from_framework_outputs() -> None:
    result = plot_histogram(
        [0, 1, 1, 0, 1],
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("0", "1")
    assert result.values == (2.0, 3.0)

    plt.close(result.figure)


def test_plot_histogram_accepts_multi_wire_sample_matrices_from_framework_outputs() -> None:
    result = plot_histogram(
        [[0, 1], [1, 1], [1, 1], [0, 1]],
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("01", "11")
    assert result.values == (2.0, 2.0)

    plt.close(result.figure)


def test_plot_histogram_accepts_myqlm_result_like_raw_data() -> None:
    result = plot_histogram(
        FakeMyQLMResult(
            raw_data=(
                FakeMyQLMSample(state=FakeMyQLMState(1), probability=2.0),
                FakeMyQLMSample(state=FakeMyQLMState(3), probability=6.0),
            ),
            nbqbits=2,
        ),
        config=build_public_histogram_config(show=False),
    )

    assert result.kind is HistogramKind.COUNTS
    assert result.state_labels == ("01", "11")
    assert result.values == (2.0, 6.0)

    plt.close(result.figure)


def test_plot_histogram_result_index_still_selects_array_like_entries() -> None:
    result = plot_histogram(
        (
            [0.2, 0.8],
            {"0": 4, "1": 1},
        ),
        config=build_public_histogram_config(show=False, result_index=0),
    )

    assert result.kind is HistogramKind.QUASI
    assert result.state_labels == ("0", "1")
    assert result.values == (0.2, 0.8)

    plt.close(result.figure)
