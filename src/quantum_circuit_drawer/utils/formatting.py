"""Formatting helpers used across adapters and layout."""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from numbers import Complex, Real

import numpy as np

from ..typing import UseMathTextMode

_GREEK_IDENTIFIER_TO_MATHTEXT: dict[str, str] = {
    "alpha": r"\alpha",
    "beta": r"\beta",
    "gamma": r"\gamma",
    "delta": r"\delta",
    "epsilon": r"\epsilon",
    "zeta": r"\zeta",
    "eta": r"\eta",
    "theta": r"\theta",
    "iota": r"\iota",
    "kappa": r"\kappa",
    "lambda": r"\lambda",
    "lam": r"\lambda",
    "mu": r"\mu",
    "nu": r"\nu",
    "xi": r"\xi",
    "pi": r"\pi",
    "rho": r"\rho",
    "sigma": r"\sigma",
    "tau": r"\tau",
    "upsilon": r"\upsilon",
    "phi": r"\phi",
    "chi": r"\chi",
    "psi": r"\psi",
    "omega": r"\omega",
}
_PARAMETER_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z]+")
_PARAMETER_MATHTEXT_TRIGGER_PATTERN = re.compile(r"[\\^_]")
_VISIBLE_LABEL_ESCAPES = str.maketrans(
    {
        "\\": r"\\",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
        "_": r"\_",
        "^": r"\^",
    }
)
_CONTROL_FLOW_DISPLAY_NAMES: dict[str, str] = {
    "IF": "if",
    "ELSE": "else",
    "IFELSE": "if/else",
    "SWITCH": "switch",
    "FOR": "for",
    "WHILE": "while",
    "LOOP": "loop",
}
_CIRCUIT_NUMBER_LABEL_PATTERN = re.compile(
    r"^circuit\s*[-_:]?\s*(?P<number>\d+)$",
    flags=re.IGNORECASE,
)
_FOR_COUNT_LABEL_PATTERN = re.compile(r"^for\s+x(?P<count>\d+)$", flags=re.IGNORECASE)


def format_gate_name(name: str) -> str:
    """Normalize a gate display name."""

    compact = re.sub(r"[^0-9A-Za-z]+", "", name)
    uppercase = compact.upper()
    if uppercase in _CONTROL_FLOW_DISPLAY_NAMES:
        return _CONTROL_FLOW_DISPLAY_NAMES[uppercase]
    for_count_match = _FOR_COUNT_LABEL_PATTERN.match(name.strip())
    if for_count_match is not None:
        return f"for x{for_count_match.group('count')}"
    circuit_number_match = _CIRCUIT_NUMBER_LABEL_PATTERN.match(name.strip())
    if circuit_number_match is not None:
        return f"circuit {circuit_number_match.group('number')}"
    if uppercase == "CIRCUITOPERATION":
        return "CircuitOp"
    if uppercase in {"PROB", "PROBS", "PROBABILITY"}:
        return "Prob"
    if uppercase == "EXPVAL":
        return "ExpVal"
    if uppercase == "COUNTS":
        return "Counts"
    if uppercase == "ISWAP":
        return "iSWAP"
    if uppercase.endswith("DG") and compact.isalpha() and 3 <= len(compact) <= 5:
        return f"{uppercase[:-2]}†"
    if compact.isalnum() and len(compact) <= 4:
        return uppercase
    return name.replace("_", " ")


def format_parameter(value: object) -> str:
    """Return a compact string for a gate parameter."""

    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, Real):
        if float(value).is_integer():
            return str(int(float(value)))
        return f"{float(value):.3g}"
    return str(value)


def format_parameters(values: Iterable[object]) -> str:
    """Format gate parameters for labels."""

    return ", ".join(format_parameter(value) for value in values)


def format_state_vector_component(value: object) -> str:
    """Return a compact state-vector component label."""

    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, Complex) and not isinstance(value, Real):
        complex_value = complex(value)
        real_part = 0.0 if abs(complex_value.real) < 1e-15 else complex_value.real
        imaginary_part = 0.0 if abs(complex_value.imag) < 1e-15 else complex_value.imag
        if imaginary_part == 0.0:
            return _format_state_vector_real_component(real_part)
        if real_part == 0.0:
            return f"{_format_state_vector_real_component(imaginary_part)}j"
        sign = "+" if imaginary_part >= 0.0 else "-"
        return (
            f"{_format_state_vector_real_component(real_part)}"
            f"{sign}{_format_state_vector_real_component(abs(imaginary_part))}j"
        )
    if isinstance(value, Real):
        return _format_state_vector_real_component(float(value))
    return str(value)


