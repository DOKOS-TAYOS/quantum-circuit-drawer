from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest

from quantum_circuit_drawer.exceptions import UnsupportedOperationError
from quantum_circuit_drawer.ir.operations import OperationKind
from tests.support import (
    assert_axes_contains_circuit_artists,
    assert_figure_has_visible_content,
    normalize_rendered_text,
)
from tests.support import (
    draw_quantum_circuit_legacy as draw_quantum_circuit,
)

pytestmark = pytest.mark.optional


def load_cudaq_adapter_type() -> type[object]:
    try:
        module = importlib.import_module("quantum_circuit_drawer.adapters.cudaq_adapter")
    except ModuleNotFoundError as exc:
        pytest.fail(f"cudaq adapter module is missing: {exc}")
    return module.CudaqAdapter


class FakePyKernel:
    def __init__(
        self,
        *,
        mlir: str,
        required_args: int = 0,
        compiled: bool = True,
    ) -> None:
        self._mlir = mlir
        self._required_args = required_args
        self._compiled = compiled
        self.compile_calls = 0

    def is_compiled(self) -> bool:
        return self._compiled

    def compile(self) -> None:
        self.compile_calls += 1
        self._compiled = True

    def launch_args_required(self) -> int:
        return self._required_args

    def __str__(self) -> str:
        return self._mlir


class FakePyKernelDecorator(FakePyKernel):
    pass


def install_fake_cudaq(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    fake_module = ModuleType("cudaq")
    fake_module.PyKernel = FakePyKernel
    fake_module.PyKernelDecorator = FakePyKernelDecorator
    monkeypatch.setitem(sys.modules, "cudaq", fake_module)
    return fake_module


def build_supported_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__cudaq_draw() attributes {"cudaq-entrypoint"} {
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %c2 = arith.constant 2 : index
    %theta = arith.constant 1.57079632679 : f64
    %q = quake.alloca() : !quake.qvec<3>
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<3>, index) -> !quake.qref
    %q1 = quake.extract_ref %q[%c1] : (!quake.qvec<3>, index) -> !quake.qref
    %q2 = quake.extract_ref %q[%c2] : (!quake.qvec<3>, index) -> !quake.qref
    quake.h %q0 : (!quake.qref) -> ()
    quake.rz (%theta) %q1 : (f64, !quake.qref) -> ()
    quake.x [%q0] %q1 : (!quake.qref, !quake.qref) -> ()
    quake.z [%q0, %q1] %q2 : (!quake.qref, !quake.qref, !quake.qref) -> ()
    quake.swap %q1, %q2 : (!quake.qref, !quake.qref) -> ()
    %mz = quake.mz %q : (!quake.qvec<3>) -> !cc.stdvec<i1>
    %mx = quake.mx %q1 : (!quake.qref) -> i1
    %my = quake.my %q2 : (!quake.qref) -> i1
    return
  }
}
""".strip()


def build_value_form_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__value_form() attributes {"cudaq-entrypoint"} {
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %q = quake.alloca() : !quake.qvec<2>
    %r0 = quake.extract_ref %q[%c0] : (!quake.qvec<2>, index) -> !quake.qref
    %r1 = quake.extract_ref %q[%c1] : (!quake.qvec<2>, index) -> !quake.qref
    %w0 = quake.unwrap %r0 : (!quake.qref) -> !quake.wire
    %w1 = quake.unwrap %r1 : (!quake.qref) -> !quake.wire
    %w0_next = quake.h %w0 : (!quake.wire) -> !quake.wire
    quake.wrap %w0_next to %r0 : !quake.wire, !quake.qref
    quake.x [%r0] %r1 : (!quake.qref, !quake.qref) -> ()
    %m = quake.mz %q : (!quake.qvec<2>) -> !cc.stdvec<i1>
    return
  }
}
""".strip()


def build_unsupported_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__unsupported() attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<1>
    %c0 = arith.constant 0 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<1>, index) -> !quake.qref
    quake.reset %q0 : (!quake.qref) -> ()
    return
  }
}
""".strip()


def build_parameterized_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__parameterized(%arg0 : f64) attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<1>
    %c0 = arith.constant 0 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<1>, index) -> !quake.qref
    quake.rx (%arg0) %q0 : (f64, !quake.qref) -> ()
    return
  }
}
""".strip()


def build_null_wire_value_form_mlir() -> str:
    """Value-form IR emitted on newer CUDA-Q builds (null_wire + wire-typed gates)."""
    return """
module {
  func.func @__nvqpp__mlirgen__null_wire_smoke() attributes {"cudaq-entrypoint"} {
    %w0 = quake.null_wire
    %w1 = quake.h %w0 : (!quake.wire) -> !quake.wire
    return
  }
}
""".strip()


def build_modern_cudaq_builder_kernel_mlir() -> str:
    """Quake IR as printed by recent cudaq.make_kernel() (colonless veq alloca, meas ty)."""
    return """
module attributes {quake.mangled_name_map = {}} {
  func.func @__nvqpp__mlirgen__PyKernel() attributes {"cudaq-entrypoint", "cudaq-kernel"} {
    %0 = quake.alloca !quake.veq<2>
    %1 = quake.extract_ref %0[0] : (!quake.veq<2>) -> !quake.ref
    quake.h %1 : (!quake.ref) -> ()
    %2 = quake.extract_ref %0[1] : (!quake.veq<2>) -> !quake.ref
    quake.x [%1] %2 : (!quake.ref, !quake.ref) -> ()
    %measOut = quake.mz %0 : (!quake.veq<2>) -> !cc.stdvec<!quake.measure>
    quake.dealloc %0 : !quake.veq<2>
    return
  }
}
""".strip()


