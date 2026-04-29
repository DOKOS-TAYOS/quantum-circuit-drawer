"""LaTeX export helpers for normalized 2D circuit figures."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from ._compat import StrEnum
from ._logging import (
    duration_ms,
    emit_render_diagnostics,
    log_event,
    logged_api_call,
    push_log_context,
)
from .config import DrawConfig, DrawMode, DrawSideConfig, OutputOptions
from .diagnostics import RenderDiagnostic
from .ir.circuit import CircuitIR, LayerIR
from .ir.measurements import MeasurementIR
from .ir.operations import CanonicalGateFamily, OperationIR, OperationKind, binary_control_states
from .ir.wires import WireKind
from .layout._layering import normalize_draw_layers
from .layout.scene import LayoutScene
from .layout.spacing import operation_label_parts
from .result import diagnostics_to_dicts
from .style import DrawStyle

if TYPE_CHECKING:
    from .drawing.pipeline import PreparedDrawPipeline

logger = logging.getLogger(__name__)


class LatexBackend(StrEnum):
    """Supported LaTeX circuit backends."""

    QUANTIKZ = "quantikz"
    TIKZ = "tikz"


class LatexMode(StrEnum):
    """Supported LaTeX export modes."""

    FULL = "full"
    PAGES = "pages"


@dataclass(frozen=True, slots=True)
class LatexResult:
    """LaTeX source and metadata returned by ``circuit_to_latex``."""

    source: str
    pages: tuple[str, ...]
    backend: LatexBackend
    mode: LatexMode
    page_count: int
    detected_framework: str | None = None
    diagnostics: tuple[RenderDiagnostic, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return result metadata without duplicating the LaTeX source."""

        return {
            "backend": self.backend.value,
            "mode": self.mode.value,
            "page_count": self.page_count,
            "detected_framework": self.detected_framework,
            "diagnostics": diagnostics_to_dicts(self.diagnostics),
        }


def circuit_to_latex(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    backend: LatexBackend | str = LatexBackend.QUANTIKZ,
    mode: LatexMode | DrawMode | str | None = None,
) -> LatexResult:
    """Return LaTeX source for a supported 2D circuit input."""

    from .drawing.preparation import prepare_draw_call

    with logged_api_call(logger, api="circuit_to_latex") as started_at:
        normalized_backend = normalize_latex_backend(backend)
        latex_mode = resolve_latex_mode(mode, config=config)
        prepared_config = _latex_draw_config(config, mode=latex_mode)
        prepared = prepare_draw_call(circuit, config=prepared_config, ax=None)
        pipeline = prepared.pipeline
        if normalized_backend is LatexBackend.QUANTIKZ:
            pages = _quantikz_pages(pipeline, mode=latex_mode)
        else:
            pages = _tikz_pages(pipeline, mode=latex_mode)
        source = _joined_pages(pages, mode=latex_mode)
        with push_log_context(
            view=prepared.resolved_config.config.view,
            mode=latex_mode.value,
            framework=pipeline.detected_framework,
            backend=normalized_backend.value,
        ):
            result = LatexResult(
                source=source,
                pages=pages,
                backend=normalized_backend,
                mode=latex_mode,
                page_count=len(pages),
                detected_framework=pipeline.detected_framework,
                diagnostics=prepared.diagnostics,
            )
            emit_render_diagnostics(logger, result.diagnostics)
            log_event(
                logger,
                logging.INFO,
                "api.completed",
                "Completed circuit_to_latex.",
                duration_ms=duration_ms(started_at),
                page_count=result.page_count,
                detected_framework=result.detected_framework,
                diagnostic_count=len(result.diagnostics),
            )
            return result


def normalize_latex_backend(value: LatexBackend | str) -> LatexBackend:
    """Return a normalized LaTeX backend enum value."""

    try:
        return value if isinstance(value, LatexBackend) else LatexBackend(str(value))
    except ValueError as exc:
        choices = ", ".join(backend.value for backend in LatexBackend)
        raise ValueError(f"backend must be one of: {choices}") from exc


