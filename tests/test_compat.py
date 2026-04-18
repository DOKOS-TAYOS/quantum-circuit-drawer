"""Tests for compatibility helpers."""

from __future__ import annotations

from enum import Enum

from quantum_circuit_drawer._compat import StrEnum


class _SampleStrEnum(StrEnum):
    A = "a"
    B = "b"


def test_strenum_members_are_strings() -> None:
    assert isinstance(_SampleStrEnum.A, str)
    assert _SampleStrEnum.A == "a"


def test_strenum_is_enum_subclass() -> None:
    assert issubclass(StrEnum, Enum)
