from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest

from quantum_circuit_drawer.exceptions import UnsupportedOperationError
from quantum_circuit_drawer.ir.lowering import lower_semantic_circuit
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


def build_reset_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__reset() attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<1>
    %c0 = arith.constant 0 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<1>, index) -> !quake.qref
    quake.h %q0 : (!quake.qref) -> ()
    quake.reset %q0 : (!quake.qref) -> ()
    %m = quake.mz %q0 : (!quake.qref) -> i1
    return
  }
}
""".strip()


def build_controlled_swap_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__controlled_swap() attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<3>
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %c2 = arith.constant 2 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<3>, index) -> !quake.qref
    %q1 = quake.extract_ref %q[%c1] : (!quake.qvec<3>, index) -> !quake.qref
    %q2 = quake.extract_ref %q[%c2] : (!quake.qvec<3>, index) -> !quake.qref
    quake.swap [%q0] %q1, %q2 : (!quake.qref, !quake.qref, !quake.qref) -> ()
    return
  }
}
""".strip()


def build_multi_controlled_swap_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__multi_controlled_swap() attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<4>
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %c2 = arith.constant 2 : index
    %c3 = arith.constant 3 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<4>, index) -> !quake.qref
    %q1 = quake.extract_ref %q[%c1] : (!quake.qvec<4>, index) -> !quake.qref
    %q2 = quake.extract_ref %q[%c2] : (!quake.qvec<4>, index) -> !quake.qref
    %q3 = quake.extract_ref %q[%c3] : (!quake.qvec<4>, index) -> !quake.qref
    quake.swap [%q0, %q1] %q2, %q3 : (!quake.qref, !quake.qref, !quake.qref, !quake.qref) -> ()
    return
  }
}
""".strip()


def build_dynamic_size_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__dynamic_qvec() attributes {"cudaq-entrypoint"} {
    %size = cc.load %arg0 : !cc.ptr<i64>
    %q = quake.alloca(%size) : !quake.qvec<?>
    return
  }
}
""".strip()


def build_modern_dynamic_size_quake_mlir() -> str:
    return """
module attributes {quake.mangled_name_map = {}} {
  func.func @__nvqpp__mlirgen__dynamic_qvec(%arg0: i64) attributes {"cudaq-entrypoint", "cudaq-kernel"} {
    %0 = quake.alloca !quake.veq<?>[%arg0 : i64]
    %1 = quake.extract_ref %0[0] : (!quake.veq<?>) -> !quake.ref
    quake.h %1 : (!quake.ref) -> ()
    %measOut = quake.mz %0 : (!quake.veq<?>) -> !cc.stdvec<!quake.measure>
    quake.dealloc %0 : !quake.veq<?>
    return
  }
}
""".strip()


def build_loaded_dynamic_size_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__loaded_dynamic_qvec(%arg0 : !cc.ptr<i64>) attributes {"cudaq-entrypoint"} {
    %size = cc.load %arg0 : !cc.ptr<i64>
    %q = quake.alloca(%size) : !quake.qvec<?>
    %c0 = arith.constant 0 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<?>, index) -> !quake.qref
    quake.x %q0 : (!quake.qref) -> ()
    return
  }
}
""".strip()


def build_cc_if_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__cc_if() attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<2>
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %cond = arith.constant 1 : i1
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<2>, index) -> !quake.qref
    %q1 = quake.extract_ref %q[%c1] : (!quake.qvec<2>, index) -> !quake.qref
    cc.if (%cond) {
      quake.h %q0 : (!quake.qref) -> ()
      quake.x [%q0] %q1 : (!quake.qref, !quake.qref) -> ()
    }
    return
  }
}
""".strip()


def build_scf_if_else_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__scf_if() attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<2>
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %cond = arith.constant 1 : i1
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<2>, index) -> !quake.qref
    %q1 = quake.extract_ref %q[%c1] : (!quake.qvec<2>, index) -> !quake.qref
    scf.if %cond {
      quake.h %q0 : (!quake.qref) -> ()
    } else {
      quake.x %q1 : (!quake.qref) -> ()
    }
    return
  }
}
""".strip()


def build_scf_for_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__scf_for() attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<2>
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %c4 = arith.constant 4 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<2>, index) -> !quake.qref
    %q1 = quake.extract_ref %q[%c1] : (!quake.qvec<2>, index) -> !quake.qref
    scf.for %i = %c0 to %c4 step %c1 {
      quake.x [%q0] %q1 : (!quake.qref, !quake.qref) -> ()
    }
    return
  }
}
""".strip()