def resolve_latex_mode(
    value: LatexMode | DrawMode | str | None,
    *,
    config: DrawConfig | None,
) -> LatexMode:
    """Resolve the effective LaTeX export mode."""

    if value is None:
        config_mode = DrawMode.AUTO if config is None else config.mode
        if config_mode is DrawMode.FULL:
            return LatexMode.FULL
        if config_mode is DrawMode.PAGES:
            return LatexMode.PAGES
        return LatexMode.PAGES
    if isinstance(value, LatexMode):
        return value
    if isinstance(value, DrawMode):
        if value is DrawMode.FULL:
            return LatexMode.FULL
        if value is DrawMode.PAGES:
            return LatexMode.PAGES
        choices = ", ".join(mode.value for mode in LatexMode)
        raise ValueError(f"mode must be one of: {choices}")
    try:
        return LatexMode(str(value))
    except ValueError as exc:
        choices = ", ".join(mode.value for mode in LatexMode)
        raise ValueError(f"mode must be one of: {choices}") from exc


def _latex_draw_config(config: DrawConfig | None, *, mode: LatexMode) -> DrawConfig:
    resolved_config = DrawConfig() if config is None else config
    if resolved_config.view == "3d":
        raise ValueError("LaTeX export only supports 2D circuits; set view='2d' before exporting")
    draw_mode = DrawMode.FULL if mode is LatexMode.FULL else DrawMode.PAGES
    render = replace(resolved_config.side.render, view="2d", mode=draw_mode)
    side = DrawSideConfig(render=render, appearance=resolved_config.side.appearance)
    output = OutputOptions(show=False, output_path=None, figsize=resolved_config.figsize)
    return DrawConfig(side=side, output=output)


def _quantikz_pages(pipeline: PreparedDrawPipeline, *, mode: LatexMode) -> tuple[str, ...]:
    layers = normalize_draw_layers(pipeline.ir)
    page_ranges: tuple[tuple[int, int], ...]
    if mode is LatexMode.FULL:
        page_ranges = ((0, max(0, len(layers) - 1)),)
    else:
        scene = _require_2d_scene(pipeline)
        page_ranges = tuple((page.start_column, page.end_column) for page in scene.pages)
    return tuple(
        _render_quantikz_page(
            pipeline.ir,
            layers,
            start_column=start_column,
            end_column=end_column,
            style=pipeline.normalized_style,
        )
        for start_column, end_column in page_ranges
    )


def _render_quantikz_page(
    circuit: CircuitIR,
    layers: tuple[LayerIR, ...],
    *,
    start_column: int,
    end_column: int,
    style: DrawStyle,
) -> str:
    wires = circuit.all_wires
    wire_indices = {wire.id: index for index, wire in enumerate(wires)}
    column_count = max(0, end_column - start_column + 1)
    cells = [[_empty_wire_command(wire.kind) for _ in range(column_count)] for wire in wires]

    for source_column in range(start_column, end_column + 1):
        if source_column >= len(layers):
            continue
        column = source_column - start_column
        for operation in layers[source_column].operations:
            _place_quantikz_operation(
                cells,
                operation,
                column=column,
                wire_indices=wire_indices,
                style=style,
            )

    rows = []
    for row_index, wire in enumerate(wires):
        prefix = (
            rf"\lstick{{{_latex_text(wire.label or wire.id)}}}"
            if style.show_wire_labels
            else _empty_wire_command(wire.kind)
        )
        rows.append(" & ".join((prefix, *cells[row_index])) + r" \\")

    body = "\n".join(rows)
    return "\n".join(
        (
            r"\begin{figure}[htbp]",
            r"\centering",
            r"\begin{quantikz}",
            body,
            r"\end{quantikz}",
            r"\end{figure}",
        )
    )


