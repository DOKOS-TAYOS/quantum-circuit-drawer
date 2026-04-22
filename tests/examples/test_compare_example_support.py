from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pytest


def test_parse_compare_example_args_reads_request(monkeypatch: pytest.MonkeyPatch) -> None:
    from examples._compare_shared import CompareExampleRequest, parse_compare_example_args

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compare_example.py",
            "--left-label",
            "Before",
            "--right-label",
            "After",
            "--no-highlight-differences",
            "--no-show-summary",
            "--sort",
            "delta_desc",
            "--top-k",
            "5",
            "--output",
            "compare-demo.png",
            "--figsize",
            "12",
            "5",
            "--no-show",
        ],
    )

    request = parse_compare_example_args(description="Render a compare demo.")

    assert request == CompareExampleRequest(
        left_label="Before",
        right_label="After",
        highlight_differences=False,
        show_summary=False,
        sort="delta_desc",
        top_k=5,
        output=Path("compare-demo.png"),
        show=False,
        figsize=(12.0, 5.0),
    )


def test_render_compare_example_dispatches_circuit_compare(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        render_compare_example,
    )

    from quantum_circuit_drawer import CircuitCompareConfig, CircuitCompareResult

    output = sandbox_tmp_path / "compare-circuits.png"
    compare_calls: list[dict[str, object]] = []

    class _FakeManager:
        def __init__(self) -> None:
            self.window_titles: list[str] = []

        def set_window_title(self, title: str) -> None:
            self.window_titles.append(title)

    class _FakeCanvas:
        def __init__(self) -> None:
            self.manager = _FakeManager()

    class _FakeFigure:
        def __init__(self) -> None:
            self.label = ""
            self.canvas = _FakeCanvas()

        def set_label(self, label: str) -> None:
            self.label = label

    fake_figure = _FakeFigure()

    def fake_compare_circuits(
        left_circuit: object,
        right_circuit: object,
        *,
        left_config: object = None,
        right_config: object = None,
        config: CircuitCompareConfig | None = None,
        axes: object = None,
    ) -> CircuitCompareResult:
        compare_calls.append(
            {
                "left_circuit": left_circuit,
                "right_circuit": right_circuit,
                "left_config": left_config,
                "right_config": right_config,
                "config": config,
                "axes": axes,
            }
        )
        return CircuitCompareResult(
            figure=fake_figure,  # type: ignore[arg-type]
            axes=(object(), object()),  # type: ignore[arg-type]
            left_result=object(),  # type: ignore[arg-type]
            right_result=object(),  # type: ignore[arg-type]
            metrics=object(),  # type: ignore[arg-type]
        )

    monkeypatch.setattr("examples._compare_shared.compare_circuits", fake_compare_circuits)

    request = CompareExampleRequest(
        left_label="Before",
        right_label="After",
        highlight_differences=False,
        show_summary=False,
        sort=None,
        top_k=None,
        output=output,
        show=False,
        figsize=(12.0, 5.0),
    )
    payload = CompareDemoPayload(
        compare_kind="circuits",
        left_data={"kind": "left"},
        right_data={"kind": "right"},
        config=CircuitCompareConfig(show=True),
    )

    render_compare_example(
        payload,
        request=request,
        saved_label="compare-circuits-qiskit-transpile",
    )

    captured = capsys.readouterr()

    assert len(compare_calls) == 1
    assert compare_calls[0]["left_circuit"] == {"kind": "left"}
    assert compare_calls[0]["right_circuit"] == {"kind": "right"}
    assert compare_calls[0]["axes"] is None
    config = compare_calls[0]["config"]
    assert isinstance(config, CircuitCompareConfig)
    assert config.left_title == "Before"
    assert config.right_title == "After"
    assert config.highlight_differences is False
    assert config.show_summary is False
    assert config.output_path == output
    assert config.show is False
    assert config.figsize == (12.0, 5.0)
    assert fake_figure.label == "compare-circuits-qiskit-transpile"
    assert fake_figure.canvas.manager.window_titles == ["compare-circuits-qiskit-transpile"]
    assert f"Saved compare-circuits-qiskit-transpile to {output}" in captured.out


