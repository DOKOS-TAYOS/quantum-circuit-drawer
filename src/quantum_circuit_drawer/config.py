"""Public drawing configuration types."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, cast

from .diagnostics import RenderDiagnostic
from .hover import HoverOptions, normalize_hover
from .presets import StylePreset, apply_draw_style_preset, normalize_style_preset
from .style import DrawStyle
from .topology import (
    TopologyInput,
    TopologyQubitMode,
    TopologyResizeMode,
    normalize_topology_input,
    normalize_topology_qubits,
    normalize_topology_resize,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from .typing import LayoutEngine3DLike, LayoutEngineLike, OutputPath

ViewMode = Literal["2d", "3d"]
TopologyMode = TopologyInput


class DrawMode(StrEnum):
    """Public render modes for managed and caller-owned drawing paths."""

    AUTO = "auto"
    PAGES = "pages"
    PAGES_CONTROLS = "pages_controls"
    SLIDER = "slider"
    FULL = "full"


class UnsupportedPolicy(StrEnum):
    """Public policy for recoverable unsupported operations."""

    RAISE = "raise"
    PLACEHOLDER = "placeholder"


@dataclass(frozen=True, slots=True)
class OutputOptions:
    """Shared output controls for public drawing and plotting APIs."""

    show: bool = True
    output_path: OutputPath | None = None
    figsize: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        _validate_bool("show", self.show)
        _validate_figsize(self.figsize)


@dataclass(frozen=True, slots=True)
class CircuitRenderOptions:
    """Public circuit-rendering controls grouped by rendering responsibility."""

    framework: str | None = None
    backend: str = "matplotlib"
    layout: LayoutEngineLike | LayoutEngine3DLike | None = None
    view: ViewMode = "2d"
    mode: DrawMode = DrawMode.AUTO
    composite_mode: str = "compact"
    topology: TopologyMode = "line"
    topology_qubits: TopologyQubitMode = "used"
    topology_resize: TopologyResizeMode = "error"
    topology_menu: bool = False
    direct: bool = True
    unsupported_policy: UnsupportedPolicy | str = UnsupportedPolicy.RAISE

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", normalize_draw_mode(self.mode))
        _validate_choice("backend", self.backend, {"matplotlib"})
        _validate_choice("view", self.view, {"2d", "3d"})
        _validate_choice("composite_mode", self.composite_mode, {"compact", "expand"})
        object.__setattr__(self, "topology", normalize_topology_input(self.topology))
        object.__setattr__(self, "topology_qubits", normalize_topology_qubits(self.topology_qubits))
        object.__setattr__(self, "topology_resize", normalize_topology_resize(self.topology_resize))
        _validate_bool("topology_menu", self.topology_menu)
        _validate_bool("direct", self.direct)
        object.__setattr__(
            self,
            "unsupported_policy",
            normalize_unsupported_policy(self.unsupported_policy),
        )


@dataclass(frozen=True, slots=True)
class CircuitAppearanceOptions:
    """Public circuit style and hover controls."""

    preset: StylePreset | str | None = None
    style: DrawStyle | Mapping[str, object] | None = None
    hover: bool | HoverOptions | Mapping[str, object] = False

    def __post_init__(self) -> None:
        normalized_preset = normalize_style_preset(self.preset)
        object.__setattr__(self, "preset", normalized_preset)
        object.__setattr__(
            self,
            "style",
            apply_draw_style_preset(self.style, preset=normalized_preset),
        )
        object.__setattr__(self, "hover", normalize_hover(self.hover))


@dataclass(frozen=True, slots=True)
class DrawSideConfig:
    """Public circuit-side configuration without output ownership."""

    render: CircuitRenderOptions = field(default_factory=CircuitRenderOptions)
    appearance: CircuitAppearanceOptions = field(default_factory=CircuitAppearanceOptions)

    def __post_init__(self) -> None:
        _validate_instance("render", self.render, CircuitRenderOptions)
        _validate_instance("appearance", self.appearance, CircuitAppearanceOptions)


@dataclass(frozen=True, slots=True)
class DrawConfig:
    """Public draw configuration grouped into typed option blocks."""

    side: DrawSideConfig = field(default_factory=DrawSideConfig)
    output: OutputOptions = field(default_factory=OutputOptions)

    def __post_init__(self) -> None:
        _validate_instance("side", self.side, DrawSideConfig)
        _validate_instance("output", self.output, OutputOptions)

    @property
    def framework(self) -> str | None:
        return self.side.render.framework

    @property
    def backend(self) -> str:
        return self.side.render.backend

    @property
    def layout(self) -> LayoutEngineLike | LayoutEngine3DLike | None:
        return self.side.render.layout

    @property
    def view(self) -> ViewMode:
        return self.side.render.view

    @property
    def mode(self) -> DrawMode:
        return self.side.render.mode

    @property
    def composite_mode(self) -> str:
        return self.side.render.composite_mode

    @property
    def topology(self) -> TopologyMode:
        return self.side.render.topology

    @property
    def topology_qubits(self) -> TopologyQubitMode:
        return self.side.render.topology_qubits

    @property
    def topology_resize(self) -> TopologyResizeMode:
        return self.side.render.topology_resize

    @property
    def topology_menu(self) -> bool:
        return self.side.render.topology_menu

    @property
    def direct(self) -> bool:
        return self.side.render.direct

    @property
    def unsupported_policy(self) -> UnsupportedPolicy:
        return cast("UnsupportedPolicy", self.side.render.unsupported_policy)

    @property
    def preset(self) -> StylePreset | None:
        return cast("StylePreset | None", self.side.appearance.preset)

    @property
    def style(self) -> DrawStyle | Mapping[str, object] | None:
        return self.side.appearance.style

    @property
    def hover(self) -> HoverOptions:
        return cast("HoverOptions", self.side.appearance.hover)

    @property
    def show(self) -> bool:
        return self.output.show

    @property
    def output_path(self) -> OutputPath | None:
        return self.output.output_path

    @property
    def figsize(self) -> tuple[float, float] | None:
        return self.output.figsize


@dataclass(frozen=True, slots=True)
class ResolvedDrawConfig:
    """Internal draw configuration after runtime defaults are resolved."""

    config: DrawConfig
    mode: DrawMode
    interactive_mode_allowed: bool
    notebook_backend_active: bool
    caller_axes: Axes | None
    diagnostics: tuple[RenderDiagnostic, ...] = ()


def normalize_draw_mode(value: DrawMode | str) -> DrawMode:
    try:
        return value if isinstance(value, DrawMode) else DrawMode(str(value))
    except ValueError as exc:
        choices = ", ".join(mode.value for mode in DrawMode)
        raise ValueError(f"mode must be one of: {choices}") from exc


def normalize_unsupported_policy(value: UnsupportedPolicy | str) -> UnsupportedPolicy:
    try:
        return value if isinstance(value, UnsupportedPolicy) else UnsupportedPolicy(str(value))
    except ValueError as exc:
        choices = ", ".join(policy.value for policy in UnsupportedPolicy)
        raise ValueError(f"unsupported_policy must be one of: {choices}") from exc


def validate_output_options(output: OutputOptions) -> None:
    """Validate one shared output block instance."""

    _validate_instance("output", output, OutputOptions)


def _validate_choice(name: str, value: object, allowed_values: set[str]) -> None:
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
    if not _is_positive_dimension(width) or not _is_positive_dimension(height):
        raise ValueError("figsize must be a 2-item tuple of positive numbers")


def _validate_instance(name: str, value: object, expected_type: type[object]) -> None:
    if isinstance(value, expected_type):
        return
    raise TypeError(f"{name} must be a {expected_type.__name__}")


def _is_positive_dimension(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and float(value) > 0.0


__all__ = [
    "CircuitAppearanceOptions",
    "CircuitRenderOptions",
    "DrawConfig",
    "DrawMode",
    "DrawSideConfig",
    "OutputOptions",
    "ResolvedDrawConfig",
    "TopologyMode",
    "TopologyQubitMode",
    "TopologyResizeMode",
    "UnsupportedPolicy",
    "ViewMode",
    "normalize_draw_mode",
    "normalize_unsupported_policy",
    "validate_output_options",
]
