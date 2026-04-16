"""Page-slider helpers for managed 2D rendering."""

from __future__ import annotations

from collections.abc import Callable

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ._draw_managed_viewport import axes_viewport_pixels
from .layout.scene import LayoutScene


def configure_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    scene: LayoutScene,
    viewport_width: float,
    set_page_slider: Callable[[Figure, object], None],
) -> None:
    """Attach and wire a slider that scrolls the rendered circuit horizontally."""

    max_scroll = max(0.0, scene.width - viewport_width)
    if max_scroll <= 0.0:
        return

    from matplotlib.widgets import Slider

    slider_axes = figure.add_axes(
        (0.12, 0.045, 0.76, 0.055),
        facecolor=scene.style.theme.axes_facecolor,
    )
    slider = Slider(
        ax=slider_axes,
        label="Scroll",
        valmin=0.0,
        valmax=max_scroll,
        valinit=0.0,
        color=scene.style.theme.gate_edgecolor,
        track_color=scene.style.theme.classical_wire_color,
        handle_style={
            "facecolor": scene.style.theme.accent_color,
            "edgecolor": scene.style.theme.text_color,
            "size": 16,
        },
    )
    slider.label.set_color(scene.style.theme.text_color)
    slider.valtext.set_visible(False)
    slider.track.set_y(0.12)
    slider.track.set_height(0.76)
    slider.track.set_alpha(0.45)
    slider.poly.set_alpha(0.75)
    slider.vline.set_linewidth(3.0)

    set_slider_view(axes, scene, x_offset=0.0, viewport_width=viewport_width)

    def update_scroll(x_offset: float) -> None:
        set_slider_view(axes, scene, x_offset=x_offset, viewport_width=viewport_width)
        if figure.canvas is not None:
            figure.canvas.draw_idle()

    slider.on_changed(update_scroll)
    set_page_slider(figure, slider)


def page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    """Return a readable managed figure size for page-slider mode."""

    width = max(4.8, viewport_width * 0.98)
    height = max(2.0, scene_height * 0.68) + 1.0
    return width, height


def slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene width for the current axes aspect ratio."""

    axes_width_pixels, axes_height_pixels = axes_viewport_pixels(axes)
    if axes_width_pixels <= 0.0 or axes_height_pixels <= 0.0:
        return scene.width
    viewport_width = scene.height * (axes_width_pixels / axes_height_pixels)
    return min(scene.width, viewport_width)


def set_slider_view(
    axes: Axes,
    scene: LayoutScene,
    *,
    x_offset: float,
    viewport_width: float,
) -> None:
    """Set the 2D axes limits used for the slider viewport."""

    axes.set_xlim(x_offset, x_offset + viewport_width)
    axes.set_ylim(scene.height, 0.0)
