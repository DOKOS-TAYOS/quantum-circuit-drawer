from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="clean.bat is only runnable on Windows")
def test_clean_bat_removes_generated_artifacts_but_preserves_venv(
    sandbox_tmp_path: Path,
) -> None:
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

    result = subprocess.run(
        ["cmd", "/c", str(target_script)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    for directory in removable_directories:
        assert not directory.exists(), f"{directory} should have been removed"
    for file_path in removable_files:
        assert not file_path.exists(), f"{file_path} should have been removed"

    assert venv_marker.exists()
    assert venv_pycache_file.exists()