def test_render_compare_example_dispatches_histogram_compare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        render_compare_example,
    )

    from quantum_circuit_drawer import HistogramCompareConfig, HistogramCompareResult

    compare_calls: list[dict[str, object]] = []

    class _FakeManager:
        def set_window_title(self, title: str) -> None:
            del title

    class _FakeCanvas:
        def __init__(self) -> None:
            self.manager = _FakeManager()

    class _FakeFigure:
        def __init__(self) -> None:
            self.canvas = _FakeCanvas()

        def set_label(self, label: str) -> None:
            del label

    def fake_compare_histograms(
        left_data: object,
        right_data: object,
        *,
        config: HistogramCompareConfig | None = None,
        ax: object = None,
    ) -> HistogramCompareResult:
        compare_calls.append(
            {
                "left_data": left_data,
                "right_data": right_data,
                "config": config,
                "ax": ax,
            }
        )
        return HistogramCompareResult(
            figure=_FakeFigure(),  # type: ignore[arg-type]
            axes=object(),  # type: ignore[arg-type]
            kind=object(),  # type: ignore[arg-type]
            state_labels=("00",),
            left_values=(0.5,),
            right_values=(0.5,),
            delta_values=(0.0,),
            metrics=object(),  # type: ignore[arg-type]
            qubits=None,
        )

    monkeypatch.setattr("examples._compare_shared.compare_histograms", fake_compare_histograms)

    request = CompareExampleRequest(
        left_label="Ideal",
        right_label="Sampled",
        highlight_differences=None,
        show_summary=None,
        sort="delta_desc",
        top_k=4,
        output=None,
        show=False,
        figsize=(11.0, 5.0),
    )
    payload = CompareDemoPayload(
        compare_kind="histograms",
        left_data={"00": 12},
        right_data={"00": 10},
        config=HistogramCompareConfig(show=True),
    )

    render_compare_example(
        payload,
        request=request,
        saved_label="compare-histograms-ideal-vs-sampled",
    )

    assert len(compare_calls) == 1
    assert compare_calls[0]["left_data"] == {"00": 12}
    assert compare_calls[0]["right_data"] == {"00": 10}
    assert compare_calls[0]["ax"] is None
    config = compare_calls[0]["config"]
    assert isinstance(config, HistogramCompareConfig)
    assert config.left_label == "Ideal"
    assert config.right_label == "Sampled"
    assert config.sort.value == "delta_desc"
    assert config.top_k == 4
    assert config.show is False
    assert config.figsize == (11.0, 5.0)


def test_render_compare_example_closes_rendered_figure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        render_compare_example,
    )

    from quantum_circuit_drawer import CircuitCompareConfig, CircuitCompareResult

    def fake_compare_circuits(
        left_circuit: object,
        right_circuit: object,
        *,
        left_config: object = None,
        right_config: object = None,
        config: CircuitCompareConfig | None = None,
        axes: object = None,
    ) -> CircuitCompareResult:
        del left_circuit, right_circuit, left_config, right_config, config, axes
        figure, subplot_axes = plt.subplots(1, 2)
        return CircuitCompareResult(
            figure=figure,
            axes=(subplot_axes[0], subplot_axes[1]),
            left_result=object(),  # type: ignore[arg-type]
            right_result=object(),  # type: ignore[arg-type]
            metrics=object(),  # type: ignore[arg-type]
        )

    monkeypatch.setattr("examples._compare_shared.compare_circuits", fake_compare_circuits)

    request = CompareExampleRequest(output=None, show=False, figsize=(12.0, 5.0))
    payload = CompareDemoPayload(
        compare_kind="circuits",
        left_data={"kind": "left"},
        right_data={"kind": "right"},
        config=CircuitCompareConfig(show=False),
    )

    plt.close("all")
    try:
        render_compare_example(
            payload,
            request=request,
            saved_label="compare-circuits-qiskit-transpile",
        )

        assert tuple(plt.get_fignums()) == ()
    finally:
        plt.close("all")


