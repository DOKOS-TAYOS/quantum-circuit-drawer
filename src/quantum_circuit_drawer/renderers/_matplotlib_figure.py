"""Shared helpers for renderer-managed Matplotlib figures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure, SubFigure

if TYPE_CHECKING:
    from ..layout.scene import LayoutScene
    from ..layout.scene_3d import LayoutScene3D

_MANAGED_SUBPLOT_LEFT = 0.02
_MANAGED_SUBPLOT_RIGHT = 0.98
_MANAGED_SUBPLOT_TOP = 0.98
_MANAGED_SUBPLOT_BOTTOM = 0.02
_METADATA_ATTR = "_quantum_circuit_drawer_metadata"
_TEXT_SCALING_ATTR = "_quantum_circuit_drawer_text_scaling_state"
_BASE_FONT_SIZE_ATTR = "_quantum_circuit_drawer_base_font_size"
_GATE_TEXT_METADATA_ATTR = "_quantum_circuit_drawer_gate_text_metadata"
_HOVER_STATE_ATTR = "_quantum_circuit_drawer_hover_state"
_ARTIST_CLICK_TARGETS_ATTR = "_quantum_circuit_drawer_artist_click_targets"


@dataclass(slots=True)
class _ManagedFigureMetadata:
    viewport_width: float | None = None
    page_slider: object | None = None
    page_window: object | None = None
    topology_menu_state: object | None = None
    histogram_state: object | None = None


@dataclass(slots=True)
class TextScalingState:
    base_view_width: float
    base_view_height: float
    scene: LayoutScene
    base_points_per_layout_unit: float = 0.0
    last_scale_factor: float = 1.0
    last_points_per_layout_unit: float = 0.0
    is_updating: bool = False
    update_queued: bool = False
    draw_callback_id: int | None = None
    xlim_callback_id: int | None = None
    ylim_callback_id: int | None = None


@dataclass(frozen=True, slots=True)
class GateTextMetadata:
    role: str
    gate_width: float
    gate_height: float
    height_fraction: float


@dataclass(slots=True)
class HoverState:
    annotation: object
    callback_id: int | None = None


@dataclass(frozen=True, slots=True)
class ArtistClickTarget:
    artist: object
    operation_id: str
    priority: int = 0


class _SupportsRemove(Protocol):
    def remove(self) -> object: ...


def create_managed_figure(
    scene: LayoutScene | LayoutScene3D,
    *,
    figure_width: float | None = None,
    figure_height: float | None = None,
    use_agg: bool = False,
    projection: str | None = None,
) -> tuple[Figure, Axes]:
    """Create a managed Matplotlib figure with consistent padding."""

    figsize = (
        figure_width if figure_width is not None else max(4.6, scene.width * 0.95),
        figure_height if figure_height is not None else max(2.1, scene.height * 0.72),
    )

    if use_agg:
        figure = Figure(figsize=figsize)
        FigureCanvasAgg(figure)
    else:
        from matplotlib import pyplot as plt

        figure = plt.figure(figsize=figsize)

    axes = figure.add_subplot(111, projection=projection)
    figure.subplots_adjust(
        left=_MANAGED_SUBPLOT_LEFT,
        right=_MANAGED_SUBPLOT_RIGHT,
        top=_MANAGED_SUBPLOT_TOP,
        bottom=_MANAGED_SUBPLOT_BOTTOM,
    )
    return figure, axes


def set_viewport_width(figure: Figure | SubFigure, *, viewport_width: float) -> None:
    """Store the effective viewport width used by text fitting."""

    _metadata_for(figure).viewport_width = viewport_width


def get_viewport_width(figure: Figure | SubFigure, *, default: float) -> float:
    """Return the stored viewport width or a provided default."""

    viewport_width = _metadata_for(figure).viewport_width
    if viewport_width is None:
        return default
    return viewport_width


def set_page_slider(figure: Figure | SubFigure, page_slider: object) -> None:
    """Store the page slider attached to a managed figure."""

    _metadata_for(figure).page_slider = page_slider


def get_page_slider(figure: Figure | SubFigure) -> object | None:
    """Return the stored page slider if one has been attached."""

    return _metadata_for(figure).page_slider


def set_page_window(figure: Figure | SubFigure, page_window: object) -> None:
    """Store the page-window state attached to a managed figure."""

    _metadata_for(figure).page_window = page_window


def get_page_window(figure: Figure | SubFigure) -> object | None:
    """Return the stored page-window state if one has been attached."""

    return _metadata_for(figure).page_window


def set_topology_menu_state(figure: Figure | SubFigure, state: object) -> None:
    """Store topology-menu state attached to a managed figure."""

    _metadata_for(figure).topology_menu_state = state


def get_topology_menu_state(figure: Figure | SubFigure) -> object | None:
    """Return topology-menu state attached to a managed figure, if any."""

    return _metadata_for(figure).topology_menu_state


def set_histogram_state(figure: Figure | SubFigure, state: object) -> None:
    """Store managed histogram state attached to a figure."""

    _metadata_for(figure).histogram_state = state


def get_histogram_state(figure: Figure | SubFigure) -> object | None:
    """Return managed histogram state attached to a figure, if any."""

    return _metadata_for(figure).histogram_state


def clear_topology_menu_state(figure: Figure | SubFigure) -> None:
    """Detach topology-menu state and remove any attached menu artists."""

    state = get_topology_menu_state(figure)
    if state is None:
        return

    if hasattr(state, "remove"):
        cast(_SupportsRemove, state).remove()
    _metadata_for(figure).topology_menu_state = None


def set_text_scaling_state(axes: Axes, state: TextScalingState) -> None:
    """Store zoom-responsive text scaling state on the provided axes."""

    setattr(axes, _TEXT_SCALING_ATTR, state)


def get_text_scaling_state(axes: Axes) -> TextScalingState | None:
    """Return zoom-responsive text scaling state attached to the axes, if any."""

    state = getattr(axes, _TEXT_SCALING_ATTR, None)
    return state if isinstance(state, TextScalingState) else None


def clear_text_scaling_state(axes: Axes) -> None:
    """Detach zoom-responsive text scaling state and disconnect its callback."""

    state = get_text_scaling_state(axes)
    if state is None:
        return

    canvas = axes.figure.canvas
    if canvas is not None and state.draw_callback_id is not None:
        canvas.mpl_disconnect(state.draw_callback_id)
    if state.xlim_callback_id is not None:
        axes.callbacks.disconnect(state.xlim_callback_id)
    if state.ylim_callback_id is not None:
        axes.callbacks.disconnect(state.ylim_callback_id)
    delattr(axes, _TEXT_SCALING_ATTR)


def set_gate_text_metadata(
    text_artist: object,
    *,
    role: str,
    gate_width: float,
    gate_height: float,
    height_fraction: float,
) -> None:
    """Store gate-specific text layout metadata on a Matplotlib text artist."""

    setattr(
        text_artist,
        _GATE_TEXT_METADATA_ATTR,
        GateTextMetadata(
            role=role,
            gate_width=gate_width,
            gate_height=gate_height,
            height_fraction=height_fraction,
        ),
    )


def get_gate_text_metadata(text_artist: object) -> GateTextMetadata | None:
    """Return gate-specific text layout metadata if attached to the artist."""

    metadata = getattr(text_artist, _GATE_TEXT_METADATA_ATTR, None)
    return metadata if isinstance(metadata, GateTextMetadata) else None


def set_base_font_size(text_artist: object, font_size: float) -> None:
    """Store the baseline font size used for future zoom scaling."""

    setattr(text_artist, _BASE_FONT_SIZE_ATTR, font_size)


def get_base_font_size(text_artist: object, *, default: float) -> float:
    """Return the stored baseline font size or a provided default."""

    base_font_size = getattr(text_artist, _BASE_FONT_SIZE_ATTR, None)
    if isinstance(base_font_size, int | float):
        return float(base_font_size)
    return default


def set_hover_state(axes: Axes, state: HoverState) -> None:
    """Store hover callback state on the provided axes."""

    setattr(axes, _HOVER_STATE_ATTR, state)


def get_hover_state(axes: Axes) -> HoverState | None:
    """Return hover callback state attached to the axes, if any."""

    state = getattr(axes, _HOVER_STATE_ATTR, None)
    return state if isinstance(state, HoverState) else None


def clear_hover_state(axes: Axes) -> None:
    """Detach hover callback state and disconnect its callback."""

    state = get_hover_state(axes)
    if state is None:
        return

    canvas = axes.figure.canvas
    if canvas is not None and state.callback_id is not None:
        canvas.mpl_disconnect(state.callback_id)
    annotation = state.annotation
    if hasattr(annotation, "remove"):
        try:
            cast(_SupportsRemove, annotation).remove()
        except NotImplementedError:
            # ``axes.clear()`` can detach the annotation before hover cleanup runs.
            pass
    delattr(axes, _HOVER_STATE_ATTR)


def append_artist_click_target(
    axes: Axes,
    *,
    artist: object,
    operation_id: str,
    priority: int,
) -> None:
    """Append one click target artist to the axes metadata."""

    current_targets = list(get_artist_click_targets(axes))
    current_targets.append(
        ArtistClickTarget(
            artist=artist,
            operation_id=operation_id,
            priority=int(priority),
        )
    )
    setattr(axes, _ARTIST_CLICK_TARGETS_ATTR, tuple(current_targets))


def get_artist_click_targets(axes: Axes) -> tuple[ArtistClickTarget, ...]:
    """Return click-target artists attached to the axes, if any."""

    targets = getattr(axes, _ARTIST_CLICK_TARGETS_ATTR, ())
    if not isinstance(targets, tuple):
        return ()
    if not all(isinstance(target, ArtistClickTarget) for target in targets):
        return ()
    return cast("tuple[ArtistClickTarget, ...]", targets)


def clear_artist_click_targets(axes: Axes) -> None:
    """Clear all click-target artist metadata from the axes."""

    setattr(axes, _ARTIST_CLICK_TARGETS_ATTR, ())


def clicked_artist_operation_id(
    axes: Axes,
    event: MouseEvent,
) -> str | None:
    """Resolve the clicked semantic operation from registered artist targets."""

    if event.inaxes is not axes:
        return None

    matches: list[tuple[int, int, str]] = []
    for index, target in enumerate(get_artist_click_targets(axes)):
        artist = target.artist
        contains, _ = artist.contains(event) if hasattr(artist, "contains") else (False, {})
        if contains:
            matches.append((int(target.priority), -index, target.operation_id))
    if not matches:
        return None
    return max(matches)[2]


def _metadata_for(figure: Figure | SubFigure) -> _ManagedFigureMetadata:
    metadata = getattr(figure, _METADATA_ATTR, None)
    if isinstance(metadata, _ManagedFigureMetadata):
        return metadata

    metadata = _ManagedFigureMetadata()
    setattr(figure, _METADATA_ATTR, metadata)
    return metadata
