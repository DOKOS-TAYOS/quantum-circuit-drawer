from __future__ import annotations

from typing import cast

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from tests.support import build_sample_scene


def test_create_managed_figure_uses_agg_canvas_when_requested(
    monkeypatch,
) -> None:
    from quantum_circuit_drawer.renderers._matplotlib_figure import create_managed_figure

    def fail_figure(*args: object, **kwargs: object) -> None:
        raise AssertionError("matplotlib.pyplot.figure should not be called for Agg figures")

    monkeypatch.setattr(plt, "figure", fail_figure)

    figure, axes = create_managed_figure(build_sample_scene(), use_agg=True)

    assert isinstance(figure.canvas, FigureCanvasAgg)
    assert axes.figure is figure


def test_managed_figure_metadata_tracks_slider_and_viewport() -> None:
    from quantum_circuit_drawer.renderers._matplotlib_figure import (
        get_page_slider,
        get_viewport_width,
        set_page_slider,
        set_viewport_width,
    )

    figure, _ = plt.subplots()
    slider = cast("object", object())

    assert get_page_slider(figure) is None
    assert get_viewport_width(figure, default=7.5) == 7.5

    set_page_slider(figure, slider)
    set_viewport_width(figure, viewport_width=3.25)

    assert get_page_slider(figure) is slider
    assert get_viewport_width(figure, default=7.5) == 3.25
    plt.close(figure)
