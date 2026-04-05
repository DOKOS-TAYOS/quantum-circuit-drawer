"""Matplotlib renderer implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path

from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure, SubFigure

from ..exceptions import RenderingError
from ..layout.scene import (
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneMeasurement,
    ScenePage,
    SceneSwap,
    SceneText,
    SceneWire,
)
from ..typing import OutputPath, RenderResult
from .base import BaseRenderer
from .matplotlib_primitives import (
    draw_barrier,
    draw_connection,
    draw_control,
    draw_gate_box,
    draw_gate_label,
    draw_measurement_box,
    draw_measurement_symbol,
    draw_swap,
    draw_text,
    draw_wire,
    finalize_axes,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ProjectedPage:
    wires: tuple[SceneWire, ...]
    barriers: tuple[SceneBarrier, ...]
    connections: tuple[SceneConnection, ...]
    gates: tuple[SceneGate, ...]
    measurements: tuple[SceneMeasurement, ...]
    controls: tuple[SceneControl, ...]
    swaps: tuple[SceneSwap, ...]
    texts: tuple[SceneText, ...]


class MatplotlibRenderer(BaseRenderer):
    """Render a neutral layout scene using Matplotlib."""

    backend_name = "matplotlib"

    def render(
        self,
        scene: LayoutScene,
        *,
        ax: Axes | None = None,
        output: OutputPath | None = None,
    ) -> RenderResult:
        axes = ax
        managed_figure: Figure | None = None
        if axes is None:
            figsize = (max(4.0, scene.width * 1.1), max(2.4, scene.height * 0.9))
            managed_figure = Figure(figsize=figsize)
            FigureCanvasAgg(managed_figure)
            axes = managed_figure.add_subplot(111)
            logger.debug("Rendering scene on renderer-managed Agg figure")
        else:
            logger.debug("Rendering scene on caller-managed axes")

        figure: Figure | SubFigure = axes.figure
        figure.patch.set_facecolor(scene.style.theme.figure_facecolor)

        for page in scene.pages:
            self._draw_page(axes, scene, page)

        finalize_axes(axes, scene)
        self._save_output(figure, output)

        if ax is None:
            assert managed_figure is not None
            return managed_figure, axes
        return axes

    def _draw_page(self, axes: Axes, scene: LayoutScene, page: ScenePage) -> None:
        projected_page = self._project_page(scene, page)

        for wire in projected_page.wires:
            draw_wire(axes, wire, scene)
        for barrier in projected_page.barriers:
            draw_barrier(axes, barrier, scene)
        for connection in projected_page.connections:
            draw_connection(axes, connection, scene)
        for gate in projected_page.gates:
            draw_gate_box(axes, gate, scene)
        for measurement in projected_page.measurements:
            draw_measurement_box(axes, measurement, scene)
        for gate in projected_page.gates:
            draw_gate_label(axes, gate, scene)
        for control in projected_page.controls:
            draw_control(axes, control, scene)
        for swap in projected_page.swaps:
            draw_swap(axes, swap, scene)
        for measurement in projected_page.measurements:
            draw_measurement_symbol(axes, measurement, scene)
        for text in projected_page.texts:
            draw_text(axes, text, scene)

    def _project_page(self, scene: LayoutScene, page: ScenePage) -> _ProjectedPage:
        return _ProjectedPage(
            wires=tuple(self._wire_for_page(wire, page, scene) for wire in scene.wires),
            barriers=tuple(
                self._barrier_for_page(barrier, page, scene)
                for barrier in scene.barriers
                if self._is_in_page(barrier.column, page)
            ),
            connections=tuple(
                self._connection_for_page(connection, page, scene)
                for connection in scene.connections
                if self._is_in_page(connection.column, page)
            ),
            gates=tuple(
                self._gate_for_page(gate, page, scene)
                for gate in scene.gates
                if self._is_in_page(gate.column, page)
            ),
            measurements=tuple(
                self._measurement_for_page(measurement, page, scene)
                for measurement in scene.measurements
                if self._is_in_page(measurement.column, page)
            ),
            controls=tuple(
                self._control_for_page(control, page, scene)
                for control in scene.controls
                if self._is_in_page(control.column, page)
            ),
            swaps=tuple(
                self._swap_for_page(swap, page, scene)
                for swap in scene.swaps
                if self._is_in_page(swap.column, page)
            ),
            texts=tuple(self._text_for_page(text, page) for text in scene.texts),
        )

    def _save_output(self, figure: Figure | SubFigure, output: OutputPath | None) -> None:
        if output is None:
            return

        try:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            save_figure: Figure
            if isinstance(figure, SubFigure):
                save_figure = figure.figure
            else:
                save_figure = figure
            save_figure.savefig(output_path, bbox_inches="tight")
        except (OSError, TypeError, ValueError) as exc:
            logger.debug("Failed to save rendered circuit to %r: %s", output, exc)
            raise RenderingError(f"failed to save rendered circuit to {output!r}: {exc}") from exc
        logger.debug("Saved rendered circuit to %s", output_path)

    def _is_in_page(self, column: int, page: ScenePage) -> bool:
        return page.start_column <= column <= page.end_column

    def _page_x_offset(self, page: ScenePage, scene: LayoutScene) -> float:
        return scene.style.margin_left - page.content_x_start

    def _page_y_offset(self, page: ScenePage) -> float:
        return page.y_offset

    def _wire_for_page(self, wire: SceneWire, page: ScenePage, scene: LayoutScene) -> SceneWire:
        return replace(
            wire,
            y=wire.y + self._page_y_offset(page),
            x_start=scene.style.margin_left,
            x_end=scene.style.margin_left + page.content_width,
        )

    def _gate_for_page(self, gate: SceneGate, page: ScenePage, scene: LayoutScene) -> SceneGate:
        return replace(
            gate,
            x=gate.x + self._page_x_offset(page, scene),
            y=gate.y + self._page_y_offset(page),
        )

    def _control_for_page(
        self, control: SceneControl, page: ScenePage, scene: LayoutScene
    ) -> SceneControl:
        return replace(
            control,
            x=control.x + self._page_x_offset(page, scene),
            y=control.y + self._page_y_offset(page),
        )

    def _connection_for_page(
        self, connection: SceneConnection, page: ScenePage, scene: LayoutScene
    ) -> SceneConnection:
        return replace(
            connection,
            x=connection.x + self._page_x_offset(page, scene),
            y_start=connection.y_start + self._page_y_offset(page),
            y_end=connection.y_end + self._page_y_offset(page),
        )

    def _swap_for_page(self, swap: SceneSwap, page: ScenePage, scene: LayoutScene) -> SceneSwap:
        return replace(
            swap,
            x=swap.x + self._page_x_offset(page, scene),
            y_top=swap.y_top + self._page_y_offset(page),
            y_bottom=swap.y_bottom + self._page_y_offset(page),
        )

    def _barrier_for_page(
        self, barrier: SceneBarrier, page: ScenePage, scene: LayoutScene
    ) -> SceneBarrier:
        return replace(
            barrier,
            x=barrier.x + self._page_x_offset(page, scene),
            y_top=barrier.y_top + self._page_y_offset(page),
            y_bottom=barrier.y_bottom + self._page_y_offset(page),
        )

    def _measurement_for_page(
        self, measurement: SceneMeasurement, page: ScenePage, scene: LayoutScene
    ) -> SceneMeasurement:
        y_offset = self._page_y_offset(page)
        return replace(
            measurement,
            x=measurement.x + self._page_x_offset(page, scene),
            quantum_y=measurement.quantum_y + y_offset,
            classical_y=measurement.classical_y + y_offset
            if measurement.classical_y is not None
            else None,
            connector_x=measurement.connector_x + self._page_x_offset(page, scene),
            connector_y=measurement.connector_y + y_offset,
        )

    def _text_for_page(self, text: SceneText, page: ScenePage) -> SceneText:
        return replace(text, y=text.y + self._page_y_offset(page))
