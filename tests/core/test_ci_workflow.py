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


def test_package_metadata_and_ci_include_python_313() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    workflow_text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    classifiers = pyproject["project"]["classifiers"]

    assert "Programming Language :: Python :: 3.13" in classifiers
    assert 'python-version: ["3.11", "3.12", "3.13"]' in workflow_text


def test_ci_workflow_uses_current_core_coverage_threshold() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "python -m coverage report --show-missing --fail-under=87" in workflow_text


def test_ci_workflow_measures_qiskit_helpers_with_optional_adapters() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "*/adapters/_qiskit_*.py" in workflow_text
    assert '--omit="*/adapters/qiskit_adapter.py,*/adapters/_qiskit_*.py' in workflow_text
    assert '--include="*/adapters/qiskit_adapter.py,*/adapters/_qiskit_*.py' in workflow_text
