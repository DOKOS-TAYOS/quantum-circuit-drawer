"""Matplotlib renderer implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import MethodType
from typing import Any, TypeVar

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure, SubFigure
from matplotlib.transforms import Bbox

from ..exceptions import RenderingError
from ..hover import HoverOptions
from ..layout.scene import (
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneHoverData,
    SceneMeasurement,
    ScenePage,
    SceneSwap,
)
from ..layout.scene_3d import LayoutScene3D
from ..typing import OutputPath, RenderResult
from ._matplotlib_figure import (
    HoverState,
    clear_hover_state,
    create_managed_figure,
    set_hover_state,
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
_HOVER_ZORDER = 10_000
_SMALL_GATE_PIXEL_THRESHOLD = 48.0


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


@dataclass(frozen=True, slots=True)
class _HoverTarget2D:
    artist: Artist
    hover_data: SceneHoverData


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
            self._attach_hover(axes, scene.hover, hover_targets)

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
                self._add_hover_target(axes, hover_targets, gate_patch, gate.hover_data)

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
                self._add_hover_target(axes, hover_targets, x_target_circle, gate.hover_data)
            x_target_segments = draw_x_target_segments(
                axes,
                (gate,),
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            if x_target_segments is not None:
                self._add_hover_target(axes, hover_targets, x_target_segments, gate.hover_data)

        for measurement in projected_page.measurements:
            measurement_patch = draw_measurement_box(
                axes,
                measurement,
                scene,
                x_offset=x_offset,
                y_offset=y_offset,
            )
            if measurement.hover_data is not None:
                self._add_hover_target(
                    axes,
                    hover_targets,
                    measurement_patch,
                    measurement.hover_data,
                )

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
                self._add_hover_target(axes, hover_targets, control_artist, control.hover_data)

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
                self._add_hover_target(axes, hover_targets, swap_artist, swap.hover_data)

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
                    self._add_hover_target(axes, hover_targets, artist, connection.hover_data)

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

    def _add_hover_target(
        self,
        axes: Axes,
        hover_targets: list[_HoverTarget2D],
        artist: Artist,
        hover_data: SceneHoverData,
    ) -> None:
        self._set_hover_artist_extent(axes, artist, hover_data)
        hover_targets.append(_HoverTarget2D(artist, hover_data))

    def _set_hover_artist_extent(
        self,
        axes: Axes,
        artist: Artist,
        hover_data: SceneHoverData,
    ) -> None:
        try:
            renderer = axes.figure.canvas.get_renderer()
            bounds = artist.get_window_extent(renderer=renderer).bounds
            if all(np.isfinite(bounds)):
                return
        except (AttributeError, RuntimeError, ValueError):
            pass

        def hover_extent(_artist: Artist, renderer: object = None) -> Bbox:
            return axes.transData.transform_bbox(
                Bbox.from_bounds(
                    hover_data.gate_x - (hover_data.gate_width / 2.0),
                    hover_data.gate_y - (hover_data.gate_height / 2.0),
                    hover_data.gate_width,
                    hover_data.gate_height,
                )
            )

        artist.get_window_extent = MethodType(hover_extent, artist)

    def _attach_hover(
        self,
        axes: Axes,
        hover_options: HoverOptions,
        hover_targets: list[_HoverTarget2D],
    ) -> None:
        annotation = axes.annotate(
            "",
            xy=(0.0, 0.0),
            xycoords="figure pixels",
            xytext=(10.0, 10.0),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=max(8.0, axes.figure.dpi / 12.0),
            color="#ffffff",
            zorder=_HOVER_ZORDER,
            annotation_clip=False,
            bbox={
                "boxstyle": "round,pad=0.18",
                "fc": "#222222",
                "ec": "#cccccc",
                "alpha": 0.9,
            },
        )
        annotation.set_visible(False)

        canvas = axes.figure.canvas
        if canvas is None:
            return

        def hide_annotation() -> None:
            if annotation.get_visible():
                annotation.set_visible(False)
                canvas.draw_idle()

        def on_motion(event: MouseEvent) -> None:
            if event.inaxes is not axes:
                hide_annotation()
                return

            for target in hover_targets:
                contains, _details = target.artist.contains(event)
                if not contains:
                    continue
                visible_width, visible_height = self._visible_gate_size_pixels(
                    axes,
                    target.hover_data,
                )
                hover_text = self._build_hover_text(
                    target.hover_data,
                    hover_options,
                    visible_width,
                    visible_height,
                )
                if not hover_text:
                    hide_annotation()
                    return
                annotation.xy = (event.x, event.y)
                annotation.set_text(hover_text)
                annotation.set_visible(True)
                canvas.draw_idle()
                return

            hide_annotation()

        callback_id = canvas.mpl_connect("motion_notify_event", on_motion)
        set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))

    def _build_hover_text(
        self,
        hover_data: SceneHoverData,
        hover_options: HoverOptions,
        visible_width: float,
        visible_height: float,
    ) -> str:
        lines: list[str] = []
        if hover_options.show_name and hover_data.name:
            lines.append(hover_data.name)
        if hover_options.show_size:
            lines.append(f"size: {visible_width:.0f} x {visible_height:.0f} px")
        if hover_options.show_qubits and hover_data.wire_labels:
            lines.append(f"wires: {', '.join(hover_data.wire_labels)}")
        if self._should_show_matrix(
            hover_data,
            hover_options,
            visible_width,
            visible_height,
        ):
            lines.append(self._format_matrix(hover_data.matrix))
        return "\n".join(line for line in lines if line)

    def _should_show_matrix(
        self,
        hover_data: SceneHoverData,
        hover_options: HoverOptions,
        visible_width: float,
        visible_height: float,
    ) -> bool:
        if hover_options.show_matrix == "never" or hover_data.matrix is None:
            return False

        matrix_array = self._matrix_array(hover_data.matrix)
        if matrix_array is None:
            return False

        qubit_count = self._matrix_qubit_count(matrix_array)
        if qubit_count is None or qubit_count > hover_options.matrix_max_qubits:
            return False

        if hover_options.show_matrix == "always":
            return True

        return max(visible_width, visible_height) <= _SMALL_GATE_PIXEL_THRESHOLD

    def _visible_gate_size_pixels(
        self,
        axes: Axes,
        hover_data: SceneHoverData,
    ) -> tuple[float, float]:
        x0, y0 = axes.transData.transform(
            (
                hover_data.gate_x - (hover_data.gate_width / 2.0),
                hover_data.gate_y - (hover_data.gate_height / 2.0),
            )
        )
        x1, y1 = axes.transData.transform(
            (
                hover_data.gate_x + (hover_data.gate_width / 2.0),
                hover_data.gate_y + (hover_data.gate_height / 2.0),
            )
        )
        return abs(float(x1 - x0)), abs(float(y1 - y0))

    def _format_matrix(self, matrix: object) -> str:
        matrix_array = self._matrix_array(matrix)
        if matrix_array is None:
            return ""
        return np.array2string(
            matrix_array,
            separator=", ",
            formatter={"complex_kind": self._format_complex, "float_kind": self._format_complex},
        )

    def _matrix_array(self, matrix: object) -> np.ndarray | None:
        try:
            matrix_array = np.asarray(matrix, dtype=np.complex128)
        except (TypeError, ValueError):
            return None
        if matrix_array.ndim != 2 or matrix_array.shape[0] != matrix_array.shape[1]:
            return None
        return matrix_array

    def _matrix_qubit_count(self, matrix: np.ndarray) -> int | None:
        dimension = int(matrix.shape[0])
        if dimension <= 0 or dimension & (dimension - 1):
            return None
        return int(np.log2(dimension))

    def _format_complex(self, value: object) -> str:
        complex_value = complex(value)
        real = complex_value.real
        imag = complex_value.imag
        if abs(imag) < 5e-4:
            return f"{real:.3g}"
        if abs(real) < 5e-4:
            return f"{imag:.3g}j"
        sign = "+" if imag >= 0.0 else "-"
        return f"{real:.3g}{sign}{abs(imag):.3g}j"
