from __future__ import annotations

import sys

import pytest


def test_qiskit_2d_exploration_showcase_accepts_columns_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("qiskit")
    from examples import qiskit_2d_exploration_showcase as module

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "qiskit_2d_exploration_showcase.py",
            "--mode",
            "slider",
            "--columns",
            "9",
        ],
    )

    args = module._parse_args()

    assert args.mode == "slider"
    assert args.motifs == 9


def test_qiskit_3d_exploration_showcase_accepts_view_and_columns_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("qiskit")
    from examples import qiskit_3d_exploration_showcase as module

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "qiskit_3d_exploration_showcase.py",
            "--view",
            "3d",
            "--mode",
            "slider",
            "--topology",
            "star",
            "--columns",
            "5",
        ],
    )

    args = module._parse_args()

    assert args.view == "3d"
    assert args.mode == "slider"
    assert args.topology == "star"
    assert args.motifs == 5


def test_qiskit_random_accepts_documented_render_flags_and_passes_them_to_draw_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("qiskit")
    from examples import qiskit_random as module

    captured_config: list[object] = []

    def fake_draw_quantum_circuit(*args: object, **kwargs: object) -> object:
        del args
        captured_config.append(kwargs["config"])
        return object()

    monkeypatch.setattr(module, "draw_quantum_circuit", fake_draw_quantum_circuit)
    monkeypatch.setattr(module, "release_rendered_result", lambda result: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "qiskit_random.py",
            "--mode",
            "pages_controls",
            "--preset",
            "presentation",
            "--composite-mode",
            "expand",
            "--unsupported-policy",
            "placeholder",
            "--hover-matrix",
            "always",
            "--hover-matrix-max-qubits",
            "4",
            "--hover-show-size",
            "--figsize",
            "12",
            "6",
            "--no-show",
        ],
    )

    module.main()

    assert len(captured_config) == 1
    config = captured_config[0]
    assert str(config.preset) == "presentation"
    assert config.composite_mode == "expand"
    assert str(config.unsupported_policy) == "placeholder"
    assert config.hover.show_matrix == "always"
    assert config.hover.matrix_max_qubits == 4
    assert config.hover.show_size is True
    assert config.figsize == (12.0, 6.0)
