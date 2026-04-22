from __future__ import annotations

import argparse
import importlib
import json
import sys
from argparse import Namespace
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Literal, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from examples._shared import (  # noqa: E402
    DEFAULT_DEMO_FIGSIZE,
    ExampleBuilder,
    ExampleRequest,
    RenderMode,
    build_draw_config,
    demo_adapter_options,
    request_from_namespace,
)
from examples.demo_catalog import DemoSpec, catalog_by_id  # noqa: E402

from quantum_circuit_drawer.adapters.registry import get_adapter  # noqa: E402
from quantum_circuit_drawer.api import draw_quantum_circuit  # noqa: E402
from quantum_circuit_drawer.config import DrawConfig  # noqa: E402
from quantum_circuit_drawer.drawing.pipeline import prepare_draw_pipeline  # noqa: E402
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR  # noqa: E402
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind  # noqa: E402
from quantum_circuit_drawer.ir.wires import WireIR, WireKind  # noqa: E402
from quantum_circuit_drawer.layout import LayoutEngine, LayoutEngine3D  # noqa: E402
from quantum_circuit_drawer.layout.topology_3d import TopologyName  # noqa: E402
from quantum_circuit_drawer.renderers import (  # noqa: E402
    MatplotlibRenderer,
    MatplotlibRenderer3D,
)
from quantum_circuit_drawer.style import DrawStyle, normalize_style  # noqa: E402

if TYPE_CHECKING:
    from matplotlib.figure import Figure

ViewMode = Literal["2d", "3d"]
DemoBenchmarkScenario = tuple[str, int, int, str]


def _managed_rendered_figure(render_result: object) -> Figure:
    """Return the managed figure from a renderer call without caller-owned axes."""

    if not isinstance(render_result, tuple):
        raise TypeError("managed benchmark renders must return a (figure, axes) tuple")
    from matplotlib.figure import Figure

    figure = render_result[0]
    if not isinstance(figure, Figure):
        raise TypeError("managed benchmark renders must return a Matplotlib figure")
    return figure


def build_synthetic_circuit(wires: int, layers: int) -> CircuitIR:
    quantum_wires = [
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(wires)
    ]
    layer_items: list[LayerIR] = []
    for layer_index in range(layers):
        operations: list[OperationIR] = []
        for qubit_index in range(0, wires, 2):
            operations.append(
                OperationIR(
                    kind=OperationKind.GATE,
                    name="H" if layer_index % 2 == 0 else "RX",
                    target_wires=(f"q{qubit_index}",),
                    parameters=(0.5,) if layer_index % 2 else (),
                )
            )
            if qubit_index + 1 < wires:
                operations.append(
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=(f"q{qubit_index + 1}",),
                        control_wires=(f"q{qubit_index}",),
                    )
                )
        layer_items.append(LayerIR(operations=operations))
    return CircuitIR(quantum_wires=quantum_wires, layers=layer_items)


def benchmark_render(
    wires: int,
    layers: int,
    repeats: int,
    *,
    view: ViewMode = "2d",
    topology: TopologyName = "line",
) -> dict[str, float | int | str]:
    circuit = build_synthetic_circuit(wires=wires, layers=layers)
    style = normalize_style(DrawStyle())
    prepare_seconds = 0.0
    layout_seconds = 0.0
    render_seconds = 0.0
    full_draw_seconds = 0.0
    pipeline_options = (
        {"view": "3d", "topology": topology, "direct": True, "hover": False} if view == "3d" else {}
    )
    layout_engine_2d = LayoutEngine()
    layout_engine_3d = LayoutEngine3D()
    renderer_2d = MatplotlibRenderer()
    renderer_3d = MatplotlibRenderer3D()

    for _ in range(repeats):
        prepare_start = perf_counter()
        prepare_draw_pipeline(
            circuit=circuit,
            framework="ir",
            style=None,
            layout=None,
            options=pipeline_options,
        )
        prepare_seconds += perf_counter() - prepare_start

        layout_start = perf_counter()
        if view == "3d":
            scene = layout_engine_3d.compute(
                circuit,
                style,
                topology_name=topology,
                direct=True,
                hover_enabled=False,
            )
        else:
            scene = layout_engine_2d.compute(circuit, style)
        layout_seconds += perf_counter() - layout_start

        render_start = perf_counter()
        if view == "3d":
            figure = _managed_rendered_figure(renderer_3d.render(scene))
        else:
            figure = _managed_rendered_figure(renderer_2d.render(scene))
        render_seconds += perf_counter() - render_start
        figure.clear()

        full_draw_start = perf_counter()
        if view == "3d":
            full_result = draw_quantum_circuit(
                circuit,
                config=DrawConfig(
                    framework="ir",
                    view="3d",
                    topology=topology,
                    show=False,
                ),
            )
        else:
            full_result = draw_quantum_circuit(
                circuit,
                config=DrawConfig(framework="ir", show=False),
            )
        full_draw_seconds += perf_counter() - full_draw_start
        for figure in full_result.figures:
            figure.clear()

    results: dict[str, float | int | str] = {
        "wires": wires,
        "layers": layers,
        "repeats": repeats,
        "prepare_seconds": prepare_seconds / repeats,
        "layout_seconds": layout_seconds / repeats,
        "render_seconds": render_seconds / repeats,
        "full_draw_seconds": full_draw_seconds / repeats,
    }
    if view == "3d":
        results["view"] = view
        results["topology"] = topology
    return results


