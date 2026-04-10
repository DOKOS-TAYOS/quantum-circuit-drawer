from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.text import Text

import quantum_circuit_drawer
from quantum_circuit_drawer.api import draw_quantum_circuit
from quantum_circuit_drawer.exceptions import (
    RenderingError,
    StyleValidationError,
    UnsupportedBackendError,
    UnsupportedFrameworkError,
)
from tests.support import (
    build_sample_ir,
    build_sample_myqlm_circuit,
    install_fake_cudaq,
    install_fake_myqlm,
)


def _text_labels(texts: Iterable[Text]) -> set[str]:
    return {text.get_text() for text in texts}


def test_draw_quantum_circuit_returns_populated_managed_agg_figure_for_ir() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert isinstance(figure.canvas, FigureCanvasAgg)
    assert axes.figure is figure
    assert axes.lines
    assert axes.patches
    assert {"H", "M", "q0", "q1", "c0"}.issubset(_text_labels(axes.texts))
    plt.close(figure)


def test_draw_quantum_circuit_draws_on_existing_axes() -> None:
    figure, axes = plt.subplots()

    result = draw_quantum_circuit(build_sample_ir(), ax=axes)

    assert result is axes
    assert axes.figure is figure
    assert axes.lines
    assert axes.patches
    plt.close(figure)


def test_draw_quantum_circuit_saves_non_empty_output(sandbox_tmp_path: Path) -> None:
    output = sandbox_tmp_path / "circuit.png"

    figure, _ = draw_quantum_circuit(build_sample_ir(), output=output, show=False)

    assert output.exists()
    assert output.stat().st_size > 0
    plt.close(figure)


def test_draw_quantum_circuit_rejects_invalid_backend() -> None:
    with pytest.raises(UnsupportedBackendError, match="unsupported backend 'svg'"):
        draw_quantum_circuit(build_sample_ir(), backend="svg")


@pytest.mark.parametrize(
    ("option_name", "option_value", "message"),
    [
        ("view", "bogus", "view must be one of: 2d, 3d"),
        ("topology", "bogus", "topology must be one of: grid, honeycomb, line, star, star_tree"),
        ("composite_mode", "typo", "composite_mode must be one of: compact, expand"),
        ("show", "yes", "show must be a boolean"),
        ("page_slider", 1, "page_slider must be a boolean"),
        ("direct", "yes", "direct must be a boolean"),
        ("hover", 1, "hover must be a boolean"),
    ],
)
def test_draw_quantum_circuit_rejects_invalid_public_options(
    option_name: str,
    option_value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        draw_quantum_circuit(build_sample_ir(), **{option_name: option_value})


def test_draw_quantum_circuit_validates_style_input() -> None:
    with pytest.raises(StyleValidationError, match="font_size must be a positive number"):
        draw_quantum_circuit(build_sample_ir(), style={"font_size": -1})


def test_draw_quantum_circuit_applies_requested_theme() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), style={"theme": "paper"}, show=False)

    assert figure.get_facecolor() == to_rgba("#fffdf7")
    assert axes.get_facecolor() == to_rgba("#fffdf7")
    plt.close(figure)


def test_draw_quantum_circuit_uses_dark_theme_by_default() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure.get_facecolor() == to_rgba("#000000")
    assert axes.get_facecolor() == to_rgba("#000000")
    plt.close(figure)


def test_draw_quantum_circuit_reports_explicit_framework_mismatches() -> None:
    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"requested framework 'qiskit'.*autodetected 'ir'",
    ):
        draw_quantum_circuit(build_sample_ir(), framework="qiskit")


def test_draw_quantum_circuit_accepts_cudaq_framework_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_kernel_type = install_fake_cudaq(monkeypatch)

    figure, axes = draw_quantum_circuit(fake_kernel_type(), framework="cudaq", show=False)

    assert isinstance(figure.canvas, FigureCanvasAgg)
    assert {"H", "MZ", "q0", "c"}.issubset(_text_labels(axes.texts))
    plt.close(figure)


def test_draw_quantum_circuit_accepts_myqlm_framework_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_myqlm(monkeypatch)

    figure, axes = draw_quantum_circuit(
        build_sample_myqlm_circuit(),
        framework="myqlm",
        show=False,
    )

    assert isinstance(figure.canvas, FigureCanvasAgg)
    assert {"H", "M", "q0", "c"}.issubset(_text_labels(axes.texts))
    plt.close(figure)


def test_draw_quantum_circuit_wraps_output_errors() -> None:
    def fail_savefig(self: Figure, *args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(Figure, "savefig", fail_savefig)
    try:
        with pytest.raises(RenderingError, match="disk full"):
            draw_quantum_circuit(build_sample_ir(), output=Path("ignored.png"), show=False)
    finally:
        monkeypatch.undo()


def test_package_level_draw_quantum_circuit_forwards_show_parameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected_result = (object(), object())

    def fake_draw_quantum_circuit(
        circuit: object,
        framework: str | None = None,
        *,
        style: object = None,
        layout: object = None,
        backend: str = "matplotlib",
        ax: object = None,
        output: object = None,
        show: bool = True,
        page_slider: bool = False,
        composite_mode: str = "compact",
        **options: object,
    ) -> tuple[object, object]:
        captured.update(
            {
                "circuit": circuit,
                "framework": framework,
                "style": style,
                "layout": layout,
                "backend": backend,
                "ax": ax,
                "output": output,
                "show": show,
                "page_slider": page_slider,
                "composite_mode": composite_mode,
                "options": options,
            }
        )
        return expected_result

    monkeypatch.setattr(
        "quantum_circuit_drawer.api.draw_quantum_circuit", fake_draw_quantum_circuit
    )

    result = quantum_circuit_drawer.draw_quantum_circuit(
        build_sample_ir(),
        show=False,
        composite_mode="expand",
    )

    assert result is expected_result
    assert captured["show"] is False
    assert captured["backend"] == "matplotlib"
    assert captured["composite_mode"] == "expand"
    assert captured["framework"] is None


def test_draw_quantum_circuit_exposes_version() -> None:
    assert quantum_circuit_drawer.__version__ == "0.1.1"


def test_draw_quantum_circuit_emits_debug_logs_when_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")

    figure, _ = draw_quantum_circuit(build_sample_ir(), show=False)

    messages = [record.getMessage() for record in caplog.records]

    assert any("backend='matplotlib'" in message for message in messages)
    assert any("Prepared render pipeline" in message for message in messages)
    assert any("Rendered managed figure without page slider" in message for message in messages)
    plt.close(figure)
