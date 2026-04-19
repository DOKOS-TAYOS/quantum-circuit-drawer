from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer import DrawResult
from quantum_circuit_drawer.ir.operations import OperationKind


def _benchmark_script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "benchmark_render.py"


def _load_benchmark_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "benchmark_render_script", _benchmark_script_path()
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_synthetic_circuit_creates_expected_shape() -> None:
    benchmark_module = _load_benchmark_module()

    circuit = benchmark_module.build_synthetic_circuit(wires=4, layers=3)

    assert circuit.quantum_wire_count == 4
    assert len(circuit.layers) == 3
    assert [operation.kind for operation in circuit.layers[0].operations] == [
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
    ]


def test_parse_args_reads_custom_values() -> None:
    benchmark_module = _load_benchmark_module()

    args = benchmark_module.parse_args(
        ["--wires", "4", "--layers", "8", "--repeats", "2", "--json"]
    )

    assert args.wires == 4
    assert args.layers == 8
    assert args.repeats == 2
    assert args.emit_json is True
    assert args.benchmark == "synthetic"


def test_parse_args_reads_3d_render_options() -> None:
    benchmark_module = _load_benchmark_module()

    args = benchmark_module.parse_args(
        ["--wires", "4", "--layers", "8", "--repeats", "2", "--view", "3d", "--topology", "grid"]
    )

    assert args.view == "3d"
    assert args.topology == "grid"


def test_parse_args_rejects_non_positive_values() -> None:
    benchmark_module = _load_benchmark_module()

    with pytest.raises(SystemExit):
        benchmark_module.parse_args(["--repeats", "0"])


