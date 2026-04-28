from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import examples.run_compare_demo as run_compare_demo_module
import pytest
from examples.compare_demo_catalog import catalog_by_id, get_demo_catalog

from tests.paths import external_workspace_root_for, repo_root_for
from tests.support import assert_saved_image_has_visible_content


def test_compare_demo_catalog_entries_reference_existing_scripts() -> None:
    demo_ids = [spec.demo_id for spec in get_demo_catalog()]

    assert len(demo_ids) == len(set(demo_ids))
    assert set(catalog_by_id()) == set(demo_ids)

    for spec in get_demo_catalog():
        assert run_compare_demo_module.script_path_for(spec).is_file()


def test_compare_demo_catalog_exposes_expected_demo_ids() -> None:
    demo_ids = {spec.demo_id for spec in get_demo_catalog()}

    assert demo_ids == {
        "compare-circuits-qiskit-transpile",
        "compare-circuits-composite-modes",
        "compare-circuits-multi-transpile",
        "compare-histograms-ideal-vs-sampled",
        "compare-histograms-multi-series",
    }


def test_parse_args_preserves_forwarded_compare_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_compare_demo.py",
            "--demo",
            "compare-histograms-ideal-vs-sampled",
            "--output",
            "compare.png",
            "--no-show",
            "--sort",
            "delta_desc",
        ],
    )

    args, forwarded_args = run_compare_demo_module.parse_args()

    assert args.demo == "compare-histograms-ideal-vs-sampled"
    assert args.output == Path("compare.png")
    assert args.show is False
    assert forwarded_args == ["--sort", "delta_desc"]


def test_run_compare_demo_forwards_output_and_no_show(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    spec = catalog_by_id()["compare-histograms-ideal-vs-sampled"]
    output_path = sandbox_tmp_path / "compare.png"
    commands: list[list[str]] = []

    monkeypatch.setattr(run_compare_demo_module, "ensure_demo_dependency", lambda spec: None)
    monkeypatch.setattr(
        run_compare_demo_module.subprocess,
        "run",
        lambda command, check=False: commands.append(command) or SimpleNamespace(returncode=0),
    )

    run_compare_demo_module.run_demo(
        spec,
        output=output_path,
        show=False,
        forwarded_args=["--sort", "delta_desc"],
    )

    assert commands == [
        [
            sys.executable,
            str(run_compare_demo_module.script_path_for(spec)),
            "--sort",
            "delta_desc",
            "--output",
            str(output_path),
            "--no-show",
        ]
    ]


def test_compare_main_requires_demo_or_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_compare_demo_module,
        "parse_args",
        lambda: (SimpleNamespace(list=False, demo=None, output=None, show=True), []),
    )

    with pytest.raises(SystemExit, match="Choose one compare demo with --demo or use --list"):
        run_compare_demo_module.main()


def test_run_compare_demo_reports_clear_message_when_optional_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = catalog_by_id()["compare-circuits-qiskit-transpile"]
    monkeypatch.setattr(run_compare_demo_module, "find_spec", lambda name: None)

    with pytest.raises(SystemExit) as exc_info:
        run_compare_demo_module.ensure_demo_dependency(spec)

    message = str(exc_info.value)

    assert "compare-circuits-qiskit-transpile" in message
    assert "qiskit" in message
    assert 'python.exe -m pip install -e ".[qiskit]"' in message
    assert "Traceback" not in message


def test_compare_examples_runner_lists_all_demo_ids() -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "run_compare_demo.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--list"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    for spec in get_demo_catalog():
        assert spec.demo_id in result.stdout


def test_run_compare_demo_script_imports_drawer_from_local_worktree_src() -> None:
    worktree_root = repo_root_for(Path(__file__))
    workspace_root = external_workspace_root_for(Path(__file__))
    script_path = worktree_root / "examples" / "run_compare_demo.py"
    expected_module_path = worktree_root / "src" / "quantum_circuit_drawer" / "__init__.py"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import pathlib, runpy; "
                f"runpy.run_path(r'{script_path}', run_name='codex_compare_examples_test'); "
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
def test_compare_examples_runner_can_render_builtin_histogram_demo(
    sandbox_tmp_path: Path,
) -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "run_compare_demo.py"
    output_path = sandbox_tmp_path / "compare-histograms-ideal-vs-sampled.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "compare-histograms-ideal-vs-sampled",
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
    assert f"Saved compare-histograms-ideal-vs-sampled to {output_path}" in result.stdout


@pytest.mark.integration
def test_compare_histogram_script_can_render_directly(
    sandbox_tmp_path: Path,
) -> None:
    script_path = (
        repo_root_for(Path(__file__)) / "examples" / "compare_histograms_ideal_vs_sampled.py"
    )
    output_path = sandbox_tmp_path / "compare-histograms-direct.png"

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
    assert f"Saved compare-histograms-ideal-vs-sampled to {output_path}" in result.stdout


@pytest.mark.optional
@pytest.mark.integration
def test_compare_circuit_script_can_render_directly(
    sandbox_tmp_path: Path,
) -> None:
    if run_compare_demo_module.find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the compare-circuits smoke test")

    script_path = (
        repo_root_for(Path(__file__)) / "examples" / "compare_circuits_qiskit_transpile.py"
    )
    output_path = sandbox_tmp_path / "compare-circuits-direct.png"

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
    assert f"Saved compare-circuits-qiskit-transpile to {output_path}" in result.stdout
