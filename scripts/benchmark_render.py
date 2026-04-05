from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quantum_circuit_drawer.api import _prepare_draw_pipeline, draw_quantum_circuit  # noqa: E402
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR  # noqa: E402
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind  # noqa: E402
from quantum_circuit_drawer.ir.wires import WireIR, WireKind  # noqa: E402
from quantum_circuit_drawer.layout import LayoutEngine  # noqa: E402
from quantum_circuit_drawer.renderers import MatplotlibRenderer  # noqa: E402
from quantum_circuit_drawer.style import DrawStyle, normalize_style  # noqa: E402


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


def benchmark_render(wires: int, layers: int, repeats: int) -> dict[str, float | int]:
    circuit = build_synthetic_circuit(wires=wires, layers=layers)
    style = normalize_style(DrawStyle())
    layout_engine = LayoutEngine()
    renderer = MatplotlibRenderer()
    prepare_seconds = 0.0
    layout_seconds = 0.0
    render_seconds = 0.0
    full_draw_seconds = 0.0

    for _ in range(repeats):
        prepare_start = perf_counter()
        _prepare_draw_pipeline(
            circuit=circuit,
            framework="ir",
            style=None,
            layout=None,
            options={},
        )
        prepare_seconds += perf_counter() - prepare_start

        layout_start = perf_counter()
        scene = layout_engine.compute(circuit, style)
        layout_seconds += perf_counter() - layout_start

        render_start = perf_counter()
        figure, _ = renderer.render(scene)
        render_seconds += perf_counter() - render_start
        figure.clear()

        full_draw_start = perf_counter()
        full_figure, _ = draw_quantum_circuit(circuit, framework="ir", show=False)
        full_draw_seconds += perf_counter() - full_draw_start
        full_figure.clear()

    return {
        "wires": wires,
        "layers": layers,
        "repeats": repeats,
        "prepare_seconds": prepare_seconds / repeats,
        "layout_seconds": layout_seconds / repeats,
        "render_seconds": render_seconds / repeats,
        "full_draw_seconds": full_draw_seconds / repeats,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark synthetic layout and render passes.")
    parser.add_argument("--wires", type=int, default=16)
    parser.add_argument("--layers", type=int, default=120)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--json", action="store_true", dest="emit_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = benchmark_render(wires=args.wires, layers=args.layers, repeats=args.repeats)
    if args.emit_json:
        print(json.dumps(results))
        return 0

    print(
        "Synthetic benchmark:"
        f" wires={results['wires']}"
        f" layers={results['layers']}"
        f" repeats={results['repeats']}"
        f" prepare={results['prepare_seconds']:.6f}s"
        f" layout={results['layout_seconds']:.6f}s"
        f" render={results['render_seconds']:.6f}s"
        f" full_draw={results['full_draw_seconds']:.6f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
