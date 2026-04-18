"""Normalized request objects and runtime validation for draw orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from .exceptions import UnsupportedBackendError
from .hover import HoverOptions, disable_hover, normalize_hover
from .renderers._render_support import (
    NON_INTERACTIVE_BACKENDS,
    figure_backend_name,
    pyplot_backend_supports_interaction,
)
from .style import DrawStyle
from .typing import LayoutEngine3DLike, LayoutEngineLike, OutputPath

if TYPE_CHECKING:
    from matplotlib.axes import Axes

ViewMode = Literal["2d", "3d"]
TopologyMode = Literal["line", "grid", "star", "star_tree", "honeycomb"]
_VALID_VIEW_MODES = frozenset({"2d", "3d"})
_VALID_TOPOLOGIES = frozenset({"line", "grid", "star", "star_tree", "honeycomb"})
_VALID_COMPOSITE_MODES = frozenset({"compact", "expand"})


@dataclass(frozen=True, slots=True)
class DrawPipelineOptions:
    """Typed rendering options carried through adapter, layout, and rendering.

    The object keeps the stable public options together and stores any
    additional adapter-specific keyword arguments in ``extra`` so the
    public signature does not need to expose every future extension.
    """

    composite_mode: str = "compact"
    view: ViewMode = "2d"
    topology: TopologyMode = "line"
    direct: bool = True
    hover: HoverOptions = field(default_factory=lambda: HoverOptions(enabled=False))
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", dict(self.extra))

    def to_mapping(self) -> dict[str, object]:
        """Return the full option set as a plain mapping."""

        return {
            "composite_mode": self.composite_mode,
            "view": self.view,
            "topology": self.topology,
            "direct": self.direct,
            "hover": self.hover,
            **self.extra,
        }

    def adapter_options(self) -> dict[str, object]:
        """Return only the options that adapters should see.

        View-specific render controls such as ``view`` and ``hover`` are kept
        out of adapter conversion because they affect layout or rendering, not
        framework-to-IR translation.
        """

        options = self.to_mapping()
        for key in ("view", "topology", "direct", "hover"):
            options.pop(key, None)
        return options


@dataclass(frozen=True, slots=True)
class DrawRequest:
    """High-level draw request after public arguments are normalized."""

    circuit: object
    framework: str | None
    style: DrawStyle | Mapping[str, object] | None
    layout: LayoutEngineLike | LayoutEngine3DLike | None
    backend: str
    ax: Axes | None
    output: OutputPath | None
    show: bool
    figsize: tuple[float, float] | None
    page_slider: bool
    pipeline_options: DrawPipelineOptions


def build_draw_request(
    *,
    circuit: object,
    framework: str | None = None,
    style: DrawStyle | Mapping[str, object] | None = None,
    layout: LayoutEngineLike | LayoutEngine3DLike | None = None,
    backend: str = "matplotlib",
    ax: Axes | None = None,
    output: OutputPath | None = None,
    show: bool = True,
    figsize: tuple[float, float] | None = None,
    page_slider: bool = False,
    composite_mode: str = "compact",
    view: ViewMode = "2d",
    topology: TopologyMode = "line",
    direct: bool = True,
    hover: bool | HoverOptions | Mapping[str, object] = False,
    **options: object,
) -> DrawRequest:
    """Build the internal draw request without changing the public signature.

    This step resolves effective hover behavior and packages the runtime
    options into typed structures used by later orchestration stages.
    """

    normalized_hover = normalize_hover(hover)
    validate_public_options(
        view=view,
        topology=topology,
        composite_mode=composite_mode,
        direct=direct,
        show=show,
        page_slider=page_slider,
        figsize=figsize,
    )
    effective_hover = resolve_effective_hover(
        hover=normalized_hover,
        ax=ax,
        output=output,
        show=show,
        view=view,
    )
    resolved_options = _resolved_adapter_extra_options(options, effective_hover)
    return DrawRequest(
        circuit=circuit,
        framework=framework,
        style=style,
        layout=layout,
        backend=backend,
        ax=ax,
        output=output,
        show=show,
        figsize=figsize,
        page_slider=page_slider,
        pipeline_options=DrawPipelineOptions(
            composite_mode=composite_mode,
            view=view,
            topology=topology,
            direct=direct,
            hover=effective_hover,
            extra=resolved_options,
        ),
    )


def validate_public_options(
    *,
    view: object,
    topology: object,
    composite_mode: object,
    direct: object,
    show: object,
    page_slider: object,
    figsize: object,
) -> None:
    """Validate public draw options that are not enforced by Python typing."""

    _validate_choice("view", view, _VALID_VIEW_MODES)
    _validate_choice("topology", topology, _VALID_TOPOLOGIES)
    _validate_choice("composite_mode", composite_mode, _VALID_COMPOSITE_MODES)
    _validate_bool("direct", direct)
    _validate_bool("show", show)
    _validate_bool("page_slider", page_slider)
    _validate_figsize(figsize)


def _validate_choice(name: str, value: object, allowed_values: frozenset[str]) -> None:
    if isinstance(value, str) and value in allowed_values:
        return
    choices = ", ".join(sorted(allowed_values))
    raise ValueError(f"{name} must be one of: {choices}")


def _validate_bool(name: str, value: object) -> None:
    if isinstance(value, bool):
        return
    raise ValueError(f"{name} must be a boolean")


def _validate_figsize(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, tuple | list) or len(value) != 2:
        raise ValueError("figsize must be a 2-item tuple of positive numbers")
    width, height = value
    if not isinstance(width, int | float) or not isinstance(height, int | float):
        raise ValueError("figsize must be a 2-item tuple of positive numbers")
    if float(width) <= 0.0 or float(height) <= 0.0:
        raise ValueError("figsize must be a 2-item tuple of positive numbers")


def validate_draw_request(request: DrawRequest) -> None:
    """Validate public runtime combinations before preparing the pipeline."""

    if request.backend != "matplotlib":
        raise UnsupportedBackendError(f"unsupported backend '{request.backend}'")
    if request.ax is not None and request.page_slider:
        raise ValueError(
            "page_slider=True requires a Matplotlib-managed figure and cannot be used with ax"
        )
    if request.ax is not None and request.figsize is not None:
        raise ValueError(
            "figsize cannot be used with ax because the caller already owns the figure"
        )
    if request.pipeline_options.view == "3d" and request.page_slider:
        raise ValueError("page_slider=True is only supported for view='2d'")


def resolve_effective_hover(
    *,
    hover: HoverOptions,
    ax: Axes | None,
    output: OutputPath | None,
    show: bool,
    view: ViewMode,
) -> HoverOptions:
    """Resolve whether hover annotations can actually stay interactive.

    Hover labels are disabled for saved output and non-interactive backends.
    Managed hidden 2D renders also disable hover because there is no
    visible interaction to preserve and the hover payloads are expensive
    to build for dense circuits.
    """

    if not hover.enabled or output is not None:
        return disable_hover(hover)
    if ax is not None:
        if figure_backend_name(ax.figure) in NON_INTERACTIVE_BACKENDS:
            return disable_hover(hover)
        return hover
    if view == "2d" and not show:
        return disable_hover(hover)
    if not pyplot_backend_supports_interaction():
        return disable_hover(hover)
    return hover


def _resolved_adapter_extra_options(
    options: Mapping[str, object],
    effective_hover: HoverOptions,
) -> dict[str, object]:
    """Return adapter options after applying hover-related defaults."""

    resolved_options = dict(options)
    if not effective_hover.enabled and resolved_options.get("explicit_matrices") is not True:
        resolved_options["explicit_matrices"] = False
    return resolved_options
