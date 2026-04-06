from __future__ import annotations

import subprocess
import sys
from argparse import Namespace
from importlib.util import find_spec
from pathlib import Path

import examples.run_demo as run_demo_module
import pytest
from examples.demo_catalog import DemoSpec, catalog_by_id, examples_directory, get_demo_catalog


def test_demo_catalog_entries_are_unique_and_reference_existing_example_files() -> None:
    catalog = get_demo_catalog()
    demo_ids = [spec.demo_id for spec in catalog]

    assert len(demo_ids) == len(set(demo_ids))
    assert set(catalog_by_id()) == set(demo_ids)

    for spec in catalog:
        example_path = examples_directory() / f"{spec.module_name.removeprefix('examples.')}.py"

        assert catalog_by_id()[spec.demo_id] == spec
        assert example_path.exists()
        assert spec.builder_name in {"build_circuit", "build_tape", "build_kernel"}
        assert spec.style["show_params"] is True
        assert "max_page_width" in spec.style
        assert isinstance(spec.page_slider, bool)


def test_run_demo_passes_spec_to_draw_quantum_circuit_and_reports_output(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    output = sandbox_tmp_path / "runner-demo.png"
    built_subject = {"kind": "demo"}
    draw_calls: list[dict[str, object]] = []
    builder_calls: list[str] = []
    spec = DemoSpec(
        demo_id="custom-demo",
        description="Custom demo",
        module_name="examples.qiskit_example",
        builder_name="build_circuit",
        framework="qiskit",
        style={"theme": "paper"},
        page_slider=True,
        composite_mode="expand",
    )

    def fake_builder() -> object:
        builder_calls.append("called")
        return built_subject

    def fake_draw_quantum_circuit(
        circuit: object,
        framework: str | None = None,
        *,
        style: dict[str, object],
        output: Path | None = None,
        show: bool = True,
        page_slider: bool = False,
        composite_mode: str = "compact",
    ) -> None:
        draw_calls.append(
            {
                "circuit": circuit,
                "framework": framework,
                "style": style,
                "output": output,
                "show": show,
                "page_slider": page_slider,
                "composite_mode": composite_mode,
            }
        )

    monkeypatch.setattr(run_demo_module, "load_demo_builder", lambda demo_spec: fake_builder)
    monkeypatch.setattr(run_demo_module, "draw_quantum_circuit", fake_draw_quantum_circuit)

    run_demo_module.run_demo(spec, output=output, show=False)

    captured = capsys.readouterr()

    assert builder_calls == ["called"]
    assert draw_calls == [
        {
            "circuit": built_subject,
            "framework": "qiskit",
            "style": {"theme": "paper"},
            "output": output,
            "show": False,
            "page_slider": True,
            "composite_mode": "expand",
        }
    ]
    assert f"Saved {spec.demo_id} to {output}" in captured.out


def test_main_requires_demo_or_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_demo_module,
        "parse_args",
        lambda: Namespace(list=False, demo=None, output=None, show=True),
    )

    with pytest.raises(SystemExit, match="Choose one demo with --demo or use --list"):
        run_demo_module.main()


def test_examples_runner_lists_all_demo_ids() -> None:
    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_demo.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--list"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    for spec in get_demo_catalog():
        assert spec.demo_id in result.stdout


def test_demo_catalog_exposes_new_classical_control_and_composite_demos() -> None:
    demo_ids = {spec.demo_id for spec in get_demo_catalog()}

    assert {
        "qiskit-conditional-composite",
        "cirq-conditional-composite",
        "pennylane-conditional-composite",
    }.issubset(demo_ids)


@pytest.mark.parametrize(
    ("demo_id", "dependency"),
    [
        ("qiskit-balanced", "qiskit"),
        ("qiskit-conditional-composite", "qiskit"),
        ("cirq-balanced", "cirq"),
        ("cirq-conditional-composite", "cirq"),
        ("pennylane-balanced", "pennylane"),
        ("pennylane-conditional-composite", "pennylane"),
    ],
)
def test_examples_runner_can_render_selected_optional_demo(
    demo_id: str,
    dependency: str,
    sandbox_tmp_path: Path,
) -> None:
    if find_spec(dependency) is None:
        pytest.skip(f"{dependency} is required for optional example smoke tests")

    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_demo.py"
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
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert f"Saved {demo_id} to {output_path}" in result.stdout
