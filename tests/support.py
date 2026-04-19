from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace

import matplotlib.image as mpimg
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from quantum_circuit_drawer._draw_managed import (
    is_3d_axes,
    render_draw_pipeline_on_axes,
    render_managed_draw_pipeline,
)
from quantum_circuit_drawer._draw_pipeline import prepare_draw_pipeline
from quantum_circuit_drawer._draw_request import build_draw_request, validate_draw_request
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.layout.scene import LayoutScene
from quantum_circuit_drawer.style import DrawStyle

_MATHTEXT_GREEK_TO_NAME: dict[str, str] = {
    r"\alpha": "alpha",
    r"\beta": "beta",
    r"\gamma": "gamma",
    r"\delta": "delta",
    r"\epsilon": "epsilon",
    r"\zeta": "zeta",
    r"\eta": "eta",
    r"\theta": "theta",
    r"\iota": "iota",
    r"\kappa": "kappa",
    r"\lambda": "lambda",
    r"\mu": "mu",
    r"\nu": "nu",
    r"\xi": "xi",
    r"\pi": "pi",
    r"\rho": "rho",
    r"\sigma": "sigma",
    r"\tau": "tau",
    r"\upsilon": "upsilon",
    r"\phi": "phi",
    r"\chi": "chi",
    r"\psi": "psi",
    r"\omega": "omega",
}
_MATHTEXT_WRAPPER_PATTERN = re.compile(r"^\$(?P<inner>.*)\$$")


@dataclass(frozen=True, slots=True)
class OperationSignature:
    kind: OperationKind
    canonical_family: CanonicalGateFamily | None
    name: str
    parameters: tuple[object, ...]
    target_wires: tuple[str, ...]
    control_wires: tuple[str, ...] = ()


def build_sample_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",)),
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    ),
                ]
            ),
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q1",),
                        classical_target="c0",
                    )
                ]
            ),
        ],
    )


def build_wrapped_ir() -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        layers=[
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="X", target_wires=("q1",))]
            ),
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="X",
                        target_wires=("q1",),
                        control_wires=("q0",),
                    )
                ]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Z", target_wires=("q0",))]
            ),
            LayerIR(
                operations=[OperationIR(kind=OperationKind.GATE, name="Y", target_wires=("q1",))]
            ),
        ],
    )


def build_dense_rotation_ir(*, layer_count: int, wire_count: int = 4) -> CircuitIR:
    return CircuitIR(
        quantum_wires=[
            WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=str(index))
            for index in range(wire_count)
        ],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RX",
                        target_wires=(f"q{layer_index % wire_count}",),
                        parameters=(0.5,),
                    )
                ]
            )
            for layer_index in range(layer_count)
        ],
    )


def build_sample_scene() -> LayoutScene:
    return LayoutEngine().compute(build_sample_ir(), DrawStyle())


def flatten_operations(circuit: CircuitIR) -> list[OperationIR]:
    return [operation for layer in circuit.layers for operation in layer.operations]


def operation_signature(operation: OperationIR) -> OperationSignature:
    return OperationSignature(
        kind=operation.kind,
        canonical_family=operation.canonical_family,
        name=operation.name,
        parameters=tuple(operation.parameters),
        target_wires=tuple(operation.target_wires),
        control_wires=tuple(operation.control_wires),
    )


def assert_operation_signatures(
    circuit: CircuitIR,
    expected: Sequence[OperationSignature],
) -> None:
    assert [operation_signature(operation) for operation in flatten_operations(circuit)] == list(
        expected
    )


def assert_quantum_wire_labels(circuit: CircuitIR, expected: Sequence[str]) -> None:
    assert [wire.label for wire in circuit.quantum_wires] == list(expected)


def assert_classical_wire_bundles(
    circuit: CircuitIR,
    expected: Sequence[tuple[str, int]],
) -> None:
    assert [
        (wire.label, int(wire.metadata.get("bundle_size", 1))) for wire in circuit.classical_wires
    ] == list(expected)


