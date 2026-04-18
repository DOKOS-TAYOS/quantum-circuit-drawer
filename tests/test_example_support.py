from __future__ import annotations

import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest


def test_parse_example_args_reads_full_request(monkeypatch: pytest.MonkeyPatch) -> None:
    from examples._shared import ExampleRequest, parse_example_args

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "example.py",
            "--qubits",
            "12",
            "--columns",
            "24",
            "--mode",
            "slider",
            "--view",
            "2d",
            "--topology",
            "grid",
            "--seed",
            "13",
            "--output",
            "demo.png",
            "--figsize",
            "9",
            "4",
            "--hover-matrix",
            "always",
            "--hover-matrix-max-qubits",
            "3",
            "--hover-show-size",
            "--no-show",
        ],
    )

    request = parse_example_args(
        description="Render a demo.",
        default_qubits=8,
        default_columns=6,
        columns_help="Random circuit columns to generate",
    )

    assert request == ExampleRequest(
        qubits=12,
        columns=24,
        mode="slider",
        view="2d",
        topology="grid",
        seed=13,
        output=Path("demo.png"),
        show=False,
        figsize=(9.0, 4.0),
        hover=True,
        hover_matrix="always",
        hover_matrix_max_qubits=3,
        hover_show_size=True,
    )


def test_request_from_namespace_rejects_3d_slider() -> None:
    from examples._shared import request_from_namespace

    args = Namespace(
        qubits=6,
        columns=8,
        mode="slider",
        view="3d",
        topology="line",
        seed=7,
        output=None,
        show=True,
        figsize=(14.0, 8.0),
        hover=True,
        hover_matrix="auto",
        hover_matrix_max_qubits=2,
        hover_show_size=False,
    )

    with pytest.raises(SystemExit, match="Slider mode is only available in 2D"):
        request_from_namespace(args, default_qubits=4, default_columns=5)


def test_request_from_namespace_rejects_non_positive_hover_matrix_max_qubits() -> None:
    from examples._shared import request_from_namespace

    args = Namespace(
        qubits=6,
        columns=8,
        mode="pages",
        view="2d",
        topology="line",
        seed=7,
        output=None,
        show=True,
        figsize=(14.0, 8.0),
        hover=True,
        hover_matrix="auto",
        hover_matrix_max_qubits=0,
        hover_show_size=False,
    )

    with pytest.raises(SystemExit, match="--hover-matrix-max-qubits must be at least 1"):
        request_from_namespace(args, default_qubits=4, default_columns=5)


def test_demo_style_scales_with_columns_and_clamps() -> None:
    from examples._shared import DEFAULT_DEMO_FIGSIZE, demo_style

    assert demo_style(columns=2) == {
        "font_size": 12.0,
        "show_params": True,
        "max_page_width": 6.5,
    }
    assert demo_style(columns=20)["max_page_width"] > 8.5
    assert demo_style(columns=80)["max_page_width"] == 12.0
    assert DEFAULT_DEMO_FIGSIZE == (10.0, 5.5)


def test_build_render_options_enables_hover_in_2d() -> None:
    from examples._shared import ExampleRequest, build_render_options

    from quantum_circuit_drawer import HoverOptions

    request = ExampleRequest(
        qubits=8,
        columns=10,
        mode="pages",
        view="2d",
        topology="grid",
        seed=7,
        output=None,
        show=True,
        figsize=(10.0, 5.5),
        hover=True,
        hover_matrix="always",
        hover_matrix_max_qubits=1,
        hover_show_size=True,
    )

    assert build_render_options(request) == {
        "hover": HoverOptions(
            enabled=True,
            show_size=True,
            show_matrix="always",
            matrix_max_qubits=1,
        )
    }


def test_build_render_options_enables_topology_menu_in_3d() -> None:
    from examples._shared import ExampleRequest, build_render_options

    from quantum_circuit_drawer import HoverOptions

    request = ExampleRequest(
        qubits=8,
        columns=10,
        mode="pages",
        view="3d",
        topology="grid",
        seed=7,
        output=None,
        show=True,
        figsize=(10.0, 5.5),
        hover=True,
        hover_matrix="always",
        hover_matrix_max_qubits=1,
        hover_show_size=True,
    )

    assert build_render_options(request) == {
        "hover": HoverOptions(
            enabled=True,
            show_size=True,
            show_matrix="always",
            matrix_max_qubits=1,
        ),
        "view": "3d",
        "topology": "grid",
        "topology_menu": True,
        "direct": False,
    }


