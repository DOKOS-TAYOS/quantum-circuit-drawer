"""Render a histogram through the public qcd CLI from a Python example."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path

try:
    from examples._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer.cli import main as qcd_main  # noqa: E402

DEFAULT_OUTPUT_FILENAME = "cli-export-showcase.png"


def demo_payload() -> dict[str, dict[str, int]]:
    """Return a nested JSON payload for the qcd --data-key workflow."""

    return {
        "counts": {
            "000": 18,
            "001": 7,
            "010": 24,
            "011": 41,
            "100": 13,
            "101": 5,
            "110": 21,
            "111": 36,
        }
    }


def main() -> None:
    """Run the CLI export showcase."""

    output_path, show = _parse_args()
    if output_path is None:
        output_path = default_output_path()

    payload_path = output_path.with_name(f"{output_path.stem}_counts.json")
    _run_cli_export(
        payload_path=payload_path,
        output_path=output_path,
        show=show,
        persistent_output=output_path,
    )


def _run_cli_export(
    *,
    payload_path: Path,
    output_path: Path,
    show: bool,
    persistent_output: Path | None,
) -> None:
    """Write a JSON payload and render it through the public qcd CLI."""

    payload_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(demo_payload(), indent=2), encoding="utf-8")
    exit_code = qcd_main(
        [
            "histogram",
            str(payload_path),
            "--data-key",
            "counts",
            "--sort",
            "value_desc",
            "--top-k",
            "6",
            "--preset",
            "accessible",
            "--output",
            str(output_path),
            *(["--show"] if show else []),
        ]
    )
    if exit_code != 0:
        raise SystemExit(exit_code)
    if persistent_output is not None:
        print(f"Saved cli-export-showcase to {persistent_output}")


def default_output_path() -> Path:
    """Return the persistent default PNG path for the export demo."""

    return Path(__file__).resolve().parent / "output" / DEFAULT_OUTPUT_FILENAME


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render through the qcd command-line interface.")
    parser.add_argument("--output", type=Path, help="Output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
