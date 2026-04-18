from __future__ import annotations

import pytest

from quantum_circuit_drawer.exceptions import StyleValidationError
from quantum_circuit_drawer.style import DrawStyle, normalize_style
from quantum_circuit_drawer.style.theme import DrawTheme, resolve_theme


def test_normalize_style_returns_default_dark_style_for_none() -> None:
    normalized = normalize_style(None)

    assert normalized.theme.name == "dark"
    assert normalized.font_size == DrawStyle().font_size


def test_normalize_style_copies_draw_style_instances() -> None:
    style = DrawStyle(font_size=14.0, theme=resolve_theme("paper"))

    normalized = normalize_style(style)

    assert normalized is not style
    assert normalized.font_size == 14.0
    assert normalized.theme.name == "paper"


def test_normalize_style_applies_mapping_values_and_keeps_defaults() -> None:
    normalized = normalize_style(
        {
            "font_size": 10.0,
            "show_params": False,
            "theme": "light",
            "use_mathtext": False,
        }
    )

    assert normalized.font_size == 10.0
    assert normalized.show_params is False
    assert normalized.use_mathtext is False
    assert normalized.theme.name == "light"
    assert normalized.layer_spacing == DrawStyle().layer_spacing


def test_normalize_style_rejects_unknown_keys() -> None:
    with pytest.raises(StyleValidationError, match="unknown style option"):
        normalize_style({"unknown_key": 1})


@pytest.mark.parametrize("field_name", ["font_size", "max_page_width"])
def test_normalize_style_rejects_invalid_positive_fields(field_name: str) -> None:
    with pytest.raises(StyleValidationError, match=rf"{field_name} must be a positive number"):
        normalize_style({field_name: 0})


@pytest.mark.parametrize("field_name", ["show_params", "show_wire_labels", "use_mathtext"])
def test_normalize_style_rejects_invalid_boolean_fields(field_name: str) -> None:
    with pytest.raises(StyleValidationError, match=rf"{field_name} must be a boolean"):
        normalize_style({field_name: "yes"})


def test_draw_style_enables_mathtext_by_default() -> None:
    assert DrawStyle().use_mathtext is True


def test_resolve_theme_accepts_theme_instances_and_rejects_unknown_names() -> None:
    theme = DrawTheme(
        name="custom",
        figure_facecolor="#000000",
        axes_facecolor="#000000",
        wire_color="#ffffff",
        classical_wire_color="#cccccc",
        gate_facecolor="#111111",
        gate_edgecolor="#eeeeee",
        measurement_facecolor="#222222",
        text_color="#ffffff",
        barrier_color="#999999",
        measurement_color="#aaaaaa",
        accent_color="#123456",
    )

    assert resolve_theme(theme) is theme

    with pytest.raises(StyleValidationError, match="unknown theme 'missing'"):
        resolve_theme("missing")
