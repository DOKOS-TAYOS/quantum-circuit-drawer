from __future__ import annotations

from importlib import import_module


def test_histogram_split_modules_are_importable() -> None:
    histogram_models = import_module("quantum_circuit_drawer.plots.histogram_models")
    histogram_normalize = import_module("quantum_circuit_drawer.plots.histogram_normalize")
    histogram_render = import_module("quantum_circuit_drawer.plots.histogram_render")
    histogram_compare = import_module("quantum_circuit_drawer.plots.histogram_compare")

    assert histogram_models.HistogramConfig.__name__ == "HistogramConfig"
    assert callable(histogram_normalize.normalize_histogram_data)
    assert callable(histogram_render.draw_histogram_axes)
    assert callable(histogram_compare.draw_histogram_compare_axes)


def test_histogram_module_reexports_new_owner_symbols() -> None:
    import quantum_circuit_drawer.plots.histogram as histogram_module
    from quantum_circuit_drawer.plots.histogram_compare import draw_histogram_compare_axes
    from quantum_circuit_drawer.plots.histogram_models import (
        HistogramCompareConfig,
        HistogramCompareMetrics,
        HistogramCompareResult,
        HistogramConfig,
        HistogramResult,
    )
    from quantum_circuit_drawer.plots.histogram_normalize import normalize_histogram_data
    from quantum_circuit_drawer.plots.histogram_render import draw_histogram_axes

    assert histogram_module.HistogramConfig is HistogramConfig
    assert histogram_module.HistogramResult is HistogramResult
    assert histogram_module.HistogramCompareConfig is HistogramCompareConfig
    assert histogram_module.HistogramCompareMetrics is HistogramCompareMetrics
    assert histogram_module.HistogramCompareResult is HistogramCompareResult
    assert histogram_module._normalize_histogram_data is normalize_histogram_data
    assert histogram_module._draw_histogram_axes is draw_histogram_axes
    assert histogram_module._draw_histogram_compare_axes is draw_histogram_compare_axes


def test_histogram_interactive_split_modules_are_importable() -> None:
    interactive_state = import_module("quantum_circuit_drawer.plots.histogram_interactive_state")
    interactive_controls = import_module(
        "quantum_circuit_drawer.plots.histogram_interactive_controls"
    )
    interactive_hover = import_module("quantum_circuit_drawer.plots.histogram_interactive_hover")

    assert interactive_state.HistogramInteractiveState.__name__ == "HistogramInteractiveState"
    assert callable(interactive_controls.attach_histogram_controls)
    assert callable(interactive_hover.attach_histogram_hover)


def test_histogram_interactive_entrypoint_stays_importable() -> None:
    import quantum_circuit_drawer.plots.histogram_interactive as histogram_interactive_module

    assert callable(histogram_interactive_module.attach_histogram_interactivity)
