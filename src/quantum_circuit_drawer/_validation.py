"""Shared internal validation helpers for typed public option objects."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from math import isfinite
from os import PathLike


def validate_bool(name: str, value: object) -> None:
    """Raise when ``value`` is not a boolean."""

    if isinstance(value, bool):
        return
    raise ValueError(f"{name} must be a boolean")


def validate_choice(name: str, value: object, allowed_values: Collection[str]) -> None:
    """Raise when ``value`` is not one of the allowed string choices."""

    if isinstance(value, str) and value in allowed_values:
        return
    choices = ", ".join(sorted(allowed_values))
    raise ValueError(f"{name} must be one of: {choices}")


def validate_figsize(value: object) -> None:
    """Raise when ``value`` is not ``None`` or a positive 2-item size pair."""

    if value is None:
        return
    if not isinstance(value, tuple | list) or len(value) != 2:
        raise ValueError("figsize must be a 2-item tuple of positive numbers")
    width, height = value
    if not is_positive_dimension(width) or not is_positive_dimension(height):
        raise ValueError("figsize must be a 2-item tuple of positive numbers")


def validate_instance(name: str, value: object, expected_type: type[object]) -> None:
    """Raise when ``value`` does not match the expected type."""

    if isinstance(value, expected_type):
        return
    raise TypeError(f"{name} must be a {expected_type.__name__}")


def validate_mapping(name: str, value: object) -> None:
    """Raise when ``value`` is not a mapping."""

    if isinstance(value, Mapping):
        return
    raise TypeError(f"{name} must be a mapping")


def validate_optional_str(name: str, value: object) -> None:
    """Raise when ``value`` is not ``None`` or a string."""

    if value is None or isinstance(value, str):
        return
    raise ValueError(f"{name} must be a string")


def validate_optional_pathlike(name: str, value: object) -> None:
    """Raise when ``value`` is not ``None`` or a supported filesystem path."""

    if value is None:
        return
    if isinstance(value, str):
        path_value = value
    elif isinstance(value, PathLike):
        path_value = value.__fspath__()
    else:
        raise ValueError(f"{name} must be a path-like value")
    if not isinstance(path_value, str):
        raise ValueError(f"{name} must be a path-like value")
    if not path_value:
        raise ValueError(f"{name} must be a non-empty path-like value")


def normalize_optional_non_empty_str(name: str, value: object) -> str | None:
    """Return a stripped optional string, rejecting blank values."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be a non-empty string")
    return normalized


def validate_str(name: str, value: object) -> None:
    """Raise when ``value`` is not a string."""

    if isinstance(value, str):
        return
    raise ValueError(f"{name} must be a string")


def validate_str_tuple(name: str, value: object) -> None:
    """Raise when ``value`` is not a tuple of strings."""

    if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
        return
    raise ValueError(f"{name} must be a tuple of strings")


def is_positive_dimension(value: object) -> bool:
    """Return whether ``value`` is a positive numeric dimension."""

    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and isfinite(float(value))
        and float(value) > 0.0
    )


def is_non_negative_integer(value: object) -> bool:
    """Return whether ``value`` is a non-negative integer but not ``bool``."""

    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def is_positive_integer(value: object) -> bool:
    """Return whether ``value`` is a positive integer but not ``bool``."""

    return isinstance(value, int) and not isinstance(value, bool) and value > 0
