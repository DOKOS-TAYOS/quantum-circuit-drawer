from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest


def test_parse_histogram_example_args_reads_request(monkeypatch: pytest.MonkeyPatch) -> None:
    from examples._histogram_shared import HistogramExampleRequest, parse_histogram_example_args

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "histogram_example.py",
            "--output",
            "histogram-demo.png",
            "--figsize",
            "8",
            "4",
            "--no-show",
        ],
    )

    request = parse_histogram_example_args(description="Render a histogram demo.")

    assert request == HistogramExampleRequest(
        output=Path("histogram-demo.png"),
        show=False,
        figsize=(8.0, 4.0),
    )


def test_request_from_namespace_accepts_histogram_request() -> None:
    from examples._histogram_shared import HistogramExampleRequest, request_from_namespace

    args = Namespace(
        output=Path("counts.png"),
        show=False,
        figsize=(9.0, 4.5),
    )

    assert request_from_namespace(args) == HistogramExampleRequest(
        output=Path("counts.png"),
        show=False,
        figsize=(9.0, 4.5),
    )


def test_render_histogram_example_plots_and_reports_saved_output(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    from examples._histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        render_histogram_example,
    )

    from quantum_circuit_drawer import HistogramConfig, HistogramKind, HistogramResult

    output = sandbox_tmp_path / "render-histogram-demo.png"
    plot_calls: list[dict[str, object]] = []

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

    def fake_plot_histogram(
        data: object,
        *,
        config: HistogramConfig | None = None,
        ax: object = None,
    ) -> HistogramResult:
        plot_calls.append(
            {
                "data": data,
                "config": config,
                "ax": ax,
            }
        )
        return HistogramResult(
            figure=fake_figure,  # type: ignore[arg-type]
            axes=object(),  # type: ignore[arg-type]
            kind=HistogramKind.COUNTS,
            state_labels=("00", "11"),
            values=(5.0, 3.0),
            qubits=None,
        )

    monkeypatch.setattr("examples._histogram_shared.plot_histogram", fake_plot_histogram)

    request = HistogramExampleRequest(
        output=output,
        show=False,
        figsize=(8.0, 4.0),
    )
    payload = HistogramDemoPayload(
        data={"00": 5, "11": 3},
        config=HistogramConfig(kind=HistogramKind.COUNTS, show=True),
    )

    render_histogram_example(
        payload,
        request=request,
        saved_label="histogram-counts",
    )

    captured = capsys.readouterr()

    assert len(plot_calls) == 1
    assert plot_calls[0]["data"] == {"00": 5, "11": 3}
    assert plot_calls[0]["ax"] is None
    config = plot_calls[0]["config"]
    assert isinstance(config, HistogramConfig)
    assert config.kind is HistogramKind.COUNTS
    assert config.output_path == output
    assert config.show is False
    assert config.figsize == (8.0, 4.0)
    assert fake_figure.label == "histogram-counts"
    assert fake_figure.canvas.manager.window_titles == ["histogram-counts"]
    assert f"Saved histogram-counts to {output}" in captured.out
