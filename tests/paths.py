"""Shared path helpers for tests that should not depend on folder depth."""

from __future__ import annotations

from pathlib import Path


def repo_root_for(file_path: Path) -> Path:
    """Resolve the repository root from one test file path."""

    resolved_path = file_path.resolve()
    return next(parent for parent in resolved_path.parents if (parent / "pyproject.toml").is_file())


def external_workspace_root_for(file_path: Path) -> Path:
    """Resolve one stable directory outside the repository worktree for subprocess tests."""

    repo_root = repo_root_for(file_path)
    return repo_root.parent.parent
