from __future__ import annotations

import builtins

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg

import quantum_circuit_drawer
import quantum_circuit_drawer._runtime_context as runtime_context_module
from quantum_circuit_drawer import DrawConfig, DrawMode, DrawResult
from quantum_circuit_drawer._runtime_context import RuntimeContext
from quantum_circuit_drawer.api import draw_quantum_circuit
from tests.support import build_sample_ir


def test_public_package_exports_v2_draw_types() -> None:
    assert quantum_circuit_drawer.DrawConfig is DrawConfig
    assert quantum_circuit_drawer.DrawMode is DrawMode
    assert quantum_circuit_drawer.DrawResult is DrawResult
    assert DrawConfig().mode is DrawMode.AUTO


def test_draw_quantum_circuit_returns_draw_result_for_managed_render() -> None:
    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(show=False),
    )

    assert isinstance(result, DrawResult)
    assert isinstance(result.primary_figure.canvas, FigureCanvasAgg)
    assert result.primary_axes.figure is result.primary_figure
    assert result.figures == (result.primary_figure,)
    assert result.axes == (result.primary_axes,)
    assert result.page_count >= 1

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_returns_draw_result_for_caller_axes() -> None:
    figure, axes = plt.subplots()

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(),
        ax=axes,
    )

    assert isinstance(result, DrawResult)
    assert result.primary_figure is figure
    assert result.primary_axes is axes
    assert result.figures == (figure,)
    assert result.axes == (axes,)

    plt.close(figure)


def test_package_level_draw_quantum_circuit_forwards_config_and_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected_result = DrawResult(
        primary_figure=object(),
        primary_axes=object(),
        figures=(object(),),
        axes=(object(),),
        mode=DrawMode.FULL,
        page_count=1,
    )

    def fake_draw_quantum_circuit(
        circuit: object,
        *,
        config: DrawConfig | None = None,
        ax: object = None,
    ) -> DrawResult:
        captured["circuit"] = circuit
        captured["config"] = config
        captured["ax"] = ax
        return expected_result

    monkeypatch.setattr(
        "quantum_circuit_drawer.api.draw_quantum_circuit",
        fake_draw_quantum_circuit,
    )

    figure, axes = plt.subplots()
    config = DrawConfig(mode=DrawMode.FULL, show=False)

    result = quantum_circuit_drawer.draw_quantum_circuit(
        build_sample_ir(),
        config=config,
        ax=axes,
    )

    assert result is expected_result
    assert captured["config"] is config
    assert captured["ax"] is axes

    plt.close(figure)


def test_draw_quantum_circuit_resolves_auto_mode_to_pages_controls_for_scripts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer._runtime_context.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=False, pyplot_backend="agg"),
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(show=False),
    )

    assert result.mode is DrawMode.PAGES_CONTROLS

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_resolves_auto_mode_to_pages_for_notebooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer._runtime_context.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="inline"),
    )

    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(show=False),
    )

    assert result.mode is DrawMode.PAGES

    plt.close(result.primary_figure)


def test_draw_quantum_circuit_rejects_interactive_mode_in_non_widget_notebook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quantum_circuit_drawer._runtime_context.detect_runtime_context",
        lambda: RuntimeContext(is_notebook=True, pyplot_backend="inline"),
    )

    with pytest.raises(ValueError, match="requires a notebook widget backend"):
        draw_quantum_circuit(
            build_sample_ir(),
            config=DrawConfig(mode=DrawMode.SLIDER, show=False),
        )


def test_runtime_context_detects_non_notebook_without_importing_ipython(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_context_module._running_inside_notebook.cache_clear()
    monkeypatch.delattr(builtins, "get_ipython", raising=False)
    monkeypatch.delitem(runtime_context_module.sys.modules, "IPython", raising=False)

    original_import = builtins.__import__

    def fail_ipython_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "IPython":
            raise AssertionError(f"unexpected import attempt for {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_ipython_import)

    assert runtime_context_module._running_inside_notebook() is False


def test_draw_config_validates_public_choices() -> None:
    with pytest.raises(ValueError, match="mode must be one of"):
        DrawConfig(mode="invalid")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="view must be one of"):
        DrawConfig(view="invalid")  # type: ignore[arg-type]


def test_draw_config_rejects_boolean_figsize_entries() -> None:
    with pytest.raises(ValueError, match="figsize must be a 2-item tuple of positive numbers"):
        DrawConfig(figsize=(True, 2.0))


def test_draw_quantum_circuit_rejects_explicit_interactive_mode_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="requires a Matplotlib-managed figure"):
        draw_quantum_circuit(
            build_sample_ir(),
            config=DrawConfig(mode=DrawMode.SLIDER, show=False),
            ax=axes,
        )

    plt.close(figure)
