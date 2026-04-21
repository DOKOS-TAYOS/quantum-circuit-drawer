"""CUDA-Q adapter backed by Quake/MLIR parsing."""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping

from ..exceptions import UnsupportedOperationError
from ..ir.circuit import CircuitIR
from ._cudaq_quake_parser import CudaqQuakeParser
from ._helpers import build_classical_register, extract_dependency_types, sequential_bit_labels
from .base import BaseAdapter

_ENTRYPOINT_RE = re.compile(r"func\.func\s+@(?P<name>[^\(\s]+)\((?P<args>[^\)]*)\)(?P<rest>.*)")


class CudaqAdapter(BaseAdapter):
    """Convert CUDA-Q kernels into CircuitIR."""

    framework_name = "cudaq"

    @classmethod
    def explicit_framework_unavailable_reason(cls) -> str | None:
        kernel_types = extract_dependency_types("cudaq", ("PyKernel", "PyKernelDecorator"))
        if kernel_types:
            return None
        if sys.platform.startswith("win"):
            return (
                "CUDA-Q support is Linux/WSL2-only in this project and is not expected to work "
                "on native Windows. Use WSL2 or Linux, then install "
                "'quantum-circuit-drawer[cudaq]' there."
            )
        return (
            "CUDA-Q support requires the optional dependency 'cudaq'. Use Linux or WSL2, then "
            "install 'quantum-circuit-drawer[cudaq]'."
        )

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        kernel_types = extract_dependency_types("cudaq", ("PyKernel", "PyKernelDecorator"))
        return bool(kernel_types) and isinstance(circuit, kernel_types)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        del options
        if not self.can_handle(circuit):
            raise TypeError("CudaqAdapter received a non-CUDA-Q kernel")

        self._ensure_closed_kernel(circuit)
        mlir = self._materialize_mlir(circuit)
        parser = CudaqQuakeParser(mlir)
        quantum_wires, operations = parser.parse()
        classical_wires, _ = build_classical_register(
            sequential_bit_labels(parser.measurement_count)
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