def test_cudaq_adapter_converts_supported_quake_mlir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_supported_quake_mlir())

    ir = adapter_type().to_ir(kernel)

    assert ir.metadata["framework"] == "cudaq"
    assert [wire.label for wire in ir.quantum_wires] == ["q0", "q1", "q2"]
    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].metadata["bundle_size"] == 5

    operations = [operation for layer in ir.layers for operation in layer.operations]
    assert [operation.kind for operation in operations[:5]] == [
        OperationKind.GATE,
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.SWAP,
    ]
    assert operations[0].name == "H"
    assert operations[1].name == "RZ"
    assert operations[1].parameters == (pytest.approx(1.57079632679),)
    assert operations[2].control_wires == ("q0",)
    assert operations[2].target_wires == ("q1",)
    assert operations[3].control_wires == ("q0", "q1")
    assert operations[3].target_wires == ("q2",)

    measurements = operations[5:]
    assert [measurement.name for measurement in measurements] == ["MZ", "MZ", "MZ", "MX", "MY"]
    assert [measurement.label for measurement in measurements] == ["MZ", "MZ", "MZ", "MX", "MY"]
    assert [measurement.metadata["measurement_basis"] for measurement in measurements] == [
        "z",
        "z",
        "z",
        "x",
        "y",
    ]
    assert [measurement.target_wires for measurement in measurements] == [
        ("q0",),
        ("q1",),
        ("q2",),
        ("q1",),
        ("q2",),
    ]
    assert [measurement.metadata["classical_bit_label"] for measurement in measurements] == [
        "c[0]",
        "c[1]",
        "c[2]",
        "c[3]",
        "c[4]",
    ]


def test_cudaq_adapter_supports_value_form_quake_mlir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_value_form_quake_mlir())

    ir = adapter_type().to_ir(kernel)

    operations = [operation for layer in ir.layers for operation in layer.operations]
    assert [operation.kind for operation in operations] == [
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.MEASUREMENT,
        OperationKind.MEASUREMENT,
    ]
    assert operations[1].control_wires == ("q0",)
    assert operations[1].target_wires == ("q1",)


def test_cudaq_adapter_supports_null_wire_in_value_form_mlir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_null_wire_value_form_mlir())

    ir = adapter_type().to_ir(kernel)

    operations = [operation for layer in ir.layers for operation in layer.operations]
    assert len(operations) == 1
    assert operations[0].kind is OperationKind.GATE
    assert operations[0].name == "H"
    assert operations[0].target_wires == ("q0",)


def test_cudaq_adapter_supports_modern_colonless_veq_alloca_mlir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_modern_cudaq_builder_kernel_mlir())

    ir = adapter_type().to_ir(kernel)

    operations = [operation for layer in ir.layers for operation in layer.operations]
    assert [wire.label for wire in ir.quantum_wires] == ["q0", "q1"]
    assert [operation.kind for operation in operations] == [
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.MEASUREMENT,
        OperationKind.MEASUREMENT,
    ]
    assert operations[0].name == "H"
    assert operations[1].name == "X"
    assert operations[1].control_wires == ("q0",)
    assert operations[1].target_wires == ("q1",)


def test_cudaq_adapter_compiles_kernel_before_reading_mlir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_supported_quake_mlir(), compiled=False)

    adapter_type().to_ir(kernel)

    assert kernel.compile_calls == 1


def test_cudaq_adapter_rejects_parameterized_kernels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_parameterized_quake_mlir(), required_args=1)

    with pytest.raises(UnsupportedOperationError, match="closed kernels"):
        adapter_type().to_ir(kernel)


def test_cudaq_adapter_rejects_non_cudaq_kernel_objects() -> None:
    adapter_type = load_cudaq_adapter_type()

    with pytest.raises(TypeError, match="non-CUDA-Q kernel"):
        adapter_type().to_ir(object())


def test_cudaq_adapter_rejects_empty_mlir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir="")

    with pytest.raises(UnsupportedOperationError, match="did not produce a Quake/MLIR string"):
        adapter_type().to_ir(kernel)


def test_cudaq_adapter_rejects_entrypoint_arguments_from_mlir_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(
        mlir="""
module {
  func.func @__nvqpp__mlirgen__argument_kernel(%arg0 : f64) {
    return
  }
}
""".strip()
    )

    with pytest.raises(UnsupportedOperationError, match="closed kernels"):
        adapter_type().to_ir(kernel)


def test_cudaq_adapter_rejects_unsupported_quake_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_unsupported_quake_mlir())

    with pytest.raises(UnsupportedOperationError, match="reset"):
        adapter_type().to_ir(kernel)


def test_cudaq_adapter_can_handle_returns_false_when_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_type = load_cudaq_adapter_type()
    monkeypatch.delitem(sys.modules, "cudaq", raising=False)

    assert adapter_type.can_handle(object()) is False


def test_cudaq_adapter_can_handle_does_not_swallow_unexpected_import_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_type = load_cudaq_adapter_type()
    original_import = __import__

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "cudaq" or name.startswith("cudaq."):
            raise RuntimeError("boom: cudaq")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(RuntimeError, match="boom: cudaq"):
        adapter_type.can_handle(object())


def test_draw_quantum_circuit_accepts_cudaq_framework_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    kernel = FakePyKernel(mlir=build_supported_quake_mlir())

    figure, axes = draw_quantum_circuit(kernel, framework="cudaq")
    texts = {normalize_rendered_text(text.get_text()) for text in axes.texts}

    assert axes.figure is figure
    assert_axes_contains_circuit_artists(axes, expected_texts={"H", "MZ", "q0", "q1", "q2"})
    assert any(text.startswith("RZ\n") for text in texts)
    assert_figure_has_visible_content(figure)
