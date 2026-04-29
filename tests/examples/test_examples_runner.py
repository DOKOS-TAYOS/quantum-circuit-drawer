from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import examples.run_demo as run_demo_module
import pytest
from examples.demo_catalog import catalog_by_id, get_demo_catalog

from tests.paths import external_workspace_root_for, repo_root_for
from tests.support import assert_saved_image_has_visible_content


def test_demo_catalog_entries_reference_existing_example_scripts() -> None:
    demo_ids = [spec.demo_id for spec in get_demo_catalog()]

    assert len(demo_ids) == len(set(demo_ids))
    assert set(catalog_by_id()) == set(demo_ids)

    for spec in get_demo_catalog():
        assert run_demo_module.script_path_for(spec).is_file()


def test_demo_catalog_exposes_only_the_refreshed_demo_ids() -> None:
    demo_ids = {spec.demo_id for spec in get_demo_catalog()}

    assert demo_ids == {
        "qiskit-random",
        "qiskit-qaoa",
        "qiskit-2d-exploration-showcase",
        "qiskit-3d-exploration-showcase",
        "qiskit-control-flow-showcase",
        "qiskit-composite-modes-showcase",
        "openqasm-showcase",
        "cirq-random",
        "cirq-qaoa",
        "cirq-native-controls-showcase",
        "pennylane-random",
        "pennylane-qaoa",
        "pennylane-terminal-outputs-showcase",
        "myqlm-random",
        "myqlm-structural-showcase",
        "cudaq-random",
        "cudaq-kernel-showcase",
        "ir-basic-workflow",
    }


def test_parse_args_preserves_forwarded_script_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_demo.py",
            "--demo",
            "qiskit-random",
            "--output",
            "demo.png",
            "--no-show",
            "--mode",
            "slider",
            "--columns",
            "9",
        ],
    )

    args, forwarded_args = run_demo_module.parse_args()

    assert args.demo == "qiskit-random"
    assert args.output == Path("demo.png")
    assert args.show is False
    assert forwarded_args == ["--mode", "slider", "--columns", "9"]


def test_run_demo_forwards_output_and_no_show(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    spec = catalog_by_id()["ir-basic-workflow"]
    output_path = sandbox_tmp_path / "ir-basic-workflow.png"
    commands: list[list[str]] = []

    monkeypatch.setattr(run_demo_module, "ensure_demo_dependency", lambda spec: None)
    monkeypatch.setattr(
        run_demo_module.subprocess,
        "run",
        lambda command, check=False: commands.append(command) or SimpleNamespace(returncode=0),
    )

    run_demo_module.run_demo(
        spec,
        output=output_path,
        show=False,
        forwarded_args=["--motifs", "5"],
    )

    assert commands == [
        [
            sys.executable,
            str(run_demo_module.script_path_for(spec)),
            "--motifs",
            "5",
            "--output",
            str(output_path),
            "--no-show",
        ]
    ]


def test_run_demo_respects_explicit_script_flags(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    spec = catalog_by_id()["ir-basic-workflow"]
    runner_output = sandbox_tmp_path / "runner.png"
    commands: list[list[str]] = []

    monkeypatch.setattr(run_demo_module, "ensure_demo_dependency", lambda spec: None)
    monkeypatch.setattr(
        run_demo_module.subprocess,
        "run",
        lambda command, check=False: commands.append(command) or SimpleNamespace(returncode=0),
    )

    run_demo_module.run_demo(
        spec,
        output=runner_output,
        show=False,
        forwarded_args=["--output", "script.png", "--show"],
    )

    assert commands == [
        [
            sys.executable,
            str(run_demo_module.script_path_for(spec)),
            "--output",
            "script.png",
            "--show",
        ]
    ]


def test_main_requires_demo_or_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_demo_module,
        "parse_args",
        lambda: (SimpleNamespace(list=False, demo=None, output=None, show=True), []),
    )

    with pytest.raises(SystemExit, match="Choose one demo with --demo or use --list"):
        run_demo_module.main()


def test_run_demo_reports_clear_message_when_optional_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = catalog_by_id()["myqlm-random"]
    monkeypatch.setattr(run_demo_module, "find_spec", lambda name: None)

    with pytest.raises(SystemExit) as exc_info:
        run_demo_module.ensure_demo_dependency(spec)

    message = str(exc_info.value)

    assert "myqlm-random" in message
    assert "qat" in message
    assert 'python.exe -m pip install -e ".[myqlm]"' in message
    assert "Traceback" not in message


def test_examples_runner_lists_all_demo_ids() -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "run_demo.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--list"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    for spec in get_demo_catalog():
        assert spec.demo_id in result.stdout


def test_run_demo_script_imports_drawer_from_local_worktree_src() -> None:
    worktree_root = repo_root_for(Path(__file__))
    workspace_root = external_workspace_root_for(Path(__file__))
    script_path = worktree_root / "examples" / "run_demo.py"
    expected_module_path = worktree_root / "src" / "quantum_circuit_drawer" / "__init__.py"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import pathlib, runpy; "
                f"runpy.run_path(r'{script_path}', run_name='codex_examples_test'); "
                "import quantum_circuit_drawer; "
                "print(pathlib.Path(quantum_circuit_drawer.__file__).resolve())"
            ),
        ],
        cwd=workspace_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(expected_module_path.resolve())


@pytest.mark.integration
def test_examples_runner_can_render_ir_basic_workflow(
    sandbox_tmp_path: Path,
) -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "run_demo.py"
    output_path = sandbox_tmp_path / "ir-basic-workflow.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "ir-basic-workflow",
            "--no-show",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert_saved_image_has_visible_content(output_path)
    assert f"Saved ir-basic-workflow to {output_path}" in result.stdout


@pytest.mark.integration
def test_public_api_utilities_showcase_script_exports_companion_files(
    sandbox_tmp_path: Path,
) -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "public_api_utilities_showcase.py"
    output_path = sandbox_tmp_path / "public-api-utilities.png"
    pages_dir = output_path.with_name("public-api-utilities_pages")
    histogram_csv_path = output_path.with_name("public-api-utilities_histogram.csv")
    latex_path = output_path.with_name("public-api-utilities_quantikz.tex")

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--no-show",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert_saved_image_has_visible_content(output_path)
    assert pages_dir.is_dir()
    assert histogram_csv_path.is_file()
    assert "\\begin{quantikz}" in latex_path.read_text(encoding="utf-8")
    assert f"Saved public-api-utilities-showcase to {output_path}" in result.stdout


@pytest.mark.integration
def test_logging_showcase_script_reports_programmatic_capture() -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "logging_showcase.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--no-show",
            "--profile",
            "summary",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Logging configured with profile=summary" in result.stdout
    assert "Captured " in result.stdout
    assert "First event=" in result.stdout


@pytest.mark.optional
@pytest.mark.integration
def test_qiskit_2d_exploration_showcase_script_can_render_directly(
    sandbox_tmp_path: Path,
) -> None:
    if run_demo_module.find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the showcase smoke test")

    script_path = repo_root_for(Path(__file__)) / "examples" / "qiskit_2d_exploration_showcase.py"
    output_path = sandbox_tmp_path / "qiskit-2d-exploration-showcase.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--no-show",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert_saved_image_has_visible_content(output_path)
    assert f"Saved qiskit-2d-exploration-showcase to {output_path}" in result.stdout
