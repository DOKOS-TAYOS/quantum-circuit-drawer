from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from quantum_circuit_drawer.api import draw_quantum_circuit
from quantum_circuit_drawer.exceptions import RenderingError
from quantum_circuit_drawer.export import save_matplotlib_figure
from quantum_circuit_drawer.histogram import plot_histogram


def test_domain_packages_expose_draw_and_histogram_entrypoints() -> None:
    from quantum_circuit_drawer.drawing.api import (
        draw_quantum_circuit as drawing_draw_quantum_circuit,
    )
    from quantum_circuit_drawer.plots.histogram import plot_histogram as plots_plot_histogram

    assert drawing_draw_quantum_circuit is draw_quantum_circuit
    assert plots_plot_histogram is plot_histogram


def test_second_pass_managed_facades_reexport_split_helpers() -> None:
    from quantum_circuit_drawer.managed.controls import managed_3d_axes_bounds
    from quantum_circuit_drawer.managed.page_window_3d import (
        windowed_3d_page_ranges as facade_windowed_3d_page_ranges,
    )
    from quantum_circuit_drawer.managed.page_window_3d_ranges import windowed_3d_page_ranges
    from quantum_circuit_drawer.managed.slider import (
        _horizontal_scene_for_start_column as facade_horizontal_scene_for_start_column,
    )
    from quantum_circuit_drawer.managed.slider import (
        configure_3d_page_slider as facade_configure_3d_page_slider,
    )
    from quantum_circuit_drawer.managed.slider import (
        managed_3d_axes_bounds as facade_managed_3d_axes_bounds,
    )
    from quantum_circuit_drawer.managed.slider_2d_windowing import (
        _horizontal_scene_for_start_column,
    )
    from quantum_circuit_drawer.managed.slider_3d import configure_3d_page_slider

    assert facade_managed_3d_axes_bounds is managed_3d_axes_bounds
    assert facade_horizontal_scene_for_start_column is _horizontal_scene_for_start_column
    assert facade_configure_3d_page_slider is configure_3d_page_slider
    assert facade_windowed_3d_page_ranges is windowed_3d_page_ranges


def test_second_pass_3d_renderer_and_layout_helpers_are_importable() -> None:
    from importlib import import_module

    import quantum_circuit_drawer.layout._engine_3d_classical as engine_3d_classical
    import quantum_circuit_drawer.layout._engine_3d_metrics as engine_3d_metrics
    import quantum_circuit_drawer.layout._engine_3d_operations as engine_3d_operations
    import quantum_circuit_drawer.layout._engine_3d_topology as engine_3d_topology
    from quantum_circuit_drawer.layout.engine_3d import LayoutEngine3D
    from quantum_circuit_drawer.renderers.matplotlib_renderer_3d import (
        _MANAGED_3D_VIEWPORT_BOUNDS_ATTR,
        MatplotlibRenderer3D,
    )

    renderer_3d_viewport = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_viewport"
    )
    renderer_3d_geometry = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_geometry"
    )
    renderer_3d_text = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_text"
    )
    renderer_3d_hover = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_hover"
    )
    renderer_3d_segments = import_module(
        "quantum_circuit_drawer.renderers._matplotlib_renderer_3d_segments"
    )

    assert LayoutEngine3D.__name__ == "LayoutEngine3D"
    assert MatplotlibRenderer3D.__name__ == "MatplotlibRenderer3D"
    assert isinstance(_MANAGED_3D_VIEWPORT_BOUNDS_ATTR, str)
    assert renderer_3d_viewport.__name__.endswith("_viewport")
    assert renderer_3d_geometry.__name__.endswith("_geometry")
    assert renderer_3d_text.__name__.endswith("_text")
    assert renderer_3d_hover.__name__.endswith("_hover")
    assert renderer_3d_segments.__name__.endswith("_segments")
    assert engine_3d_topology.__name__.endswith("_topology")
    assert engine_3d_operations.__name__.endswith("_operations")
    assert engine_3d_metrics.__name__.endswith("_metrics")
    assert engine_3d_classical.__name__.endswith("_classical")


def test_save_matplotlib_figure_creates_parent_directories(sandbox_tmp_path: Path) -> None:
    figure = plt.figure()
    output = sandbox_tmp_path / "nested" / "exported.png"

    save_matplotlib_figure(figure, output)

    assert output.is_file()
    plt.close(figure)


def test_save_matplotlib_figure_wraps_save_errors() -> None:
    figure = plt.figure()

    def fail_savefig(self: Figure, *args: object, **kwargs: object) -> None:
        del self, args, kwargs
        raise OSError("disk full")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(Figure, "savefig", fail_savefig)
    try:
        with pytest.raises(RenderingError, match="disk full"):
            save_matplotlib_figure(figure, Path("ignored.png"))
    finally:
        monkeypatch.undo()
        plt.close(figure)
