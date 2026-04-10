from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind
from quantum_circuit_drawer.layout.engine import LayoutEngine
from quantum_circuit_drawer.layout.scene import LayoutScene
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
    type: str = "GATETYPE"
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
