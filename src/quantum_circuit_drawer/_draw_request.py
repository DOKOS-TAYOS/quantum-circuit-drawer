"""Normalized request objects and runtime validation for draw orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from .exceptions import UnsupportedBackendError
from .renderers._render_support import (
    NON_INTERACTIVE_BACKENDS,
    figure_backend_name,
    normalize_backend_name,
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
    hover: bool = False
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
    page_slider: bool = False,
    composite_mode: str = "compact",
    view: ViewMode = "2d",
    topology: TopologyMode = "line",
    direct: bool = True,
    hover: bool = False,
    **options: object,
) -> DrawRequest:
    """Build the internal draw request without changing the public signature.

    This step resolves effective hover behavior and packages the runtime
    options into typed structures used by later orchestration stages.
    """

    validate_public_options(
        view=view,
        topology=topology,
        composite_mode=composite_mode,
        direct=direct,
        hover=hover,
        show=show,
        page_slider=page_slider,
    )
    effective_hover = resolve_effective_hover(
        hover=hover,
        view=view,
        ax=ax,
        output=output,
        show=show,
    )
    return DrawRequest(
        circuit=circuit,
        framework=framework,
        style=style,
        layout=layout,
        backend=backend,
        ax=ax,
        output=output,
        show=show,
        page_slider=page_slider,
        pipeline_options=DrawPipelineOptions(
            composite_mode=composite_mode,
            view=view,
            topology=topology,
            direct=direct,
            hover=effective_hover,
            extra=options,
        ),
    )


def validate_public_options(
    *,
    view: object,
    topology: object,
    composite_mode: object,
    direct: object,
    hover: object,
    show: object,
    page_slider: object,
) -> None:
    """Validate public draw options that are not enforced by Python typing."""

    _validate_choice("view", view, _VALID_VIEW_MODES)
    _validate_choice("topology", topology, _VALID_TOPOLOGIES)
    _validate_choice("composite_mode", composite_mode, _VALID_COMPOSITE_MODES)
    _validate_bool("direct", direct)
    _validate_bool("hover", hover)
    _validate_bool("show", show)
    _validate_bool("page_slider", page_slider)


def _validate_choice(name: str, value: object, allowed_values: frozenset[str]) -> None:
    if isinstance(value, str) and value in allowed_values:
        return
    choices = ", ".join(sorted(allowed_values))
    raise ValueError(f"{name} must be one of: {choices}")


def _validate_bool(name: str, value: object) -> None:
    if isinstance(value, bool):
        return
    raise ValueError(f"{name} must be a boolean")


def validate_draw_request(request: DrawRequest) -> None:
    """Validate public runtime combinations before preparing the pipeline."""

    if request.backend != "matplotlib":
        raise UnsupportedBackendError(f"unsupported backend '{request.backend}'")
    if request.ax is not None and request.page_slider:
        raise ValueError(
            "page_slider=True requires a Matplotlib-managed figure and cannot be used with ax"
        )
    if request.pipeline_options.view == "3d" and request.page_slider:
        raise ValueError("page_slider=True is only supported for view='2d'")


def resolve_effective_hover(
    *,
    hover: bool,
    view: ViewMode,
    ax: Axes | None,
    output: OutputPath | None,
    show: bool,
) -> bool:
    """Resolve whether hover annotations can actually stay interactive.

    Hover labels are intentionally disabled for 2D renders, saved output,
    caller-supplied axes on non-interactive backends, and managed figures
    created with ``show=False``.
    """

    if not hover or view != "3d" or output is not None:
        return False
    if ax is not None:
        return figure_backend_name(ax.figure) not in NON_INTERACTIVE_BACKENDS
    if not show:
        return False

    from matplotlib import pyplot as plt

    return normalize_backend_name(str(plt.get_backend())) not in NON_INTERACTIVE_BACKENDS