def demo_benchmark_scenarios() -> tuple[DemoBenchmarkScenario, ...]:
    """Return the multi-framework demo scenarios used for cold-start profiling."""

    return (
        ("qiskit-random", 24, 32, "pages"),
        ("cirq-random", 24, 32, "pages"),
        ("cirq-qaoa", 18, 12, "slider"),
        ("pennylane-random", 24, 32, "pages"),
        ("pennylane-qaoa", 18, 12, "slider"),
        ("myqlm-random", 24, 32, "pages"),
    )


def benchmark_demo(
    demo_id: str,
    qubits: int,
    columns: int,
    mode: RenderMode,
    repeats: int = 3,
) -> dict[str, float | int | str]:
    """Benchmark one real framework demo split into import, build, adapt, and draw phases."""

    spec = catalog_by_id()[demo_id]
    import_seconds = 0.0
    build_seconds = 0.0
    adapt_seconds = 0.0
    draw_seconds = 0.0
    total_seconds = 0.0
    operation_count = 0
    quantum_wires = 0
    classical_wires = 0

    for _ in range(repeats):
        started_at = perf_counter()
        builder = _load_demo_builder(spec)
        imported_at = perf_counter()
        request = _build_example_request(spec, qubits=qubits, columns=columns, mode=mode)
        subject = builder(request)
        built_at = perf_counter()
        ir = _build_ir(subject, framework=spec.framework, request=request)
        adapted_at = perf_counter()
        draw_result = draw_quantum_circuit(
            ir,
            config=build_draw_config(request, framework="ir"),
        )
        draw_completed_at = perf_counter()
        for figure in draw_result.figures:
            figure.clear()

        import_seconds += imported_at - started_at
        build_seconds += built_at - imported_at
        adapt_seconds += adapted_at - built_at
        draw_seconds += draw_completed_at - adapted_at
        total_seconds += draw_completed_at - started_at
        operation_count = _operation_count(ir)
        quantum_wires = _quantum_wire_count(ir)
        classical_wires = _classical_wire_count(ir)

    return {
        "demo_id": demo_id,
        "framework": "ir" if spec.framework is None else spec.framework,
        "qubits": qubits,
        "columns": columns,
        "mode": mode,
        "repeats": repeats,
        "import_seconds": import_seconds / repeats,
        "build_seconds": build_seconds / repeats,
        "adapt_seconds": adapt_seconds / repeats,
        "draw_seconds": draw_seconds / repeats,
        "total_seconds": total_seconds / repeats,
        "operation_count": operation_count,
        "quantum_wires": quantum_wires,
        "classical_wires": classical_wires,
    }


def _build_example_request(
    spec: DemoSpec,
    *,
    qubits: int,
    columns: int,
    mode: RenderMode,
) -> ExampleRequest:
    return request_from_namespace(
        Namespace(
            qubits=qubits,
            columns=columns,
            mode=mode,
            view="2d",
            topology="line",
            seed=7,
            output=None,
            show=False,
            figsize=DEFAULT_DEMO_FIGSIZE,
            hover=True,
            hover_matrix="auto",
            hover_matrix_max_qubits=2,
            hover_show_size=False,
        ),
        default_qubits=spec.default_qubits,
        default_columns=spec.default_columns,
    )


def _load_demo_builder(spec: DemoSpec) -> ExampleBuilder:
    module = importlib.import_module(spec.module_name)
    builder = getattr(module, spec.builder_name, None)
    if not callable(builder):
        raise TypeError(f"Demo '{spec.demo_id}' builder '{spec.builder_name}' must be callable")
    return cast(ExampleBuilder, builder)


def _build_ir(
    subject: object,
    *,
    framework: str | None,
    request: ExampleRequest,
) -> CircuitIR:
    adapter = get_adapter(subject, framework)
    return adapter.to_ir(
        subject,
        options={
            "composite_mode": "compact",
            **demo_adapter_options(request, framework=framework),
        },
    )


