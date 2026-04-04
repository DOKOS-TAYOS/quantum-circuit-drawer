from __future__ import annotations

import json
import subprocess
import sys


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
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())

    assert payload["version"] == "0.1.1"
    assert payload["matplotlib_modules"] == []


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
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip()) == []
