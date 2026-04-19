from __future__ import annotations

import importlib
import os
import subprocess
import sys
from argparse import Namespace
from importlib.util import find_spec
from pathlib import Path

import examples.run_demo as run_demo_module
import pytest
from examples._shared import ExampleRequest
from examples.demo_catalog import DemoSpec, catalog_by_id, examples_directory, get_demo_catalog

from tests.support import assert_saved_image_has_visible_content


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
        assert spec.default_qubits > 0
        assert spec.default_columns > 0
        assert spec.columns_help


def test_run_demo_uses_spec_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    built_subject = {"kind": "default-demo"}
    builder_calls: list[ExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    spec = DemoSpec(
        demo_id="custom-demo",
        description="Custom demo",
        module_name="examples.qiskit_random",
        builder_name="build_circuit",
        framework="qiskit",
        default_qubits=9,
        default_columns=14,
        columns_help="Random circuit columns to generate",
        dependency_module="qiskit",
    )

    def fake_builder(request: ExampleRequest) -> object:
        builder_calls.append(request)
        return built_subject

    def fake_render_example(
        subject: object,
        *,
        request: ExampleRequest,
        framework: str | None,
        saved_label: str,
    ) -> None:
        render_calls.append(
            {
                "subject": subject,
                "request": request,
                "framework": framework,
                "saved_label": saved_label,
            }
        )

    monkeypatch.setattr(run_demo_module, "load_demo_builder", lambda demo_spec: fake_builder)
    monkeypatch.setattr(run_demo_module, "render_example", fake_render_example)

    run_demo_module.run_demo(spec, output=None, show=False)

    assert builder_calls == [
        ExampleRequest(
            qubits=9,
            columns=14,
            mode="pages",
            view="2d",
            topology="line",
            seed=7,
            output=None,
            show=False,
            figsize=(10.0, 5.5),
            hover=True,
            hover_matrix="auto",
            hover_matrix_max_qubits=2,
            hover_show_size=False,
        )
    ]
    assert render_calls == [
        {
            "subject": built_subject,
            "request": builder_calls[0],
            "framework": "qiskit",
            "saved_label": "custom-demo",
        }
    ]


def test_run_demo_with_args_builds_subject_and_renders(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    output = sandbox_tmp_path / "runner-demo.png"
    built_subject = {"kind": "demo"}
    builder_calls: list[ExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    spec = DemoSpec(
        demo_id="custom-demo",
        description="Custom demo",
        module_name="examples.qiskit_random",
        builder_name="build_circuit",
        framework="qiskit",
        default_qubits=8,
        default_columns=6,
        columns_help="Random circuit columns to generate",
        dependency_module="qiskit",
    )
    args = Namespace(
        list=False,
        demo="custom-demo",
        qubits=12,
        columns=20,
        mode="slider",
        view="2d",
        topology="grid",
        seed=19,
        output=output,
        show=False,
        figsize=(9.0, 4.0),
        hover=True,
        hover_matrix="always",
        hover_matrix_max_qubits=3,
        hover_show_size=True,
    )

    def fake_builder(request: ExampleRequest) -> object:
        builder_calls.append(request)
        return built_subject

    def fake_render_example(
        subject: object,
        *,
        request: ExampleRequest,
        framework: str | None,
        saved_label: str,
    ) -> None:
        render_calls.append(
            {
                "subject": subject,
                "request": request,
                "framework": framework,
                "saved_label": saved_label,
            }
        )

    monkeypatch.setattr(run_demo_module, "load_demo_builder", lambda demo_spec: fake_builder)
    monkeypatch.setattr(run_demo_module, "render_example", fake_render_example)

    run_demo_module.run_demo_with_args(spec, args)

    assert builder_calls == [
        ExampleRequest(
            qubits=12,
            columns=20,
            mode="slider",
            view="2d",
            topology="grid",
            seed=19,
            output=output,
            show=False,
            figsize=(9.0, 4.0),
            hover=True,
            hover_matrix="always",
            hover_matrix_max_qubits=3,
            hover_show_size=True,
        )
    ]
    assert render_calls == [
        {
            "subject": built_subject,
            "request": builder_calls[0],
            "framework": "qiskit",
            "saved_label": "custom-demo",
        }
    ]


def test_run_demo_with_args_accepts_3d_slider_and_loads_demo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built_subject = {"kind": "3d-slider-demo"}
    builder_calls: list[ExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    spec = DemoSpec(
        demo_id="custom-demo",
        description="Custom demo",
        module_name="examples.qiskit_random",
        builder_name="build_circuit",
        framework="qiskit",
        default_qubits=8,
        default_columns=6,
        columns_help="Random circuit columns to generate",
        dependency_module="qiskit",
    )
    args = Namespace(
        list=False,
        demo="custom-demo",
        qubits=12,
        columns=20,
        mode="slider",
        view="3d",
        topology="grid",
        seed=19,
        output=None,
        show=False,
        figsize=(9.0, 4.0),
        hover=True,
        hover_matrix="auto",
        hover_matrix_max_qubits=2,
        hover_show_size=False,
    )

    def fake_builder(request: ExampleRequest) -> object:
        builder_calls.append(request)
        return built_subject

    def fake_render_example(
        subject: object,
        *,
        request: ExampleRequest,
        framework: str | None,
        saved_label: str,
    ) -> None:
        render_calls.append(
            {
                "subject": subject,
                "request": request,
                "framework": framework,
                "saved_label": saved_label,
            }
        )

    monkeypatch.setattr(run_demo_module, "load_demo_builder", lambda demo_spec: fake_builder)
    monkeypatch.setattr(run_demo_module, "render_example", fake_render_example)

    run_demo_module.run_demo_with_args(spec, args)

    assert builder_calls == [
        ExampleRequest(
            qubits=12,
            columns=20,
            mode="slider",
            view="3d",
            topology="grid",
            seed=19,
            output=None,
            show=False,
            figsize=(9.0, 4.0),
            hover=True,
            hover_matrix="auto",
            hover_matrix_max_qubits=2,
            hover_show_size=False,
        )
    ]
    assert render_calls == [
        {
            "subject": built_subject,
            "request": builder_calls[0],
            "framework": "qiskit",
            "saved_label": "custom-demo",
        }
    ]


def test_run_demo_with_args_accepts_2d_window_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built_subject = {"kind": "2d-window-demo"}
    builder_calls: list[ExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    spec = DemoSpec(
        demo_id="custom-demo",
        description="Custom demo",
        module_name="examples.qiskit_random",
        builder_name="build_circuit",
        framework="qiskit",
        default_qubits=8,
        default_columns=6,
        columns_help="Random circuit columns to generate",
        dependency_module="qiskit",
    )
    args = Namespace(
        list=False,
        demo="custom-demo",
        qubits=14,
        columns=28,
        mode="window",
        view="2d",
        topology="grid",
        seed=23,
        output=None,
        show=False,
        figsize=(10.0, 5.5),
        hover=True,
        hover_matrix="auto",
        hover_matrix_max_qubits=2,
        hover_show_size=False,
    )

    def fake_builder(request: ExampleRequest) -> object:
        builder_calls.append(request)
        return built_subject

    def fake_render_example(
        subject: object,
        *,
        request: ExampleRequest,
        framework: str | None,
        saved_label: str,
    ) -> None:
        render_calls.append(
            {
                "subject": subject,
                "request": request,
                "framework": framework,
                "saved_label": saved_label,
            }
        )

    monkeypatch.setattr(run_demo_module, "load_demo_builder", lambda demo_spec: fake_builder)
    monkeypatch.setattr(run_demo_module, "render_example", fake_render_example)

    run_demo_module.run_demo_with_args(spec, args)

    assert builder_calls == [
        ExampleRequest(
            qubits=14,
            columns=28,
            mode="window",
            view="2d",
            topology="grid",
            seed=23,
            output=None,
            show=False,
            figsize=(10.0, 5.5),
            hover=True,
            hover_matrix="auto",
            hover_matrix_max_qubits=2,
            hover_show_size=False,
        )
    ]
    assert render_calls == [
        {
            "subject": built_subject,
            "request": builder_calls[0],
            "framework": "qiskit",
            "saved_label": "custom-demo",
        }
    ]


def test_main_requires_demo_or_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_demo_module,
        "parse_args",
        lambda: Namespace(list=False, demo=None, output=None, show=True, figsize=(10.0, 5.5)),
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


def test_demo_catalog_exposes_only_the_refreshed_demo_ids() -> None:
    demo_ids = {spec.demo_id for spec in get_demo_catalog()}

    assert demo_ids == {
        "qiskit-random",
        "qiskit-qaoa",
        "cirq-random",
        "cirq-qaoa",
        "pennylane-random",
        "pennylane-qaoa",
        "myqlm-random",
        "cudaq-random",
    }


def test_run_demo_reports_clear_message_when_optional_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = catalog_by_id()["myqlm-random"]

    monkeypatch.setattr(run_demo_module, "find_spec", lambda name: None)

    with pytest.raises(SystemExit) as exc_info:
        run_demo_module.load_demo_builder(spec)

    message = str(exc_info.value)

    assert "myqlm-random" in message
    assert "qat" in message
    assert 'python.exe -m pip install -e ".[myqlm]"' in message
    assert "Traceback" not in message


def test_run_demo_script_imports_drawer_from_local_worktree_src() -> None:
    worktree_root = Path(__file__).resolve().parents[1]
    workspace_root = Path(__file__).resolve().parents[3]
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


@pytest.mark.optional
@pytest.mark.integration
@pytest.mark.parametrize(
    ("demo_id", "dependency"),
    [
        ("qiskit-random", "qiskit"),
        ("qiskit-qaoa", "qiskit"),
        ("cirq-random", "cirq"),
        ("cirq-qaoa", "cirq"),
        ("pennylane-random", "pennylane"),
        ("pennylane-qaoa", "pennylane"),
        ("myqlm-random", "qat"),
    ],
)
def test_examples_runner_can_render_selected_optional_demo(
    demo_id: str,
    dependency: str,
    sandbox_tmp_path: Path,
) -> None:
    if sys.platform.startswith("win") and dependency in {"cirq", "pennylane"}:
        pytest.skip(f"{dependency} example smoke tests are not reliable on native Windows")

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
            "--qubits",
            "4",
            "--columns",
            "3",
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
def test_examples_runner_can_render_slider_demo_for_random_qiskit(sandbox_tmp_path: Path) -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the slider smoke test")

    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_demo.py"
    output_path = sandbox_tmp_path / "qiskit-slider.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "qiskit-random",
            "--qubits",
            "8",
            "--columns",
            "18",
            "--mode",
            "slider",
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


@pytest.mark.optional
@pytest.mark.integration
def test_examples_runner_can_render_window_demo_for_random_qiskit(sandbox_tmp_path: Path) -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the page-window smoke test")

    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_demo.py"
    output_path = sandbox_tmp_path / "qiskit-window.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "qiskit-random",
            "--qubits",
            "8",
            "--columns",
            "24",
            "--mode",
            "window",
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


@pytest.mark.optional
@pytest.mark.integration
def test_examples_runner_can_render_3d_demo_for_random_qiskit(sandbox_tmp_path: Path) -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the 3D smoke test")

    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_demo.py"
    output_path = sandbox_tmp_path / "qiskit-3d.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "qiskit-random",
            "--qubits",
            "9",
            "--columns",
            "8",
            "--view",
            "3d",
            "--topology",
            "grid",
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


@pytest.mark.optional
@pytest.mark.integration
def test_examples_runner_can_render_3d_slider_demo_for_random_qiskit(
    sandbox_tmp_path: Path,
) -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the 3D slider smoke test")

    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_demo.py"
    output_path = sandbox_tmp_path / "qiskit-3d-slider.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "qiskit-random",
            "--qubits",
            "12",
            "--columns",
            "18",
            "--view",
            "3d",
            "--mode",
            "slider",
            "--topology",
            "grid",
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


@pytest.mark.optional
@pytest.mark.integration
@pytest.mark.parametrize(
    "module_path",
    [
        "cirq_random.py",
        "cirq_qaoa.py",
    ],
)
def test_cirq_examples_use_narrow_imports(
    module_path: str,
) -> None:
    source = (examples_directory() / module_path).read_text(encoding="utf-8")

    assert "import cirq" not in source
    assert "from cirq.circuits import Circuit, Moment" in source
    assert "from cirq.devices import LineQubit" in source
    assert "from cirq.ops import" in source
    assert "measure" in source


@pytest.mark.parametrize(
    "module_path",
    [
        "pennylane_random.py",
        "pennylane_qaoa.py",
    ],
)
def test_pennylane_examples_use_narrow_imports(
    module_path: str,
) -> None:
    source = (examples_directory() / module_path).read_text(encoding="utf-8")

    assert "import pennylane as qml" not in source
    assert "from pennylane.tape import QuantumTape" in source
    assert "from pennylane.ops import" in source
    assert "from pennylane.measurements import probs" in source


@pytest.mark.parametrize(
    ("demo_id", "dependency", "expected_module_prefix"),
    [
        ("cirq-random", "cirq", "cirq"),
        ("cirq-qaoa", "cirq", "cirq"),
        ("pennylane-random", "pennylane", "pennylane"),
        ("pennylane-qaoa", "pennylane", "pennylane"),
    ],
)
def test_optional_demo_builders_return_real_framework_objects(
    demo_id: str,
    dependency: str,
    expected_module_prefix: str,
) -> None:
    if sys.platform.startswith("win") and dependency in {"cirq", "pennylane"}:
        pytest.skip(f"{dependency} builder smoke tests are not reliable on native Windows")

    if find_spec(dependency) is None:
        pytest.skip(f"{dependency} is required for optional demo builder smoke tests")

    spec = catalog_by_id()[demo_id]
    module = importlib.import_module(spec.module_name)
    builder = getattr(module, spec.builder_name)
    request = ExampleRequest(
        qubits=4,
        columns=3,
        mode="pages",
        view="2d",
        topology="line",
        seed=7,
        output=None,
        show=False,
        figsize=(10.0, 5.5),
        hover=True,
        hover_matrix="auto",
        hover_matrix_max_qubits=2,
        hover_show_size=False,
    )

    built_subject = builder(request)

    assert type(built_subject).__module__.startswith(expected_module_prefix)
