from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure

import quantum_circuit_drawer
from quantum_circuit_drawer.api import draw_quantum_circuit
from quantum_circuit_drawer.exceptions import (
    RenderingError,
    StyleValidationError,
    UnsupportedBackendError,
    UnsupportedFrameworkError,
)
from tests.support import build_sample_ir, install_fake_cudaq


def test_draw_quantum_circuit_returns_figure_and_axes_for_ir() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_draws_on_existing_axes() -> None:
    _, axes = plt.subplots()

    result = draw_quantum_circuit(build_sample_ir(), ax=axes)

    assert result is axes


def test_draw_quantum_circuit_saves_output(sandbox_tmp_path: Path) -> None:
    output = sandbox_tmp_path / "circuit.png"

    draw_quantum_circuit(build_sample_ir(), output=output, show=False)

    assert output.exists()


def test_draw_quantum_circuit_rejects_invalid_backend() -> None:
    with pytest.raises(UnsupportedBackendError):
        draw_quantum_circuit(build_sample_ir(), backend="svg")


def test_draw_quantum_circuit_validates_style_input() -> None:
    with pytest.raises(StyleValidationError):
        draw_quantum_circuit(build_sample_ir(), style={"font_size": -1})


def test_draw_quantum_circuit_accepts_dark_theme() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), style={"theme": "dark"}, show=False)

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_accepts_page_wrapping_style() -> None:
    figure, axes = draw_quantum_circuit(
        build_sample_ir(), style={"max_page_width": 4.0}, show=False
    )

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_uses_dark_theme_by_default() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure.get_facecolor() == to_rgba("#000000")
    assert axes.get_facecolor() == to_rgba("#000000")


def test_draw_quantum_circuit_honors_explicit_framework_override() -> None:
    with pytest.raises(UnsupportedFrameworkError):
        draw_quantum_circuit(build_sample_ir(), framework="qiskit")


def test_draw_quantum_circuit_accepts_cudaq_framework_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_kernel_type = install_fake_cudaq(monkeypatch)

    figure, axes = draw_quantum_circuit(fake_kernel_type(), framework="cudaq", show=False)

    assert figure is not None
    assert axes.figure is figure


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


def test_package_level_draw_quantum_circuit_forwards_show_parameter() -> None:
    figure, axes = quantum_circuit_drawer.draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_exposes_version() -> None:
    assert quantum_circuit_drawer.__version__ == "0.1.1"


def test_draw_quantum_circuit_emits_debug_logs_when_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")

    draw_quantum_circuit(build_sample_ir(), show=False)

    assert any("backend='matplotlib'" in record.getMessage() for record in caplog.records)
