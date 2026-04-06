"""Import bootstrap helpers for standalone examples."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_local_project_on_path(anchor_file: str) -> Path:
    """Prepend the example project root and ``src`` directory to ``sys.path``."""

    project_root = Path(anchor_file).resolve().parents[1]
    source_root = project_root / "src"
    for candidate in (source_root, project_root):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
    return source_root
