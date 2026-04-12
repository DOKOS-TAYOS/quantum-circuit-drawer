"""Shared command-line entrypoint for all example demos."""

from __future__ import annotations

import importlib
import sys
from argparse import ArgumentParser, Namespace
from importlib.util import find_spec
from pathlib import Path
from typing import Any

_EXAMPLES_DIR = Path(__file__).resolve().parent
if str(_EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_DIR))

try:
    from ._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from examples.demo_catalog import DemoSpec, catalog_by_id, get_demo_catalog  # noqa: E402
from quantum_circuit_drawer import draw_quantum_circuit  # noqa: E402


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

    if spec.dependency_module is not None and find_spec(spec.dependency_module) is None:
        raise SystemExit(_missing_dependency_message(spec))

    module = importlib.import_module(spec.module_name)
    return getattr(module, spec.builder_name)


def _missing_dependency_message(spec: DemoSpec) -> str:
    dependency = spec.dependency_module or "the optional framework dependency"
    extra_name = spec.framework or dependency
    return (
        f"Demo '{spec.demo_id}' needs optional dependency '{dependency}'.\n"
        "Install it inside your .venv and run the demo again:\n"
        f'  .\\.venv\\Scripts\\python.exe -m pip install -e ".[{extra_name}]"\n'
        "Linux or WSL:\n"
        f'  .venv/bin/python -m pip install -e ".[{extra_name}]"'
    )


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
        **spec.render_options,
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
