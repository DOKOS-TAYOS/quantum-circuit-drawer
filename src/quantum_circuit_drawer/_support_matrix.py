"""Internal support-matrix data used to keep user docs synchronized."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputSupportRow:
    """One supported input path and its release-level contract."""

    input_path: str
    circuit_inputs: str
    result_inputs: str
    support_level: str
    platform_notes: str


@dataclass(frozen=True, slots=True)
class CapabilitySupportRow:
    """One framework capability row for the detailed support table."""

    input_path: str
    basic_gates: str
    measurements: str
    open_controls: str
    classical_control_flow: str
    composites: str
    resets_barriers: str
    terminal_outputs: str
    histograms: str


INPUT_SUPPORT_ROWS: tuple[InputSupportRow, ...] = (
    InputSupportRow(
        input_path="Internal IR",
        circuit_inputs="`CircuitIR`",
        result_inputs="Mappings for histograms",
        support_level="Strong support",
        platform_notes="Core built-in path on Windows and Linux",
    ),
    InputSupportRow(
        input_path="Qiskit",
        circuit_inputs="`QuantumCircuit`",
        result_inputs="Counts, quasi distributions, sampler containers, `BitArray`, `DataBin`",
        support_level="Strong support",
        platform_notes="Primary external backend on Windows and Linux",
    ),
    InputSupportRow(
        input_path="OpenQASM 2/3",
        circuit_inputs="Text, `.qasm`, and `.qasm3` files",
        result_inputs="Use normal histogram inputs after execution",
        support_level="Strong support through Qiskit parsers",
        platform_notes="OpenQASM 3 requires the `qasm3` extra",
    ),
    InputSupportRow(
        input_path="Cirq",
        circuit_inputs="`Circuit` and `FrozenCircuit`",
        result_inputs="`Result` / `ResultDict` measurements",
        support_level="Best-effort on native Windows",
        platform_notes="Prefer Linux or WSL for repeated demos",
    ),
    InputSupportRow(
        input_path="PennyLane",
        circuit_inputs="`QuantumTape`, `QuantumScript`, materialized tape wrappers",
        result_inputs="`counts`, `probs`, and `sample` outputs",
        support_level="Best-effort on native Windows",
        platform_notes="Prefer Linux or WSL for repeated demos",
    ),
    InputSupportRow(
        input_path="MyQLM",
        circuit_inputs="`Circuit`, `Program`, `QRoutine`",
        result_inputs="`qat.core.Result.raw_data`",
        support_level="Scoped adapter + contract support",
        platform_notes="Not a first-class multiplatform CI backend",
    ),
    InputSupportRow(
        input_path="CUDA-Q",
        circuit_inputs="Closed kernels and scalar-argument kernels with `cudaq_args`",
        result_inputs="`SampleResult`-style count containers",
        support_level="Linux/WSL2 only",
        platform_notes="Upstream CUDA-Q is not available for native Windows",
    ),
)


CAPABILITY_SUPPORT_ROWS: tuple[CapabilitySupportRow, ...] = (
    CapabilitySupportRow(
        input_path="Internal IR",
        basic_gates="Exact through public IR",
        measurements="Exact",
        open_controls="Exact when encoded",
        classical_control_flow="Classical conditions only",
        composites="Caller-defined",
        resets_barriers="Supported",
        terminal_outputs="Use explicit IR boxes",
        histograms="Mappings and framework-neutral data",
    ),
    CapabilitySupportRow(
        input_path="Qiskit",
        basic_gates="Common gates plus canonical families",
        measurements="Supported",
        open_controls="`ctrl_state` supported",
        classical_control_flow="Simple `if_test` can expand; richer flow is compact",
        composites="Compact or expanded instructions",
        resets_barriers="Supported",
        terminal_outputs="Not applicable",
        histograms="Counts, quasi, sampler, primitive, bit-array payloads",
    ),
    CapabilitySupportRow(
        input_path="OpenQASM 2/3",
        basic_gates="Whatever Qiskit parser accepts",
        measurements="Supported after parsing",
        open_controls="Through parsed Qiskit circuit",
        classical_control_flow="Through parsed Qiskit circuit",
        composites="Through parsed Qiskit circuit",
        resets_barriers="Through parsed Qiskit circuit",
        terminal_outputs="Not applicable",
        histograms="Use normal histogram inputs after execution",
    ),
    CapabilitySupportRow(
        input_path="Cirq",
        basic_gates="Common gates",
        measurements="Supported",
        open_controls="Singleton binary `control_values` supported",
        classical_control_flow="Normalized conditions or hover fallback",
        composites="`CircuitOperation` compact or expanded",
        resets_barriers="Swap and measurements supported",
        terminal_outputs="Not applicable",
        histograms="Measurement dictionaries from Cirq results",
    ),
    CapabilitySupportRow(
        input_path="PennyLane",
        basic_gates="Common operations",
        measurements="Mid-circuit `qml.measure` supported",
        open_controls="Binary `control_values` supported when exposed",
        classical_control_flow="`qml.cond` conditions when normalizable",
        composites="Decomposable operations such as `QFT` can expand",
        resets_barriers="Supported when present in tape",
        terminal_outputs="Compact output boxes for expval, var, probs, sample, counts, state",
        histograms="Direct counts, probabilities, and sample arrays",
    ),
    CapabilitySupportRow(
        input_path="MyQLM",
        basic_gates="Common gates and gate definitions",
        measurements="Supported",
        open_controls="Controlled gates from definitions",
        classical_control_flow="Drawable formulas or hover-preserved fallback",
        composites="`gateDic`, remap, and ancilla-heavy composites compactly",
        resets_barriers="Qubit resets supported; classical-only reset metadata is limited",
        terminal_outputs="Not applicable",
        histograms="`raw_data` probabilities",
    ),
    CapabilitySupportRow(
        input_path="CUDA-Q",
        basic_gates="Supported Quake/MLIR gate subset",
        measurements="Basis-preserving measurements",
        open_controls="Supported controlled operations in parser subset",
        classical_control_flow="Structured flow compact; low-level CFG outside subset",
        composites="Compact callable boxes for apply/compute/adjoint",
        resets_barriers="Reset supported",
        terminal_outputs="Not applicable",
        histograms="Sample-result count containers",
    ),
)


def render_support_tables_markdown() -> str:
    """Render the detailed support tables embedded in user documentation."""

    return "\n\n".join(
        (
            "## Detailed Support Tables\n\n"
            "These tables are generated from the package's internal support data so the "
            "documentation stays aligned with the release contract.",
            _markdown_table(
                headers=(
                    "Input path",
                    "Circuit inputs",
                    "Result inputs",
                    "Support level",
                    "Platform notes",
                ),
                rows=tuple(
                    (
                        row.input_path,
                        row.circuit_inputs,
                        row.result_inputs,
                        row.support_level,
                        row.platform_notes,
                    )
                    for row in INPUT_SUPPORT_ROWS
                ),
            ),
            _markdown_table(
                headers=(
                    "Input path",
                    "Basic gates",
                    "Measurements",
                    "Open controls",
                    "Classical/control flow",
                    "Composites",
                    "Resets/barriers",
                    "Terminal outputs",
                    "Histograms",
                ),
                rows=tuple(
                    (
                        row.input_path,
                        row.basic_gates,
                        row.measurements,
                        row.open_controls,
                        row.classical_control_flow,
                        row.composites,
                        row.resets_barriers,
                        row.terminal_outputs,
                        row.histograms,
                    )
                    for row in CAPABILITY_SUPPORT_ROWS
                ),
            ),
        )
    )


def _markdown_table(
    *,
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = tuple("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join((header_line, separator_line, *row_lines))


__all__ = [
    "CAPABILITY_SUPPORT_ROWS",
    "INPUT_SUPPORT_ROWS",
    "CapabilitySupportRow",
    "InputSupportRow",
    "render_support_tables_markdown",
]
