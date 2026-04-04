from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_benchmark_render_script_emits_json_summary() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_render.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
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
    assert payload["layout_seconds"] >= 0.0
    assert payload["render_seconds"] >= 0.0
