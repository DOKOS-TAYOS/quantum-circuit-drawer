"""CUDA-Q adapter backed by Quake/MLIR parsing."""

from __future__ import annotations

import re
from collections.abc import Mapping

from ..exceptions import UnsupportedOperationError
from ..ir.circuit import CircuitIR
from ..ir.wires import WireIR, WireKind
from ._cudaq_quake_parser import CudaqQuakeParser
from .base import BaseAdapter

_ENTRYPOINT_RE = re.compile(
    r"func\.func\s+@(?P<name>[^\(\s]+)\((?P<args>[^\)]*)\)(?P<rest>.*)"
)


class CudaqAdapter(BaseAdapter):
    """Convert CUDA-Q kernels into CircuitIR."""

    framework_name = "cudaq"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        try:
            import cudaq  # type: ignore[import-not-found]
        except ImportError:
            return False

        kernel_types = tuple(
            candidate
            for candidate in (
                getattr(cudaq, "PyKernel", None),
                getattr(cudaq, "PyKernelDecorator", None),
            )
            if isinstance(candidate, type)
        )
        return bool(kernel_types) and isinstance(circuit, kernel_types)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        if not self.can_handle(circuit):
            raise TypeError("CudaqAdapter received a non-CUDA-Q kernel")

        self._ensure_closed_kernel(circuit)
        mlir = self._materialize_mlir(circuit)
        parser = CudaqQuakeParser(mlir)
        quantum_wires, operations = parser.parse()
        classical_wires: list[WireIR] = []
        if parser.measurement_count:
            classical_wires.append(
                WireIR(
                    id="c0",
                    index=0,
                    kind=WireKind.CLASSICAL,
                    label="c",
                    metadata={"bundle_size": parser.measurement_count},
                )
            )

        return CircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=self.pack_operations(operations),
            name=getattr(circuit, "name", None),
            metadata={"framework": self.framework_name},
        )

    def _ensure_closed_kernel(self, circuit: object) -> None:
        if hasattr(circuit, "launch_args_required"):
            required_args = circuit.launch_args_required()
            if isinstance(required_args, int) and required_args > 0:
                raise UnsupportedOperationError(
                    "CUDA-Q support in v0.1 only supports closed kernels without runtime arguments"
                )

    def _materialize_mlir(self, circuit: object) -> str:
        if hasattr(circuit, "is_compiled") and hasattr(circuit, "compile"):
            is_compiled = circuit.is_compiled()
            if isinstance(is_compiled, bool) and not is_compiled:
                circuit.compile()

        mlir = str(circuit).strip()
        if not mlir:
            raise UnsupportedOperationError("CUDA-Q kernel did not produce a Quake/MLIR string")

        entrypoint = self._find_entrypoint_signature(mlir)
        if entrypoint is not None and entrypoint.group("args").strip():
            raise UnsupportedOperationError(
                "CUDA-Q support in v0.1 only supports closed kernels without runtime arguments"
            )
        return mlir

    def _find_entrypoint_signature(self, mlir: str) -> re.Match[str] | None:
        entrypoint_match: re.Match[str] | None = None
        for raw_line in mlir.splitlines():
            line = raw_line.strip()
            if "func.func" not in line:
                continue
            match = _ENTRYPOINT_RE.search(line)
            if match is None:
                continue
            if "cudaq-entrypoint" in line:
                return match
            if entrypoint_match is None:
                entrypoint_match = match
        return entrypoint_match