def assert_axes_contains_circuit_artists(
    axes: Axes,
    *,
    expected_texts: set[str] | None = None,
    min_line_like_artists: int = 1,
    min_patches: int = 1,
) -> None:
    line_like_count = len(axes.lines) + len(axes.collections)

    assert line_like_count >= min_line_like_artists
    assert len(axes.patches) >= min_patches

    if expected_texts is not None:
        observed_texts = {normalize_rendered_text(text.get_text()) for text in axes.texts}
        assert expected_texts.issubset(observed_texts)


def figure_rgb_array(figure: Figure) -> np.ndarray:
    figure.canvas.draw()
    return np.asarray(figure.canvas.buffer_rgba())[..., :3].copy()


def assert_figure_has_visible_content(
    figure: Figure,
    *,
    min_changed_pixels: int = 250,
    tolerance: int = 4,
) -> None:
    rgb = figure_rgb_array(figure).astype(np.int16)
    background = rgb[0, 0]
    changed = np.any(np.abs(rgb - background) > tolerance, axis=2)

    assert int(changed.sum()) >= min_changed_pixels


def assert_saved_image_has_visible_content(
    path: Path,
    *,
    min_changed_pixels: int = 250,
    tolerance: float = 0.01,
) -> None:
    assert path.exists()

    image = np.asarray(mpimg.imread(path))
    if image.ndim == 2:
        rgb = image[..., np.newaxis]
    else:
        rgb = image[..., :3]

    background = rgb[0, 0]
    changed = np.any(np.abs(rgb - background) > tolerance, axis=-1)

    assert int(changed.sum()) >= min_changed_pixels


def normalize_rendered_text(text: str) -> str:
    """Normalize plain text and MathText strings into a comparable plain form."""

    if "\n" in text:
        return "\n".join(normalize_rendered_text(line) for line in text.split("\n"))

    match = _MATHTEXT_WRAPPER_PATTERN.match(text)
    if match is None:
        return text

    inner_text = match.group("inner")
    if inner_text.startswith(r"\mathrm{") and inner_text.endswith("}"):
        inner_text = inner_text[len(r"\mathrm{") : -1]

    inner_text = inner_text.replace(r"\ ", " ")
    inner_text = inner_text.replace(r"\{", "{").replace(r"\}", "}")
    inner_text = inner_text.replace(r"\$", "$")
    inner_text = inner_text.replace(r"\%", "%")
    inner_text = inner_text.replace(r"\&", "&")
    inner_text = inner_text.replace(r"\#", "#")
    inner_text = inner_text.replace(r"\_", "_")
    inner_text = inner_text.replace(r"\^", "^")
    inner_text = inner_text.replace(r"\\", "\\")

    for mathtext_command, plain_name in _MATHTEXT_GREEK_TO_NAME.items():
        inner_text = inner_text.replace(mathtext_command, plain_name)

    return inner_text


def install_fake_cudaq(monkeypatch: pytest.MonkeyPatch) -> type[object]:
    class FakePyKernel:
        def __init__(self) -> None:
            self._compiled = True

        def is_compiled(self) -> bool:
            return self._compiled

        def compile(self) -> None:
            self._compiled = True

        def launch_args_required(self) -> int:
            return 0

        def __str__(self) -> str:
            return """
module {
  func.func @__nvqpp__mlirgen__api_cudaq() attributes {"cudaq-entrypoint"} {
    %c0 = arith.constant 0 : index
    %q = quake.alloca() : !quake.qvec<1>
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<1>, index) -> !quake.qref
    quake.h %q0 : (!quake.qref) -> ()
    %m = quake.mz %q0 : (!quake.qref) -> i1
    return
  }
}
""".strip()

    fake_module = ModuleType("cudaq")
    fake_module.PyKernel = FakePyKernel
    fake_module.PyKernelDecorator = FakePyKernel
    monkeypatch.setitem(sys.modules, "cudaq", fake_module)
    return FakePyKernel


@dataclass(slots=True)
class FakeMyQLMSyntax:
    name: str
    parameters: tuple[object, ...] = ()


@dataclass(slots=True)
class FakeMyQLMCircuitImplementation:
    ops: tuple[object, ...]
    ancillas: int = 0
    nbqbits: int = 0


