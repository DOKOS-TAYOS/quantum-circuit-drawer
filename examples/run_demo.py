"""Shared command-line entrypoint for all example demos."""

from __future__ import annotations

import importlib
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

from quantum_circuit_drawer import draw_quantum_circuit

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.demo_catalog import DemoSpec, catalog_by_id, get_demo_catalog


def parse_args() -> Namespace:
    """Parse command-line arguments for the shared demo runner."""

    demo_ids = sorted(demo.demo_id for demo in get_demo_catalog())
    parser = ArgumentParser(description="Run any bundled quantum-circuit-drawer demo.")
    parser.add_argument(
        "--demo",
        choices=demo_ids,
        help="Demo id to execute.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the available demo ids and exit.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    parser.add_argument(
        "--show",
        dest="show",
        action="store_true",
        default=True,
        help="Open the Matplotlib window after rendering.",
    )
    parser.add_argument(
        "--no-show",
        dest="show",
        action="store_false",
        help="Render without opening the Matplotlib window.",
    )
    return parser.parse_args()


def load_demo_builder(spec: DemoSpec) -> Any:
    """Load the configured builder callable for one demo spec."""

    module = importlib.import_module(spec.module_name)
    return getattr(module, spec.builder_name)


def list_demos() -> None:
    """Print the available demo ids."""

    for demo in get_demo_catalog():
        print(f"{demo.demo_id}: {demo.description}")


def run_demo(spec: DemoSpec, *, output: Path | None, show: bool) -> None:
    """Build and render one selected demo."""

    builder = load_demo_builder(spec)
    circuit = builder()
    draw_quantum_circuit(
        circuit,
        framework=spec.framework,
        style=spec.style,
        output=output,
        show=show,
        page_slider=spec.page_slider,
        composite_mode=spec.composite_mode,
    )

    if output is not None:
        print(f"Saved {spec.demo_id} to {output}")


def main() -> None:
    """Run the shared example entrypoint."""

    args = parse_args()
    if args.list:
        list_demos()
        return
    if args.demo is None:
        raise SystemExit("Choose one demo with --demo or use --list to inspect the catalog.")

    spec = catalog_by_id()[args.demo]
    run_demo(spec, output=args.output, show=args.show)


if __name__ == "__main__":
    main()
