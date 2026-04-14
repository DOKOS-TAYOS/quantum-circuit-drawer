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

from examples._shared import (  # noqa: E402
    add_render_arguments,
    render_example,
    request_from_namespace,
)
from examples.demo_catalog import DemoSpec, catalog_by_id, get_demo_catalog  # noqa: E402


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
    add_render_arguments(
        parser,
        default_qubits=None,
        default_columns=None,
        columns_help="Random circuit columns or QAOA layers to generate",
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
    request = request_from_namespace(
        Namespace(
            qubits=None,
            columns=None,
            mode="pages",
            view="2d",
            topology="line",
            seed=7,
            output=output,
            show=show,
        ),
        default_qubits=spec.default_qubits,
        default_columns=spec.default_columns,
    )
    render_example(
        builder(request),
        request=request,
        framework=spec.framework,
        saved_label=spec.demo_id,
    )


def run_demo_with_args(spec: DemoSpec, args: Namespace) -> None:
    """Build and render one selected demo using parsed CLI options."""

    builder = load_demo_builder(spec)
    request = request_from_namespace(
        args,
        default_qubits=spec.default_qubits,
        default_columns=spec.default_columns,
    )
    render_example(
        builder(request),
        request=request,
        framework=spec.framework,
        saved_label=spec.demo_id,
    )


def main() -> None:
    """Run the shared example entrypoint."""

    args = parse_args()
    if args.list:
        list_demos()
        return
    if args.demo is None:
        raise SystemExit("Choose one demo with --demo or use --list to inspect the catalog.")

    spec = catalog_by_id()[args.demo]
    run_demo_with_args(spec, args)


if __name__ == "__main__":
    main()