@dataclass(slots=True)
class FakeMyQLMGateDefinition:
    name: str
    arity: int
    syntax: FakeMyQLMSyntax | None = None
    nbctrls: int | None = None
    subgate: str | None = None
    circuit_implementation: FakeMyQLMCircuitImplementation | None = None


@dataclass(slots=True)
class FakeMyQLMOp:
    gate: str | None = None
    qbits: tuple[int, ...] = ()
    type: str | int = "GATETYPE"
    cbits: tuple[int, ...] = ()
    formula: str | None = None
    remap: tuple[int, ...] | None = None


class FakeMyQLMCircuit:
    def __init__(
        self,
        *,
        ops: tuple[FakeMyQLMOp, ...],
        gate_dic: dict[str, FakeMyQLMGateDefinition],
        nbqbits: int,
        nbcbits: int,
        name: str | None = None,
    ) -> None:
        self.ops = ops
        self.gateDic = gate_dic
        self.nbqbits = nbqbits
        self.nbcbits = nbcbits
        self.name = name


def build_sample_myqlm_circuit() -> FakeMyQLMCircuit:
    gate_dic = {
        "H": FakeMyQLMGateDefinition(name="H", arity=1, syntax=FakeMyQLMSyntax(name="H")),
    }
    return FakeMyQLMCircuit(
        ops=(
            FakeMyQLMOp(gate="H", qbits=(0,)),
            FakeMyQLMOp(type="MEASURE", qbits=(0,), cbits=(0,)),
        ),
        gate_dic=gate_dic,
        nbqbits=1,
        nbcbits=1,
        name="fake_myqlm_demo",
    )


def install_fake_myqlm(monkeypatch: pytest.MonkeyPatch) -> type[FakeMyQLMCircuit]:
    fake_module = ModuleType("qat")
    fake_module.core = SimpleNamespace(Circuit=FakeMyQLMCircuit)
    monkeypatch.setitem(sys.modules, "qat", fake_module)
    return FakeMyQLMCircuit


def draw_quantum_circuit_legacy(
    circuit: object,
    framework: str | None = None,
    *,
    style: DrawStyle | dict[str, object] | None = None,
    layout: object = None,
    backend: str = "matplotlib",
    ax: Axes | None = None,
    output: Path | str | None = None,
    show: bool = True,
    figsize: tuple[float, float] | None = None,
    page_slider: bool = False,
    page_window: bool = False,
    composite_mode: str = "compact",
    view: str = "2d",
    topology: str = "line",
    topology_menu: bool = False,
    direct: bool = True,
    hover: object = False,
    **options: object,
) -> tuple[Figure, Axes] | Axes:
    """Provide the pre-v2 draw contract for legacy behavioral tests.

    The current public API intentionally returns ``DrawResult`` and uses
    ``DrawConfig``. A large part of the older renderer suite still wants
    the historical tuple-or-axes contract while validating rendering
    behavior rather than public argument plumbing, so the suite routes
    those calls through this helper instead of the public entrypoint.
    """

    request = build_draw_request(
        circuit=circuit,
        framework=framework,
        style=style,
        layout=layout,
        backend=backend,
        ax=ax,
        output=output,
        show=show,
        figsize=figsize,
        page_slider=page_slider,
        page_window=page_window,
        composite_mode=composite_mode,
        view=view,  # type: ignore[arg-type]
        topology=topology,  # type: ignore[arg-type]
        topology_menu=topology_menu,
        direct=direct,
        hover=hover,
        **options,
    )
    validate_draw_request(request)
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )

    if request.ax is None:
        return render_managed_draw_pipeline(
            pipeline,
            output=request.output,
            show=request.show,
            figsize=request.figsize,
            page_slider=request.page_slider,
            page_window=request.page_window,
        )

    if request.pipeline_options.view == "3d" and not is_3d_axes(request.ax):
        raise ValueError("view='3d' requires a 3D Matplotlib axes")

    return render_draw_pipeline_on_axes(
        pipeline,
        axes=request.ax,
        output=request.output,
    )
