from __future__ import annotations

import sys

import pytest

from quantum_circuit_drawer.adapters.cudaq_adapter import CudaqAdapter
from quantum_circuit_drawer.ir.operations import OperationKind

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="CUDA-Q integration coverage is Linux/WSL-first in v0.1",
)


def test_cudaq_adapter_converts_make_kernel_kernel_on_linux() -> None:
    cudaq = pytest.importorskip("cudaq")

    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(2)
    kernel.h(qubits[0])
    kernel.cx(qubits[0], qubits[1])
    kernel.mz(qubits)

    ir = CudaqAdapter().to_ir(kernel)

    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert ir.metadata["framework"] == "cudaq"
    assert [wire.label for wire in ir.quantum_wires] == ["q0", "q1"]
    assert len(ir.classical_wires) == 1
    assert [operation.kind for operation in operations] == [
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.MEASUREMENT,
        OperationKind.MEASUREMENT,
    ]


def test_cudaq_adapter_converts_decorated_kernel_on_linux() -> None:
    cudaq = pytest.importorskip("cudaq")

    @cudaq.kernel
    def bell_pair() -> None:
        qubits = cudaq.qvector(2)
        h(qubits[0])
        x.ctrl(qubits[0], qubits[1])
        mz(qubits)

    ir = CudaqAdapter().to_ir(bell_pair)

    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert ir.metadata["framework"] == "cudaq"
    assert any(operation.kind is OperationKind.CONTROLLED_GATE for operation in operations)
    assert [operation.name for operation in operations[-2:]] == ["MZ", "MZ"]
