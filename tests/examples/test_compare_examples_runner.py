from __future__ import annotations

import importlib
import subprocess
import sys
import warnings
from argparse import Namespace
from pathlib import Path

import examples.run_compare_demo as run_compare_demo_module
import pytest
from examples._compare_shared import CompareDemoPayload, CompareExampleRequest
from examples.compare_demo_catalog import (
    CompareDemoSpec,
    catalog_by_id,
    examples_directory,
    get_demo_catalog,
)

from quantum_circuit_drawer import CircuitCompareConfig, OutputOptions
from tests.paths import repo_root_for
from tests.support import assert_saved_image_has_visible_content


def test_compare_demo_catalog_entries_are_unique_and_reference_existing_example_files() -> None:
    catalog = get_demo_catalog()
    demo_ids = [spec.demo_id for spec in catalog]

    assert len(demo_ids) == len(set(demo_ids))
    assert set(catalog_by_id()) == set(demo_ids)

    for spec in catalog:
        example_path = examples_directory() / f"{spec.module_name.removeprefix('examples.')}.py"

        assert catalog_by_id()[spec.demo_id] == spec
        assert example_path.exists()
        assert spec.builder_name == "build_demo"
        assert spec.compare_kind in {"circuits", "histograms"}


def test_run_compare_demo_uses_spec_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = CompareDemoPayload(
        compare_kind="circuits",
        left_data={"kind": "left"},
        right_data={"kind": "right"},
        config=CircuitCompareConfig(output=OutputOptions(show=True)),
    )
    builder_calls: list[CompareExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    spec = CompareDemoSpec(
        demo_id="custom-compare-demo",
        description="Custom compare demo",
        module_name="examples.compare_circuits_qiskit_transpile",
        builder_name="build_demo",
        compare_kind="circuits",
        dependency_module="qiskit",
    )

    def fake_builder(request: CompareExampleRequest) -> CompareDemoPayload:
        builder_calls.append(request)
        return payload

    def fake_render_compare_example(
        built_payload: CompareDemoPayload,
        *,
        request: CompareExampleRequest,
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
        run_compare_demo_module,
        "load_demo_builder",
        lambda demo_spec: fake_builder,
    )
    monkeypatch.setattr(
        run_compare_demo_module,
        "render_compare_example",
        fake_render_compare_example,
    )

    run_compare_demo_module.run_demo(spec, output=None, show=False)

    assert builder_calls == [
        CompareExampleRequest(
            left_label=None,
            right_label=None,
            highlight_differences=None,
            show_summary=None,
            sort=None,
            top_k=None,
            output=None,
            show=False,
            figsize=(11.0, 5.6),
        )
    ]
    assert render_calls == [
        {
            "payload": payload,
            "request": builder_calls[0],
            "saved_label": "custom-compare-demo",
        }
    ]


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


def test_compare_demo_catalog_exposes_expected_demo_ids() -> None:
    demo_ids = {spec.demo_id for spec in get_demo_catalog()}

    assert demo_ids == {
        "compare-circuits-qiskit-transpile",
        "compare-circuits-composite-modes",
        "compare-histograms-ideal-vs-sampled",
    }


def test_compare_examples_readme_mentions_histogram_legend_toggle() -> None:
    examples_readme = Path("examples/README.md").read_text(encoding="utf-8")

    assert "compare-histograms-ideal-vs-sampled" in examples_readme
    assert "legend" in examples_readme.lower()


def test_compare_composite_modes_builder_avoids_qft_deprecation_warning() -> None:
    if run_compare_demo_module.find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the QFT deprecation regression test")

    module = importlib.import_module("examples.compare_circuits_composite_modes")

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always", DeprecationWarning)
        payload = module.build_demo(
            CompareExampleRequest(
                left_label=None,
                right_label=None,
                highlight_differences=None,
                show_summary=None,
                sort=None,
                top_k=None,
                output=None,
                show=False,
                figsize=(11.0, 5.6),
            )
        )

    assert payload.compare_kind == "circuits"
    assert not [
        warning
        for warning in caught_warnings
        if issubclass(warning.category, DeprecationWarning) and "QFT" in str(warning.message)
    ]


def test_compare_main_requires_demo_or_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_compare_demo_module,
        "parse_args",
        lambda: Namespace(
            list=False,
            demo=None,
            output=None,
            show=True,
            figsize=(11.0, 5.6),
        ),
    )

    with pytest.raises(SystemExit, match="Choose one compare demo with --demo or use --list"):
        run_compare_demo_module.main()


def test_run_compare_demo_reports_clear_message_when_optional_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = catalog_by_id()["compare-circuits-qiskit-transpile"]

    monkeypatch.setattr(run_compare_demo_module, "find_spec", lambda name: None)

    with pytest.raises(SystemExit) as exc_info:
        run_compare_demo_module.load_demo_builder(spec)

    message = str(exc_info.value)

    assert "compare-circuits-qiskit-transpile" in message
    assert "qiskit" in message
    assert 'python.exe -m pip install -e ".[qiskit]"' in message
    assert "Traceback" not in message


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
        pytest.skip("qiskit is required for the direct compare-circuits smoke test")

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
