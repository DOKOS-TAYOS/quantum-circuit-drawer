"""Formatting helpers used across adapters and layout."""

from __future__ import annotations

from collections.abc import Iterable
from numbers import Real

import numpy as np


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