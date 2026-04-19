"""Formatting helpers used across adapters and layout."""

from __future__ import annotations

import re
from collections.abc import Iterable
from numbers import Real

import numpy as np

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


def format_gate_name(name: str) -> str:
    """Normalize a gate display name."""

    compact = name.replace("_", "").replace("-", "")
    uppercase = compact.upper()
    if uppercase == "ISWAP":
        return "iSWAP"
    if uppercase.endswith("DG") and compact.isalpha() and 3 <= len(compact) <= 5:
        return f"{uppercase[:-2]}dg"
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


def format_visible_label(text: str, *, use_mathtext: bool) -> str:
    """Return visible circuit text in either plain text or MathText form."""

    if not use_mathtext:
        return text
    return format_visible_label_mathtext(text)


def format_parameter_text(text: str, *, use_mathtext: bool) -> str:
    """Return parameter text in either plain text or MathText form."""

    if not use_mathtext:
        return text
    return format_parameter_text_mathtext(text)


def format_gate_text_block(
    label: str,
    subtitle: str | None,
    *,
    use_mathtext: bool,
) -> str:
    """Return gate text as a single centered block, multiline when needed."""

    visible_label = format_visible_label(label, use_mathtext=use_mathtext)
    if not subtitle:
        return visible_label
    visible_subtitle = format_parameter_text(subtitle, use_mathtext=use_mathtext)
    return f"{visible_label}\n{visible_subtitle}"


def _replace_parameter_identifier(match: re.Match[str]) -> str:
    identifier = match.group(0)
    return _GREEK_IDENTIFIER_TO_MATHTEXT.get(identifier.lower(), identifier)
