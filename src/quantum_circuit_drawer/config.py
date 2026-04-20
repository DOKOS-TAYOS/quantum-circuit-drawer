"""Public drawing configuration types."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from .hover import HoverOptions, normalize_hover
from .style import DrawStyle, normalize_style

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from .typing import LayoutEngine3DLike, LayoutEngineLike, OutputPath

ViewMode = Literal["2d", "3d"]
TopologyMode = Literal["line", "grid", "star", "star_tree", "honeycomb"]


class DrawMode(StrEnum):
    """Public render modes for managed and caller-owned drawing paths."""

    AUTO = "auto"
    PAGES = "pages"
    PAGES_CONTROLS = "pages_controls"
    SLIDER = "slider"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class DrawConfig:
    """Public draw configuration grouped by responsibility.

    The object keeps the user-facing rendering options together so the
    main entrypoint can stay compact and predictable.

    The field order follows the public API contract:

    1. framework and backend
    2. layout and view
    3. mode selection
    4. topology-related 3D options
    5. display and saving
    6. style and hover
    """

    framework: str | None = None
    backend: str = "matplotlib"
    layout: LayoutEngineLike | LayoutEngine3DLike | None = None
    view: ViewMode = "2d"
    mode: DrawMode = DrawMode.AUTO
    composite_mode: str = "compact"
    topology: TopologyMode = "line"
    topology_menu: bool = False
    direct: bool = True
    show: bool = True
    output_path: OutputPath | None = None
    figsize: tuple[float, float] | None = None
    style: DrawStyle | Mapping[str, object] | None = None
    hover: bool | HoverOptions | Mapping[str, object] = False

    def __post_init__(self) -> None:
        """Validate and normalize the public configuration.

        String-like public choices are checked immediately so invalid
        values fail early, while ``style`` and ``hover`` are normalized
        into their typed public objects.
        """

        object.__setattr__(self, "mode", self._normalize_mode(self.mode))
        self._validate_choice("backend", self.backend, {"matplotlib"})
        self._validate_choice("view", self.view, {"2d", "3d"})
        self._validate_choice("composite_mode", self.composite_mode, {"compact", "expand"})
        self._validate_choice(
            "topology",
            self.topology,
            {"line", "grid", "star", "star_tree", "honeycomb"},
        )
        self._validate_bool("topology_menu", self.topology_menu)
        self._validate_bool("direct", self.direct)
        self._validate_bool("show", self.show)
        self._validate_figsize(self.figsize)
        object.__setattr__(self, "style", normalize_style(self.style))
        object.__setattr__(self, "hover", normalize_hover(self.hover))

    @staticmethod
    def _normalize_mode(value: DrawMode | str) -> DrawMode:
        try:
            return value if isinstance(value, DrawMode) else DrawMode(str(value))
        except ValueError as exc:
            choices = ", ".join(mode.value for mode in DrawMode)
            raise ValueError(f"mode must be one of: {choices}") from exc

    @staticmethod
    def _validate_choice(name: str, value: object, allowed_values: set[str]) -> None:
        if isinstance(value, str) and value in allowed_values:
            return
        choices = ", ".join(sorted(allowed_values))
        raise ValueError(f"{name} must be one of: {choices}")

    @staticmethod
    def _validate_bool(name: str, value: object) -> None:
        if isinstance(value, bool):
            return
        raise ValueError(f"{name} must be a boolean")

    @staticmethod
    def _validate_figsize(value: object) -> None:
        if value is None:
            return
        if not isinstance(value, tuple | list) or len(value) != 2:
            raise ValueError("figsize must be a 2-item tuple of positive numbers")
        width, height = value
        if not _is_positive_dimension(width) or not _is_positive_dimension(height):
            raise ValueError("figsize must be a 2-item tuple of positive numbers")


def _is_positive_dimension(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and float(value) > 0.0


@dataclass(frozen=True, slots=True)
class ResolvedDrawConfig:
    """Internal draw configuration after runtime defaults are resolved."""

    config: DrawConfig
    mode: DrawMode
    interactive_mode_allowed: bool
    notebook_backend_active: bool
    caller_axes: Axes | None
