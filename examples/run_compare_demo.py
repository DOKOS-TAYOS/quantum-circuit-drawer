"""Small command-line entrypoint for launching compare example scripts."""

from __future__ import annotations

import subprocess
import sys
from argparse import ArgumentParser, Namespace
from importlib.util import find_spec
from pathlib import Path

_EXAMPLES_DIR = Path(__file__).resolve().parent
if str(_EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_DIR))

try:
    from ._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from examples.compare_demo_catalog import (  # noqa: E402
    CompareDemoSpec,
    catalog_by_id,
    get_demo_catalog,
)


def parse_args() -> tuple[Namespace, list[str]]:
    """Parse runner-specific arguments and return any script flags to forward."""

    demo_ids = sorted(demo.demo_id for demo in get_demo_catalog())
    parser = ArgumentParser(description="List or launch bundled compare example scripts.")
    parser.add_argument("--demo", choices=demo_ids, help="Compare demo id to execute.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the available compare demo ids and exit.",
    )
    parser.add_argument("--output", type=Path, help="Optional output file passed to the script.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_known_args()


def ensure_demo_dependency(spec: CompareDemoSpec) -> None:
    """Validate that the optional dependency for one compare demo is installed."""

    if spec.dependency_module is not None and find_spec(spec.dependency_module) is None:
        raise SystemExit(_missing_dependency_message(spec))


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


def script_path_for(spec: CompareDemoSpec) -> Path:
    """Return the filesystem path for one compare example module."""

    module_name = spec.module_name.removeprefix("examples.")
    return _EXAMPLES_DIR / f"{module_name}.py"


def run_demo(
    spec: CompareDemoSpec,
    *,
    output: Path | None,
    show: bool,
    forwarded_args: list[str],
) -> None:
    """Launch one direct compare example script with optional forwarded flags."""

    ensure_demo_dependency(spec)
    command = [sys.executable, str(script_path_for(spec)), *forwarded_args]
    existing_flags = set(forwarded_args)
    if output is not None and "--output" not in existing_flags:
        command.extend(["--output", str(output)])
    if "--show" not in existing_flags and "--no-show" not in existing_flags and not show:
        command.append("--no-show")

    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    """Run the shared compare demo entrypoint."""

    args, forwarded_args = parse_args()
    if args.list:
        list_demos()
        return
    if args.demo is None:
        raise SystemExit(
            "Choose one compare demo with --demo or use --list to inspect the catalog."
        )

    spec = catalog_by_id()[args.demo]
    run_demo(
        spec,
        output=args.output,
        show=bool(args.show),
        forwarded_args=forwarded_args,
    )


if __name__ == "__main__":
    main()
