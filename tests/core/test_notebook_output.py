from __future__ import annotations

import sys
from types import SimpleNamespace

import matplotlib.pyplot as plt
import pytest

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit
from quantum_circuit_drawer.drawing.runtime import RuntimeContext
from quantum_circuit_drawer.histogram import plot_histogram
from quantum_circuit_drawer.renderers._render_support import (
    backend_supports_interaction,
    normalize_backend_name,
)
from tests.support import build_public_histogram_config, build_sample_ir


def test_normalize_backend_name_recognizes_matplotlib_inline_backend() -> None:
    assert normalize_backend_name("module://matplotlib_inline.backend_inline") == "inline"


def test_normalize_backend_name_recognizes_ipympl_widget_backend() -> None:
    assert normalize_backend_name("module://ipympl.backend_nbagg") == "ipympl"


def test_inline_backend_is_not_treated_as_interactive() -> None:
    assert backend_supports_interaction("inline") is False


def test_plot_histogram_displays_only_the_figure_when_returned_in_notebook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    display_calls: list[object] = []
    monkeypatch.setitem(
        sys.modules,
        "IPython.display",
        SimpleNamespace(display=lambda value: display_calls.append(value)),
    )
    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="inline"),
    )

    result = plot_histogram(
        {"0": 1, "1": 2},
        config=build_public_histogram_config(show=True),
    )

    result._ipython_display_()

    assert display_calls == [result.figure]
    plt.close(result.figure)


def test_plot_histogram_show_false_suppresses_notebook_result_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    display_calls: list[object] = []
    monkeypatch.setitem(
        sys.modules,
        "IPython.display",
        SimpleNamespace(display=lambda value: display_calls.append(value)),
    )
    monkeypatch.setattr(
        "quantum_circuit_drawer.plots.histogram.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="inline"),
    )

    result = plot_histogram(
        {"0": 1, "1": 2},
        config=build_public_histogram_config(show=False),
    )

    result._ipython_display_()

    assert display_calls == []
    plt.close(result.figure)


def test_draw_quantum_circuit_show_false_suppresses_notebook_result_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    display_calls: list[object] = []
    monkeypatch.setitem(
        sys.modules,
        "IPython.display",
        SimpleNamespace(display=lambda value: display_calls.append(value)),
    )
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="inline"),
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(output=OutputOptions(show=False)),
    )

    result._ipython_display_()

    assert display_calls == []
    for figure in result.figures:
        plt.close(figure)


def test_draw_quantum_circuit_widget_notebook_displays_ipympl_canvas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    display_calls: list[object] = []
    monkeypatch.setitem(
        sys.modules,
        "IPython.display",
        SimpleNamespace(display=lambda value: display_calls.append(value)),
    )
    monkeypatch.setattr(
        "quantum_circuit_drawer.drawing.runtime.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="ipympl"),
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        mode="pages_controls",
    )
    setattr(result.primary_figure.canvas, "_repr_mimebundle_", lambda *args, **kwargs: {})

    result._ipython_display_()

    assert display_calls == [result.primary_figure.canvas]
    plt.close(result.primary_figure)