def build_cc_loop_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__cc_loop() attributes {"cudaq-entrypoint"} {
    %q = quake.alloca() : !quake.qvec<2>
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %cond = arith.constant 1 : i1
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<2>, index) -> !quake.qref
    %q1 = quake.extract_ref %q[%c1] : (!quake.qvec<2>, index) -> !quake.qref
    cc.loop while {
      cc.condition %cond
    } do {
      quake.x [%q0] %q1 : (!quake.qref, !quake.qref) -> ()
      cc.continue
    } step {
    }
    return
  }
}
""".strip()


def build_cfg_control_flow_quake_mlir() -> str:
    return """
module {
  func.func @__nvqpp__mlirgen__control_flow() attributes {"cudaq-entrypoint"} {
    cf.cond_br %cond, ^bb1, ^bb2
  ^bb1:
      return
  ^bb2:
    return
  }
}
""".strip()


def build_unsupported_named_operation_mlir(op_name: str) -> str:
    return f"""
module {{
  func.func @__nvqpp__mlirgen__{op_name}() attributes {{"cudaq-entrypoint"}} {{
    %q = quake.alloca() : !quake.qvec<1>
    %c0 = arith.constant 0 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<1>, index) -> !quake.qref
    quake.{op_name} %q0 : (!quake.qref) -> ()
    return
  }}
}}
""".strip()


def build_compact_named_operation_mlir(
    op_name: str,
    *,
    symbol_names: tuple[str, ...],
) -> str:
    symbol_list = ", ".join(f"@{name}" for name in symbol_names)
    return f"""
module {{
  func.func @__nvqpp__mlirgen__compact_{op_name}() attributes {{"cudaq-entrypoint"}} {{
    %q = quake.alloca() : !quake.qvec<2>
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %q0 = quake.extract_ref %q[%c0] : (!quake.qvec<2>, index) -> !quake.qref
    %q1 = quake.extract_ref %q[%c1] : (!quake.qvec<2>, index) -> !quake.qref
    quake.{op_name} {symbol_list} %q0, %q1 : (!quake.qref, !quake.qref) -> ()
    return
  }}
}}
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


