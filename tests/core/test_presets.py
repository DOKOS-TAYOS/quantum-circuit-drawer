from __future__ import annotations

import pytest

from quantum_circuit_drawer.exceptions import StyleValidationError
from quantum_circuit_drawer.presets import (
    StylePreset,
    apply_draw_style_preset,
    histogram_draw_style_for_preset,
    histogram_figsize_for_preset,
    histogram_theme_for_preset,
    normalize_style_preset,
)
from quantum_circuit_drawer.style import DrawStyle
from quantum_circuit_drawer.style.theme import resolve_theme


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, None),
        ("paper", StylePreset.PAPER),
        (StylePreset.COMPACT, StylePreset.COMPACT),
    ],
)
def test_normalize_style_preset_accepts_supported_values(
    raw_value: StylePreset | str | None,
    expected: StylePreset | None,
) -> None:
    assert normalize_style_preset(raw_value) is expected


def test_normalize_style_preset_rejects_unknown_values() -> None:
    with pytest.raises(
        ValueError,
        match="preset must be one of: paper, notebook, compact, presentation",
    ):
        normalize_style_preset("poster")


@pytest.mark.parametrize(
    (
        "preset",
        "expected_theme_name",
        "expected_font_size",
        "expected_wire_spacing",
        "expected_layer_spacing",
        "expected_gate_size",
    ),
    [
        (StylePreset.PAPER, "paper", 11.5, 1.15, 0.45, 0.76),
        (StylePreset.NOTEBOOK, "light", 12.0, 1.25, 0.45, 0.78),
        (StylePreset.COMPACT, "dark", 10.5, 1.0, 0.38, 0.66),
        (StylePreset.PRESENTATION, "dark", 13.5, 1.3, 0.45, 0.84),
    ],
)
def test_apply_draw_style_preset_uses_expected_baselines(
    preset: StylePreset,
    expected_theme_name: str,
    expected_font_size: float,
    expected_wire_spacing: float,
    expected_layer_spacing: float,
    expected_gate_size: float,
) -> None:
    normalized = apply_draw_style_preset(None, preset=preset)

    assert normalized.theme.name == expected_theme_name
    assert normalized.font_size == pytest.approx(expected_font_size)
    assert normalized.wire_spacing == pytest.approx(expected_wire_spacing)
    assert normalized.layer_spacing == pytest.approx(expected_layer_spacing)
    assert normalized.gate_width == pytest.approx(expected_gate_size)
    assert normalized.gate_height == pytest.approx(expected_gate_size)


def test_apply_draw_style_preset_copies_draw_style_instances_without_merging_preset() -> None:
    explicit_style = DrawStyle(
        font_size=15.0,
        theme=resolve_theme("light"),
        line_width=2.1,
    )

    normalized = apply_draw_style_preset(explicit_style, preset=StylePreset.PAPER)

    assert normalized is not explicit_style
    assert normalized.font_size == pytest.approx(15.0)
    assert normalized.theme.name == "light"
    assert normalized.line_width == pytest.approx(2.1)


def test_apply_draw_style_preset_merges_mapping_over_preset_defaults() -> None:
    normalized = apply_draw_style_preset(
        {
            "font_size": 16.0,
            "theme": "light",
            "show_wire_labels": False,
        },
        preset=StylePreset.COMPACT,
    )

    assert normalized.font_size == pytest.approx(16.0)
    assert normalized.theme.name == "light"
    assert normalized.show_wire_labels is False
    assert normalized.wire_spacing == pytest.approx(1.0)
    assert normalized.layer_spacing == pytest.approx(0.38)
    assert normalized.gate_width == pytest.approx(0.66)
    assert normalized.gate_height == pytest.approx(0.66)


def test_apply_draw_style_preset_rejects_invalid_non_mapping_inputs() -> None:
    with pytest.raises(
        StyleValidationError,
        match="style must be None, a DrawStyle, or a mapping",
    ):
        apply_draw_style_preset([], preset=StylePreset.PAPER)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("preset", "expected_theme_name", "expected_draw_style", "expected_figsize"),
    [
        (None, None, None, None),
        (StylePreset.PAPER, "paper", "soft", (8.4, 4.6)),
        (StylePreset.NOTEBOOK, "light", "soft", (8.4, 4.6)),
        (StylePreset.COMPACT, "dark", "outline", (7.0, 3.8)),
        (StylePreset.PRESENTATION, "dark", "solid", (10.0, 5.6)),
    ],
)
def test_histogram_preset_helpers_return_expected_values(
    preset: StylePreset | None,
    expected_theme_name: str | None,
    expected_draw_style: str | None,
    expected_figsize: tuple[float, float] | None,
) -> None:
    resolved_theme = histogram_theme_for_preset(preset)

    assert (resolved_theme.name if resolved_theme is not None else None) == expected_theme_name
    assert histogram_draw_style_for_preset(preset) == expected_draw_style
    assert histogram_figsize_for_preset(preset) == expected_figsize
