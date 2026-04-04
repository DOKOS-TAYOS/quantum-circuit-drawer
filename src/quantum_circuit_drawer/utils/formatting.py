"""Formatting helpers used across adapters and layout."""

from __future__ import annotations

from collections.abc import Iterable
from numbers import Real

import numpy as np


def format_gate_name(name: str) -> str:
    """Normalize a gate display name."""

    compact = name.replace("_", "").replace("-", "")
    if compact.isalpha() and len(compact) <= 4:
        return compact.upper()
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
