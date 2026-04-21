"""Shared command-line entrypoint for histogram demos."""

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

from examples._histogram_shared import (  # noqa: E402
    DEFAULT_HISTOGRAM_FIGSIZE,
    HistogramExampleRequest,
    add_histogram_arguments,
    render_histogram_example,
    request_from_namespace,
)
from examples.histogram_demo_catalog import (  # noqa: E402
    HistogramDemoSpec,
    catalog_by_id,
    get_demo_catalog,
)


def parse_args() -> Namespace:
    """Parse command-line arguments for the shared histogram demo runner."""

    demo_ids = sorted(demo.demo_id for demo in get_demo_catalog())
    parser = ArgumentParser(description="Run any bundled histogram demo.")
    parser.add_argument(
        "--demo",
        choices=demo_ids,
        help="Histogram demo id to execute.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the available histogram demo ids and exit.",
    )
    add_histogram_arguments(parser)
    return parser.parse_args()


def load_demo_builder(spec: HistogramDemoSpec) -> Any:
    """Load the configured builder callable for one histogram demo spec."""

    if spec.dependency_module is not None and find_spec(spec.dependency_module) is None:
        raise SystemExit(_missing_dependency_message(spec))

    module = importlib.import_module(spec.module_name)
    return getattr(module, spec.builder_name)


def _missing_dependency_message(spec: HistogramDemoSpec) -> str:
    dependency = spec.dependency_module or "the optional framework dependency"
    extra_name = spec.extra_name or dependency
    return (
        f"Histogram demo '{spec.demo_id}' needs optional dependency '{dependency}'.\n"
        "Install it inside your .venv and run the demo again:\n"
        f'  .\\.venv\\Scripts\\python.exe -m pip install -e ".[{extra_name}]"\n'
        "Linux or WSL:\n"
        f'  .venv/bin/python -m pip install -e ".[{extra_name}]"'
    )


def list_demos() -> None:
    """Print the available histogram demo ids."""

    for demo in get_demo_catalog():
        print(f"{demo.demo_id}: {demo.description}")


def run_demo(spec: HistogramDemoSpec, *, output: Path | None, show: bool) -> None:
    """Build and render one selected histogram demo."""

    builder = load_demo_builder(spec)
    request = HistogramExampleRequest(
        output=output,
        show=show,
        figsize=DEFAULT_HISTOGRAM_FIGSIZE,
    )
    render_histogram_example(
        builder(request),
        request=request,
        saved_label=spec.demo_id,
    )


def run_demo_with_args(spec: HistogramDemoSpec, args: Namespace) -> None:
    """Build and render one selected histogram demo using parsed CLI options."""

    request = request_from_namespace(args)
    builder = load_demo_builder(spec)
    render_histogram_example(
        builder(request),
        request=request,
        saved_label=spec.demo_id,
    )


def main() -> None:
    """Run the shared histogram example entrypoint."""

    args = parse_args()
    if args.list:
        list_demos()
        return
    if args.demo is None:
        raise SystemExit(
            "Choose one histogram demo with --demo or use --list to inspect the catalog."
        )

    spec = catalog_by_id()[args.demo]
    run_demo_with_args(spec, args)


if __name__ == "__main__":
    main()
