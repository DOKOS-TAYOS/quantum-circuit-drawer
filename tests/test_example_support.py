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


def test_request_from_namespace_accepts_3d_slider() -> None:
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

    request = request_from_namespace(args, default_qubits=4, default_columns=5)

    assert request.mode == "slider"
    assert request.view == "3d"
    assert request.topology == "line"


def test_request_from_namespace_accepts_2d_window() -> None:
    from examples._shared import request_from_namespace

    args = Namespace(
        qubits=6,
        columns=8,
        mode="pages_controls",
        view="2d",
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

    request = request_from_namespace(args, default_qubits=4, default_columns=5)

    assert request.mode == "pages_controls"
    assert request.view == "2d"
    assert request.topology == "line"


def test_request_from_namespace_accepts_3d_pages_controls() -> None:
    from examples._shared import request_from_namespace

    args = Namespace(
        qubits=6,
        columns=8,
        mode="pages_controls",
        view="3d",
        topology="grid",
        seed=7,
        output=None,
        show=True,
        figsize=(14.0, 8.0),
        hover=True,
        hover_matrix="auto",
        hover_matrix_max_qubits=2,
        hover_show_size=False,
    )

    request = request_from_namespace(args, default_qubits=4, default_columns=5)

    assert request.mode == "pages_controls"
    assert request.view == "3d"
    assert request.topology == "grid"


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


def test_build_draw_config_enables_hover_in_2d() -> None:
    from examples._shared import ExampleRequest, build_draw_config, demo_style

    from quantum_circuit_drawer import DrawMode, HoverOptions

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

    config = build_draw_config(request, framework="qiskit")

    assert config.framework == "qiskit"
    assert config.mode is DrawMode.PAGES
    assert config.view == "2d"
    assert config.topology == "grid"
    assert config.topology_menu is False
    assert config.direct is True
    assert config.show is True
    assert config.output_path is None
    assert config.figsize == (10.0, 5.5)
    assert config.style.font_size == demo_style(columns=10)["font_size"]
    assert config.style.show_params is demo_style(columns=10)["show_params"]
    assert config.style.max_page_width == pytest.approx(demo_style(columns=10)["max_page_width"])
    assert config.hover == HoverOptions(
        enabled=True,
        show_size=True,
        show_matrix="always",
        matrix_max_qubits=1,
    )


def test_build_draw_config_enables_topology_menu_in_3d_interactive_modes() -> None:
    from examples._shared import ExampleRequest, build_draw_config

    from quantum_circuit_drawer import DrawMode, HoverOptions

    request = ExampleRequest(
        qubits=8,
        columns=10,
        mode="pages_controls",
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

    config = build_draw_config(request, framework=None)

    assert config.framework is None
    assert config.mode is DrawMode.PAGES_CONTROLS
    assert config.view == "3d"
    assert config.topology == "grid"
    assert config.topology_menu is True
    assert config.direct is False
    assert config.hover == HoverOptions(
        enabled=True,
        show_size=True,
        show_matrix="always",
        matrix_max_qubits=1,
    )


def test_render_example_draws_and_reports_saved_output(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    from examples._shared import ExampleRequest, render_example

    from quantum_circuit_drawer import DrawConfig, DrawMode, HoverOptions

    output = sandbox_tmp_path / "render-demo.png"
    draw_calls: list[dict[str, object]] = []

    def fake_draw_quantum_circuit(
        circuit: object,
        *,
        config: DrawConfig | None = None,
        ax: object = None,
    ) -> None:
        draw_calls.append(
            {
                "circuit": circuit,
                "config": config,
                "ax": ax,
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

    assert len(draw_calls) == 1
    assert draw_calls[0]["circuit"] == {"kind": "demo"}
    assert draw_calls[0]["ax"] is None
    config = draw_calls[0]["config"]
    assert isinstance(config, DrawConfig)
    assert config.framework == "qiskit"
    assert config.mode is DrawMode.PAGES
    assert config.view == "3d"
    assert config.topology == "grid"
    assert config.topology_menu is False
    assert config.direct is False
    assert config.show is False
    assert config.output_path == output
    assert config.figsize == (9.0, 3.5)
    assert config.style.max_page_width == pytest.approx(8.9)
    assert config.hover == HoverOptions()
    assert f"Saved qiskit-random to {output}" in captured.out


def test_render_example_forwards_page_slider_in_3d_slider_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from examples._shared import ExampleRequest, render_example

    from quantum_circuit_drawer import DrawConfig, DrawMode, HoverOptions

    draw_calls: list[dict[str, object]] = []

    def fake_draw_quantum_circuit(
        circuit: object,
        *,
        config: DrawConfig | None = None,
        ax: object = None,
    ) -> None:
        draw_calls.append(
            {
                "circuit": circuit,
                "config": config,
                "ax": ax,
            }
        )

    monkeypatch.setattr("examples._shared.draw_quantum_circuit", fake_draw_quantum_circuit)

    request = ExampleRequest(
        qubits=12,
        columns=20,
        mode="slider",
        view="3d",
        topology="grid",
        seed=7,
        output=None,
        show=False,
        figsize=(10.0, 5.5),
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

    assert len(draw_calls) == 1
    assert draw_calls[0]["circuit"] == {"kind": "demo"}
    assert draw_calls[0]["ax"] is None
    config = draw_calls[0]["config"]
    assert isinstance(config, DrawConfig)
    assert config.framework == "qiskit"
    assert config.mode is DrawMode.SLIDER
    assert config.view == "3d"
    assert config.topology == "grid"
    assert config.topology_menu is True
    assert config.direct is False
    assert config.show is False
    assert config.output_path is None
    assert config.figsize == (10.0, 5.5)
    assert config.style.max_page_width == pytest.approx(8.9)
    assert config.hover == HoverOptions()


def test_render_example_forwards_pages_controls_in_2d_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from examples._shared import ExampleRequest, render_example

    from quantum_circuit_drawer import DrawConfig, DrawMode, HoverOptions

    draw_calls: list[dict[str, object]] = []

    def fake_draw_quantum_circuit(
        circuit: object,
        *,
        config: DrawConfig | None = None,
        ax: object = None,
    ) -> None:
        draw_calls.append(
            {
                "circuit": circuit,
                "config": config,
                "ax": ax,
            }
        )

    monkeypatch.setattr("examples._shared.draw_quantum_circuit", fake_draw_quantum_circuit)

    request = ExampleRequest(
        qubits=12,
        columns=24,
        mode="pages_controls",
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

    render_example(
        {"kind": "demo"},
        request=request,
        framework="qiskit",
        saved_label="qiskit-random-pages-controls",
    )

    assert len(draw_calls) == 1
    assert draw_calls[0]["circuit"] == {"kind": "demo"}
    assert draw_calls[0]["ax"] is None
    config = draw_calls[0]["config"]
    assert isinstance(config, DrawConfig)
    assert config.framework == "qiskit"
    assert config.mode is DrawMode.PAGES_CONTROLS
    assert config.view == "2d"
    assert config.topology == "line"
    assert config.topology_menu is False
    assert config.direct is True
    assert config.show is False
    assert config.output_path is None
    assert config.figsize == (10.0, 5.5)
    assert config.style.max_page_width == pytest.approx(9.78)
    assert config.hover == HoverOptions()


def test_demo_adapter_options_disables_explicit_matrices_for_cirq_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import examples._shared as shared_module
    from examples._shared import ExampleRequest, demo_adapter_options

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

    assert demo_adapter_options(request, framework="cirq") == {"explicit_matrices": False}


def test_demo_adapter_options_keeps_explicit_matrices_for_windows_hover_matrix_always(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import examples._shared as shared_module
    from examples._shared import ExampleRequest, demo_adapter_options

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

    assert demo_adapter_options(request, framework="pennylane") == {"explicit_matrices": True}


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