def _place_quantikz_operation(
    cells: list[list[str]],
    operation: OperationIR,
    *,
    column: int,
    wire_indices: dict[str, int],
    style: DrawStyle,
) -> None:
    if isinstance(operation, MeasurementIR) or operation.kind is OperationKind.MEASUREMENT:
        _place_measurement(cells, operation, column=column, wire_indices=wire_indices)
        return
    if operation.kind is OperationKind.BARRIER:
        _place_barrier(cells, operation, column=column, wire_indices=wire_indices)
        return
    if operation.kind is OperationKind.SWAP:
        _place_swap(cells, operation, column=column, wire_indices=wire_indices)
        return
    if operation.kind is OperationKind.CONTROLLED_GATE:
        _place_controlled_gate(
            cells, operation, column=column, wire_indices=wire_indices, style=style
        )
        return
    _place_gate(cells, operation, column=column, wire_indices=wire_indices, style=style)


def _place_gate(
    cells: list[list[str]],
    operation: OperationIR,
    *,
    column: int,
    wire_indices: dict[str, int],
    style: DrawStyle,
) -> None:
    target_rows = _operation_rows(operation.target_wires, wire_indices)
    if not target_rows:
        return
    label = _operation_label(operation, style)
    top_row = min(target_rows)
    if len(target_rows) == 1:
        cells[top_row][column] = rf"\gate{{{label}}}"
        return
    cells[top_row][column] = rf"\gate[{len(target_rows)}]{{{label}}}"
    for row in target_rows:
        if row != top_row:
            cells[row][column] = rf"\ghost{{{label}}}"


def _place_controlled_gate(
    cells: list[list[str]],
    operation: OperationIR,
    *,
    column: int,
    wire_indices: dict[str, int],
    style: DrawStyle,
) -> None:
    target_rows = _operation_rows(operation.target_wires, wire_indices)
    control_rows = _operation_rows(operation.control_wires, wire_indices)
    if not target_rows:
        return

    simple_states = binary_control_states(operation)
    anchor_row = target_rows[0]
    for control_index, control_row in enumerate(control_rows):
        state = simple_states[control_index] if simple_states is not None else 1
        command = "ctrl" if state == 1 else "octrl"
        cells[control_row][column] = rf"\{command}{{{anchor_row - control_row}}}"

    if (
        operation.canonical_family is CanonicalGateFamily.X
        and len(target_rows) == 1
        and simple_states is not None
    ):
        cells[target_rows[0]][column] = r"\targ{}"
        return
    _place_gate(cells, operation, column=column, wire_indices=wire_indices, style=style)


def _place_measurement(
    cells: list[list[str]],
    operation: OperationIR,
    *,
    column: int,
    wire_indices: dict[str, int],
) -> None:
    target_rows = _operation_rows(operation.target_wires[:1], wire_indices)
    if target_rows:
        cells[target_rows[0]][column] = r"\meter{}"
    if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
        classical_row = wire_indices.get(operation.classical_target)
        if classical_row is not None:
            cells[classical_row][column] = r"\cw"


def _place_swap(
    cells: list[list[str]],
    operation: OperationIR,
    *,
    column: int,
    wire_indices: dict[str, int],
) -> None:
    target_rows = _operation_rows(operation.target_wires, wire_indices)
    if len(target_rows) < 2:
        return
    top_row, bottom_row = min(target_rows), max(target_rows)
    cells[top_row][column] = rf"\swap{{{bottom_row - top_row}}}"
    cells[bottom_row][column] = r"\targX{}"


def _place_barrier(
    cells: list[list[str]],
    operation: OperationIR,
    *,
    column: int,
    wire_indices: dict[str, int],
) -> None:
    target_rows = _operation_rows(operation.target_wires, wire_indices)
    if not target_rows:
        return
    top_row = min(target_rows)
    cells[top_row][column] = rf"\barrier[{len(target_rows)}]{{}}"


def _operation_rows(wire_ids: Iterable[str], wire_indices: dict[str, int]) -> list[int]:
    return [wire_indices[wire_id] for wire_id in wire_ids if wire_id in wire_indices]


def _operation_label(operation: OperationIR, style: DrawStyle) -> str:
    label, subtitle = operation_label_parts(operation, style)
    if subtitle:
        return rf"{_latex_text(label)}\\{_latex_text(subtitle)}"
    return _latex_text(label)


