from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import examples.run_histogram_demo as run_histogram_demo_module
import pytest
from examples.histogram_demo_catalog import catalog_by_id, get_demo_catalog

from tests.paths import external_workspace_root_for, repo_root_for
from tests.support import assert_saved_image_has_visible_content


def test_histogram_demo_catalog_entries_reference_existing_scripts() -> None:
    demo_ids = [spec.demo_id for spec in get_demo_catalog()]

    assert len(demo_ids) == len(set(demo_ids))
    assert set(catalog_by_id()) == set(demo_ids)

    for spec in get_demo_catalog():
        assert run_histogram_demo_module.script_path_for(spec).is_file()


def test_histogram_demo_catalog_exposes_expected_demo_ids() -> None:
    demo_ids = {spec.demo_id for spec in get_demo_catalog()}

    assert demo_ids == {
        "histogram-binary-order",
        "histogram-cirq-result",
        "histogram-count-order",
        "histogram-cudaq-sample",
        "histogram-interactive-large",
        "histogram-multi-register",
        "histogram-myqlm-result",
        "histogram-pennylane-probs",
        "histogram-quasi",
        "histogram-quasi-nonnegative",
        "histogram-marginal",
        "histogram-result-index",
        "histogram-top-k",
        "histogram-uniform-reference",
    }


def test_parse_args_preserves_forwarded_histogram_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_histogram_demo.py",
            "--demo",
            "histogram-top-k",
            "--output",
            "histogram.png",
            "--no-show",
            "--top-k",
            "3",
            "--sort",
            "value_desc",
        ],
    )

    args, forwarded_args = run_histogram_demo_module.parse_args()

    assert args.demo == "histogram-top-k"
    assert args.output == Path("histogram.png")
    assert args.show is False
    assert forwarded_args == ["--top-k", "3", "--sort", "value_desc"]


def test_run_histogram_demo_forwards_output_and_no_show(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    spec = catalog_by_id()["histogram-top-k"]
    output_path = sandbox_tmp_path / "histogram-top-k.png"
    commands: list[list[str]] = []

    monkeypatch.setattr(run_histogram_demo_module, "ensure_demo_dependency", lambda spec: None)
    monkeypatch.setattr(
        run_histogram_demo_module.subprocess,
        "run",
        lambda command, check=False: commands.append(command) or SimpleNamespace(returncode=0),
    )

    run_histogram_demo_module.run_demo(
        spec,
        output=output_path,
        show=False,
        forwarded_args=["--top-k", "3"],
    )

    assert commands == [
        [
            sys.executable,
            str(run_histogram_demo_module.script_path_for(spec)),
            "--top-k",
            "3",
            "--output",
            str(output_path),
            "--no-show",
        ]
    ]


def test_histogram_main_requires_demo_or_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_histogram_demo_module,
        "parse_args",
        lambda: (SimpleNamespace(list=False, demo=None, output=None, show=True), []),
    )

    with pytest.raises(SystemExit, match="Choose one histogram demo with --demo or use --list"):
        run_histogram_demo_module.main()


def test_run_histogram_demo_reports_clear_message_when_optional_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = catalog_by_id()["histogram-myqlm-result"]
    monkeypatch.setattr(run_histogram_demo_module, "find_spec", lambda name: None)

    with pytest.raises(SystemExit) as exc_info:
        run_histogram_demo_module.ensure_demo_dependency(spec)

    message = str(exc_info.value)

    assert "histogram-myqlm-result" in message
    assert "qat" in message
    assert 'python.exe -m pip install -e ".[myqlm]"' in message
    assert "Traceback" not in message


def test_histogram_examples_runner_lists_all_demo_ids() -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "run_histogram_demo.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--list"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    for spec in get_demo_catalog():
        assert spec.demo_id in result.stdout


def test_run_histogram_demo_script_imports_drawer_from_local_worktree_src() -> None:
    worktree_root = repo_root_for(Path(__file__))
    workspace_root = external_workspace_root_for(Path(__file__))
    script_path = worktree_root / "examples" / "run_histogram_demo.py"
    expected_module_path = worktree_root / "src" / "quantum_circuit_drawer" / "__init__.py"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import pathlib, runpy; "
                f"runpy.run_path(r'{script_path}', run_name='codex_histogram_examples_test'); "
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
def test_histogram_examples_runner_can_render_builtin_demo(
    sandbox_tmp_path: Path,
) -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "run_histogram_demo.py"
    output_path = sandbox_tmp_path / "histogram-binary-order.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "histogram-binary-order",
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
    assert f"Saved histogram-binary-order to {output_path}" in result.stdout


@pytest.mark.integration
def test_histogram_top_k_script_can_render_directly(
    sandbox_tmp_path: Path,
) -> None:
    script_path = repo_root_for(Path(__file__)) / "examples" / "histogram_top_k.py"
    output_path = sandbox_tmp_path / "histogram-top-k.png"

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
    assert f"Saved histogram-top-k to {output_path}" in result.stdout


@pytest.mark.optional
@pytest.mark.integration
def test_histogram_marginal_demo_can_render_when_qiskit_is_available(
    sandbox_tmp_path: Path,
) -> None:
    if run_histogram_demo_module.find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the histogram marginal smoke test")

    script_path = repo_root_for(Path(__file__)) / "examples" / "run_histogram_demo.py"
    output_path = sandbox_tmp_path / "histogram-marginal.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "histogram-marginal",
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
