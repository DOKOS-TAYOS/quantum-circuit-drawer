from __future__ import annotations

import json
import tomllib
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt

from quantum_circuit_drawer import DrawConfig, DrawMode, HistogramConfig, HistogramMode
from tests.support import assert_saved_image_has_visible_content


def test_cli_draw_builds_hidden_3d_config_and_reports_output(
    monkeypatch,
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    from quantum_circuit_drawer import cli

    captured: dict[str, object] = {}
    qasm_path = sandbox_tmp_path / "bell.qasm"
    output_path = sandbox_tmp_path / "bell.png"
    qasm_path.write_text('OPENQASM 2.0; include "qelib1.inc"; qreg q[2];', encoding="utf-8")

    def fake_draw_quantum_circuit(
        circuit: object,
        *,
        config: DrawConfig | None = None,
    ) -> object:
        captured["circuit"] = circuit
        captured["config"] = config
        return SimpleNamespace(saved_path=str(output_path.resolve()))

    monkeypatch.setattr(cli, "draw_quantum_circuit", fake_draw_quantum_circuit)

    exit_code = cli.main(
        [
            "draw",
            str(qasm_path),
            "--output",
            str(output_path),
            "--view",
            "3d",
        ]
    )

    assert exit_code == 0
    assert captured["circuit"] == str(qasm_path)
    config = captured["config"]
    assert isinstance(config, DrawConfig)
    assert config.show is False
    assert config.output_path == output_path
    assert config.view == "3d"
    assert config.mode is DrawMode.PAGES
    assert config.direct is False
    assert "Saved circuit to" in capsys.readouterr().out


def test_cli_histogram_writes_image_from_counts_json(sandbox_tmp_path: Path) -> None:
    from quantum_circuit_drawer import cli

    counts_path = sandbox_tmp_path / "counts.json"
    output_path = sandbox_tmp_path / "counts.png"
    counts_path.write_text(json.dumps({"00": 5, "11": 3}), encoding="utf-8")

    exit_code = cli.main(["histogram", str(counts_path), "--output", str(output_path)])

    assert exit_code == 0
    assert_saved_image_has_visible_content(output_path)

    plt.close("all")


def test_cli_histogram_data_key_selects_nested_json_mapping(
    monkeypatch,
    sandbox_tmp_path: Path,
) -> None:
    from quantum_circuit_drawer import cli

    payload_path = sandbox_tmp_path / "payload.json"
    output_path = sandbox_tmp_path / "nested.png"
    payload_path.write_text(json.dumps({"counts": {"0": 4, "1": 2}}), encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_plot_histogram(
        data: object,
        *,
        config: HistogramConfig | None = None,
    ) -> object:
        captured["data"] = data
        captured["config"] = config
        return SimpleNamespace(saved_path=str(output_path.resolve()))

    monkeypatch.setattr(cli, "plot_histogram", fake_plot_histogram)

    exit_code = cli.main(
        [
            "histogram",
            str(payload_path),
            "--output",
            str(output_path),
            "--data-key",
            "counts",
        ]
    )

    assert exit_code == 0
    assert captured["data"] == {"0": 4, "1": 2}
    config = captured["config"]
    assert isinstance(config, HistogramConfig)
    assert config.data_key is None
    assert config.mode is HistogramMode.STATIC
    assert config.show is False
    assert config.output_path == output_path


def test_cli_histogram_returns_argument_error_for_invalid_json(
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    from quantum_circuit_drawer import cli

    payload_path = sandbox_tmp_path / "broken.json"
    output_path = sandbox_tmp_path / "broken.png"
    payload_path.write_text("{broken", encoding="utf-8")

    exit_code = cli.main(["histogram", str(payload_path), "--output", str(output_path)])

    assert exit_code == 2
    assert "Invalid JSON" in capsys.readouterr().err


def test_pyproject_declares_qcd_console_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["qcd"] == "quantum_circuit_drawer.cli:main"
