from __future__ import annotations

from argparse import Namespace
from pathlib import Path


def test_run_example_draws_and_reports_saved_output(
    monkeypatch,
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    from examples._shared import run_example

    built_objects: list[object] = []
    draw_calls: list[dict[str, object]] = []
    output = sandbox_tmp_path / "demo.png"

    def build_demo() -> object:
        demo = {"kind": "demo"}
        built_objects.append(demo)
        return demo

    def fake_parse_output_args(*, description: str) -> Namespace:
        assert description == "Render a shared example."
        return Namespace(output=output)

    def fake_draw_quantum_circuit(
        circuit: object,
        framework: str | None = None,
        *,
        style: dict[str, object],
        output: Path | None = None,
        page_slider: bool = False,
    ) -> None:
        draw_calls.append(
            {
                "circuit": circuit,
                "framework": framework,
                "style": style,
                "output": output,
                "page_slider": page_slider,
            }
        )

    monkeypatch.setattr("examples._shared.parse_output_args", fake_parse_output_args)
    monkeypatch.setattr("examples._shared.draw_quantum_circuit", fake_draw_quantum_circuit)

    run_example(
        build_demo,
        description="Render a shared example.",
        framework="ir",
        style={"max_page_width": 7.5},
        page_slider=True,
        saved_label="demo",
    )

    captured = capsys.readouterr()

    assert len(built_objects) == 1
    assert draw_calls == [
        {
            "circuit": built_objects[0],
            "framework": "ir",
            "style": {"max_page_width": 7.5},
            "output": output,
            "page_slider": True,
        }
    ]
    assert f"Saved demo to {output}" in captured.out
