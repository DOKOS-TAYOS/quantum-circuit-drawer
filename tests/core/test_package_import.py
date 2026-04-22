from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.paths import repo_root_for


def _subprocess_env() -> dict[str, str]:
    src_path = repo_root_for(Path(__file__)) / "src"
    current_pythonpath = os.environ.get("PYTHONPATH")
    pythonpath_parts = [str(src_path)]
    if current_pythonpath:
        pythonpath_parts.append(current_pythonpath)
    return {**os.environ, "PYTHONPATH": os.pathsep.join(pythonpath_parts)}


def test_package_import_does_not_eagerly_import_matplotlib() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys; "
                "import quantum_circuit_drawer; "
                "print(json.dumps({"
                "'version': quantum_circuit_drawer.__version__, "
                "'matplotlib_modules': sorted("
                "name for name in sys.modules if name == 'matplotlib' or name.startswith('matplotlib.')"
                ")"
                "}))"
            ),
        ],
        capture_output=True,
        env=_subprocess_env(),
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())

    assert payload["version"] == "0.4.0"
    assert payload["matplotlib_modules"] == []


def test_package_import_does_not_eagerly_import_qiskit() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys; "
                "import quantum_circuit_drawer; "
                "print(json.dumps(sorted("
                "name for name in sys.modules if name == 'qiskit' or name.startswith('qiskit.')"
                ")))"
            ),
        ],
        capture_output=True,
        env=_subprocess_env(),
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip()) == []


def test_api_module_import_does_not_eagerly_import_matplotlib() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys; "
                "import quantum_circuit_drawer.api; "
                "print(json.dumps(sorted("
                "name for name in sys.modules if name == 'matplotlib' or name.startswith('matplotlib.')"
                ")))"
            ),
        ],
        capture_output=True,
        env=_subprocess_env(),
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip()) == []


def test_histogram_module_import_does_not_eagerly_import_qiskit() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys; "
                "import quantum_circuit_drawer.histogram; "
                "print(json.dumps(sorted("
                "name for name in sys.modules if name == 'qiskit' or name.startswith('qiskit.')"
                ")))"
            ),
        ],
        capture_output=True,
        env=_subprocess_env(),
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip()) == []
