"""Matplotlib renderer implementation."""

from __future__ import annotations

import logging
from math import fabs
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
from ..utils.formatting import format_parameter_text, format_visible_label
from ._matplotlib_figure import clear_hover_state, create_managed_figure
from ._matplotlib_hover import _HoverTarget2D, add_hover_target, attach_hover
from ._matplotlib_page_projection import (
    _ProjectedPage,
    is_in_page,
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
        gate_text_cache: dict[tuple[object, float, float], float] = {}
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
        gate_text_cache: dict[tuple[object, float, float], float],
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
            text_fit_context=gate_text_context,
            text_fit_cache=gate_text_cache,
        )
        draw_barriers(axes, projected_page.barriers, scene, x_offset=x_offset, y_offset=y_offset)
        draw_connections(
            axes,
            projected_page.connections,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
            text_fit_context=gate_text_context,
            text_fit_cache=gate_text_cache,
        )

        for gate in projected_page.gates:
            gate_patch = draw_gate_box(axes, gate, scene, x_offset=x_offset, y_offset=y_offset)
            if gate_patch is not None and hover_enabled and gate.hover_data is not None:
                self._add_gate_hover_target(
                    hover_targets,
                    gate,
                    x_offset=x_offset,
                    y_offset=y_offset,
                )

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
            measurement_patch = draw_measurement_box(
                axes,
                measurement,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            if (
                measurement_patch is not None
                and hover_enabled
                and measurement.hover_data is not None
            ):
                self._add_measurement_hover_target(
                    hover_targets,
                    measurement,
                    x_offset=x_offset,
                    y_offset=y_offset,
                )

        for gate in projected_page.gates:
            if gate.render_style.value != "x_target":
                label_y, subtitle_y, label_height_fraction, subtitle_height_fraction = (
                    _gate_text_layout(gate)
                )
                visible_label = format_visible_label(
                    gate.label,
                    use_mathtext=scene.style.use_mathtext,
                )
                label_font_size = _fit_gate_text_font_size_with_context(
                    context=gate_text_context,
                    width=gate.width,
                    height=gate.height,
                    text=visible_label,
                    default_font_size=scene.style.font_size,
                    height_fraction=label_height_fraction,
                    cache=gate_text_cache,
                )
                subtitle_font_size = (
                    _fit_gate_text_font_size_with_context(
                        context=gate_text_context,
                        width=gate.width,
                        height=gate.height,
                        text=format_parameter_text(
                            gate.subtitle,
                            use_mathtext=scene.style.use_mathtext,
                        ),
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
                    text_fit_context=gate_text_context,
                    text_fit_cache=gate_text_cache,
                )
                continue
            draw_gate_label(
                axes,
                gate,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
                text_fit_context=gate_text_context,
                text_fit_cache=gate_text_cache,
            )
        for annotation in projected_page.gate_annotations:
            draw_gate_annotation(
                axes,
                annotation,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
                text_fit_context=gate_text_context,
                text_fit_cache=gate_text_cache,
            )
        draw_controls(
            axes,
            projected_page.controls,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        if hover_enabled:
            for control in projected_page.controls:
                if control.hover_data is None:
                    continue
                self._add_control_hover_target(
                    hover_targets,
                    control,
                    scene,
                    x_offset=x_offset,
                    y_offset=y_offset,
                )

        draw_swaps(
            axes,
            projected_page.swaps,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        if hover_enabled:
            for swap in projected_page.swaps:
                if swap.hover_data is None:
                    continue
                self._add_swap_hover_target(
                    hover_targets,
                    swap,
                    x_offset=x_offset,
                    y_offset=y_offset,
                )
            for connection in projected_page.connections:
                if connection.hover_data is None:
                    continue
                self._add_connection_hover_target(
                    hover_targets,
                    connection,
                    scene,
                    x_offset=x_offset,
                    y_offset=y_offset,
                )

        for measurement in projected_page.measurements:
            draw_measurement_symbol(
                axes,
                measurement,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
                text_fit_context=gate_text_context,
                text_fit_cache=gate_text_cache,
            )
        for text in scene.texts:
            draw_text(
                axes,
                text,
                scene,
                y_offset=y_offset,
                text_fit_context=gate_text_context,
                text_fit_cache=gate_text_cache,
            )

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

    def _page_x_offset(self, page: ScenePage, scene: LayoutScene) -> float:
        return page_x_offset(page, scene)

    def _page_y_offset(self, page: ScenePage) -> float:
        return page_y_offset(page)

    def _add_gate_hover_target(
        self,
        hover_targets: list[_HoverTarget2D],
        gate: SceneGate,
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        assert gate.hover_data is not None
        add_hover_target(
            hover_targets,
            gate.hover_data,
            x_min=gate.x + x_offset - (gate.width / 2.0),
            x_max=gate.x + x_offset + (gate.width / 2.0),
            y_min=gate.y + y_offset - (gate.height / 2.0),
            y_max=gate.y + y_offset + (gate.height / 2.0),
        )

    def _add_measurement_hover_target(
        self,
        hover_targets: list[_HoverTarget2D],
        measurement: SceneMeasurement,
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        assert measurement.hover_data is not None
        add_hover_target(
            hover_targets,
            measurement.hover_data,
            x_min=measurement.x + x_offset - (measurement.width / 2.0),
            x_max=measurement.x + x_offset + (measurement.width / 2.0),
            y_min=measurement.quantum_y + y_offset - (measurement.height / 2.0),
            y_max=measurement.quantum_y + y_offset + (measurement.height / 2.0),
        )

    def _add_control_hover_target(
        self,
        hover_targets: list[_HoverTarget2D],
        control: SceneControl,
        scene: LayoutScene,
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        assert control.hover_data is not None
        radius = scene.style.control_radius
        add_hover_target(
            hover_targets,
            control.hover_data,
            x_min=control.x + x_offset - radius,
            x_max=control.x + x_offset + radius,
            y_min=control.y + y_offset - radius,
            y_max=control.y + y_offset + radius,
        )

    def _add_swap_hover_target(
        self,
        hover_targets: list[_HoverTarget2D],
        swap: SceneSwap,
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        assert swap.hover_data is not None
        add_hover_target(
            hover_targets,
            swap.hover_data,
            x_min=swap.x + x_offset - swap.marker_size,
            x_max=swap.x + x_offset + swap.marker_size,
            y_min=swap.y_top + y_offset - swap.marker_size,
            y_max=swap.y_bottom + y_offset + swap.marker_size,
        )

    def _add_connection_hover_target(
        self,
        hover_targets: list[_HoverTarget2D],
        connection: SceneConnection,
        scene: LayoutScene,
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        assert connection.hover_data is not None
        half_width = max(0.08, fabs(scene.style.line_width) * 2.0)
        add_hover_target(
            hover_targets,
            connection.hover_data,
            x_min=connection.x + x_offset - half_width,
            x_max=connection.x + x_offset + half_width,
            y_min=connection.y_start + y_offset,
            y_max=connection.y_end + y_offset,
        )