def _operation_count(circuit: CircuitIR) -> int:
    return sum(len(layer.operations) for layer in circuit.layers)


def _quantum_wire_count(circuit: CircuitIR) -> int:
    return circuit.quantum_wire_count


def _classical_wire_count(circuit: CircuitIR) -> int:
    return circuit.classical_wire_count


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark synthetic layout and render passes.")
    parser.add_argument(
        "--benchmark",
        choices=("synthetic", "demo", "demo-suite"),
        default="synthetic",
        help="Benchmark mode: synthetic pipeline, one demo, or the full demo suite.",
    )
    parser.add_argument("--wires", type=positive_int, default=16)
    parser.add_argument("--layers", type=positive_int, default=120)
    parser.add_argument("--repeats", type=positive_int, default=3)
    parser.add_argument("--view", choices=("2d", "3d"), default="2d")
    parser.add_argument(
        "--topology",
        choices=("line", "grid", "star", "star_tree", "honeycomb"),
        default="line",
    )
    parser.add_argument("--demo-id", type=str, default="qiskit-random")
    parser.add_argument("--qubits", type=positive_int, default=24)
    parser.add_argument("--columns", type=positive_int, default=32)
    parser.add_argument(
        "--mode",
        choices=("pages", "pages_controls", "slider", "full"),
        default="pages",
    )
    parser.add_argument("--json", action="store_true", dest="emit_json")
    return parser.parse_args(argv)


def positive_int(raw_value: str) -> int:
    """Parse a strictly positive integer for benchmark dimensions."""

    value = int(raw_value)
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.benchmark == "synthetic":
        results = benchmark_render(
            wires=args.wires,
            layers=args.layers,
            repeats=args.repeats,
            view=args.view,
            topology=args.topology,
        )
        if args.emit_json:
            print(json.dumps(results))
            return 0

        summary = (
            "Synthetic benchmark:"
            f" wires={results['wires']}"
            f" layers={results['layers']}"
            f" repeats={results['repeats']}"
        )
        if args.view == "3d":
            summary += f" view={args.view} topology={args.topology}"
        summary += (
            f" prepare={results['prepare_seconds']:.6f}s"
            f" layout={results['layout_seconds']:.6f}s"
            f" render={results['render_seconds']:.6f}s"
            f" full_draw={results['full_draw_seconds']:.6f}s"
        )
        print(summary)
        return 0

    if args.benchmark == "demo":
        results = benchmark_demo(
            demo_id=args.demo_id,
            qubits=args.qubits,
            columns=args.columns,
            mode=cast(RenderMode, args.mode),
            repeats=args.repeats,
        )
        if args.emit_json:
            print(json.dumps(results))
        else:
            print(
                "Demo benchmark:"
                f" id={results['demo_id']}"
                f" framework={results['framework']}"
                f" qubits={results['qubits']}"
                f" columns={results['columns']}"
                f" mode={results['mode']}"
                f" repeats={results['repeats']}"
                f" import={results['import_seconds']:.6f}s"
                f" build={results['build_seconds']:.6f}s"
                f" adapt={results['adapt_seconds']:.6f}s"
                f" draw={results['draw_seconds']:.6f}s"
                f" total={results['total_seconds']:.6f}s"
            )
        return 0

    suite_results: list[dict[str, float | int | str]] = []
    for demo_id, qubits, columns, mode in demo_benchmark_scenarios():
        try:
            suite_results.append(
                benchmark_demo(
                    demo_id=demo_id,
                    qubits=qubits,
                    columns=columns,
                    mode=cast(RenderMode, mode),
                    repeats=args.repeats,
                )
            )
        except Exception as exc:
            suite_results.append(
                {
                    "demo_id": demo_id,
                    "qubits": qubits,
                    "columns": columns,
                    "mode": mode,
                    "repeats": args.repeats,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    if args.emit_json:
        print(json.dumps(suite_results))
    else:
        print("Demo-suite benchmark:")
        for result in suite_results:
            if "error" in result:
                print(
                    f" - {result['demo_id']}: ERROR {result['error']}"
                    f" (qubits={result['qubits']} columns={result['columns']} mode={result['mode']})"
                )
                continue
            print(
                f" - {result['demo_id']} ({result['framework']}):"
                f" import={result['import_seconds']:.6f}s"
                f" build={result['build_seconds']:.6f}s"
                f" adapt={result['adapt_seconds']:.6f}s"
                f" draw={result['draw_seconds']:.6f}s"
                f" total={result['total_seconds']:.6f}s"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
