from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure

import quantum_circuit_drawer
from quantum_circuit_drawer import DrawMode
from quantum_circuit_drawer.exceptions import (
    RenderingError,
    StyleValidationError,
    UnsupportedBackendError,
    UnsupportedFrameworkError,
)
from quantum_circuit_drawer.hover import HoverOptions
from tests.support import (
    assert_axes_contains_circuit_artists,
    assert_figure_has_visible_content,
    assert_saved_image_has_visible_content,
    build_public_draw_config,
    build_sample_ir,
    build_sample_myqlm_circuit,
    install_fake_cudaq,
    install_fake_myqlm,
)
from tests.support import (
    draw_quantum_circuit_legacy as draw_quantum_circuit,
)


def test_draw_quantum_circuit_returns_populated_managed_agg_figure_for_ir() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert isinstance(figure.canvas, FigureCanvasAgg)
    assert axes.figure is figure
    assert_axes_contains_circuit_artists(axes, expected_texts={"H", "M", "q0", "q1", "c0"})
    assert_figure_has_visible_content(figure)
    plt.close(figure)


def test_draw_quantum_circuit_draws_on_existing_axes() -> None:
    figure, axes = plt.subplots()

    result = draw_quantum_circuit(build_sample_ir(), ax=axes)

    assert result is axes
    assert axes.figure is figure
    assert_axes_contains_circuit_artists(axes, expected_texts={"H", "M", "q0", "q1", "c0"})
    assert_figure_has_visible_content(figure)
    plt.close(figure)


def test_draw_quantum_circuit_saves_non_empty_output(sandbox_tmp_path: Path) -> None:
    output = sandbox_tmp_path / "circuit.png"

    figure, _ = draw_quantum_circuit(build_sample_ir(), output=output, show=False)

    assert_saved_image_has_visible_content(output)
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
        ("page_window", 1, "page_window must be a boolean"),
        ("topology_menu", 1, "topology_menu must be a boolean"),
        ("direct", "yes", "direct must be a boolean"),
        ("hover", 1, "hover must be a boolean, HoverOptions, or a mapping"),
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


def test_draw_quantum_circuit_exports_hover_options() -> None:
    assert quantum_circuit_drawer.HoverOptions is HoverOptions
    assert HoverOptions().show_matrix == "auto"
    assert HoverOptions().show_matrix_dimensions is True
    assert HoverOptions().show_size is False


def test_draw_quantum_circuit_accepts_hover_options_mapping() -> None:
    figure, axes = draw_quantum_circuit(
        build_sample_ir(),
        hover={"show_matrix": "always", "matrix_max_qubits": 1},
        show=False,
    )

    assert axes.figure is figure
    plt.close(figure)


def test_draw_quantum_circuit_validates_hover_options_mapping() -> None:
    with pytest.raises(ValueError, match="hover.show_matrix must be one of: always, auto, never"):
        draw_quantum_circuit(build_sample_ir(), hover={"show_matrix": "sometimes"})


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"enabled": 1}, "hover.enabled must be a boolean"),
        ({"show_matrix": "sometimes"}, "hover.show_matrix must be one of: always, auto, never"),
        ({"matrix_max_qubits": True}, "hover.matrix_max_qubits must be a positive integer"),
    ],
)
def test_hover_options_reject_invalid_direct_values(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        HoverOptions(**kwargs)


def test_draw_quantum_circuit_rejects_invalid_figsize() -> None:
    with pytest.raises(ValueError, match="figsize must be a 2-item tuple of positive numbers"):
        draw_quantum_circuit(build_sample_ir(), figsize=(8.0, 0.0))


def test_draw_quantum_circuit_rejects_figsize_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="figsize cannot be used with ax"):
        draw_quantum_circuit(build_sample_ir(), ax=axes, figsize=(8.0, 3.0))

    plt.close(figure)


def test_draw_quantum_circuit_applies_requested_theme() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), style={"theme": "paper"}, show=False)

    assert figure.get_facecolor() == to_rgba("#fffdf7")
    assert axes.get_facecolor() == to_rgba("#fffdf7")
    plt.close(figure)


def test_draw_quantum_circuit_uses_dark_theme_by_default() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure.get_facecolor() == to_rgba("#0b0f14")
    assert axes.get_facecolor() == to_rgba("#11161d")
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
    assert_axes_contains_circuit_artists(axes, expected_texts={"H", "MZ", "q0", "c"})
    assert_figure_has_visible_content(figure)
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
    assert_axes_contains_circuit_artists(axes, expected_texts={"H", "M", "q0", "c"})
    assert_figure_has_visible_content(figure)
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
    expected_result = object()

    def fake_draw_quantum_circuit(
        circuit: object,
        *,
        config: object = None,
        ax: object = None,
    ) -> object:
        captured.update(
            {
                "circuit": circuit,
                "config": config,
                "ax": ax,
            }
        )
        return expected_result

    monkeypatch.setattr(
        "quantum_circuit_drawer.api.draw_quantum_circuit", fake_draw_quantum_circuit
    )
    config = build_public_draw_config(
        show=False,
        figsize=(8.0, 3.0),
        mode=DrawMode.PAGES_CONTROLS,
        composite_mode="expand",
        topology_menu=True,
    )

    result = quantum_circuit_drawer.draw_quantum_circuit(
        build_sample_ir(),
        config=config,
    )

    assert result is expected_result
    assert captured["config"] is config
    assert captured["ax"] is None


def test_draw_quantum_circuit_exposes_version() -> None:
    assert quantum_circuit_drawer.__version__ == "0.4.0"


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