def _empty_wire_command(kind: WireKind) -> str:
    return r"\cw" if kind is WireKind.CLASSICAL else r"\qw"


def _tikz_pages(pipeline: PreparedDrawPipeline, *, mode: LatexMode) -> tuple[str, ...]:
    from .drawing.pages import single_page_scenes

    scene = _require_2d_scene(pipeline)
    scenes = (scene,) if mode is LatexMode.FULL else single_page_scenes(scene)
    return tuple(_render_tikz_scene(page_scene) for page_scene in scenes)


def _render_tikz_scene(scene: LayoutScene) -> str:
    lines = [r"\begin{tikzpicture}[x=1cm,y=1cm]"]
    for wire in scene.wires:
        y = -wire.y
        lines.append(rf"\draw ({wire.x_start:.3f},{y:.3f}) -- ({wire.x_end:.3f},{y:.3f});")
    for text in scene.texts:
        lines.append(
            rf"\node[anchor=east] at ({text.x:.3f},{-text.y:.3f}) {{{_latex_text(text.text)}}};"
        )
    for connection in scene.connections:
        style = "dashed" if connection.linestyle == "dashed" else "solid"
        arrow = "->" if connection.arrow_at_end else "-"
        lines.append(
            rf"\draw[{style},{arrow}] ({connection.x:.3f},{-connection.y_start:.3f}) -- "
            rf"({connection.x:.3f},{-connection.y_end:.3f});"
        )
    for gate in scene.gates:
        x0 = gate.x - (gate.width / 2.0)
        y0 = -(gate.y + (gate.height / 2.0))
        lines.append(
            rf"\draw ({x0:.3f},{y0:.3f}) rectangle ++({gate.width:.3f},{gate.height:.3f}) "
            rf"node[midway] {{{_latex_text(_tikz_gate_label(gate.label, gate.subtitle))}}};"
        )
    for control in scene.controls:
        command = r"\fill" if control.state == 1 else r"\draw"
        lines.append(rf"{command} ({control.x:.3f},{-control.y:.3f}) circle (0.060);")
    for swap in scene.swaps:
        lines.append(rf"\node at ({swap.x:.3f},{-swap.y_top:.3f}) {{$\times$}};")
        lines.append(rf"\node at ({swap.x:.3f},{-swap.y_bottom:.3f}) {{$\times$}};")
    for barrier in scene.barriers:
        lines.append(
            rf"\draw[densely dashed] ({barrier.x:.3f},{-barrier.y_top:.3f}) -- "
            rf"({barrier.x:.3f},{-barrier.y_bottom:.3f});"
        )
    for measurement in scene.measurements:
        x0 = measurement.x - (measurement.width / 2.0)
        y0 = -(measurement.quantum_y + (measurement.height / 2.0))
        lines.append(
            rf"\draw ({x0:.3f},{y0:.3f}) rectangle ++"
            rf"({measurement.width:.3f},{measurement.height:.3f}) node[midway] {{$M$}};"
        )
    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)


def _tikz_gate_label(label: str, subtitle: str | None) -> str:
    if subtitle:
        return f"{label}\\\\{subtitle}"
    return label


def _require_2d_scene(pipeline: PreparedDrawPipeline) -> LayoutScene:
    scene = pipeline.paged_scene
    if not isinstance(scene, LayoutScene):
        raise ValueError("LaTeX export only supports 2D circuits; set view='2d' before exporting")
    return scene


def _joined_pages(pages: tuple[str, ...], *, mode: LatexMode) -> str:
    if mode is LatexMode.FULL:
        return pages[0]
    return "\n\n".join(f"% Page {index}\n{page}" for index, page in enumerate(pages, start=1))


def _latex_text(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
        "_": r"\_",
        "^": r"\^{}",
        "~": r"\~{}",
    }
    return "".join(replacements.get(character, character) for character in text)


__all__ = [
    "LatexBackend",
    "LatexMode",
    "LatexResult",
    "circuit_to_latex",
    "normalize_latex_backend",
    "resolve_latex_mode",
]