def test_render_example_draws_and_reports_saved_output(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    from examples._shared import ExampleRequest, render_example

    from quantum_circuit_drawer import HoverOptions

    output = sandbox_tmp_path / "render-demo.png"
    draw_calls: list[dict[str, object]] = []

    def fake_draw_quantum_circuit(
        circuit: object,
        framework: str | None = None,
        *,
        style: dict[str, object],
        output: Path | None = None,
        show: bool = True,
        page_slider: bool = False,
        view: str = "2d",
        topology: str = "line",
        topology_menu: bool = False,
        direct: bool = True,
        hover: object = False,
        figsize: tuple[float, float] | None = None,
        **options: object,
    ) -> None:
        draw_calls.append(
            {
                "circuit": circuit,
                "framework": framework,
                "style": style,
                "output": output,
                "show": show,
                "page_slider": page_slider,
                "view": view,
                "topology": topology,
                "topology_menu": topology_menu,
                "direct": direct,
                "hover": hover,
                "figsize": figsize,
                "options": options,
            }
        )

    monkeypatch.setattr("examples._shared.draw_quantum_circuit", fake_draw_quantum_circuit)

    request = ExampleRequest(
        qubits=9,
        columns=20,
        mode="pages",
        view="3d",
        topology="grid",
        seed=7,
        output=output,
        show=False,
        figsize=(9.0, 3.5),
        hover=True,
        hover_matrix="auto",
        hover_matrix_max_qubits=2,
        hover_show_size=False,
    )
    render_example(
        {"kind": "demo"},
        request=request,
        framework="qiskit",
        saved_label="qiskit-random",
    )

    captured = capsys.readouterr()

    assert draw_calls == [
        {
            "circuit": {"kind": "demo"},
            "framework": "qiskit",
            "style": {
                "font_size": 12.0,
                "show_params": True,
                "max_page_width": 8.9,
            },
            "output": output,
            "show": False,
            "page_slider": False,
            "view": "3d",
            "topology": "grid",
            "topology_menu": True,
            "direct": False,
            "hover": HoverOptions(),
            "figsize": (9.0, 3.5),
            "options": {},
        }
    ]
    assert f"Saved qiskit-random to {output}" in captured.out


def test_render_example_disables_explicit_matrices_for_cirq_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import examples._shared as shared_module
    from examples._shared import ExampleRequest, render_example

    draw_calls: list[dict[str, object]] = []

    def fake_draw_quantum_circuit(
        circuit: object,
        framework: str | None = None,
        *,
        style: dict[str, object],
        output: Path | None = None,
        show: bool = True,
        page_slider: bool = False,
        hover: object = False,
        figsize: tuple[float, float] | None = None,
        **options: object,
    ) -> None:
        draw_calls.append(
            {
                "circuit": circuit,
                "framework": framework,
                "style": style,
                "output": output,
                "show": show,
                "page_slider": page_slider,
                "hover": hover,
                "figsize": figsize,
                "options": options,
            }
        )

    monkeypatch.setattr("examples._shared.draw_quantum_circuit", fake_draw_quantum_circuit)
    monkeypatch.setattr(shared_module.sys, "platform", "win32")

    request = ExampleRequest(
        qubits=8,
        columns=12,
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

    render_example({"kind": "demo"}, request=request, framework="cirq", saved_label="cirq-random")

    assert draw_calls[0]["options"]["explicit_matrices"] is False


def test_render_example_keeps_explicit_matrices_for_windows_hover_matrix_always(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import examples._shared as shared_module
    from examples._shared import ExampleRequest, render_example

    draw_calls: list[dict[str, object]] = []

    def fake_draw_quantum_circuit(
        circuit: object,
        framework: str | None = None,
        *,
        style: dict[str, object],
        output: Path | None = None,
        show: bool = True,
        page_slider: bool = False,
        hover: object = False,
        figsize: tuple[float, float] | None = None,
        **options: object,
    ) -> None:
        draw_calls.append(
            {
                "circuit": circuit,
                "framework": framework,
                "style": style,
                "output": output,
                "show": show,
                "page_slider": page_slider,
                "hover": hover,
                "figsize": figsize,
                "options": options,
            }
        )

    monkeypatch.setattr("examples._shared.draw_quantum_circuit", fake_draw_quantum_circuit)
    monkeypatch.setattr(shared_module.sys, "platform", "win32")

    request = ExampleRequest(
        qubits=8,
        columns=12,
        mode="pages",
        view="2d",
        topology="line",
        seed=7,
        output=None,
        show=False,
        figsize=(10.0, 5.5),
        hover=True,
        hover_matrix="always",
        hover_matrix_max_qubits=2,
        hover_show_size=False,
    )

    render_example(
        {"kind": "demo"},
        request=request,
        framework="pennylane",
        saved_label="pennylane-random",
    )

    assert draw_calls[0]["options"]["explicit_matrices"] is True


def test_run_example_builds_subject_from_parsed_request(monkeypatch: pytest.MonkeyPatch) -> None:
    from examples._shared import ExampleRequest, run_example

    request = ExampleRequest(
        qubits=7,
        columns=15,
        mode="slider",
        view="2d",
        topology="star",
        seed=11,
        output=None,
        show=False,
        figsize=(10.0, 5.5),
        hover=True,
        hover_matrix="auto",
        hover_matrix_max_qubits=2,
        hover_show_size=False,
    )
    builder_calls: list[ExampleRequest] = []
    render_calls: list[dict[str, object]] = []
    built_subject = {"kind": "random-demo"}

    def fake_parse_example_args(**_: object) -> ExampleRequest:
        return request

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

    def build_demo(parsed_request: ExampleRequest) -> object:
        builder_calls.append(parsed_request)
        return built_subject

    monkeypatch.setattr("examples._shared.parse_example_args", fake_parse_example_args)
    monkeypatch.setattr("examples._shared.render_example", fake_render_example)

    run_example(
        build_demo,
        description="Render a shared example.",
        framework="cirq",
        saved_label="cirq-random",
        default_qubits=10,
        default_columns=18,
        columns_help="Random circuit columns to generate",
    )

    assert builder_calls == [request]
    assert render_calls == [
        {
            "subject": built_subject,
            "request": request,
            "framework": "cirq",
            "saved_label": "cirq-random",
        }
    ]


def test_shared_example_support_imports_drawer_from_local_worktree_src() -> None:
    worktree_root = Path(__file__).resolve().parents[1]
    workspace_root = Path(__file__).resolve().parents[3]
    examples_dir = worktree_root / "examples"
    expected_module_path = worktree_root / "src" / "quantum_circuit_drawer" / "__init__.py"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import pathlib, sys; "
                f"sys.path.insert(0, r'{examples_dir}'); "
                "import _shared, quantum_circuit_drawer; "
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
