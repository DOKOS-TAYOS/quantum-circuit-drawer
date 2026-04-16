"""Matplotlib renderer implementation."""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from matplotlib.artist import Artist
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
from ._matplotlib_figure import clear_hover_state, create_managed_figure
from ._matplotlib_hover import _HoverTarget2D, add_hover_target, attach_hover
from ._matplotlib_page_projection import (
    _ProjectedPage,
    bucket_by_page,
    is_in_page,
    page_index_by_column,
    page_x_offset,
    page_y_offset,
    project_pages,
)
from ._render_support import save_rendered_figure
from .base import BaseRenderer
from .matplotlib_primitives import (
    _build_gate_text_fitting_context,
    _fit_gate_text_font_size_with_context,
    _gate_text_layout,
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
        hover_targets: list[_HoverTarget2D] = []
        clear_hover_state(axes)

        for page, projected_page in zip(scene.pages, projected_pages, strict=True):
            self._draw_page(
                axes,
                scene,
                page,
                projected_page,
                gate_text_context=gate_text_context,
                gate_text_cache=gate_text_cache,
                hover_targets=hover_targets,
            )

        if scene.hover.enabled and hover_targets:
            attach_hover(axes, scene.hover, hover_targets)

        finalize_axes(axes, scene)
        from .._draw_managed import configure_zoom_text_scaling

        configure_zoom_text_scaling(axes, scene=scene)
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
        hover_targets: list[_HoverTarget2D],
    ) -> None:
        x_offset = self._page_x_offset(page, scene)
        y_offset = self._page_y_offset(page)
        hover_enabled = scene.hover.enabled

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
            tuple(
                connection
                for connection in projected_page.connections
                if not hover_enabled or connection.hover_data is None
            ),
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )

        for gate in projected_page.gates:
            gate_patch = draw_gate_box(axes, gate, scene, x_offset=x_offset, y_offset=y_offset)
            if gate_patch is not None and hover_enabled and gate.hover_data is not None:
                add_hover_target(axes, hover_targets, gate_patch, gate.hover_data)

        draw_x_target_circles(
            axes,
            tuple(
                gate
                for gate in projected_page.gates
                if not hover_enabled or gate.hover_data is None
            ),
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        draw_x_target_segments(
            axes,
            tuple(
                gate
                for gate in projected_page.gates
                if not hover_enabled or gate.hover_data is None
            ),
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        for gate in projected_page.gates:
            if (
                not hover_enabled
                or gate.hover_data is None
                or gate.render_style.value != "x_target"
            ):
                continue
            x_target_circle = draw_x_target_circles(
                axes,
                (gate,),
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            if x_target_circle is not None:
                add_hover_target(axes, hover_targets, x_target_circle, gate.hover_data)
            x_target_segments = draw_x_target_segments(
                axes,
                (gate,),
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            if x_target_segments is not None:
                add_hover_target(axes, hover_targets, x_target_segments, gate.hover_data)

        for measurement in projected_page.measurements:
            measurement_patch = draw_measurement_box(
                axes,
                measurement,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            if measurement.hover_data is not None:
                add_hover_target(axes, hover_targets, measurement_patch, measurement.hover_data)

        for gate in projected_page.gates:
            if gate.render_style.value != "x_target":
                label_y, subtitle_y, label_height_fraction, subtitle_height_fraction = (
                    _gate_text_layout(gate)
                )
                label_font_size = _fit_gate_text_font_size_with_context(
                    context=gate_text_context,
                    width=gate.width,
                    height=gate.height,
                    text=gate.label,
                    default_font_size=scene.style.font_size,
                    height_fraction=label_height_fraction,
                    cache=gate_text_cache,
                )
                subtitle_font_size = (
                    _fit_gate_text_font_size_with_context(
                        context=gate_text_context,
                        width=gate.width,
                        height=gate.height,
                        text=gate.subtitle,
                        default_font_size=scene.style.font_size * 0.78,
                        height_fraction=subtitle_height_fraction,
                        cache=gate_text_cache,
                    )
                    if gate.subtitle and subtitle_y is not None
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
            tuple(
                control
                for control in projected_page.controls
                if not hover_enabled or control.hover_data is None
            ),
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        for control in projected_page.controls:
            if not hover_enabled or control.hover_data is None:
                continue
            control_artist = draw_controls(
                axes,
                (control,),
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            if control_artist is not None:
                add_hover_target(axes, hover_targets, control_artist, control.hover_data)

        draw_swaps(
            axes,
            tuple(
                swap
                for swap in projected_page.swaps
                if not hover_enabled or swap.hover_data is None
            ),
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        for swap in projected_page.swaps:
            if not hover_enabled or swap.hover_data is None:
                continue
            swap_artist = draw_swaps(
                axes,
                (swap,),
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            if swap_artist is not None:
                add_hover_target(axes, hover_targets, swap_artist, swap.hover_data)

        for connection in projected_page.connections:
            if not hover_enabled or connection.hover_data is None:
                continue
            for artist in draw_connections(
                axes,
                (connection,),
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            ):
                if isinstance(artist, Artist):
                    add_hover_target(axes, hover_targets, artist, connection.hover_data)

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
        return project_pages(scene)

    def _save_output(self, figure: Figure | SubFigure, output: OutputPath | None) -> None:
        try:
            save_rendered_figure(figure, output)
        except RenderingError as exc:
            logger.debug("Failed to save rendered circuit to %r: %s", output, exc)
            raise

    def _is_in_page(self, column: int, page: ScenePage) -> bool:
        return is_in_page(column, page)

    def _page_index_by_column(self, pages: tuple[ScenePage, ...]) -> tuple[int, ...]:
        return page_index_by_column(pages)

    def _bucket_by_page(
        self,
        items: tuple[_SceneColumnItem, ...],
        page_index_lookup: tuple[int, ...],
        page_count: int,
    ) -> tuple[tuple[_SceneColumnItem, ...], ...]:
        return bucket_by_page(items, page_index_lookup, page_count)

    def _page_x_offset(self, page: ScenePage, scene: LayoutScene) -> float:
        return page_x_offset(page, scene)

    def _page_y_offset(self, page: ScenePage) -> float:
        return page_y_offset(page)
