from __future__ import annotations

import sys
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def close_matplotlib_figures() -> None:
    try:
        yield
    finally:
        plt.close("all")


@pytest.fixture
def sandbox_tmp_path() -> Path:
    base = Path(__file__).resolve().parents[1] / "test_tmp"
    base.mkdir(exist_ok=True)
    path = base / uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)
