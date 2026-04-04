from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import matplotlib.pyplot as plt
import pytest
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure

import quantum_circuit_drawer
from quantum_circuit_drawer.api import draw_quantum_circuit
from quantum_circuit_drawer.exceptions import (
    RenderingError,
    StyleValidationError,
    UnsupportedBackendError,
    UnsupportedFrameworkError,
)
from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.style import DrawStyle


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


def test_draw_quantum_circuit_returns_figure_and_axes_for_ir() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_draws_on_existing_axes() -> None:
    _, axes = plt.subplots()

    result = draw_quantum_circuit(build_sample_ir(), ax=axes)

    assert result is axes


def test_draw_quantum_circuit_saves_output(sandbox_tmp_path: Path) -> None:
    output = sandbox_tmp_path / "circuit.png"

    draw_quantum_circuit(build_sample_ir(), output=output, show=False)

    assert output.exists()


def test_draw_quantum_circuit_rejects_invalid_backend() -> None:
    with pytest.raises(UnsupportedBackendError):
        draw_quantum_circuit(build_sample_ir(), backend="svg")


def test_draw_quantum_circuit_validates_style_input() -> None:
    with pytest.raises(StyleValidationError):
        draw_quantum_circuit(build_sample_ir(), style={"font_size": -1})


def test_draw_quantum_circuit_accepts_dark_theme() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), style={"theme": "dark"}, show=False)

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_accepts_page_wrapping_style() -> None:
    figure, axes = draw_quantum_circuit(
        build_sample_ir(), style={"max_page_width": 4.0}, show=False
    )

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_uses_dark_theme_by_default() -> None:
    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure.get_facecolor() == to_rgba("#0b1220")
    assert axes.get_facecolor() == to_rgba("#0b1220")


def test_draw_quantum_circuit_honors_explicit_framework_override() -> None:
    with pytest.raises(UnsupportedFrameworkError):
        draw_quantum_circuit(build_sample_ir(), framework="qiskit")


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


def test_draw_quantum_circuit_accepts_cudaq_framework_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_kernel_type = install_fake_cudaq(monkeypatch)

    figure, axes = draw_quantum_circuit(fake_kernel_type(), framework="cudaq", show=False)

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_wraps_output_errors() -> None:
    def fail_savefig(self: Figure, *args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(Figure, "savefig", fail_savefig)
    try:
        with pytest.raises(RenderingError, match="disk full"):
            draw_quantum_circuit(build_sample_ir(), output=Path("ignored.png"), show=False)
    finally:
        monkeypatch.undo()


def test_package_level_draw_quantum_circuit_forwards_show_parameter() -> None:
    figure, axes = quantum_circuit_drawer.draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure is not None
    assert axes.figure is figure


def test_draw_quantum_circuit_exposes_version() -> None:
    assert quantum_circuit_drawer.__version__ == "0.1.1"


def test_draw_quantum_circuit_emits_debug_logs_when_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG", logger="quantum_circuit_drawer")

    draw_quantum_circuit(build_sample_ir(), show=False)

    assert any("backend='matplotlib'" in record.getMessage() for record in caplog.records)


def test_draw_quantum_circuit_shows_managed_figures_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    show_calls: list[bool] = []

    def fake_show(*args: object, **kwargs: object) -> None:
        show_calls.append(True)

    monkeypatch.setattr(plt, "show", fake_show)

    figure, axes = draw_quantum_circuit(build_sample_ir())

    assert figure is not None
    assert axes.figure is figure
    assert show_calls == [True]
    plt.close(figure)


def test_draw_quantum_circuit_skips_show_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_show(*args: object, **kwargs: object) -> None:
        raise AssertionError("matplotlib.pyplot.show should not be called when show=False")

    monkeypatch.setattr(plt, "show", fail_show)

    figure, axes = draw_quantum_circuit(build_sample_ir(), show=False)

    assert figure is not None
    assert axes.figure is figure
    plt.close(figure)


def test_draw_quantum_circuit_does_not_show_existing_axes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    figure, axes = plt.subplots()

    def fail_show(*args: object, **kwargs: object) -> None:
        raise AssertionError("matplotlib.pyplot.show should not be called for caller-managed axes")

    monkeypatch.setattr(plt, "show", fail_show)

    result = draw_quantum_circuit(build_sample_ir(), ax=axes)

    assert result is axes
    plt.close(figure)


def test_draw_quantum_circuit_rejects_page_slider_with_existing_axes() -> None:
    figure, axes = plt.subplots()

    with pytest.raises(ValueError, match="page_slider"):
        draw_quantum_circuit(build_sample_ir(), ax=axes, page_slider=True)

    plt.close(figure)


def test_draw_quantum_circuit_adds_continuous_page_slider_for_wrapped_managed_figures() -> None:
    paged_scene = LayoutEngine().compute(build_wrapped_ir(), DrawStyle(max_page_width=4.0))
    long_scene = LayoutEngine().compute(build_wrapped_ir(), DrawStyle(max_page_width=100.0))

    assert len(paged_scene.pages) > 1
    assert len(long_scene.pages) == 1

    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        page_slider=True,
        show=False,
    )

    page_slider = getattr(figure, "_quantum_circuit_drawer_page_slider", None)

    assert page_slider is not None
    assert len(figure.axes) == 2
    assert axes.get_xlim() == pytest.approx((0.0, paged_scene.width))
    assert axes.get_ylim() == pytest.approx((long_scene.height, 0.0))

    page_slider.set_val(page_slider.valmax)

    assert axes.get_xlim() == pytest.approx(
        (long_scene.width - paged_scene.width, long_scene.width)
    )
    plt.close(figure)


def test_draw_quantum_circuit_saves_paged_figure_before_adding_continuous_slider(
    monkeypatch: pytest.MonkeyPatch,
    sandbox_tmp_path: Path,
) -> None:
    output = sandbox_tmp_path / "wrapped-circuit.png"
    original_savefig = Figure.savefig
    saved_axes_counts: list[int] = []

    def count_savefig(self: Figure, *args: object, **kwargs: object) -> None:
        saved_axes_counts.append(len(self.axes))
        original_savefig(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", count_savefig)

    figure, axes = draw_quantum_circuit(
        build_wrapped_ir(),
        style={"max_page_width": 4.0},
        output=output,
        page_slider=True,
        show=False,
    )

    assert axes.figure is figure
    assert output.exists()
    assert saved_axes_counts == [1]
    assert len(figure.axes) == 2
    plt.close(figure)
