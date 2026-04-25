from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

GENERATED_DIRECTORIES: tuple[Path, ...] = (
    Path(".pytest_cache"),
    Path(".ruff_cache"),
    Path(".mypy_cache"),
    Path(".pytest_tmp"),
    Path("test_tmp"),
    Path("build"),
    Path("dist"),
    Path("htmlcov"),
    Path("examples") / "output",
)
GENERATED_FILES: tuple[Path, ...] = (
    Path(".coverage"),
    Path("coverage.xml"),
)
PROTECTED_DIRECTORY_NAMES: frozenset[str] = frozenset({".git", ".venv", ".worktrees"})


@dataclass(slots=True)
class CleanStats:
    removed_directories: int = 0
    removed_files: int = 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if any(arg in {"--help", "-h"} for arg in args):
        _print_usage()
        return 0

    unknown_args = [arg for arg in args if arg not in {"--dry-run", "-n"}]
    if unknown_args:
        print(f'Unknown option "{unknown_args[0]}"')
        print()
        _print_usage()
        return 2

    dry_run = any(arg in {"--dry-run", "-n"} for arg in args)
    repo_root = _repo_root_for_script(Path(__file__))
    stats = clean_repo(repo_root, dry_run=dry_run)

    print()
    print(f"Removed {stats.removed_directories} directorie(s) and {stats.removed_files} file(s).")
    return 0


def clean_repo(repo_root: Path, *, dry_run: bool) -> CleanStats:
    root = repo_root.resolve()
    venv_dir = root / ".venv"
    stats = CleanStats()

    print(f'Cleaning generated artifacts under "{root}"')
    if dry_run:
        print("Dry-run mode enabled. Nothing will be deleted.")

    for relative_directory in GENERATED_DIRECTORIES:
        _remove_directory(
            root / relative_directory, venv_dir=venv_dir, dry_run=dry_run, stats=stats
        )

    for directory in _walk_generated_directories(root):
        _remove_directory(directory, venv_dir=venv_dir, dry_run=dry_run, stats=stats)

    for relative_file in GENERATED_FILES:
        _remove_file(root / relative_file, venv_dir=venv_dir, dry_run=dry_run, stats=stats)

    for file_path in _walk_generated_files(root):
        _remove_file(file_path, venv_dir=venv_dir, dry_run=dry_run, stats=stats)

    return stats


def _repo_root_for_script(script_path: Path) -> Path:
    return script_path.resolve().parents[1]


def _walk_generated_directories(root: Path) -> Iterable[Path]:
    for current_root, directory_names, _ in os.walk(root):
        _prune_protected_directories(directory_names)
        current_path = Path(current_root)
        for directory_name in list(directory_names):
            if directory_name == "__pycache__" or directory_name.endswith(".egg-info"):
                yield current_path / directory_name


def _walk_generated_files(root: Path) -> Iterable[Path]:
    for current_root, directory_names, file_names in os.walk(root):
        _prune_protected_directories(directory_names)
        current_path = Path(current_root)
        for file_name in file_names:
            if file_name.endswith((".pyc", ".pyo")):
                yield current_path / file_name


def _prune_protected_directories(directory_names: list[str]) -> None:
    directory_names[:] = [
        directory_name
        for directory_name in directory_names
        if directory_name not in PROTECTED_DIRECTORY_NAMES
    ]


def _remove_directory(
    target: Path,
    *,
    venv_dir: Path,
    dry_run: bool,
    stats: CleanStats,
) -> None:
    if not target.exists():
        return
    if _is_inside_directory(target, venv_dir):
        return

    if dry_run:
        print(f'[dry-run] Removing directory "{target}"')
        stats.removed_directories += 1
        return

    try:
        shutil.rmtree(target)
    except OSError:
        print(f'Warning: could not remove directory "{target}"')
        return

    print(f'Removed directory "{target}"')
    stats.removed_directories += 1


def _remove_file(
    target: Path,
    *,
    venv_dir: Path,
    dry_run: bool,
    stats: CleanStats,
) -> None:
    if not target.exists():
        return
    if _is_inside_directory(target, venv_dir):
        return

    if dry_run:
        print(f'[dry-run] Removing file "{target}"')
        stats.removed_files += 1
        return

    try:
        target.unlink()
    except OSError:
        print(f'Warning: could not remove file "{target}"')
        return

    print(f'Removed file "{target}"')
    stats.removed_files += 1


def _is_inside_directory(target: Path, directory: Path) -> bool:
    try:
        target.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _print_usage() -> None:
    print("Usage: clean.py [--dry-run]")
    print()
    print("Removes common Python cache and temporary artifacts from this repository")
    print('without touching ".venv".')


if __name__ == "__main__":
    raise SystemExit(main())
