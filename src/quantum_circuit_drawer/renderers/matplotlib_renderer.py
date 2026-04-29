"""Matplotlib renderer implementation."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Sequence
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
from ..style import resolved_connection_line_width
from ..typing import OutputPath, RenderResult, UseMathTextMode
from ._matplotlib_figure import clear_hover_state, create_managed_figure
from ._matplotlib_hover import _HoverTarget2D, add_hover_target, attach_hover
from ._matplotlib_page_projection import (
    _ProjectedPage,
    page_x_offset,
    page_y_offset,
    project_pages,
    projection_cache_key,
)
from ._render_support import save_rendered_figure
from .base import BaseRenderer
from .matplotlib_primitives import (
    _build_gate_text_fitting_context,
    _fit_gate_text_font_size_with_context,
    _GateTextCache,
    _prepared_gate_text,
    _PreparedGateText,
    draw_barriers,
    draw_connections,
    draw_controls,
    draw_gate_annotation,
    draw_gate_boxes,
    draw_gate_label,
    draw_group_highlights,
    draw_measurement_boxes,
    draw_measurement_symbol,
    draw_swaps,
    draw_text,
    draw_wire_fold_markers,
    draw_wires,
    draw_x_target_circles,
    draw_x_target_segments,
    finalize_axes,
    prepare_axes,
    trim_gate_text_fit_cache,
)

logger = logging.getLogger(__name__)
_WIRE_STUB_FRACTION_OF_GATE_WIDTH = 0.16
_WIRE_STUB_LABEL_MARGIN_FRACTION = 0.75
_WIRE_STUB_PAGE_MARGIN_FRACTION = 0.75
_PROJECTED_PAGES_CACHE_SIZE = 8
_CONNECTION_HOVER_LINE_WIDTH_MULTIPLIER = 1.5
_CONNECTION_HOVER_MIN_HALF_WIDTH_PIXELS = 4.0
_CONNECTION_HOVER_MIN_HALF_WIDTH_DATA = 1e-6
_PreparedGateTextCacheKey = tuple[object, str, str | None, UseMathTextMode]

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

    def __init__(self) -> None:
        self._projected_pages_cache: OrderedDict[
            tuple[object, ...],
            tuple[_ProjectedPage, ...],
        ] = OrderedDict()
        self._gate_text_fit_cache: _GateTextCache = {}

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

        self._render_2d_scene(
            scene,
            axes=axes,
            output=output,
            gate_text_cache=self._gate_text_fit_cache,
        )

        if ax is None:
            assert managed_figure is not None
            return managed_figure, axes
        return axes

    def _render_2d_scene(
        self,
        scene: LayoutScene,
        *,
        axes: Axes,
        output: OutputPath | None,
        gate_text_cache: _GateTextCache,
    ) -> None:
        figure: Figure | SubFigure = axes.figure
        figure.patch.set_facecolor(scene.style.theme.figure_facecolor)
        prepare_axes(axes, scene)
        projected_pages = self._project_pages(scene)
        gate_text_context = _build_gate_text_fitting_context(axes, scene)
        prepared_gate_text_cache: dict[
            _PreparedGateTextCacheKey,
            _PreparedGateText | None,
        ] = {}
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
                prepared_gate_text_cache=prepared_gate_text_cache,
                hover_targets=hover_targets,
            )

        if scene.hover.enabled and hover_targets:
            attach_hover(axes, scene.hover, hover_targets, theme=scene.style.theme)

        finalize_axes(axes)
        from ..managed.zoom import configure_zoom_text_scaling

        configure_zoom_text_scaling(axes, scene=scene)
        self._save_output(figure, output)
        trim_gate_text_fit_cache(gate_text_cache)

    def _draw_page(
        self,
        axes: Axes,
        scene: LayoutScene,
        page: ScenePage,
        projected_page: _ProjectedPage,
        *,
        gate_text_context: Any,
        gate_text_cache: _GateTextCache,
        hover_targets: list[_HoverTarget2D],
        prepared_gate_text_cache: (
            dict[_PreparedGateTextCacheKey, _PreparedGateText | None] | None
        ) = None,
    ) -> None:
        x_offset = self._page_x_offset(page, scene)
        y_offset = self._page_y_offset(page)
        hover_enabled = scene.hover.enabled
        wire_x_start, wire_x_end = self._page_wire_span(page, scene)
        resolved_prepared_gate_text_cache = (
            {} if prepared_gate_text_cache is None else prepared_gate_text_cache
        )
        grouped_label_font_sizes = self._grouped_gate_label_font_sizes(
            projected_page.gates,
            scene=scene,
            gate_text_context=gate_text_context,
            gate_text_cache=gate_text_cache,
            prepared_gate_text_cache=resolved_prepared_gate_text_cache,
        )

        draw_wires(
            axes,
            scene.wires,
            scene,
            y_offset=y_offset,
            x_start=wire_x_start,
            x_end=wire_x_end,
            text_fit_context=gate_text_context,
            text_fit_cache=gate_text_cache,
        )
        draw_group_highlights(
            axes,
            projected_page.group_highlights,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
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
        draw_gate_boxes(
            axes,
            projected_page.gates,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        if hover_enabled:
            self._add_gate_hover_targets(
                hover_targets,
                projected_page.gates,
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

        draw_measurement_boxes(
            axes,
            projected_page.measurements,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        if hover_enabled:
            self._add_measurement_hover_targets(
                hover_targets,
                projected_page.measurements,
                x_offset=x_offset,
                y_offset=y_offset,
            )

        for gate in projected_page.gates:
            if gate.render_style.value != "x_target":
                prepared_text = self._prepared_gate_text_for_render(
                    gate,
                    scene=scene,
                    cache=resolved_prepared_gate_text_cache,
                )
                if prepared_text is not None:
                    label_font_size = grouped_label_font_sizes.get(id(gate))
                    if label_font_size is None:
                        label_font_size = _fit_gate_text_font_size_with_context(
                            context=gate_text_context,
                            width=gate.width,
                            height=gate.height,
                            text=prepared_text.text,
                            default_font_size=scene.style.font_size,
                            height_fraction=prepared_text.height_fraction,
                            cache=gate_text_cache,
                        )
                    draw_gate_label(
                        axes,
                        gate,
                        scene,
                        label_font_size=label_font_size,
                        prepared_text=prepared_text,
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
            self._add_control_hover_targets(
                hover_targets,
                projected_page.controls,
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
            self._add_swap_hover_targets(
                hover_targets,
                projected_page.swaps,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            self._add_connection_hover_targets(
                hover_targets,
                projected_page.connections,
                scene,
                axes=axes,
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
        draw_wire_fold_markers(
            axes,
            scene.wire_fold_markers,
            scene,
            x_offset=x_offset,
            y_offset=y_offset,
            text_fit_context=gate_text_context,
            text_fit_cache=gate_text_cache,
        )

    def _grouped_gate_label_font_sizes(
        self,
        gates: Sequence[SceneGate],
        *,
        scene: LayoutScene,
        gate_text_context: Any,
        gate_text_cache: _GateTextCache,
        prepared_gate_text_cache: dict[_PreparedGateTextCacheKey, _PreparedGateText | None],
    ) -> dict[int, float]:
        grouped_gates: dict[
            tuple[str, float, float, float], list[tuple[SceneGate, _PreparedGateText]]
        ] = {}
        for gate in gates:
            prepared_text = self._prepared_gate_text_for_render(
                gate,
                scene=scene,
                cache=prepared_gate_text_cache,
            )
            if prepared_text is None:
                continue
            group_key = (
                self._gate_label_group_key(gate.label),
                round(gate.width, 9),
                round(gate.height, 9),
                round(prepared_text.height_fraction, 9),
            )
            grouped_gates.setdefault(group_key, []).append((gate, prepared_text))

        resolved_font_sizes: dict[int, float] = {}
        for grouped_entries in grouped_gates.values():
            minimum_font_size: float | None = None
            for gate, prepared_text in grouped_entries:
                fitted_font_size = _fit_gate_text_font_size_with_context(
                    context=gate_text_context,
                    width=gate.width,
                    height=gate.height,
                    text=prepared_text.text,
                    default_font_size=scene.style.font_size,
                    height_fraction=prepared_text.height_fraction,
                    cache=gate_text_cache,
                )
                minimum_font_size = (
                    fitted_font_size
                    if minimum_font_size is None
                    else min(minimum_font_size, fitted_font_size)
                )
            if minimum_font_size is None:
                continue
            for gate, _prepared_text in grouped_entries:
                resolved_font_sizes[id(gate)] = minimum_font_size
        return resolved_font_sizes

    def _gate_label_group_key(self, label: str) -> str:
        if label in {"P", "RZ", "RX", "RY"}:
            return "rotation_single_axis"
        if (
            label.startswith("R")
            and len(label) >= 3
            and all(axis in {"X", "Y", "Z"} for axis in label[1:])
        ):
            return "rotation_multi_axis"
        if label in {"H", "X", "Y", "Z", "T", "S"}:
            return "single_letter_pauli_phase"
        if label in {"SX", "SY", "SZ"}:
            return "sqrt_pauli"
        return f"label:{label}"

    def _prepared_gate_text_for_render(
        self,
        gate: SceneGate,
        *,
        scene: LayoutScene,
        cache: dict[_PreparedGateTextCacheKey, _PreparedGateText | None],
    ) -> _PreparedGateText | None:
        cache_key = (
            gate.render_style,
            gate.label,
            gate.subtitle,
            scene.style.use_mathtext,
        )
        cached_text = cache.get(cache_key)
        if cached_text is not None or cache_key in cache:
            return cached_text

        prepared_text = _prepared_gate_text(
            gate,
            use_mathtext=scene.style.use_mathtext,
        )
        cache[cache_key] = prepared_text
        return prepared_text

    def _project_pages(self, scene: LayoutScene) -> tuple[_ProjectedPage, ...]:
        cache_key = projection_cache_key(scene)
        cached_pages = self._projected_pages_cache.get(cache_key)
        if cached_pages is not None:
            self._projected_pages_cache.move_to_end(cache_key)
            return cached_pages

        projected_pages = project_pages(scene)
        self._projected_pages_cache[cache_key] = projected_pages
        while len(self._projected_pages_cache) > _PROJECTED_PAGES_CACHE_SIZE:
            self._projected_pages_cache.popitem(last=False)
        return projected_pages

    def _save_output(self, figure: Figure | SubFigure, output: OutputPath | None) -> None:
        try:
            save_rendered_figure(figure, output)
        except RenderingError as exc:
            logger.debug("Failed to save rendered circuit to %r: %s", output, exc)
            raise

    def _page_x_offset(self, page: ScenePage, scene: LayoutScene) -> float:
        return page_x_offset(page, scene)

    def _page_y_offset(self, page: ScenePage) -> float:
        return page_y_offset(page)

    def _page_wire_span(self, page: ScenePage, scene: LayoutScene) -> tuple[float, float]:
        lead_in = self._page_wire_stub(scene, for_leading_edge=True)
        lead_out = self._page_wire_stub(scene, for_leading_edge=False)
        return (
            scene.style.margin_left - lead_in,
            scene.style.margin_left + page.content_width + lead_out,
        )

    def _page_wire_stub(self, scene: LayoutScene, *, for_leading_edge: bool) -> float:
        base_stub = scene.style.gate_width * _WIRE_STUB_FRACTION_OF_GATE_WIDTH
        if for_leading_edge:
            budget = (
                scene.style.label_margin * _WIRE_STUB_LABEL_MARGIN_FRACTION
                if scene.style.show_wire_labels
                else scene.style.margin_left * _WIRE_STUB_PAGE_MARGIN_FRACTION
            )
        else:
            budget = scene.style.margin_right * _WIRE_STUB_PAGE_MARGIN_FRACTION
        return max(0.0, min(base_stub, budget))

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

    def _add_gate_hover_targets(
        self,
        hover_targets: list[_HoverTarget2D],
        gates: tuple[SceneGate, ...],
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        for gate in gates:
            if gate.hover_data is None:
                continue
            self._add_gate_hover_target(
                hover_targets,
                gate,
                x_offset=x_offset,
                y_offset=y_offset,
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

    def _add_measurement_hover_targets(
        self,
        hover_targets: list[_HoverTarget2D],
        measurements: tuple[SceneMeasurement, ...],
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        for measurement in measurements:
            if measurement.hover_data is None:
                continue
            self._add_measurement_hover_target(
                hover_targets,
                measurement,
                x_offset=x_offset,
                y_offset=y_offset,
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

    def _add_control_hover_targets(
        self,
        hover_targets: list[_HoverTarget2D],
        controls: tuple[SceneControl, ...],
        scene: LayoutScene,
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        for control in controls:
            if control.hover_data is None:
                continue
            self._add_control_hover_target(
                hover_targets,
                control,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
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

    def _add_swap_hover_targets(
        self,
        hover_targets: list[_HoverTarget2D],
        swaps: tuple[SceneSwap, ...],
        *,
        x_offset: float,
        y_offset: float,
    ) -> None:
        for swap in swaps:
            if swap.hover_data is None:
                continue
            self._add_swap_hover_target(
                hover_targets,
                swap,
                x_offset=x_offset,
                y_offset=y_offset,
            )

    def _add_connection_hover_target(
        self,
        hover_targets: list[_HoverTarget2D],
        connection: SceneConnection,
        scene: LayoutScene,
        *,
        axes: Axes,
        x_offset: float,
        y_offset: float,
    ) -> None:
        assert connection.hover_data is not None
        half_width = self._connection_hover_half_width(axes, scene)
        add_hover_target(
            hover_targets,
            connection.hover_data,
            x_min=connection.x + x_offset - half_width,
            x_max=connection.x + x_offset + half_width,
            y_min=connection.y_start + y_offset,
            y_max=connection.y_end + y_offset,
        )

    def _add_connection_hover_targets(
        self,
        hover_targets: list[_HoverTarget2D],
        connections: tuple[SceneConnection, ...],
        scene: LayoutScene,
        *,
        axes: Axes,
        x_offset: float,
        y_offset: float,
    ) -> None:
        half_width = self._connection_hover_half_width(axes, scene)
        for connection in connections:
            if connection.hover_data is None:
                continue
            assert connection.hover_data is not None
            add_hover_target(
                hover_targets,
                connection.hover_data,
                x_min=connection.x + x_offset - half_width,
                x_max=connection.x + x_offset + half_width,
                y_min=connection.y_start + y_offset,
                y_max=connection.y_end + y_offset,
            )

    def _connection_hover_half_width(
        self,
        axes: Axes,
        scene: LayoutScene,
    ) -> float:
        line_width_points = fabs(resolved_connection_line_width(scene.style))
        line_width_pixels = line_width_points * (axes.figure.dpi / 72.0)
        hover_half_width_pixels = max(
            _CONNECTION_HOVER_MIN_HALF_WIDTH_PIXELS,
            line_width_pixels * _CONNECTION_HOVER_LINE_WIDTH_MULTIPLIER,
        )
        origin_x, origin_y = axes.transData.transform((0.0, 0.0))
        data_origin_x, _ = axes.transData.inverted().transform((origin_x, origin_y))
        data_hover_x, _ = axes.transData.inverted().transform(
            (origin_x + hover_half_width_pixels, origin_y)
        )
        return max(
            _CONNECTION_HOVER_MIN_HALF_WIDTH_DATA,
            fabs(float(data_hover_x - data_origin_x)),
        )