def format_state_vector_parameters(values: Iterable[object]) -> str:
    """Return a bracketed compact state-vector label."""

    return f"[{', '.join(format_state_vector_component(value) for value in values)}]"


def _format_state_vector_real_component(value: float) -> str:
    if value == 0.0:
        return "0"
    absolute_value = abs(value)
    if 0.001 <= absolute_value < 10000.0:
        return f"{value:.4g}"
    return _trim_scientific_notation(f"{value:.3e}")


def _trim_scientific_notation(text: str) -> str:
    mantissa, _, exponent = text.partition("e")
    mantissa = mantissa.rstrip("0").rstrip(".")
    exponent_sign = "-" if exponent.startswith("-") else ""
    exponent_digits = exponent.lstrip("+-").lstrip("0") or "0"
    return f"{mantissa}e{exponent_sign}{exponent_digits}"


def format_gate_name_mathtext(name: str) -> str:
    """Return an upright MathText gate label."""

    return format_visible_label_mathtext(format_gate_name(name))


def format_parameter_text_mathtext(text: str) -> str:
    """Return a MathText parameter expression from an already formatted string."""

    if not text:
        return text

    transformed = _PARAMETER_IDENTIFIER_PATTERN.sub(_replace_parameter_identifier, text.strip())
    return f"${transformed}$"


def format_visible_label_mathtext(text: str) -> str:
    """Return generic visible circuit text wrapped as upright MathText."""

    if not text:
        return text

    escaped_text = text.translate(_VISIBLE_LABEL_ESCAPES).replace(" ", r"\ ")
    return rf"$\mathrm{{{escaped_text}}}$"


def format_visible_label(text: str, *, use_mathtext: UseMathTextMode) -> str:
    """Return visible circuit text in either plain text or MathText form."""

    return _format_resolved_text(text, role="visible_label", use_mathtext=use_mathtext)


def format_parameter_text(text: str, *, use_mathtext: UseMathTextMode) -> str:
    """Return parameter text in either plain text or MathText form."""

    return _format_resolved_text(text, role="parameter", use_mathtext=use_mathtext)


def format_gate_text_block(
    label: str,
    subtitle: str | None,
    *,
    use_mathtext: UseMathTextMode,
) -> str:
    """Return gate text as a single centered block, multiline when needed."""

    return _format_gate_text_block_cached(label, subtitle, use_mathtext)


def _replace_parameter_identifier(match: re.Match[str]) -> str:
    identifier = match.group(0)
    return _GREEK_IDENTIFIER_TO_MATHTEXT.get(identifier.lower(), identifier)


@lru_cache(maxsize=1024)
def _format_resolved_text(
    text: str,
    *,
    role: str,
    use_mathtext: UseMathTextMode,
) -> str:
    if use_mathtext is False or not text:
        return text
    if use_mathtext is True:
        return _format_text_for_role_mathtext(text, role=role)
    if role == "visible_label":
        return text
    if _parameter_uses_mathtext_auto(text):
        return format_parameter_text_mathtext(text)
    return text


def _format_text_for_role_mathtext(text: str, *, role: str) -> str:
    if role == "parameter":
        return format_parameter_text_mathtext(text)
    return format_visible_label_mathtext(text)


def _parameter_uses_mathtext_auto(text: str) -> bool:
    stripped_text = text.strip()
    if not stripped_text:
        return False
    transformed_text = _PARAMETER_IDENTIFIER_PATTERN.sub(
        _replace_parameter_identifier,
        stripped_text,
    )
    if transformed_text != stripped_text:
        return True
    return _PARAMETER_MATHTEXT_TRIGGER_PATTERN.search(stripped_text) is not None


@lru_cache(maxsize=512)
def _format_gate_text_block_cached(
    label: str,
    subtitle: str | None,
    use_mathtext: UseMathTextMode,
) -> str:
    visible_label = format_visible_label(label, use_mathtext=use_mathtext)
    if not subtitle:
        return visible_label
    visible_subtitle = format_parameter_text(subtitle, use_mathtext=use_mathtext)
    return f"{visible_label}\n{visible_subtitle}"
