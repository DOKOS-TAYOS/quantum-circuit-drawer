from __future__ import annotations

import sys
from pathlib import Path

import pytest

from quantum_circuit_drawer.adapters.cudaq_adapter import CudaqAdapter
from quantum_circuit_drawer.api import draw_quantum_circuit
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


def test_cudaq_example_smoke_render_on_linux(sandbox_tmp_path: Path) -> None:
    pytest.importorskip("cudaq")
    from examples._shared import ExampleRequest
    from examples.cudaq_random import build_kernel

    output = sandbox_tmp_path / "cudaq-demo.png"
    request = ExampleRequest(
        qubits=4,
        columns=6,
        mode="pages",
        view="2d",
        topology="line",
        seed=7,
        output=None,
        show=False,
        figsize=(8.0, 3.0),
    )

    figure, axes = draw_quantum_circuit(
        build_kernel(request),
        framework="cudaq",
        output=output,
        show=False,
    )

    assert output.exists()
    assert output.stat().st_size > 0
    assert axes.lines
    assert axes.patches
    figure.clear()
