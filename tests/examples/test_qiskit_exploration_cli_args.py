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