def test_render_compare_example_ignores_destroyed_window_title_errors_and_closes_figure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        render_compare_example,
    )

    from quantum_circuit_drawer import CircuitCompareConfig, CircuitCompareResult

    class TclError(RuntimeError):
        pass

    figure, subplot_axes = plt.subplots(1, 2)
    manager = figure.canvas.manager
    assert manager is not None
    titles: list[str] = []

    def failing_set_window_title(title: str) -> None:
        titles.append(title)
        raise TclError('can\'t invoke "wm" command: application has been destroyed')

    monkeypatch.setattr(manager, "set_window_title", failing_set_window_title)

    def fake_compare_circuits(
        left_circuit: object,
        right_circuit: object,
        *,
        left_config: object = None,
        right_config: object = None,
        config: CircuitCompareConfig | None = None,
        axes: object = None,
    ) -> CircuitCompareResult:
        del left_circuit, right_circuit, left_config, right_config, config, axes
        return CircuitCompareResult(
            figure=figure,
            axes=(subplot_axes[0], subplot_axes[1]),
            left_result=object(),  # type: ignore[arg-type]
            right_result=object(),  # type: ignore[arg-type]
            metrics=object(),  # type: ignore[arg-type]
        )

    monkeypatch.setattr("examples._compare_shared.compare_circuits", fake_compare_circuits)

    request = CompareExampleRequest(output=None, show=False, figsize=(12.0, 5.0))
    payload = CompareDemoPayload(
        compare_kind="circuits",
        left_data={"kind": "left"},
        right_data={"kind": "right"},
        config=CircuitCompareConfig(show=False),
    )

    plt.close("all")
    try:
        render_compare_example(
            payload,
            request=request,
            saved_label="compare-circuits-qiskit-transpile",
        )

        assert figure.get_label() == "compare-circuits-qiskit-transpile"
        assert titles == ["compare-circuits-qiskit-transpile"]
        assert tuple(plt.get_fignums()) == ()
    finally:
        plt.close("all")


def test_render_compare_example_reraises_unexpected_window_title_errors_and_closes_figure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        render_compare_example,
    )

    from quantum_circuit_drawer import CircuitCompareConfig, CircuitCompareResult

    figure, subplot_axes = plt.subplots(1, 2)
    manager = figure.canvas.manager
    assert manager is not None

    def failing_set_window_title(title: str) -> None:
        del title
        raise RuntimeError("unexpected title failure")

    monkeypatch.setattr(manager, "set_window_title", failing_set_window_title)

    def fake_compare_circuits(
        left_circuit: object,
        right_circuit: object,
        *,
        left_config: object = None,
        right_config: object = None,
        config: CircuitCompareConfig | None = None,
        axes: object = None,
    ) -> CircuitCompareResult:
        del left_circuit, right_circuit, left_config, right_config, config, axes
        return CircuitCompareResult(
            figure=figure,
            axes=(subplot_axes[0], subplot_axes[1]),
            left_result=object(),  # type: ignore[arg-type]
            right_result=object(),  # type: ignore[arg-type]
            metrics=object(),  # type: ignore[arg-type]
        )

    monkeypatch.setattr("examples._compare_shared.compare_circuits", fake_compare_circuits)

    request = CompareExampleRequest(output=None, show=False, figsize=(12.0, 5.0))
    payload = CompareDemoPayload(
        compare_kind="circuits",
        left_data={"kind": "left"},
        right_data={"kind": "right"},
        config=CircuitCompareConfig(show=False),
    )

    plt.close("all")
    try:
        with pytest.raises(RuntimeError, match="unexpected title failure"):
            render_compare_example(
                payload,
                request=request,
                saved_label="compare-circuits-qiskit-transpile",
            )

        assert tuple(plt.get_fignums()) == ()
    finally:
        plt.close("all")
