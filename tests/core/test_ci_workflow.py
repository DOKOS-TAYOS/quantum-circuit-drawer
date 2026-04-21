from __future__ import annotations

import re
import tomllib
from pathlib import Path


def test_ci_workflow_referenced_test_files_exist() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow_text = workflow_path.read_text(encoding="utf-8")

    referenced_paths = {
        Path(match.group(0).replace("\\", "/"))
        for match in re.finditer(r"tests[\\/][^\"'\s]+\.py", workflow_text)
    }

    missing_paths = sorted(
        str(path).replace("\\", "/") for path in referenced_paths if not path.exists()
    )

    assert missing_paths == []


def test_dev_dependencies_include_pyright() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]

    assert any(dependency.startswith("pyright") for dependency in dev_dependencies)


def test_ci_workflow_runs_pyright() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "python -m pyright -p ." in workflow_text
