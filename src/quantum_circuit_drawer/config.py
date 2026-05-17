"""Public drawing configuration types."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, cast

from ._validation import (
    normalize_optional_non_empty_str as _normalize_optional_non_empty_str,
)
from ._validation import (
    validate_bool as _validate_bool,
)
from ._validation import (
    validate_choice as _validate_choice,
)
from ._validation import (
    validate_figsize as _validate_figsize,
)
from ._validation import (
    validate_instance as _validate_instance,
)
from ._validation import (
    validate_mapping as _validate_mapping,
)
from ._validation import (
    validate_optional_pathlike as _validate_optional_pathlike,
)
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
    """Render modes accepted by ``draw_quantum_circuit(...)``.

    Values:
        ``AUTO`` chooses a notebook-friendly or script-friendly mode from the runtime.
        ``PAGES`` creates explicit pages without interactive controls. ``PAGES_CONTROLS``
        adds page controls, ``SLIDER`` adds a viewport slider, and ``FULL`` draws the
        complete circuit in one scene.
    """

    AUTO = "auto"
    PAGES = "pages"
    PAGES_CONTROLS = "pages_controls"
    SLIDER = "slider"
    FULL = "full"


class UnsupportedPolicy(StrEnum):
    """Policy for operations that can be represented only approximately.

    Values:
        ``RAISE`` stops rendering with ``UnsupportedOperationError``. ``PLACEHOLDER``
        keeps the circuit drawable by inserting a labeled placeholder where possible.
    """

    RAISE = "raise"
    PLACEHOLDER = "placeholder"


@dataclass(frozen=True, slots=True)
class OutputOptions:
    """Shared output controls for drawing, comparison, and histogram APIs.

    Attributes:
        show: Whether the library should display the managed Matplotlib figure. In
            notebooks, ``show=False`` also suppresses automatic rich output for the
            returned result object.
        output_path: Optional filesystem path where the rendered image is saved.
            Pass ``None`` to render without writing a file.
        figsize: Optional managed figure size as ``(width, height)`` in inches.
            It cannot be combined with caller-owned axes because the caller already
            owns that figure.
    """

    show: bool = True
    output_path: OutputPath | None = None
    figsize: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        _validate_bool("show", self.show)
        _validate_optional_pathlike("output_path", self.output_path)
        _validate_figsize(self.figsize)


@dataclass(frozen=True, slots=True)
class CircuitRenderOptions:
    """Circuit interpretation and render-mode options used by ``DrawConfig``.

    Attributes:
        framework: Optional explicit adapter name such as ``"ir"``, ``"qiskit"``,
            ``"cirq"``, ``"pennylane"``, ``"myqlm"``, ``"cudaq"``, or ``"qasm"``.
            Leave ``None`` to autodetect supported inputs.
        backend: Renderer backend. The public value is currently ``"matplotlib"``.
        layout: Optional custom 2D or 3D layout engine implementing the public layout
            protocol.
        view: ``"2d"`` for standard diagrams or ``"3d"`` for topology-aware hardware
            views.
        mode: ``DrawMode`` or one of ``"auto"``, ``"pages"``, ``"pages_controls"``,
            ``"slider"``, or ``"full"``.
        composite_mode: ``"compact"`` keeps composite/control-flow operations as
            boxes when possible; ``"expand"`` draws their interior operations.
        topology: Built-in topology name, ``HardwareTopology``, ``FunctionalTopology``,
            ``PeriodicTopology1D``, or ``PeriodicTopology2D`` used for 3D views.
        topology_qubits: ``"used"`` draws only nodes used by the circuit; ``"all"``
            keeps the whole topology footprint.
        topology_resize: ``"error"`` rejects undersized flexible topologies; ``"fit"``
            allows generated topologies to resize to the circuit.
        topology_menu: Whether managed 3D modes show a topology selector.
        direct: 3D routing flag used by topology layouts.
        keyboard_shortcuts: Whether managed interactive circuit viewers respond to
            keyboard navigation.
        double_click_toggle: Whether double-clicking semantic blocks toggles collapse
            and expansion in managed viewers.
        unsupported_policy: ``UnsupportedPolicy.RAISE`` or ``PLACEHOLDER``.
        adapter_options: Adapter-specific options, for example CUDA-Q runtime
            arguments.
    """

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
    keyboard_shortcuts: bool = True
    double_click_toggle: bool = True
    unsupported_policy: UnsupportedPolicy | str = UnsupportedPolicy.RAISE
    adapter_options: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", normalize_draw_mode(self.mode))
        object.__setattr__(
            self,
            "framework",
            _normalize_optional_non_empty_str("framework", self.framework),
        )
        _validate_choice("backend", self.backend, {"matplotlib"})
        _validate_choice("view", self.view, {"2d", "3d"})
        _validate_choice("composite_mode", self.composite_mode, {"compact", "expand"})
        object.__setattr__(self, "topology", normalize_topology_input(self.topology))
        object.__setattr__(self, "topology_qubits", normalize_topology_qubits(self.topology_qubits))
        object.__setattr__(self, "topology_resize", normalize_topology_resize(self.topology_resize))
        _validate_bool("topology_menu", self.topology_menu)
        _validate_bool("direct", self.direct)
        _validate_bool("keyboard_shortcuts", self.keyboard_shortcuts)
        _validate_bool("double_click_toggle", self.double_click_toggle)
        object.__setattr__(
            self,
            "unsupported_policy",
            normalize_unsupported_policy(self.unsupported_policy),
        )
        _validate_mapping("adapter_options", self.adapter_options)
        if any(not isinstance(key, str) for key in self.adapter_options):
            raise ValueError("adapter_options keys must be strings")
        object.__setattr__(self, "adapter_options", dict(self.adapter_options))


@dataclass(frozen=True, slots=True)
class CircuitAppearanceOptions:
    """Circuit appearance options used by ``DrawConfig.side``.

    Attributes:
        preset: Optional ``StylePreset`` or preset string. Valid strings are
            ``"paper"``, ``"notebook"``, ``"compact"``, ``"presentation"``, and
            ``"accessible"``.
        style: Explicit ``DrawStyle`` or mapping of style fields. Explicit values win
            over preset defaults.
        hover: ``False`` disables hover, ``True`` enables default hover, a
            ``HoverOptions`` instance gives typed control, and a mapping may override
            selected hover fields.
    """

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
    """Circuit-side configuration shared by drawing and comparison calls.

    Attributes:
        render: ``CircuitRenderOptions`` for framework selection, render mode,
            composite expansion, view, topology, and adapter behavior.
        appearance: ``CircuitAppearanceOptions`` for preset, style, and hover behavior.
            Output ownership lives separately in ``OutputOptions``.
    """

    render: CircuitRenderOptions = field(default_factory=CircuitRenderOptions)
    appearance: CircuitAppearanceOptions = field(default_factory=CircuitAppearanceOptions)

    def __post_init__(self) -> None:
        _validate_instance("render", self.render, CircuitRenderOptions)
        _validate_instance("appearance", self.appearance, CircuitAppearanceOptions)


@dataclass(frozen=True, slots=True)
class DrawConfig:
    """Full advanced configuration for ``draw_quantum_circuit(...)``.

    Attributes:
        side: Circuit-specific configuration. It contains ``side.render`` for
            framework, mode, view, topology, and adapter choices, plus
            ``side.appearance`` for styling and hover.
        output: Shared output controls for ``show``, ``output_path``, and ``figsize``.
            Direct kwargs on ``draw_quantum_circuit(...)`` override only their matching
            fields when they are not ``None``.
    """

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
    def keyboard_shortcuts(self) -> bool:
        return self.side.render.keyboard_shortcuts

    @property
    def double_click_toggle(self) -> bool:
        return self.side.render.double_click_toggle

    @property
    def unsupported_policy(self) -> UnsupportedPolicy:
        return cast("UnsupportedPolicy", self.side.render.unsupported_policy)

    @property
    def adapter_options(self) -> Mapping[str, object]:
        return self.side.render.adapter_options

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
    is_notebook: bool
    pyplot_backend: str
    notebook_backend_active: bool
    caller_axes: Axes | None
    diagnostics: tuple[RenderDiagnostic, ...] = ()


def normalize_draw_mode(value: DrawMode | str) -> DrawMode:
    """Validate and normalize a draw-mode value.

    Args:
        value: A ``DrawMode`` member or one of ``"auto"``, ``"pages"``,
            ``"pages_controls"``, ``"slider"``, or ``"full"``.

    Returns:
        The corresponding ``DrawMode`` enum member.
    """

    try:
        return value if isinstance(value, DrawMode) else DrawMode(str(value))
    except ValueError as exc:
        choices = ", ".join(mode.value for mode in DrawMode)
        raise ValueError(f"mode must be one of: {choices}") from exc


def normalize_unsupported_policy(value: UnsupportedPolicy | str) -> UnsupportedPolicy:
    """Validate and normalize unsupported-operation policy input.

    Args:
        value: ``UnsupportedPolicy`` or one of ``"raise"`` and ``"placeholder"``.

    Returns:
        The corresponding ``UnsupportedPolicy`` enum member.
    """

    try:
        return value if isinstance(value, UnsupportedPolicy) else UnsupportedPolicy(str(value))
    except ValueError as exc:
        choices = ", ".join(policy.value for policy in UnsupportedPolicy)
        raise ValueError(f"unsupported_policy must be one of: {choices}") from exc


def validate_output_options(output: OutputOptions) -> None:
    """Validate one shared output block instance.

    Args:
        output: The ``OutputOptions`` object to validate.

    Returns:
        ``None``. A ``ValueError`` is raised by nested validators if the object is not
        a valid output block.
    """

    _validate_instance("output", output, OutputOptions)


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
