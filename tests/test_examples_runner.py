from __future__ import annotations

import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

import pytest


def _qiskit_available() -> bool:
    return find_spec("qiskit") is not None


def test_examples_runner_lists_all_demo_ids() -> None:
    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_demo.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--list"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "qiskit-balanced" in result.stdout
    assert "qiskit-qaoa" in result.stdout
    assert "cirq-grover" in result.stdout
    assert "pennylane-deep" in result.stdout
    assert "cudaq-wide" in result.stdout


@pytest.mark.skipif(not _qiskit_available(), reason="Selected example render test requires qiskit")
def test_examples_runner_can_render_a_selected_demo(sandbox_tmp_path: Path) -> None:
    script_path = Path(__file__).resolve().parents[1] / "examples" / "run_demo.py"
    output_path = sandbox_tmp_path / "runner-demo.png"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--demo",
            "qiskit-balanced",
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
