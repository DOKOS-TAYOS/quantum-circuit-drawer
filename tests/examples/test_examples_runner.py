from __future__ import annotations

import importlib
import os
import subprocess
import sys
import warnings
from argparse import Namespace
from importlib.util import find_spec
from pathlib import Path
from types import SimpleNamespace

import examples._shared as shared_module
import examples.ir_basic_workflow as ir_basic_workflow_module
import examples.run_demo as run_demo_module
import matplotlib.pyplot as plt
import pytest
from examples._shared import ExampleRequest
from examples.demo_catalog import DemoSpec, catalog_by_id, examples_directory, get_demo_catalog
from matplotlib.figure import Figure

from tests.paths import external_workspace_root_for, repo_root_for
from tests.support import assert_saved_image_has_visible_content, flatten_operations


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
            mode="auto",
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


@pytest.mark.parametrize(
    ("topology", "expected_qubits"),
    [
        ("star_tree", 10),
        ("honeycomb", 53),
    ],
)
def test_run_demo_with_args_uses_topology_compatible_3d_defaults_when_qubits_omitted(
    monkeypatch: pytest.MonkeyPatch,
    topology: str,
    expected_qubits: int,
) -> None:
    built_subject = {"kind": "3d-pages-controls-demo"}
    builder_calls: list[ExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    spec = DemoSpec(
        demo_id="custom-demo",
        description="Custom demo",
        module_name="examples.qiskit_qaoa",
        builder_name="build_circuit",
        framework="qiskit",
        default_qubits=8,
        default_columns=6,
        columns_help="QAOA layers to generate",
        dependency_module="qiskit",
    )
    args = Namespace(
        list=False,
        demo="custom-demo",
        qubits=None,
        columns=None,
        mode="pages_controls",
        view="3d",
        topology=topology,
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
            qubits=expected_qubits,
            columns=6,
            mode="pages_controls",
            view="3d",
            topology=topology,
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


def test_run_demo_with_args_accepts_2d_pages_controls_mode(
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
        mode="pages_controls",
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
            mode="pages_controls",
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


def test_demo_catalog_exposes_only_the_refreshed_demo_ids() -> None:
    demo_ids = {spec.demo_id for spec in get_demo_catalog()}

    assert demo_ids == {
        "qiskit-random",
        "qiskit-qaoa",
        "qiskit-2d-exploration-showcase",
        "qiskit-control-flow-showcase",
        "qiskit-composite-modes-showcase",
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


def test_ir_basic_workflow_builder_populates_rotation_parameters() -> None:
    circuit = ir_basic_workflow_module.build_circuit(
        ExampleRequest(
            qubits=4,
            columns=3,
            mode="auto",
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
    )

    rotation_parameters = [
        tuple(operation.parameters)
        for operation in flatten_operations(circuit)
        if operation.name == "RZ"
    ]

    assert rotation_parameters == [(0.2,), (0.4,), (0.6000000000000001,)]


def test_qiskit_composite_modes_showcase_build_circuit_avoids_qft_deprecation_warning() -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the QFT deprecation regression test")

    module = importlib.import_module("examples.qiskit_composite_modes_showcase")

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always", DeprecationWarning)
        circuit = module.build_circuit(
            ExampleRequest(
                qubits=5,
                columns=4,
                mode="auto",
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
        )

    assert circuit.num_qubits == 5
    assert not [
        warning
        for warning in caught_warnings
        if issubclass(warning.category, DeprecationWarning) and "QFT" in str(warning.message)
    ]


def test_showcase_docs_reference_the_new_framework_demos() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    examples_readme = Path("examples/README.md").read_text(encoding="utf-8")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    frameworks_guide = Path("docs/frameworks.md").read_text(encoding="utf-8")
    user_guide = Path("docs/user-guide.md").read_text(encoding="utf-8")

    for demo_id in (
        "qiskit-2d-exploration-showcase",
        "qiskit-control-flow-showcase",
        "qiskit-composite-modes-showcase",
        "ir-basic-workflow",
        "cirq-native-controls-showcase",
        "pennylane-terminal-outputs-showcase",
        "myqlm-structural-showcase",
        "cudaq-kernel-showcase",
    ):
        assert demo_id in examples_readme

    assert "Recommended demos" in readme
    assert "qiskit-2d-exploration-showcase" in readme
    assert "qiskit-control-flow-showcase" in readme
    assert "qiskit-composite-modes-showcase" in readme
    assert "pennylane-terminal-outputs-showcase" in readme
    assert "qiskit-2d-exploration-showcase" in docs_index
    assert "qiskit-control-flow-showcase" in frameworks_guide
    assert "qiskit-composite-modes-showcase" in frameworks_guide
    assert "ir-basic-workflow" in frameworks_guide
    assert "cirq-native-controls-showcase" in frameworks_guide
    assert "pennylane-terminal-outputs-showcase" in frameworks_guide
    assert "myqlm-structural-showcase" in frameworks_guide
    assert "cudaq-kernel-showcase" in frameworks_guide
    assert "qiskit-2d-exploration-showcase" in user_guide


def test_showcase_catalog_and_examples_readme_use_current_compatibility_language() -> None:
    examples_readme = Path("examples/README.md").read_text(encoding="utf-8")
    showcase_specs = catalog_by_id()

    assert showcase_specs["qiskit-2d-exploration-showcase"].description == (
        "Qiskit showcase for managed 2D exploration, active-wire filtering, and contextual block controls"
    )
    assert showcase_specs["qiskit-control-flow-showcase"].description == (
        "Qiskit showcase for compact control-flow boxes and open controls"
    )
    assert showcase_specs["qiskit-composite-modes-showcase"].description == (
        "Qiskit showcase for compact versus expanded composite instructions"
    )
    assert showcase_specs["cirq-native-controls-showcase"].description == (
        "Cirq showcase for native controls, classical control, and CircuitOperation provenance"
    )
    assert showcase_specs["pennylane-terminal-outputs-showcase"].description == (
        "PennyLane showcase for mid-measurement, qml.cond(...), and terminal-output boxes"
    )
    assert showcase_specs["myqlm-structural-showcase"].description == (
        "myQLM showcase for compact composite routines on the native adapter path"
    )
    assert showcase_specs["cudaq-kernel-showcase"].description == (
        "CUDA-Q showcase for the supported closed-kernel subset with reset and basis measurements"
    )
    assert showcase_specs["ir-basic-workflow"].description == (
        "Framework-free workflow built directly from the public CircuitIR types"
    )

    assert "qml.cond(...)" in examples_readme
    assert "native MyQLM adapter path" in examples_readme
    assert "supported closed-kernel subset" in examples_readme
    assert "CircuitOperation provenance" in examples_readme
    assert "compact versus expanded composite instructions" in examples_readme
    assert "CircuitIR" in examples_readme
    assert "Wires: All/Active" in examples_readme
    assert "Ancillas: Show/Hide" in examples_readme


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


def test_render_example_closes_rendered_figures(monkeypatch: pytest.MonkeyPatch) -> None:
    closed_figures: list[Figure] = []
    figure_one = Figure()
    figure_two = Figure()

    def fake_draw_quantum_circuit(*args: object, **kwargs: object) -> object:
        return SimpleNamespace(
            primary_figure=figure_one,
            figures=(figure_one, figure_two),
        )

    def track_close(figure: Figure) -> None:
        closed_figures.append(figure)

    monkeypatch.setattr(shared_module, "draw_quantum_circuit", fake_draw_quantum_circuit)
    monkeypatch.setattr(plt, "close", track_close)

    shared_module.render_example(
        {"kind": "demo"},
        request=ExampleRequest(
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
        ),
        framework="cirq",
        saved_label="cleanup-demo",
    )

    assert closed_figures == [figure_one, figure_two]


@pytest.mark.optional
@pytest.mark.integration
@pytest.mark.parametrize(
    ("demo_id", "dependency"),
    [
        ("qiskit-random", "qiskit"),
        ("qiskit-qaoa", "qiskit"),
        ("qiskit-control-flow-showcase", "qiskit"),
        ("cirq-random", "cirq"),
        ("cirq-qaoa", "cirq"),
        ("cirq-native-controls-showcase", "cirq"),
        ("pennylane-random", "pennylane"),
        ("pennylane-qaoa", "pennylane"),
        ("pennylane-terminal-outputs-showcase", "pennylane"),
        ("myqlm-random", "qat"),
        ("myqlm-structural-showcase", "qat"),
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

    script_path = repo_root_for(Path(__file__)) / "examples" / "run_demo.py"
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

    script_path = repo_root_for(Path(__file__)) / "examples" / "run_demo.py"
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

    script_path = repo_root_for(Path(__file__)) / "examples" / "run_demo.py"
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
            "pages_controls",
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

    script_path = repo_root_for(Path(__file__)) / "examples" / "run_demo.py"
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

    script_path = repo_root_for(Path(__file__)) / "examples" / "run_demo.py"
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
        "cirq_native_controls_showcase.py",
    ],
)
def test_cirq_examples_use_narrow_imports(
    module_path: str,
) -> None:
    source = (examples_directory() / module_path).read_text(encoding="utf-8")

    assert "import cirq" not in source
    assert "from cirq.circuits import" in source
    assert "Circuit" in source
    assert "Moment" in source
    assert "from cirq.devices import LineQubit" in source
    assert "from cirq.ops import" in source
    assert "measure" in source


@pytest.mark.parametrize(
    "module_path",
    [
        "pennylane_random.py",
        "pennylane_qaoa.py",
        "pennylane_terminal_outputs_showcase.py",
    ],
)
def test_pennylane_examples_use_narrow_imports(
    module_path: str,
) -> None:
    source = (examples_directory() / module_path).read_text(encoding="utf-8")

    assert "import pennylane as qml" not in source
    assert "from pennylane.tape import QuantumTape" in source
    assert "from pennylane.ops import" in source
    assert "from pennylane.measurements import" in source
    assert "probs" in source


@pytest.mark.parametrize(
    ("demo_id", "dependency", "expected_module_prefix"),
    [
        ("cirq-random", "cirq", "cirq"),
        ("cirq-qaoa", "cirq", "cirq"),
        ("cirq-native-controls-showcase", "cirq", "cirq"),
        ("pennylane-random", "pennylane", "pennylane"),
        ("pennylane-qaoa", "pennylane", "pennylane"),
        ("pennylane-terminal-outputs-showcase", "pennylane", "pennylane"),
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


@pytest.mark.optional
@pytest.mark.integration
def test_qiskit_showcase_script_can_render_directly(sandbox_tmp_path: Path) -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the direct showcase smoke test")

    script_path = repo_root_for(Path(__file__)) / "examples" / "qiskit_control_flow_showcase.py"
    output_path = sandbox_tmp_path / "qiskit-control-flow-showcase-direct.png"

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
    assert f"Saved qiskit-control-flow-showcase to {output_path}" in result.stdout


@pytest.mark.optional
@pytest.mark.integration
def test_qiskit_2d_exploration_showcase_script_can_render_directly(
    sandbox_tmp_path: Path,
) -> None:
    if find_spec("qiskit") is None:
        pytest.skip("qiskit is required for the direct showcase smoke test")

    script_path = repo_root_for(Path(__file__)) / "examples" / "qiskit_2d_exploration_showcase.py"
    output_path = sandbox_tmp_path / "qiskit-2d-exploration-showcase-direct.png"

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
