from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

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
        lambda wires, layers, repeats: {
            "wires": wires,
            "layers": layers,
            "repeats": repeats,
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
