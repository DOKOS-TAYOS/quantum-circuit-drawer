"""Matplotlib renderer implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, TypeVar

from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure

from ..exceptions import RenderingError
from ..layout.scene import (
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneMeasurement,
    ScenePage,
    SceneSwap,
)
from ..layout.scene_3d import LayoutScene3D
from ..typing import OutputPath, RenderResult
from ._matplotlib_figure import create_managed_figure
from ._render_support import save_rendered_figure
from .base import BaseRenderer
from .matplotlib_primitives import (
    _build_gate_text_fitting_context,
    _fit_gate_text_font_size_with_context,
    draw_barriers,
    draw_connections,
    draw_controls,
    draw_gate_annotation,
    draw_gate_box,
    draw_gate_label,
    draw_measurement_box,
    draw_measurement_symbol,
    draw_swaps,
    draw_text,
    draw_wires,
    draw_x_target_circles,
    draw_x_target_segments,
    finalize_axes,
    prepare_axes,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ProjectedPage:
    barriers: tuple[SceneBarrier, ...]
    connections: tuple[SceneConnection, ...]
    gates: tuple[SceneGate, ...]
    gate_annotations: tuple[SceneGateAnnotation, ...]
    measurements: tuple[SceneMeasurement, ...]
    controls: tuple[SceneControl, ...]
    swaps: tuple[SceneSwap, ...]


_SceneColumnItem = TypeVar(
    "_SceneColumnItem",
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneMeasurement,
    SceneSwap,
)


class MatplotlibRenderer(BaseRenderer):
    """Render a neutral layout scene using Matplotlib."""

    backend_name = "matplotlib"

    def render(
        self,
        scene: LayoutScene | LayoutScene3D,
        *,
        ax: Axes | None = None,
        output: OutputPath | None = None,
    ) -> RenderResult:
        if not isinstance(scene, LayoutScene):
            raise TypeError("MatplotlibRenderer only supports 2D layout scenes")
        axes = ax
        managed_figure: Figure | None = None
        if axes is None:
            managed_figure, axes = create_managed_figure(scene, use_agg=True)
            logger.debug("Rendering scene on renderer-managed Agg figure")
        else:
            logger.debug("Rendering scene on caller-managed axes")

        figure: Figure | SubFigure = axes.figure
        figure.patch.set_facecolor(scene.style.theme.figure_facecolor)
        prepare_axes(axes, scene)
        projected_pages = self._project_pages(scene)
        gate_text_context = _build_gate_text_fitting_context(axes, scene)
        gate_text_cache: dict[tuple[str, float, float], float] = {}

        for page, projected_page in zip(scene.pages, projected_pages, strict=True):
            self._draw_page(
                axes,
                scene,
                page,
                projected_page,
                gate_text_context=gate_text_context,
                gate_text_cache=gate_text_cache,
            )

        finalize_axes(axes, scene)
        self._save_output(figure, output)

        if ax is None:
            assert managed_figure is not None
            return managed_figure, axes
        return axes

    def _draw_page(
        self,
        axes: Axes,
        scene: LayoutScene,
        page: ScenePage,
        projected_page: _ProjectedPage,
        *,
        gate_text_context: Any,
        gate_text_cache: dict[tuple[str, float, float], float],
    ) -> None:
        x_offset = self._page_x_offset(page, scene)
        y_offset = self._page_y_offset(page)

        draw_wires(
            axes,
            scene.wires,
            scene,
            y_offset=y_offset,
            x_start=scene.style.margin_left,
            x_end=scene.style.margin_left + page.content_width,
        )
        draw_barriers(axes, projected_page.barriers, scene, x_offset=x_offset, y_offset=y_offset)
        draw_connections(
            axes,
            projected_page.connections,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        for gate in projected_page.gates:
            draw_gate_box(axes, gate, scene, x_offset=x_offset, y_offset=y_offset)
        draw_x_target_circles(
            axes,
            projected_page.gates,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        draw_x_target_segments(
            axes,
            projected_page.gates,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        for measurement in projected_page.measurements:
            draw_measurement_box(axes, measurement, scene, x_offset=x_offset, y_offset=y_offset)
        for gate in projected_page.gates:
            if gate.render_style.value != "x_target":
                label_font_size = _fit_gate_text_font_size_with_context(
                    context=gate_text_context,
                    width=gate.width,
                    text=gate.label,
                    default_font_size=scene.style.font_size,
                    cache=gate_text_cache,
                )
                subtitle_font_size = (
                    _fit_gate_text_font_size_with_context(
                        context=gate_text_context,
                        width=gate.width,
                        text=gate.subtitle,
                        default_font_size=scene.style.font_size * 0.78,
                        cache=gate_text_cache,
                    )
                    if gate.subtitle
                    else None
                )
                draw_gate_label(
                    axes,
                    gate,
                    scene,
                    label_font_size=label_font_size,
                    subtitle_font_size=subtitle_font_size,
                    x_offset=x_offset,
                    y_offset=y_offset,
                )
                continue
            draw_gate_label(axes, gate, scene, x_offset=x_offset, y_offset=y_offset)
        for annotation in projected_page.gate_annotations:
            draw_gate_annotation(
                axes,
                annotation,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
        draw_controls(
            axes,
            projected_page.controls,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        draw_swaps(axes, projected_page.swaps, scene, x_offset=x_offset, y_offset=y_offset)
        for measurement in projected_page.measurements:
            draw_measurement_symbol(
                axes,
                measurement,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
        for text in scene.texts:
            draw_text(axes, text, scene, y_offset=y_offset)

    def _project_pages(self, scene: LayoutScene) -> tuple[_ProjectedPage, ...]:
        page_index_by_column = self._page_index_by_column(scene.pages)
        page_count = len(scene.pages)
        barriers = self._bucket_by_page(scene.barriers, page_index_by_column, page_count)
        connections = self._bucket_by_page(scene.connections, page_index_by_column, page_count)
        gates = self._bucket_by_page(scene.gates, page_index_by_column, page_count)
        gate_annotations = self._bucket_by_page(
            scene.gate_annotations,
            page_index_by_column,
            page_count,
        )
        measurements = self._bucket_by_page(scene.measurements, page_index_by_column, page_count)
        controls = self._bucket_by_page(scene.controls, page_index_by_column, page_count)
        swaps = self._bucket_by_page(scene.swaps, page_index_by_column, page_count)
        return tuple(
            _ProjectedPage(
                barriers=barriers[page_index],
                connections=connections[page_index],
                gates=gates[page_index],
                gate_annotations=gate_annotations[page_index],
                measurements=measurements[page_index],
                controls=controls[page_index],
                swaps=swaps[page_index],
            )
            for page_index in range(page_count)
        )

    def _save_output(self, figure: Figure | SubFigure, output: OutputPath | None) -> None:
        try:
            save_rendered_figure(figure, output)
        except RenderingError as exc:
            logger.debug("Failed to save rendered circuit to %r: %s", output, exc)
            raise

    def _is_in_page(self, column: int, page: ScenePage) -> bool:
        return page.start_column <= column <= page.end_column

    def _page_index_by_column(self, pages: tuple[ScenePage, ...]) -> tuple[int, ...]:
        if not pages:
            return (0,)
        max_column = max(page.end_column for page in pages)
        page_indexes = [0] * (max_column + 1)
        for page in pages:
            for column in range(page.start_column, page.end_column + 1):
                page_indexes[column] = page.index
        return tuple(page_indexes)

    def _bucket_by_page(
        self,
        items: tuple[_SceneColumnItem, ...],
        page_index_by_column: tuple[int, ...],
        page_count: int,
    ) -> tuple[tuple[_SceneColumnItem, ...], ...]:
        buckets: list[list[_SceneColumnItem]] = [[] for _ in range(page_count)]
        for item in items:
            buckets[page_index_by_column[item.column]].append(item)
        return tuple(tuple(bucket) for bucket in buckets)

    def _page_x_offset(self, page: ScenePage, scene: LayoutScene) -> float:
        return scene.style.margin_left - page.content_x_start

    def _page_y_offset(self, page: ScenePage) -> float:
        return page.y_offset
