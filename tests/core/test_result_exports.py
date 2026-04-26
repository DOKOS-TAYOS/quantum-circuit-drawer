from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from quantum_circuit_drawer import (
    CircuitCompareConfig,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    HistogramCompareConfig,
    HistogramConfig,
    OutputOptions,
    compare_circuits,
    compare_histograms,
    draw_quantum_circuit,
    plot_histogram,
)
from quantum_circuit_drawer.config import CircuitRenderOptions
from tests.support import assert_saved_image_has_visible_content, build_sample_ir


def test_draw_result_save_and_save_all_pages_export_images(sandbox_tmp_path: Path) -> None:
    result = draw_quantum_circuit(
        build_sample_ir(),
        config=DrawConfig(
            side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.PAGES)),
            output=OutputOptions(show=False),
        ),
    )

    saved_path = result.save(sandbox_tmp_path / "single.png")
    page_paths = result.save_all_pages(
        sandbox_tmp_path / "pages",
        filename_prefix="circuit_page",
        extension=".png",
    )

    assert saved_path == str((sandbox_tmp_path / "single.png").resolve())
    assert_saved_image_has_visible_content(Path(saved_path))
    assert page_paths == (str((sandbox_tmp_path / "pages" / "circuit_page_1.png").resolve()),)
    assert_saved_image_has_visible_content(Path(page_paths[0]))

    payload = result.to_dict()
    assert payload["mode"] == result.mode.value
    assert payload["page_count"] == result.page_count
    assert payload["detected_framework"] == "ir"
    assert "primary_figure" not in payload

    plt.close(result.primary_figure)


def test_histogram_result_exports_dict_csv_and_image(sandbox_tmp_path: Path) -> None:
    result = plot_histogram(
        {"00": 5, "11": 3},
        config=HistogramConfig(output=OutputOptions(show=False)),
    )

    saved_path = result.save(sandbox_tmp_path / "histogram.png")
    csv_path = result.to_csv(sandbox_tmp_path / "histogram.csv")

    assert saved_path == str((sandbox_tmp_path / "histogram.png").resolve())
    assert_saved_image_has_visible_content(Path(saved_path))
    assert csv_path == str((sandbox_tmp_path / "histogram.csv").resolve())
    with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
        rows = tuple(csv.reader(csv_file))
    assert rows == (["state", "value"], ["00", "5.0"], ["11", "3.0"])
    assert result.to_dict()["values"] == (5.0, 3.0)

    plt.close(result.figure)


def test_histogram_compare_result_exports_dict_csv_and_image(sandbox_tmp_path: Path) -> None:
    result = compare_histograms(
        {"00": 5, "11": 3},
        {"00": 4, "11": 4},
        config=HistogramCompareConfig(output=OutputOptions(show=False)),
    )

    saved_path = result.save(sandbox_tmp_path / "compare.png")
    csv_path = result.to_csv(sandbox_tmp_path / "compare.csv")

    assert saved_path == str((sandbox_tmp_path / "compare.png").resolve())
    assert_saved_image_has_visible_content(Path(saved_path))
    with Path(csv_path).open(newline="", encoding="utf-8") as csv_file:
        rows = tuple(csv.reader(csv_file))
    assert rows == (
        ["state", "left", "right", "delta"],
        ["00", "5.0", "4.0", "1.0"],
        ["11", "3.0", "4.0", "-1.0"],
    )
    payload = result.to_dict()
    assert payload["metrics"]["total_variation_distance"] == result.metrics.total_variation_distance
    assert payload["delta_values"] == (1.0, -1.0)

    plt.close(result.figure)


def test_circuit_compare_result_exports_dict_and_image(sandbox_tmp_path: Path) -> None:
    result = compare_circuits(
        build_sample_ir(),
        build_sample_ir(),
        config=CircuitCompareConfig(output=OutputOptions(show=False)),
    )

    saved_path = result.save(sandbox_tmp_path / "circuit_compare.png")
    payload = result.to_dict()

    assert saved_path == str((sandbox_tmp_path / "circuit_compare.png").resolve())
    assert_saved_image_has_visible_content(Path(saved_path))
    assert payload["metrics"]["operation_delta"] == 0
    assert payload["left_result"]["detected_framework"] == "ir"
    assert payload["right_result"]["detected_framework"] == "ir"
    assert "figure" not in payload

    plt.close(result.figure)
    for figure in result.left_result.figures + result.right_result.figures:
        plt.close(figure)
