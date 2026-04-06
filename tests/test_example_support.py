from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path


def test_parse_output_args_reads_optional_output_path(
    monkeypatch,
) -> None:
    from examples._shared import parse_output_args

    monkeypatch.setattr(sys, "argv", ["example.py", "--output", "demo.png"])

    args = parse_output_args(description="Render a demo.")

    assert args.output == Path("demo.png")


def test_demo_style_returns_expected_defaults() -> None:
    from examples._shared import demo_style

    assert demo_style(max_page_width=7.5) == {
        "font_size": 12.0,
        "show_params": True,
        "max_page_width": 7.5,
    }


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


def test_run_prebuilt_example_draws_subject_and_reports_saved_output(
    monkeypatch,
    sandbox_tmp_path: Path,
    capsys,
) -> None:
    from examples._shared import run_prebuilt_example

    draw_calls: list[dict[str, object]] = []
    output = sandbox_tmp_path / "prebuilt.png"
    subject = {"kind": "prebuilt"}

    def fake_parse_output_args(*, description: str) -> Namespace:
        assert description == "Render a prebuilt example."
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

    run_prebuilt_example(
        subject,
        description="Render a prebuilt example.",
        framework="cudaq",
        style={"theme": "paper"},
        page_slider=False,
        saved_label="prebuilt demo",
    )

    captured = capsys.readouterr()

    assert draw_calls == [
        {
            "circuit": subject,
            "framework": "cudaq",
            "style": {"theme": "paper"},
            "output": output,
            "page_slider": False,
        }
    ]
    assert f"Saved prebuilt demo to {output}" in captured.out