def test_main_emits_human_readable_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    benchmark_module = _load_benchmark_module()

    monkeypatch.setattr(
        benchmark_module,
        "benchmark_render",
        lambda wires, layers, repeats, view="2d", topology="line": {
            "wires": wires,
            "layers": layers,
            "repeats": repeats,
            "view": view,
            "topology": topology,
            "prepare_seconds": 0.01,
            "layout_seconds": 0.02,
            "render_seconds": 0.03,
            "full_draw_seconds": 0.04,
        },
    )

    exit_code = benchmark_module.main(["--wires", "4", "--layers", "8", "--repeats", "1"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Synthetic benchmark:" in captured.out
    assert "wires=4" in captured.out
    assert "layers=8" in captured.out
    assert "full_draw=0.040000s" in captured.out


def test_main_emits_3d_summary_with_topology(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    benchmark_module = _load_benchmark_module()

    monkeypatch.setattr(
        benchmark_module,
        "benchmark_render",
        lambda wires, layers, repeats, view="2d", topology="line": {
            "wires": wires,
            "layers": layers,
            "repeats": repeats,
            "view": view,
            "topology": topology,
            "prepare_seconds": 0.01,
            "layout_seconds": 0.02,
            "render_seconds": 0.03,
            "full_draw_seconds": 0.04,
        },
    )

    exit_code = benchmark_module.main(
        ["--wires", "4", "--layers", "8", "--repeats", "1", "--view", "3d", "--topology", "grid"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "view=3d" in captured.out
    assert "topology=grid" in captured.out


def test_benchmark_render_script_emits_json_summary() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_benchmark_script_path()),
            "--wires",
            "4",
            "--layers",
            "8",
            "--repeats",
            "1",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["wires"] == 4
    assert payload["layers"] == 8
    assert payload["repeats"] == 1
    assert payload["prepare_seconds"] >= 0.0
    assert payload["layout_seconds"] >= 0.0
    assert payload["render_seconds"] >= 0.0
    assert payload["full_draw_seconds"] >= 0.0


def test_benchmark_render_script_emits_json_summary_for_3d() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_benchmark_script_path()),
            "--wires",
            "4",
            "--layers",
            "8",
            "--repeats",
            "1",
            "--view",
            "3d",
            "--topology",
            "grid",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["view"] == "3d"
    assert payload["topology"] == "grid"
    assert payload["wires"] == 4
    assert payload["layers"] == 8
    assert payload["repeats"] == 1
    assert payload["prepare_seconds"] >= 0.0
    assert payload["layout_seconds"] >= 0.0
    assert payload["render_seconds"] >= 0.0
    assert payload["full_draw_seconds"] >= 0.0


def test_benchmark_demo_returns_phase_breakdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    benchmark_module = _load_benchmark_module()
    fake_spec = SimpleNamespace(
        demo_id="demo-a",
        module_name="examples.demo_a",
        builder_name="build_circuit",
        framework="fake",
        default_qubits=4,
        default_columns=3,
    )
    fake_subject = object()
    fake_ir = SimpleNamespace(
        layers=(SimpleNamespace(operations=(1, 2, 3)),),
        quantum_wire_count=4,
        classical_wire_count=2,
    )

    monkeypatch.setattr(benchmark_module, "catalog_by_id", lambda: {"demo-a": fake_spec})
    monkeypatch.setattr(
        benchmark_module.importlib,
        "import_module",
        lambda name: SimpleNamespace(build_circuit=lambda request: fake_subject),
    )
    monkeypatch.setattr(
        benchmark_module,
        "get_adapter",
        lambda circuit, framework: SimpleNamespace(to_ir=lambda circuit, options=None: fake_ir),
    )
    monkeypatch.setattr(
        benchmark_module,
        "draw_quantum_circuit",
        lambda *args, **kwargs: DrawResult(
            primary_figure=SimpleNamespace(clear=lambda: None),
            primary_axes=object(),
            figures=(SimpleNamespace(clear=lambda: None),),
            axes=(object(),),
            mode="pages",  # type: ignore[arg-type]
            page_count=1,
        ),
    )

    time_points = iter((0.0, 0.2, 0.5, 0.9, 1.4))
    monkeypatch.setattr(benchmark_module, "perf_counter", lambda: next(time_points))

    results = benchmark_module.benchmark_demo(
        demo_id="demo-a",
        qubits=4,
        columns=3,
        mode="pages",
        repeats=1,
    )

    assert results == {
        "demo_id": "demo-a",
        "framework": "fake",
        "qubits": 4,
        "columns": 3,
        "mode": "pages",
        "repeats": 1,
        "import_seconds": pytest.approx(0.2),
        "build_seconds": pytest.approx(0.3),
        "adapt_seconds": pytest.approx(0.4),
        "draw_seconds": pytest.approx(0.5),
        "total_seconds": pytest.approx(1.4),
        "operation_count": 3,
        "quantum_wires": 4,
        "classical_wires": 2,
    }


def test_benchmark_demo_disables_explicit_matrices_for_windows_cirq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    benchmark_module = _load_benchmark_module()
    import examples._shared as shared_module

    fake_spec = SimpleNamespace(
        demo_id="cirq-demo",
        module_name="examples.demo_a",
        builder_name="build_circuit",
        framework="cirq",
        default_qubits=4,
        default_columns=3,
    )
    captured_options: list[dict[str, object] | None] = []
    fake_ir = SimpleNamespace(
        layers=(SimpleNamespace(operations=(1,)),),
        quantum_wire_count=4,
        classical_wire_count=0,
    )

    monkeypatch.setattr(benchmark_module, "catalog_by_id", lambda: {"cirq-demo": fake_spec})
    monkeypatch.setattr(
        benchmark_module.importlib,
        "import_module",
        lambda name: SimpleNamespace(build_circuit=lambda request: object()),
    )
    monkeypatch.setattr(
        benchmark_module,
        "get_adapter",
        lambda circuit, framework: SimpleNamespace(
            to_ir=lambda circuit, options=None: (
                captured_options.append(dict(options or {})) or fake_ir
            )
        ),
    )
    monkeypatch.setattr(
        benchmark_module,
        "draw_quantum_circuit",
        lambda *args, **kwargs: DrawResult(
            primary_figure=SimpleNamespace(clear=lambda: None),
            primary_axes=object(),
            figures=(SimpleNamespace(clear=lambda: None),),
            axes=(object(),),
            mode="pages",  # type: ignore[arg-type]
            page_count=1,
        ),
    )
    monkeypatch.setattr(shared_module.sys, "platform", "win32")

    benchmark_module.benchmark_demo(
        demo_id="cirq-demo",
        qubits=4,
        columns=3,
        mode="pages",
        repeats=1,
    )

    assert captured_options == [{"composite_mode": "compact", "explicit_matrices": False}]


def test_benchmark_demo_scenarios_cover_expected_multi_framework_cases() -> None:
    benchmark_module = _load_benchmark_module()

    scenarios = benchmark_module.demo_benchmark_scenarios()

    assert scenarios == (
        ("qiskit-random", 24, 32, "pages"),
        ("cirq-random", 24, 32, "pages"),
        ("cirq-qaoa", 18, 12, "slider"),
        ("pennylane-random", 24, 32, "pages"),
        ("pennylane-qaoa", 18, 12, "slider"),
        ("myqlm-random", 24, 32, "pages"),
    )


def test_main_emits_demo_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    benchmark_module = _load_benchmark_module()
    monkeypatch.setattr(
        benchmark_module,
        "benchmark_demo",
        lambda demo_id, qubits, columns, mode, repeats: {
            "demo_id": demo_id,
            "framework": "fake",
            "qubits": qubits,
            "columns": columns,
            "mode": mode,
            "repeats": repeats,
            "import_seconds": 0.01,
            "build_seconds": 0.02,
            "adapt_seconds": 0.03,
            "draw_seconds": 0.04,
            "total_seconds": 0.1,
        },
    )

    exit_code = benchmark_module.main(
        [
            "--benchmark",
            "demo",
            "--demo-id",
            "qiskit-random",
            "--qubits",
            "8",
            "--columns",
            "12",
            "--mode",
            "slider",
            "--repeats",
            "2",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Demo benchmark:" in captured.out
    assert "id=qiskit-random" in captured.out
    assert "mode=slider" in captured.out
    assert "total=0.100000s" in captured.out


def test_main_emits_demo_suite_json_with_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    benchmark_module = _load_benchmark_module()

    monkeypatch.setattr(
        benchmark_module,
        "demo_benchmark_scenarios",
        lambda: (("ok-demo", 4, 8, "pages"), ("bad-demo", 6, 10, "slider")),
    )

    def fake_benchmark_demo(
        demo_id: str,
        qubits: int,
        columns: int,
        mode: str,
        repeats: int,
    ) -> dict[str, float | int | str]:
        if demo_id == "bad-demo":
            raise RuntimeError("missing dependency")
        return {
            "demo_id": demo_id,
            "framework": "fake",
            "qubits": qubits,
            "columns": columns,
            "mode": mode,
            "repeats": repeats,
            "import_seconds": 0.01,
            "build_seconds": 0.02,
            "adapt_seconds": 0.03,
            "draw_seconds": 0.04,
            "total_seconds": 0.1,
        }

    monkeypatch.setattr(benchmark_module, "benchmark_demo", fake_benchmark_demo)

    exit_code = benchmark_module.main(["--benchmark", "demo-suite", "--repeats", "1", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload[0]["demo_id"] == "ok-demo"
    assert payload[1]["demo_id"] == "bad-demo"
    assert "missing dependency" in payload[1]["error"]
