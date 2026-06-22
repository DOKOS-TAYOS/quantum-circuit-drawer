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


def test_security_dependencies_include_audit_tools() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    security_dependencies = pyproject["project"]["optional-dependencies"]["security"]

    assert any(dependency.startswith("pip-audit") for dependency in security_dependencies)
    assert any(dependency.startswith("bandit") for dependency in security_dependencies)


def test_notebook_extra_includes_ipympl_widget_backend() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    notebook_dependencies = pyproject["project"]["optional-dependencies"]["notebook"]

    assert any(dependency.startswith("ipympl") for dependency in notebook_dependencies)


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


def test_ci_workflow_uses_least_privilege_permissions_and_current_actions() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow_text
    assert "actions/checkout@v7" in workflow_text
    assert "actions/setup-python@v6" in workflow_text


def test_dependabot_monitors_python_and_github_actions() -> None:
    dependabot_path = Path(".github/dependabot.yml")
    dependabot_text = dependabot_path.read_text(encoding="utf-8")

    assert 'package-ecosystem: "pip"' in dependabot_text
    assert 'package-ecosystem: "github-actions"' in dependabot_text
    assert 'versioning-strategy: "increase-if-necessary"' in dependabot_text
    assert 'timezone: "Europe/Madrid"' in dependabot_text


def test_ci_workflow_runs_static_analysis_only_on_python_311() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    workflow_text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert pyproject["tool"]["mypy"]["python_version"] == "3.11"
    assert pyproject["tool"]["pyright"]["pythonVersion"] == "3.11"
    assert "- name: Lint\n        if: matrix.python-version == '3.11'" in workflow_text
    assert "- name: Format check\n        if: matrix.python-version == '3.11'" in workflow_text
    assert "- name: Type check\n        if: matrix.python-version == '3.11'" in workflow_text
    assert "- name: Pyright check\n        if: matrix.python-version == '3.11'" in workflow_text


def test_security_workflows_are_configured() -> None:
    security_text = Path(".github/workflows/security.yml").read_text(encoding="utf-8")

    assert "actions/dependency-review-action@v5" in security_text
    assert "python -m pip_audit" in security_text
    assert "python -m bandit" in security_text
    assert 'python -m pip install -e ".[dev,security]"' in security_text
    assert "python -m pip list --format=freeze --exclude-editable" in security_text
    assert (
        "python -m pip_audit -r audit-requirements.txt --strict --no-deps --progress-spinner off"
    ) in security_text


def test_codeql_uses_github_default_setup_instead_of_advanced_workflow() -> None:
    assert not Path(".github/workflows/codeql.yml").exists()


def test_publish_workflow_uses_pypi_trusted_publishing() -> None:
    publish_text = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert "id-token: write" in publish_text
    assert "pypa/gh-action-pypi-publish@release/v1" in publish_text
    assert "PYPI_API_TOKEN" not in publish_text
    assert "password:" not in publish_text


def test_security_policy_exists_for_public_reporting() -> None:
    security_policy = Path("SECURITY.md").read_text(encoding="utf-8")

    assert "Supported Versions" in security_policy
    assert "Reporting a Vulnerability" in security_policy
    assert "GitHub security advisory" in security_policy


def test_ci_workflow_measures_qiskit_helpers_with_optional_adapters() -> None:
    workflow_path = Path(".github/workflows/ci.yml")
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "*/adapters/_qiskit_*.py" in workflow_text
    assert '--omit="*/adapters/qiskit_adapter.py,*/adapters/_qiskit_*.py' in workflow_text
    assert '--include="*/adapters/qiskit_adapter.py,*/adapters/_qiskit_*.py' in workflow_text
