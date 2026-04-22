"""Shared command-line entrypoint for compare demos."""

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

from examples._compare_shared import (  # noqa: E402
    DEFAULT_COMPARE_FIGSIZE,
    CompareExampleRequest,
    add_compare_arguments,
    render_compare_example,
    request_from_namespace,
)
from examples.compare_demo_catalog import (  # noqa: E402
    CompareDemoSpec,
    catalog_by_id,
    get_demo_catalog,
)


def parse_args() -> Namespace:
    """Parse command-line arguments for the shared compare runner."""

    demo_ids = sorted(demo.demo_id for demo in get_demo_catalog())
    parser = ArgumentParser(description="Run any bundled compare demo.")
    parser.add_argument("--demo", choices=demo_ids, help="Compare demo id to execute.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the available compare demo ids and exit.",
    )
    add_compare_arguments(parser)
    return parser.parse_args()


def load_demo_builder(spec: CompareDemoSpec) -> Any:
    """Load the configured builder callable for one compare demo spec."""

    if spec.dependency_module is not None and find_spec(spec.dependency_module) is None:
        raise SystemExit(_missing_dependency_message(spec))

    module = importlib.import_module(spec.module_name)
    return getattr(module, spec.builder_name)


def _missing_dependency_message(spec: CompareDemoSpec) -> str:
    dependency = spec.dependency_module or "the optional framework dependency"
    extra_name = spec.extra_name or dependency
    return (
        f"Compare demo '{spec.demo_id}' needs optional dependency '{dependency}'.\n"
        "Install it inside your .venv and run the demo again:\n"
        f'  .\\.venv\\Scripts\\python.exe -m pip install -e ".[{extra_name}]"\n'
        "Linux or WSL:\n"
        f'  .venv/bin/python -m pip install -e ".[{extra_name}]"'
    )


def list_demos() -> None:
    """Print the available compare demo ids."""

    for demo in get_demo_catalog():
        print(f"{demo.demo_id}: {demo.description}")


def run_demo(spec: CompareDemoSpec, *, output: Path | None, show: bool) -> None:
    """Build and render one selected compare demo."""

    builder = load_demo_builder(spec)
    request = CompareExampleRequest(
        output=output,
        show=show,
        figsize=DEFAULT_COMPARE_FIGSIZE,
    )
    render_compare_example(
        builder(request),
        request=request,
        saved_label=spec.demo_id,
    )


def run_demo_with_args(spec: CompareDemoSpec, args: Namespace) -> None:
    """Build and render one selected compare demo using parsed CLI options."""

    request = request_from_namespace(args)
    builder = load_demo_builder(spec)
    render_compare_example(
        builder(request),
        request=request,
        saved_label=spec.demo_id,
    )


def main() -> None:
    """Run the shared compare demo entrypoint."""

    args = parse_args()
    if args.list:
        list_demos()
        return
    if args.demo is None:
        raise SystemExit(
            "Choose one compare demo with --demo or use --list to inspect the catalog."
        )

    spec = catalog_by_id()[args.demo]
    run_demo_with_args(spec, args)


if __name__ == "__main__":
    main()
