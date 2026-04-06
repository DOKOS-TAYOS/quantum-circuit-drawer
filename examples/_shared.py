"""Shared helpers for standalone example entrypoints."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Mapping
from pathlib import Path

try:
    from examples._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import draw_quantum_circuit  # noqa: E402


def parse_output_args(*, description: str) -> Namespace:
    """Parse the shared output argument used by standalone examples."""

    parser = ArgumentParser(description=description)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def demo_style(*, max_page_width: float) -> dict[str, object]:
    """Return the common example style with a customized page width."""

    return {
        "font_size": 12.0,
        "show_params": True,
        "max_page_width": max_page_width,
    }


def run_example(
    builder: Callable[[], object],
    *,
    description: str,
    framework: str | None,
    style: Mapping[str, object],
    page_slider: bool,
    composite_mode: str = "compact",
    saved_label: str,
    render_options: Mapping[str, object] | None = None,
) -> None:
    """Build a demo object, draw it, and optionally report the saved file."""

    args = parse_output_args(description=description)
    _render_example(
        builder(),
        framework=framework,
        style=style,
        output=args.output,
        page_slider=page_slider,
        composite_mode=composite_mode,
        saved_label=saved_label,
        render_options=render_options,
    )


def run_prebuilt_example(
    subject: object,
    *,
    description: str,
    framework: str | None,
    style: Mapping[str, object],
    page_slider: bool,
    composite_mode: str = "compact",
    saved_label: str,
    render_options: Mapping[str, object] | None = None,
) -> None:
    """Draw a prebuilt demo object and optionally report the saved file."""

    args = parse_output_args(description=description)
    _render_example(
        subject,
        framework=framework,
        style=style,
        output=args.output,
        page_slider=page_slider,
        composite_mode=composite_mode,
        saved_label=saved_label,
        render_options=render_options,
    )


def _render_example(
    subject: object,
    *,
    framework: str | None,
    style: Mapping[str, object],
    output: Path | None,
    page_slider: bool,
    composite_mode: str,
    saved_label: str,
    render_options: Mapping[str, object] | None,
) -> None:
    draw_quantum_circuit(
        subject,
        framework=framework,
        style=style,
        output=output,
        page_slider=page_slider,
        composite_mode=composite_mode,
        **dict(render_options or {}),
    )

    if output is not None:
        print(f"Saved {saved_label} to {output}")
