"""Compatibility helpers shared across the package."""

from __future__ import annotations

import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        """Fallback ``StrEnum`` implementation for Python versions < 3.11."""