def build_mixed_parameterized_dynamic_quake_mlir() -> str:
    return """
module attributes {quake.mangled_name_map = {}} {
  func.func @__nvqpp__mlirgen__mixed_parameterized(%arg0: i64, %arg1: f64) attributes {"cudaq-entrypoint", "cudaq-kernel"} {
    %0 = quake.alloca !quake.veq<?>[%arg0 : i64]
    %1 = quake.extract_ref %0[0] : (!quake.veq<?>) -> !quake.ref
    quake.rx (%arg1) %1 : (f64, !quake.ref) -> ()
    %measOut = quake.mz %0 : (!quake.veq<?>) -> !cc.stdvec<!quake.measure>
    quake.dealloc %0 : !quake.veq<?>
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


def test_cudaq_adapter_emits_semantic_ir_with_reset_and_quake_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_reset_quake_mlir())

    semantic = adapter.to_semantic_ir(kernel)

    assert semantic is not None
    operations = [operation for layer in semantic.layers for operation in layer.operations]
    assert [operation.name for operation in operations] == ["H", "RESET", "MZ"]
    assert operations[1].kind is OperationKind.GATE
    assert operations[1].provenance.framework == "cudaq"
    assert operations[1].provenance.native_name == "reset"
    assert operations[1].provenance.native_kind == "reset"
    assert "quake: reset" in operations[1].hover_details
    assert operations[2].provenance.native_name == "mz"
    assert operations[2].metadata["measurement_basis"] == "z"

    lowered = lower_semantic_circuit(semantic)
    lowered_operations = [operation for layer in lowered.layers for operation in layer.operations]
    assert lowered_operations[1].name == "RESET"
    assert lowered_operations[1].metadata["semantic_provenance"]["native_name"] == "reset"
    assert lowered_operations[2].metadata["measurement_basis"] == "z"


def test_cudaq_adapter_compiles_kernel_before_reading_mlir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_supported_quake_mlir(), compiled=False)

    adapter_type().to_ir(kernel)

    assert kernel.compile_calls == 1


def test_cudaq_adapter_rejects_parameterized_kernels_without_runtime_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_parameterized_quake_mlir(), required_args=1)

    with pytest.raises(UnsupportedOperationError, match="cudaq_args"):
        adapter_type().to_ir(kernel)


def test_cudaq_adapter_uses_runtime_args_for_parameterized_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_parameterized_quake_mlir(), required_args=1)

    semantic = adapter.to_semantic_ir(kernel, options={"cudaq_args": (0.25,)})

    operations = [operation for layer in semantic.layers for operation in layer.operations]

    assert operations[0].name == "RX"
    assert operations[0].parameters == (0.25,)


def test_cudaq_adapter_uses_runtime_args_for_modern_dynamic_qvectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_modern_dynamic_size_quake_mlir(), required_args=1)

    semantic = adapter.to_semantic_ir(kernel, options={"cudaq_args": (3,)})

    operations = [operation for layer in semantic.layers for operation in layer.operations]

    assert [wire.label for wire in semantic.quantum_wires] == ["q0", "q1", "q2"]
    assert [operation.name for operation in operations] == ["H", "MZ", "MZ", "MZ"]


def test_cudaq_adapter_uses_runtime_args_through_cc_load_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_loaded_dynamic_size_quake_mlir(), required_args=1)

    semantic = adapter.to_semantic_ir(kernel, options={"cudaq_args": (2,)})

    operations = [operation for layer in semantic.layers for operation in layer.operations]

    assert [wire.label for wire in semantic.quantum_wires] == ["q0", "q1"]
    assert [operation.name for operation in operations] == ["X"]


def test_cudaq_adapter_uses_mixed_runtime_args_for_dynamic_size_and_gate_parameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_mixed_parameterized_dynamic_quake_mlir(), required_args=2)

    semantic = adapter.to_semantic_ir(kernel, options={"cudaq_args": (2, 0.5)})

    operations = [operation for layer in semantic.layers for operation in layer.operations]

    assert [wire.label for wire in semantic.quantum_wires] == ["q0", "q1"]
    assert operations[0].name == "RX"
    assert operations[0].parameters == (0.5,)
    assert [operation.name for operation in operations[1:]] == ["MZ", "MZ"]


def test_cudaq_adapter_rejects_wrong_runtime_arg_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_parameterized_quake_mlir(), required_args=1)

    with pytest.raises(UnsupportedOperationError, match="expected 1 CUDA-Q runtime argument"):
        adapter_type().to_ir(kernel, options={"cudaq_args": (0.25, 3)})


def test_cudaq_adapter_rejects_unsupported_runtime_arg_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_parameterized_quake_mlir(), required_args=1)

    with pytest.raises(UnsupportedOperationError, match="only supports scalar"):
        adapter_type().to_ir(kernel, options={"cudaq_args": ([0.25],)})


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

    with pytest.raises(UnsupportedOperationError, match="cudaq_args"):
        adapter_type().to_ir(kernel)


def test_cudaq_adapter_supports_controlled_swap_as_compact_controlled_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_controlled_swap_quake_mlir())

    semantic = adapter.to_semantic_ir(kernel)

    assert semantic is not None
    operations = [operation for layer in semantic.layers for operation in layer.operations]
    assert len(operations) == 1
    assert operations[0].kind is OperationKind.CONTROLLED_GATE
    assert operations[0].name == "SWAP"
    assert operations[0].label == "SWAP"
    assert operations[0].control_wires == ("q0",)
    assert operations[0].target_wires == ("q1", "q2")
    assert operations[0].hover_details == (
        "quake: swap",
        "controls: q0",
        "targets: q1, q2",
    )
    assert operations[0].provenance.framework == "cudaq"
    assert operations[0].provenance.native_name == "swap"
    assert operations[0].provenance.native_kind == "controlled_swap"

    lowered = lower_semantic_circuit(semantic)
    lowered_operation = lowered.layers[0].operations[0]
    assert lowered_operation.kind is OperationKind.CONTROLLED_GATE
    assert lowered_operation.name == "SWAP"
    assert lowered_operation.control_wires == ("q0",)
    assert lowered_operation.target_wires == ("q1", "q2")
    assert lowered_operation.metadata["semantic_provenance"]["native_kind"] == "controlled_swap"
    assert lowered_operation.metadata["hover_details"] == operations[0].hover_details


def test_cudaq_adapter_supports_multi_controlled_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_multi_controlled_swap_quake_mlir())

    semantic = adapter.to_semantic_ir(kernel)

    assert semantic is not None
    operations = [operation for layer in semantic.layers for operation in layer.operations]
    assert len(operations) == 1
    assert operations[0].kind is OperationKind.CONTROLLED_GATE
    assert operations[0].name == "SWAP"
    assert operations[0].control_wires == ("q0", "q1")
    assert operations[0].target_wires == ("q2", "q3")
    assert "controls: q0, q1" in operations[0].hover_details
    assert "targets: q2, q3" in operations[0].hover_details


@pytest.mark.parametrize(
    ("op_name", "symbol_names", "expected_label", "expected_hover_detail"),
    [
        ("apply", ("oracle",), "APPLY", "callable: @oracle"),
        ("adjoint", ("reflect",), "ADJOINT", "callable: @reflect"),
        (
            "compute_action",
            ("compute_region", "action_region"),
            "COMPUTE/ACTION",
            "callables: @compute_region, @action_region",
        ),
    ],
)
def test_cudaq_adapter_keeps_named_operations_as_compact_semantic_boxes(
    op_name: str,
    symbol_names: tuple[str, ...],
    expected_label: str,
    expected_hover_detail: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(
        mlir=build_compact_named_operation_mlir(op_name, symbol_names=symbol_names)
    )

    semantic = adapter.to_semantic_ir(kernel)

    assert semantic is not None
    operations = [operation for layer in semantic.layers for operation in layer.operations]
    assert len(operations) == 1
    assert operations[0].kind is OperationKind.GATE
    assert operations[0].name == expected_label
    assert operations[0].target_wires == ("q0", "q1")
    assert operations[0].hover_details[0] == f"quake: {op_name}"
    assert expected_hover_detail in operations[0].hover_details
    assert "wires: q0, q1" in operations[0].hover_details
    assert operations[0].provenance.framework == "cudaq"
    assert operations[0].provenance.native_name == op_name
    assert operations[0].provenance.native_kind == "composite"

    lowered = lower_semantic_circuit(semantic)
    lowered_operation = lowered.layers[0].operations[0]
    assert lowered_operation.name == expected_label
    assert lowered_operation.metadata["semantic_provenance"]["native_name"] == op_name
    assert lowered_operation.metadata["semantic_provenance"]["native_kind"] == "composite"
    assert lowered_operation.metadata["hover_details"] == operations[0].hover_details


def test_cudaq_adapter_supports_cc_if_as_compact_semantic_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_cc_if_quake_mlir())

    semantic = adapter.to_semantic_ir(kernel)

    assert semantic is not None
    operations = [operation for layer in semantic.layers for operation in layer.operations]
    assert len(operations) == 1
    assert operations[0].kind is OperationKind.GATE
    assert operations[0].name == "IF"
    assert operations[0].label == "IF"
    assert operations[0].target_wires == ("q0", "q1")
    assert operations[0].hover_details == (
        "control flow: cc.if",
        "condition: %cond",
        "branches: true only",
        "block ops: true=2",
        "wires: q0, q1",
    )
    assert operations[0].provenance.framework == "cudaq"
    assert operations[0].provenance.native_name == "cc.if"
    assert operations[0].provenance.native_kind == "control_flow"

    lowered = lower_semantic_circuit(semantic)
    lowered_operation = lowered.layers[0].operations[0]
    assert lowered_operation.name == "IF"
    assert lowered_operation.target_wires == ("q0", "q1")
    assert lowered_operation.metadata["semantic_provenance"]["native_name"] == "cc.if"
    assert lowered_operation.metadata["semantic_provenance"]["native_kind"] == "control_flow"
    assert lowered_operation.metadata["hover_details"] == operations[0].hover_details


def test_cudaq_adapter_supports_scf_if_else_as_compact_semantic_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_scf_if_else_quake_mlir())

    semantic = adapter.to_semantic_ir(kernel)

    assert semantic is not None
    operations = [operation for layer in semantic.layers for operation in layer.operations]
    assert len(operations) == 1
    assert operations[0].kind is OperationKind.GATE
    assert operations[0].name == "IF/ELSE"
    assert operations[0].label == "IF/ELSE"
    assert operations[0].target_wires == ("q0", "q1")
    assert operations[0].hover_details == (
        "control flow: scf.if",
        "condition: %cond",
        "branches: true, false",
        "block ops: true=1, false=1",
        "wires: q0, q1",
    )
    assert operations[0].provenance.native_name == "scf.if"
    assert operations[0].provenance.native_kind == "control_flow"


def test_cudaq_adapter_supports_scf_for_as_compact_semantic_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_scf_for_quake_mlir())

    semantic = adapter.to_semantic_ir(kernel)

    assert semantic is not None
    operations = [operation for layer in semantic.layers for operation in layer.operations]
    assert len(operations) == 1
    assert operations[0].kind is OperationKind.GATE
    assert operations[0].name == "FOR"
    assert operations[0].label == "FOR"
    assert operations[0].target_wires == ("q0", "q1")
    assert operations[0].hover_details == (
        "control flow: scf.for",
        "iteration: %i = %c0 to %c4 step %c1",
        "body ops: 1",
        "wires: q0, q1",
    )
    assert operations[0].provenance.native_name == "scf.for"
    assert operations[0].provenance.native_kind == "control_flow"


def test_cudaq_adapter_supports_cc_loop_as_compact_semantic_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter = load_cudaq_adapter_type()()
    kernel = FakePyKernel(mlir=build_cc_loop_quake_mlir())

    semantic = adapter.to_semantic_ir(kernel)

    assert semantic is not None
    operations = [operation for layer in semantic.layers for operation in layer.operations]
    assert len(operations) == 1
    assert operations[0].kind is OperationKind.GATE
    assert operations[0].name == "LOOP"
    assert operations[0].label == "LOOP"
    assert operations[0].target_wires == ("q0", "q1")
    assert operations[0].hover_details == (
        "control flow: cc.loop",
        "region count: 3",
        "region ops: while=1, do=2, step=0",
        "wires: q0, q1",
    )
    assert operations[0].provenance.native_name == "cc.loop"
    assert operations[0].provenance.native_kind == "control_flow"


def test_cudaq_adapter_rejects_cfg_control_flow_constructs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_cfg_control_flow_quake_mlir())

    with pytest.raises(UnsupportedOperationError, match="control-flow"):
        adapter_type().to_ir(kernel)


def test_cudaq_adapter_rejects_unresolved_dynamic_qvector_sizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    adapter_type = load_cudaq_adapter_type()
    kernel = FakePyKernel(mlir=build_dynamic_size_quake_mlir())

    with pytest.raises(UnsupportedOperationError, match="literal size"):
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


def test_draw_quantum_circuit_renders_cudaq_compact_named_operation_boxes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    kernel = FakePyKernel(
        mlir=build_compact_named_operation_mlir("apply", symbol_names=("oracle",))
    )

    figure, axes = draw_quantum_circuit(kernel, framework="cudaq", show=False)
    texts = {normalize_rendered_text(text.get_text()) for text in axes.texts}

    assert axes.figure is figure
    assert_axes_contains_circuit_artists(axes, expected_texts={"APPLY", "q0", "q1"})
    assert "H" not in texts
    assert_figure_has_visible_content(figure)


def test_draw_quantum_circuit_renders_cudaq_controlled_swap_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    kernel = FakePyKernel(mlir=build_controlled_swap_quake_mlir())

    figure, axes = draw_quantum_circuit(kernel, framework="cudaq", show=False)
    texts = {normalize_rendered_text(text.get_text()) for text in axes.texts}

    assert axes.figure is figure
    assert "SWAP" in texts
    assert_axes_contains_circuit_artists(axes, expected_texts={"SWAP", "q0", "q1", "q2"})
    assert_figure_has_visible_content(figure)


@pytest.mark.parametrize(
    ("builder", "expected_label", "expected_wires"),
    [
        (build_cc_if_quake_mlir, "if", {"q0", "q1"}),
        (build_scf_if_else_quake_mlir, "if/else", {"q0", "q1"}),
        (build_scf_for_quake_mlir, "for", {"q0", "q1"}),
        (build_cc_loop_quake_mlir, "loop", {"q0", "q1"}),
    ],
)
def test_draw_quantum_circuit_renders_cudaq_control_flow_boxes(
    builder: object,
    expected_label: str,
    expected_wires: set[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cudaq(monkeypatch)
    kernel = FakePyKernel(mlir=builder())

    figure, axes = draw_quantum_circuit(kernel, framework="cudaq", show=False)
    texts = {normalize_rendered_text(text.get_text()) for text in axes.texts}

    assert axes.figure is figure
    assert expected_label in texts
    assert_axes_contains_circuit_artists(axes, expected_texts={expected_label, *expected_wires})
    assert_figure_has_visible_content(figure)
