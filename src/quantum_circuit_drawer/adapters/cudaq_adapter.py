"""CUDA-Q adapter backed by Quake/MLIR parsing."""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from ..exceptions import UnsupportedOperationError
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.semantic import SemanticCircuitIR, pack_semantic_operations
from ._cudaq_quake_parser import CudaqQuakeParser
from ._helpers import build_classical_register, extract_dependency_types, sequential_bit_labels
from .base import BaseAdapter

_ENTRYPOINT_RE = re.compile(r"func\.func\s+@(?P<name>[^\(\s]+)\((?P<args>[^\)]*)\)(?P<rest>.*)")
_ENTRYPOINT_ARGUMENT_RE = re.compile(r"^(?P<name>%[\w$.]+)\s*:\s*(?P<type>.+)$")
_CUDAQ_ARGS_OPTION = "cudaq_args"


@dataclass(frozen=True, slots=True)
class _CudaqRuntimeArgument:
    name: str
    type_text: str


class CudaqAdapter(BaseAdapter):
    """Convert CUDA-Q kernels into semantic IR and ``CircuitIR``."""

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
        semantic_ir = self.to_semantic_ir(circuit, options=options)
        assert semantic_ir is not None
        return lower_semantic_circuit(semantic_ir)

    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR:
        if not self.can_handle(circuit):
            raise TypeError("CudaqAdapter received a non-CUDA-Q kernel")

        adapter_options = dict(options or {})
        mlir = self._materialize_mlir(circuit)
        runtime_arguments = self._entrypoint_runtime_arguments(mlir)
        runtime_values = self._runtime_values_from_options(
            adapter_options,
            expected_count=len(runtime_arguments),
            launch_required_count=self._launch_args_required(circuit),
        )
        numeric_aliases = {
            argument.name: value
            for argument, value in zip(runtime_arguments, runtime_values, strict=True)
        }

        parser = CudaqQuakeParser(mlir, initial_numeric_aliases=numeric_aliases)
        quantum_wires, semantic_operations = parser.parse_semantic()
        classical_wires, _ = build_classical_register(
            sequential_bit_labels(parser.measurement_count)
        )

        return SemanticCircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=pack_semantic_operations(semantic_operations),
            name=getattr(circuit, "name", None),
            metadata={"framework": self.framework_name},
        )

    def _materialize_mlir(self, circuit: object) -> str:
        if hasattr(circuit, "is_compiled") and hasattr(circuit, "compile"):
            is_compiled = circuit.is_compiled()
            if isinstance(is_compiled, bool) and not is_compiled:
                circuit.compile()

        mlir = str(circuit).strip()
        if not mlir:
            raise UnsupportedOperationError("CUDA-Q kernel did not produce a Quake/MLIR string")

        return mlir

    def _entrypoint_runtime_arguments(self, mlir: str) -> tuple[_CudaqRuntimeArgument, ...]:
        entrypoint = self._find_entrypoint_signature(mlir)
        if entrypoint is None:
            return ()
        args_text = entrypoint.group("args").strip()
        if not args_text:
            return ()
        arguments: list[_CudaqRuntimeArgument] = []
        for raw_arg in args_text.split(","):
            arg_text = raw_arg.strip()
            if not arg_text:
                continue
            match = _ENTRYPOINT_ARGUMENT_RE.match(arg_text)
            if match is None:
                raise UnsupportedOperationError(
                    f"CUDA-Q adapter could not parse runtime argument signature {arg_text!r}"
                )
            arguments.append(
                _CudaqRuntimeArgument(
                    name=match.group("name"),
                    type_text=match.group("type").strip(),
                )
            )
        return tuple(arguments)

    def _runtime_values_from_options(
        self,
        options: Mapping[str, object],
        *,
        expected_count: int,
        launch_required_count: int | None,
    ) -> tuple[int | float, ...]:
        has_explicit_args = _CUDAQ_ARGS_OPTION in options
        raw_args = options.get(_CUDAQ_ARGS_OPTION, ())
        runtime_values = self._normalize_cudaq_args(raw_args) if has_explicit_args else ()
        required_count = expected_count if expected_count > 0 else launch_required_count or 0

        if required_count == 0:
            if runtime_values:
                raise UnsupportedOperationError(
                    "CUDA-Q kernel does not accept runtime arguments, but cudaq_args was provided"
                )
            return ()
        if not has_explicit_args:
            raise UnsupportedOperationError(
                "CUDA-Q kernel requires runtime arguments; pass "
                "adapter_options={'cudaq_args': (...)} in CircuitRenderOptions"
            )
        if expected_count == 0:
            raise UnsupportedOperationError(
                "CUDA-Q kernel requires runtime arguments, but the adapter could not identify "
                "their MLIR names"
            )
        if len(runtime_values) != required_count:
            plural = "" if required_count == 1 else "s"
            raise UnsupportedOperationError(
                f"CUDA-Q kernel expected {required_count} CUDA-Q runtime argument{plural}, "
                f"but received {len(runtime_values)}"
            )
        return runtime_values

    def _normalize_cudaq_args(self, raw_args: object) -> tuple[int | float, ...]:
        if not isinstance(raw_args, tuple | list):
            raise UnsupportedOperationError(
                "cudaq_args must be a tuple or list of CUDA-Q runtime argument values"
            )
        return tuple(self._normalize_runtime_value(value) for value in raw_args)

    def _normalize_runtime_value(self, value: object) -> int | float:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int | float):
            return value
        raise UnsupportedOperationError(
            "CUDA-Q adapter only supports scalar int, float, or bool runtime arguments"
        )

    def _launch_args_required(self, circuit: object) -> int | None:
        launch_args_required = getattr(circuit, "launch_args_required", None)
        if not callable(launch_args_required):
            return None
        try:
            required_args = launch_args_required()
        except (AttributeError, TypeError):
            return None
        return required_args if isinstance(required_args, int) and required_args > 0 else None

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
