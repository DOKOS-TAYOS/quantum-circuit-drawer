from __future__ import annotations

import os
import subprocess
import sys
from argparse import Namespace
from importlib.util import find_spec
from pathlib import Path

import examples.run_histogram_demo as run_histogram_demo_module
import pytest
from examples._histogram_shared import (
    DEFAULT_HISTOGRAM_FIGSIZE,
    HistogramDemoPayload,
    HistogramExampleRequest,
)
from examples.histogram_demo_catalog import (
    HistogramDemoSpec,
    catalog_by_id,
    examples_directory,
    get_demo_catalog,
)

from quantum_circuit_drawer import HistogramConfig, HistogramKind
from tests.support import assert_saved_image_has_visible_content


def test_histogram_demo_catalog_entries_are_unique_and_reference_existing_example_files() -> None:
    catalog = get_demo_catalog()
    demo_ids = [spec.demo_id for spec in catalog]

    assert len(demo_ids) == len(set(demo_ids))
    assert set(catalog_by_id()) == set(demo_ids)

    for spec in catalog:
        example_path = examples_directory() / f"{spec.module_name.removeprefix('examples.')}.py"

        assert catalog_by_id()[spec.demo_id] == spec
        assert example_path.exists()
        assert spec.builder_name == "build_demo"


def test_run_histogram_demo_uses_spec_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = HistogramDemoPayload(
        data={"00": 5, "11": 3},
        config=HistogramConfig(kind=HistogramKind.COUNTS, show=True),
    )
    builder_calls: list[HistogramExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    spec = HistogramDemoSpec(
        demo_id="custom-histogram-demo",
        description="Custom histogram demo",
        module_name="examples.histogram_counts",
        builder_name="build_demo",
        dependency_module=None,
    )

    def fake_builder(request: HistogramExampleRequest) -> HistogramDemoPayload:
        builder_calls.append(request)
        return payload

    def fake_render_histogram_example(
        built_payload: HistogramDemoPayload,
        *,
        request: HistogramExampleRequest,
        saved_label: str,
    ) -> None:
        render_calls.append(
            {
                "payload": built_payload,
                "request": request,
                "saved_label": saved_label,
            }
        )

    monkeypatch.setattr(
        run_histogram_demo_module,
        "load_demo_builder",
        lambda demo_spec: fake_builder,
    )
    monkeypatch.setattr(
        run_histogram_demo_module,
        "render_histogram_example",
        fake_render_histogram_example,
    )

    run_histogram_demo_module.run_demo(spec, output=None, show=False)

    assert builder_calls == [
        HistogramExampleRequest(
            output=None,
            show=False,
            figsize=DEFAULT_HISTOGRAM_FIGSIZE,
        )
    ]
    assert render_calls == [
        {
            "payload": payload,
            "request": builder_calls[0],
            "saved_label": "custom-histogram-demo",
        }
    ]


def test_run_histogram_demo_with_args_builds_payload_and_renders(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    output = sandbox_tmp_path / "runner-histogram-demo.png"
    payload = HistogramDemoPayload(
        data={"00": 5, "11": 3},
        config=HistogramConfig(kind=HistogramKind.COUNTS, show=True),
    )
    builder_calls: list[HistogramExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    spec = HistogramDemoSpec(
        demo_id="custom-histogram-demo",
        description="Custom histogram demo",
        module_name="examples.histogram_counts",
        builder_name="build_demo",
        dependency_module=None,
    )
    args = Namespace(
        list=False,
        demo="custom-histogram-demo",
        output=output,
        show=False,
        figsize=(9.0, 4.0),
    )

    def fake_builder(request: HistogramExampleRequest) -> HistogramDemoPayload:
        builder_calls.append(request)
        return payload

    def fake_render_histogram_example(
        built_payload: HistogramDemoPayload,
        *,
        request: HistogramExampleRequest,
        saved_label: str,
    ) -> None:
        render_calls.append(
            {
                "payload": built_payload,
                "request": request,
                "saved_label": saved_label,
            }
        )

    monkeypatch.setattr(
        run_histogram_demo_module,
        "load_demo_builder",
        lambda demo_spec: fake_builder,
    )
    monkeypatch.setattr(
        run_histogram_demo_module,
        "render_histogram_example",
        fake_render_histogram_example,
    )

    run_histogram_demo_module.run_demo_with_args(spec, args)

    assert builder_calls == [
        HistogramExampleRequest(
            output=output,
            show=False,
            figsize=(9.0, 4.0),
        )
    ]
    assert render_calls == [
        {
            "payload": payload,
            "request": builder_calls[0],
            "saved_label": "custom-histogram-demo",
        }
    ]


def test_histogram_main_requires_demo_or_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_histogram_demo_module,
        "parse_args",
        lambda: Namespace(
            list=False,
            demo=None,
            output=None,
            show=True,
            figsize=DEFAULT_HISTOGRAM_FIGSIZE,
        ),
    )

    with pytest.raises(SystemExit, match="Choose one histogram demo with --demo or use --list"):
        run_histogram_demo_module.main()


def test_histogram_examples_runner_lists_all_demo_ids() -> None:
    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_histogram_demo.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--list"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    for spec in get_demo_catalog():
        assert spec.demo_id in result.stdout


def test_histogram_demo_catalog_exposes_expected_demo_ids() -> None:
    demo_ids = {spec.demo_id for spec in get_demo_catalog()}

    assert demo_ids == {
        "histogram-counts",
        "histogram-quasi",
        "histogram-qiskit-marginal",
    }


def test_run_histogram_demo_reports_clear_message_when_optional_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = catalog_by_id()["histogram-qiskit-marginal"]

    monkeypatch.setattr(run_histogram_demo_module, "find_spec", lambda name: None)

    with pytest.raises(SystemExit) as exc_info:
        run_histogram_demo_module.load_demo_builder(spec)

    message = str(exc_info.value)

    assert "histogram-qiskit-marginal" in message
    assert "qiskit" in message
    assert 'python.exe -m pip install -e ".[qiskit]"' in message
    assert "Traceback" not in message


def test_run_histogram_demo_script_imports_drawer_from_local_worktree_src() -> None:
    worktree_root = Path(__file__).resolve().parents[1]
    workspace_root = Path(__file__).resolve().parents[3]
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
@pytest.mark.parametrize(
    "demo_id",
    [
        "histogram-counts",
        "histogram-quasi",
    ],
)
def test_histogram_examples_runner_can_render_builtin_demo(
    demo_id: str,
    sandbox_tmp_path: Path,
) -> None:
    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_histogram_demo.py"
    output_path = sandbox_tmp_path / f"{demo_id}.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            demo_id,
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
    assert f"Saved {demo_id} to {output_path}" in result.stdout


@pytest.mark.optional
@pytest.mark.integration
def test_histogram_examples_runner_can_render_qiskit_marginal_demo(
    sandbox_tmp_path: Path,
) -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the histogram qiskit marginal demo")

    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_histogram_demo.py"
    output_path = sandbox_tmp_path / "histogram-qiskit-marginal.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "histogram-qiskit-marginal",
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
