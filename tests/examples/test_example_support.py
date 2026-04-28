from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

from tests.support import flatten_operations


def test_ir_basic_workflow_builder_populates_rotation_parameters() -> None:
    module = importlib.import_module("examples.ir_basic_workflow")
    circuit = module.build_circuit(qubit_count=4, motif_count=3)

    rotation_parameters = [
        tuple(operation.parameters)
        for operation in flatten_operations(circuit)
        if operation.name == "RZ"
    ]

    assert rotation_parameters == [(0.2,), (0.4,), (0.6000000000000001,)]


def test_public_api_utilities_showcase_writes_companion_exports(
    sandbox_tmp_path: Path,
) -> None:
    module = importlib.import_module("examples.public_api_utilities_showcase")
    output_path = sandbox_tmp_path / "public-api.png"

    class FakeDrawResult:
        def save_all_pages(self, output_dir: Path, *, filename_prefix: str) -> None:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / f"{filename_prefix}_page_1.png").write_text("page", encoding="utf-8")

    class FakeHistogramResult:
        def save(self, path: Path) -> None:
            path.write_text("image", encoding="utf-8")

        def to_csv(self, path: Path) -> None:
            path.write_text("state,value\n00,1\n", encoding="utf-8")

    module._save_related_outputs(
        output_path=output_path,
        draw_result=FakeDrawResult(),
        histogram_result=FakeHistogramResult(),
        latex_source="\\begin{quantikz}\n\\end{quantikz}\n",
    )

    pages_dir = output_path.with_name("public-api_pages")
    histogram_path = output_path.with_name("public-api_histogram.png")
    histogram_csv_path = output_path.with_name("public-api_histogram.csv")
    latex_path = output_path.with_name("public-api_quantikz.tex")

    assert pages_dir.is_dir()
    assert histogram_path.is_file()
    assert histogram_csv_path.read_text(encoding="utf-8").startswith("state,value")
    assert "\\begin{quantikz}" in latex_path.read_text(encoding="utf-8")


def test_caller_managed_axes_showcase_reserves_library_summary_panel() -> None:
    module = importlib.import_module("examples.caller_managed_axes_showcase")
    figure, layout = module.create_dashboard_layout()

    try:
        summary_subplotspec = layout.summary_axes.get_subplotspec()
        panel_axes = (
            layout.circuit_axes,
            layout.histogram_axes,
            *layout.compare_axes,
            layout.summary_axes,
        )

        assert len({id(axes) for axes in panel_axes}) == 5
        assert module.build_compare_config().compare.show_summary is True
        assert summary_subplotspec.rowspan.start == 2
        assert summary_subplotspec.rowspan.stop == 3
        assert summary_subplotspec.colspan.start == 0
        assert summary_subplotspec.colspan.stop == 2
    finally:
        figure.clf()


def test_qiskit_backend_topology_showcase_enables_hover_in_3d(
    monkeypatch,
) -> None:
    module = importlib.import_module("examples.qiskit_backend_topology_showcase")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        module,
        "_parse_args",
        lambda: SimpleNamespace(qubits=6, motifs=3, output=None, show=False),
    )
    monkeypatch.setattr(
        module,
        "draw_quantum_circuit",
        lambda circuit, *, config: (
            captured.update({"circuit": circuit, "config": config}) or SimpleNamespace()
        ),
    )
    monkeypatch.setattr(module, "release_rendered_result", lambda result: None)

    module.main()

    config = captured["config"]
    assert config.side.render.view == "3d"
    assert config.side.render.topology_qubits == "all"
    assert config.side.appearance.hover.enabled is True
