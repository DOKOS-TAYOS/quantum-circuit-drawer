"""Histogram models, enums, and public configuration objects."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import TYPE_CHECKING

from ..config import OutputOptions, validate_output_options
from ..presets import (
    StylePreset,
    histogram_draw_style_for_preset,
    histogram_figsize_for_preset,
    histogram_theme_for_preset,
    normalize_style_preset,
)
from ..style.theme import resolve_theme

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..diagnostics import RenderDiagnostic
    from ..style.theme import DrawTheme
    from ..typing import OutputPath


class HistogramKind(StrEnum):
    """Public histogram data modes."""

    AUTO = "auto"
    COUNTS = "counts"
    QUASI = "quasi"


class HistogramMode(StrEnum):
    """Public histogram render modes."""

    AUTO = "auto"
    STATIC = "static"
    INTERACTIVE = "interactive"


class HistogramStateLabelMode(StrEnum):
    """Public histogram state-label display modes."""

    BINARY = "binary"
    DECIMAL = "decimal"


class HistogramSort(StrEnum):
    """Public histogram ordering modes."""

    STATE = "state"
    STATE_DESC = "state_desc"
    VALUE_DESC = "value_desc"
    VALUE_ASC = "value_asc"


class HistogramDrawStyle(StrEnum):
    """Public histogram bar rendering styles."""

    SOLID = "solid"
    OUTLINE = "outline"
    SOFT = "soft"


class HistogramCompareSort(StrEnum):
    """Public ordering modes for histogram comparison plots."""

    STATE = "state"
    STATE_DESC = "state_desc"
    DELTA_DESC = "delta_desc"


@dataclass(frozen=True, slots=True)
class HistogramDataOptions:
    """Histogram data selection and interpretation controls."""

    kind: HistogramKind = HistogramKind.AUTO
    top_k: int | None = None
    qubits: tuple[int, ...] | None = None
    result_index: int = 0
    data_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _normalize_kind(self.kind))
        _validate_qubits(self.qubits)
        _validate_top_k(self.top_k)
        _validate_result_index(self.result_index)


@dataclass(frozen=True, slots=True)
class HistogramViewOptions:
    """Histogram view-specific options for single-histogram plots."""

    mode: HistogramMode = HistogramMode.AUTO
    sort: HistogramSort = HistogramSort.STATE
    state_label_mode: HistogramStateLabelMode = HistogramStateLabelMode.BINARY

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _normalize_mode(self.mode))
        object.__setattr__(self, "sort", _normalize_sort(self.sort))
        object.__setattr__(
            self,
            "state_label_mode",
            _normalize_state_label_mode(self.state_label_mode),
        )


@dataclass(frozen=True, slots=True)
class HistogramAppearanceOptions:
    """Histogram appearance and interaction options."""

    preset: StylePreset | str | None = None
    theme: DrawTheme | str | None = None
    draw_style: HistogramDrawStyle = HistogramDrawStyle.SOLID
    hover: bool = True
    show_uniform_reference: bool = False

    def __post_init__(self) -> None:
        normalized_preset = normalize_style_preset(self.preset)
        preset_theme = (
            self.theme if self.theme is not None else histogram_theme_for_preset(normalized_preset)
        )
        preset_draw_style = (
            self.draw_style
            if self.draw_style is not HistogramDrawStyle.SOLID
            else histogram_draw_style_for_preset(normalized_preset) or self.draw_style
        )
        object.__setattr__(self, "preset", normalized_preset)
        object.__setattr__(self, "theme", resolve_theme(preset_theme))
        object.__setattr__(self, "draw_style", _normalize_draw_style(preset_draw_style))
        _validate_hover(self.hover)
        _validate_show_uniform_reference(self.show_uniform_reference)


@dataclass(frozen=True, slots=True)
class HistogramCompareOptions:
    """Histogram-comparison specific presentation controls."""

    sort: HistogramCompareSort = HistogramCompareSort.STATE
    left_label: str = "Left"
    right_label: str = "Right"
    hover: bool = True
    preset: StylePreset | str | None = None
    theme: DrawTheme | str | None = None

    def __post_init__(self) -> None:
        normalized_preset = normalize_style_preset(self.preset)
        preset_theme = (
            self.theme if self.theme is not None else histogram_theme_for_preset(normalized_preset)
        )
        object.__setattr__(self, "sort", _normalize_compare_sort(self.sort))
        object.__setattr__(self, "preset", normalized_preset)
        object.__setattr__(self, "theme", resolve_theme(preset_theme))
        _validate_hover(self.hover)


@dataclass(frozen=True, slots=True)
class HistogramConfig:
    """Public configuration for ``plot_histogram``."""

    data: HistogramDataOptions = field(default_factory=HistogramDataOptions)
    view: HistogramViewOptions = field(default_factory=HistogramViewOptions)
    appearance: HistogramAppearanceOptions = field(default_factory=HistogramAppearanceOptions)
    output: OutputOptions = field(default_factory=OutputOptions)

    def __post_init__(self) -> None:
        _validate_instance("data", self.data, HistogramDataOptions)
        _validate_instance("view", self.view, HistogramViewOptions)
        _validate_instance("appearance", self.appearance, HistogramAppearanceOptions)
        validate_output_options(self.output)
        preset_figsize = histogram_figsize_for_preset(self.appearance.preset)
        if self.output.figsize is None and preset_figsize is not None:
            object.__setattr__(self, "output", replace(self.output, figsize=preset_figsize))

    @property
    def kind(self) -> HistogramKind:
        return self.data.kind

    @property
    def top_k(self) -> int | None:
        return self.data.top_k

    @property
    def qubits(self) -> tuple[int, ...] | None:
        return self.data.qubits

    @property
    def result_index(self) -> int:
        return self.data.result_index

    @property
    def data_key(self) -> str | None:
        return self.data.data_key

    @property
    def mode(self) -> HistogramMode:
        return self.view.mode

    @property
    def sort(self) -> HistogramSort:
        return self.view.sort

    @property
    def state_label_mode(self) -> HistogramStateLabelMode:
        return self.view.state_label_mode

    @property
    def preset(self) -> StylePreset | None:
        return self.appearance.preset

    @property
    def theme(self) -> DrawTheme:
        return self.appearance.theme

    @property
    def draw_style(self) -> HistogramDrawStyle:
        return self.appearance.draw_style

    @property
    def hover(self) -> bool:
        return self.appearance.hover

    @property
    def show_uniform_reference(self) -> bool:
        return self.appearance.show_uniform_reference

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
class HistogramResult:
    """Returned histogram plot handle and normalized values."""

    figure: Figure
    axes: Axes
    kind: HistogramKind
    state_labels: tuple[str, ...]
    values: tuple[float, ...]
    qubits: tuple[int, ...] | None
    diagnostics: tuple[RenderDiagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class HistogramCompareConfig:
    """Public configuration for ``compare_histograms``."""

    data: HistogramDataOptions = field(default_factory=HistogramDataOptions)
    compare: HistogramCompareOptions = field(default_factory=HistogramCompareOptions)
    output: OutputOptions = field(default_factory=OutputOptions)

    def __post_init__(self) -> None:
        _validate_instance("data", self.data, HistogramDataOptions)
        _validate_instance("compare", self.compare, HistogramCompareOptions)
        validate_output_options(self.output)
        preset_figsize = histogram_figsize_for_preset(self.compare.preset)
        if self.output.figsize is None and preset_figsize is not None:
            object.__setattr__(self, "output", replace(self.output, figsize=preset_figsize))

    @property
    def kind(self) -> HistogramKind:
        return self.data.kind

    @property
    def top_k(self) -> int | None:
        return self.data.top_k

    @property
    def qubits(self) -> tuple[int, ...] | None:
        return self.data.qubits

    @property
    def result_index(self) -> int:
        return self.data.result_index

    @property
    def data_key(self) -> str | None:
        return self.data.data_key

    @property
    def sort(self) -> HistogramCompareSort:
        return self.compare.sort

    @property
    def left_label(self) -> str:
        return self.compare.left_label

    @property
    def right_label(self) -> str:
        return self.compare.right_label

    @property
    def hover(self) -> bool:
        return self.compare.hover

    @property
    def preset(self) -> StylePreset | None:
        return self.compare.preset

    @property
    def theme(self) -> DrawTheme:
        return self.compare.theme

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
class HistogramCompareMetrics:
    """Comparison metrics derived from overlaid histograms."""

    total_variation_distance: float
    max_absolute_delta: float


@dataclass(frozen=True, slots=True)
class HistogramCompareResult:
    """Returned comparison plot handle and aligned histogram values."""

    figure: Figure
    axes: Axes
    kind: HistogramKind
    state_labels: tuple[str, ...]
    left_values: tuple[float, ...]
    right_values: tuple[float, ...]
    delta_values: tuple[float, ...]
    metrics: HistogramCompareMetrics
    qubits: tuple[int, ...] | None
    diagnostics: tuple[RenderDiagnostic, ...] = ()


def _normalize_kind(value: HistogramKind | str) -> HistogramKind:
    try:
        return value if isinstance(value, HistogramKind) else HistogramKind(str(value))
    except ValueError as exc:
        choices = ", ".join(kind.value for kind in HistogramKind)
        raise ValueError(f"kind must be one of: {choices}") from exc


def _normalize_mode(value: HistogramMode | str) -> HistogramMode:
    try:
        return value if isinstance(value, HistogramMode) else HistogramMode(str(value))
    except ValueError as exc:
        choices = ", ".join(mode.value for mode in HistogramMode)
        raise ValueError(f"mode must be one of: {choices}") from exc


def _normalize_sort(value: HistogramSort | str) -> HistogramSort:
    try:
        return value if isinstance(value, HistogramSort) else HistogramSort(str(value))
    except ValueError as exc:
        choices = ", ".join(sort.value for sort in HistogramSort)
        raise ValueError(f"sort must be one of: {choices}") from exc


def _normalize_draw_style(value: HistogramDrawStyle | str) -> HistogramDrawStyle:
    try:
        return value if isinstance(value, HistogramDrawStyle) else HistogramDrawStyle(str(value))
    except ValueError as exc:
        choices = ", ".join(style.value for style in HistogramDrawStyle)
        raise ValueError(f"draw_style must be one of: {choices}") from exc


def _normalize_state_label_mode(
    value: HistogramStateLabelMode | str,
) -> HistogramStateLabelMode:
    try:
        return (
            value
            if isinstance(value, HistogramStateLabelMode)
            else HistogramStateLabelMode(str(value))
        )
    except ValueError as exc:
        choices = ", ".join(mode.value for mode in HistogramStateLabelMode)
        raise ValueError(f"state_label_mode must be one of: {choices}") from exc


def _normalize_compare_sort(value: HistogramCompareSort | str) -> HistogramCompareSort:
    try:
        return (
            value if isinstance(value, HistogramCompareSort) else HistogramCompareSort(str(value))
        )
    except ValueError as exc:
        choices = ", ".join(sort.value for sort in HistogramCompareSort)
        raise ValueError(f"sort must be one of: {choices}") from exc


def _validate_qubits(qubits: tuple[int, ...] | None) -> None:
    if qubits is None:
        return
    if not isinstance(qubits, tuple):
        raise ValueError("qubits must be a tuple of non-negative integers")
    if any(not _is_non_negative_integer(qubit) for qubit in qubits):
        raise ValueError("qubits must be a tuple of non-negative integers")
    if len(set(qubits)) != len(qubits):
        raise ValueError("qubits must not contain duplicates")


def _validate_top_k(value: int | None) -> None:
    if value is None:
        return
    if _is_positive_integer(value):
        return
    raise ValueError("top_k must be a positive integer")


def _validate_result_index(value: int) -> None:
    if _is_non_negative_integer(value):
        return
    raise ValueError("result_index must be a non-negative integer")


def _validate_show_uniform_reference(value: bool) -> None:
    if isinstance(value, bool):
        return
    raise ValueError("show_uniform_reference must be a boolean")


def _validate_hover(value: bool) -> None:
    if isinstance(value, bool):
        return
    raise ValueError("hover must be a boolean")


def _validate_instance(name: str, value: object, expected_type: type[object]) -> None:
    if isinstance(value, expected_type):
        return
    raise TypeError(f"{name} must be a {expected_type.__name__}")


def _is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


__all__ = [
    "HistogramAppearanceOptions",
    "HistogramCompareConfig",
    "HistogramCompareMetrics",
    "HistogramCompareOptions",
    "HistogramCompareResult",
    "HistogramCompareSort",
    "HistogramConfig",
    "HistogramDataOptions",
    "HistogramDrawStyle",
    "HistogramKind",
    "HistogramMode",
    "HistogramResult",
    "HistogramSort",
    "HistogramStateLabelMode",
    "HistogramViewOptions",
]
