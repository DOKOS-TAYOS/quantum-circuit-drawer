from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="clean.bat is only runnable on Windows"
)


@dataclass(slots=True)
class _CleanTestRepo:
    repo_root: Path
    script_path: Path
    removable_directories: list[Path]
    removable_files: list[Path]
    venv_marker: Path
    venv_pycache_file: Path


def _build_clean_test_repo(sandbox_tmp_path: Path) -> _CleanTestRepo:
    repo_root = sandbox_tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)

    source_script = Path(__file__).resolve().parents[1] / "scripts" / "clean.bat"
    target_script = scripts_dir / "clean.bat"
    shutil.copy2(source_script, target_script)

    removable_directories = [
        repo_root / ".pytest_cache",
        repo_root / ".ruff_cache",
        repo_root / ".mypy_cache",
        repo_root / ".pytest_tmp",
        repo_root / "test_tmp",
        repo_root / "build",
        repo_root / "dist",
        repo_root / "htmlcov",
        repo_root / "examples" / "output",
        repo_root / "src" / "quantum_circuit_drawer.egg-info",
        repo_root / "src" / "quantum_circuit_drawer" / "__pycache__",
    ]
    removable_files = [
        repo_root / ".coverage",
        repo_root / "coverage.xml",
        repo_root / "src" / "quantum_circuit_drawer" / "module.pyc",
    ]

    for directory in removable_directories:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "marker.txt").write_text("delete me", encoding="utf-8")

    for file_path in removable_files:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("delete me", encoding="utf-8")

    venv_marker = repo_root / ".venv" / "keep.txt"
    venv_pycache_file = repo_root / ".venv" / "Lib" / "__pycache__" / "keep.pyc"
    venv_marker.parent.mkdir(parents=True, exist_ok=True)
    venv_pycache_file.parent.mkdir(parents=True, exist_ok=True)
    venv_marker.write_text("keep me", encoding="utf-8")
    venv_pycache_file.write_text("keep me too", encoding="utf-8")

    return _CleanTestRepo(
        repo_root=repo_root,
        script_path=target_script,
        removable_directories=removable_directories,
        removable_files=removable_files,
        venv_marker=venv_marker,
        venv_pycache_file=venv_pycache_file,
    )


def _run_clean_script(repo: _CleanTestRepo, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["cmd", "/c", str(repo.script_path), *args],
        cwd=repo.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_clean_bat_removes_generated_artifacts_but_preserves_venv(
    sandbox_tmp_path: Path,
) -> None:
    repo = _build_clean_test_repo(sandbox_tmp_path)

    result = _run_clean_script(repo)

    assert result.returncode == 0, result.stdout + result.stderr

    for directory in repo.removable_directories:
        assert not directory.exists(), f"{directory} should have been removed"
    for file_path in repo.removable_files:
        assert not file_path.exists(), f"{file_path} should have been removed"

    assert repo.venv_marker.exists()
    assert repo.venv_pycache_file.exists()


def test_clean_bat_reports_dry_run_without_deleting_files(sandbox_tmp_path: Path) -> None:
    repo = _build_clean_test_repo(sandbox_tmp_path)

    result = _run_clean_script(repo, "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dry-run mode enabled. Nothing will be deleted." in result.stdout
    assert "[dry-run] Removing directory" in result.stdout

    for directory in repo.removable_directories:
        assert directory.exists(), f"{directory} should remain during dry-run"
    for file_path in repo.removable_files:
        assert file_path.exists(), f"{file_path} should remain during dry-run"

    assert repo.venv_marker.exists()
    assert repo.venv_pycache_file.exists()


def test_clean_bat_shows_help(sandbox_tmp_path: Path) -> None:
    repo = _build_clean_test_repo(sandbox_tmp_path)

    result = _run_clean_script(repo, "--help")

    assert result.returncode == 0
    assert "Usage: clean.bat [--dry-run]" in result.stdout
    assert 'without touching ".venv".' in result.stdout


def test_clean_bat_rejects_unknown_option_without_cleaning(sandbox_tmp_path: Path) -> None:
    repo = _build_clean_test_repo(sandbox_tmp_path)

    result = _run_clean_script(repo, "--bogus")

    assert result.returncode == 0
    assert 'Unknown option "--bogus"' in result.stdout
    assert "Usage: clean.bat [--dry-run]" in result.stdout

    for directory in repo.removable_directories:
        assert directory.exists(), f"{directory} should remain when arguments are invalid"
