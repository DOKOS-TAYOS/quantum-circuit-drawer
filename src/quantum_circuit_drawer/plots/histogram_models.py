"""Histogram models, enums, and public configuration objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

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
class HistogramConfig:
    """Public configuration for ``plot_histogram``."""

    kind: HistogramKind = HistogramKind.AUTO
    mode: HistogramMode = HistogramMode.AUTO
    sort: HistogramSort = HistogramSort.STATE
    top_k: int | None = None
    qubits: tuple[int, ...] | None = None
    result_index: int = 0
    data_key: str | None = None
    preset: StylePreset | str | None = None
    theme: DrawTheme | str | None = None
    draw_style: HistogramDrawStyle = HistogramDrawStyle.SOLID
    state_label_mode: HistogramStateLabelMode = HistogramStateLabelMode.BINARY
    hover: bool = True
    show_uniform_reference: bool = False
    show: bool = True
    output_path: OutputPath | None = None
    figsize: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        normalized_preset = normalize_style_preset(self.preset)
        object.__setattr__(self, "kind", self._normalize_kind(self.kind))
        object.__setattr__(self, "mode", self._normalize_mode(self.mode))
        object.__setattr__(self, "sort", self._normalize_sort(self.sort))
        object.__setattr__(self, "preset", normalized_preset)
        preset_theme = (
            self.theme if self.theme is not None else histogram_theme_for_preset(normalized_preset)
        )
        preset_draw_style = (
            self.draw_style
            if self.draw_style is not HistogramDrawStyle.SOLID
            else histogram_draw_style_for_preset(normalized_preset) or self.draw_style
        )
        preset_figsize = self.figsize or histogram_figsize_for_preset(normalized_preset)
        object.__setattr__(self, "theme", resolve_theme(preset_theme))
        object.__setattr__(self, "draw_style", self._normalize_draw_style(preset_draw_style))
        object.__setattr__(self, "figsize", preset_figsize)
        object.__setattr__(
            self,
            "state_label_mode",
            self._normalize_state_label_mode(self.state_label_mode),
        )
        self._validate_qubits(self.qubits)
        self._validate_top_k(self.top_k)
        self._validate_result_index(self.result_index)
        self._validate_hover(self.hover)
        self._validate_show_uniform_reference(self.show_uniform_reference)
        self._validate_show(self.show)
        self._validate_figsize(self.figsize)

    @staticmethod
    def _normalize_kind(value: HistogramKind | str) -> HistogramKind:
        try:
            return value if isinstance(value, HistogramKind) else HistogramKind(str(value))
        except ValueError as exc:
            choices = ", ".join(kind.value for kind in HistogramKind)
            raise ValueError(f"kind must be one of: {choices}") from exc

    @staticmethod
    def _normalize_mode(value: HistogramMode | str) -> HistogramMode:
        try:
            return value if isinstance(value, HistogramMode) else HistogramMode(str(value))
        except ValueError as exc:
            choices = ", ".join(mode.value for mode in HistogramMode)
            raise ValueError(f"mode must be one of: {choices}") from exc

    @staticmethod
    def _normalize_sort(value: HistogramSort | str) -> HistogramSort:
        try:
            return value if isinstance(value, HistogramSort) else HistogramSort(str(value))
        except ValueError as exc:
            choices = ", ".join(sort.value for sort in HistogramSort)
            raise ValueError(f"sort must be one of: {choices}") from exc

    @staticmethod
    def _normalize_draw_style(value: HistogramDrawStyle | str) -> HistogramDrawStyle:
        try:
            return (
                value if isinstance(value, HistogramDrawStyle) else HistogramDrawStyle(str(value))
            )
        except ValueError as exc:
            choices = ", ".join(style.value for style in HistogramDrawStyle)
            raise ValueError(f"draw_style must be one of: {choices}") from exc

    @staticmethod
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

    @staticmethod
    def _validate_qubits(qubits: tuple[int, ...] | None) -> None:
        if qubits is None:
            return
        if not isinstance(qubits, tuple):
            raise ValueError("qubits must be a tuple of non-negative integers")
        if any(not _is_non_negative_integer(qubit) for qubit in qubits):
            raise ValueError("qubits must be a tuple of non-negative integers")
        if len(set(qubits)) != len(qubits):
            raise ValueError("qubits must not contain duplicates")

    @staticmethod
    def _validate_top_k(value: int | None) -> None:
        if value is None:
            return
        if _is_positive_integer(value):
            return
        raise ValueError("top_k must be a positive integer")

    @staticmethod
    def _validate_result_index(value: int) -> None:
        if _is_non_negative_integer(value):
            return
        raise ValueError("result_index must be a non-negative integer")

    @staticmethod
    def _validate_show_uniform_reference(value: bool) -> None:
        if isinstance(value, bool):
            return
        raise ValueError("show_uniform_reference must be a boolean")

    @staticmethod
    def _validate_hover(value: bool) -> None:
        if isinstance(value, bool):
            return
        raise ValueError("hover must be a boolean")

    @staticmethod
    def _validate_show(value: bool) -> None:
        if isinstance(value, bool):
            return
        raise ValueError("show must be a boolean")

    @staticmethod
    def _validate_figsize(value: tuple[float, float] | None) -> None:
        if value is None:
            return
        if not isinstance(value, tuple | list) or len(value) != 2:
            raise ValueError("figsize must be a 2-item tuple of positive numbers")
        width, height = value
        if not _is_positive_dimension(width) or not _is_positive_dimension(height):
            raise ValueError("figsize must be a 2-item tuple of positive numbers")


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

    kind: HistogramKind = HistogramKind.AUTO
    sort: HistogramCompareSort = HistogramCompareSort.STATE
    top_k: int | None = None
    qubits: tuple[int, ...] | None = None
    result_index: int = 0
    data_key: str | None = None
    preset: StylePreset | str | None = None
    theme: DrawTheme | str | None = None
    left_label: str = "Left"
    right_label: str = "Right"
    hover: bool = True
    show: bool = True
    output_path: OutputPath | None = None
    figsize: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        normalized_preset = normalize_style_preset(self.preset)
        object.__setattr__(self, "kind", HistogramConfig._normalize_kind(self.kind))
        object.__setattr__(self, "sort", self._normalize_sort(self.sort))
        object.__setattr__(self, "preset", normalized_preset)
        preset_theme = (
            self.theme if self.theme is not None else histogram_theme_for_preset(normalized_preset)
        )
        object.__setattr__(self, "theme", resolve_theme(preset_theme))
        object.__setattr__(
            self,
            "figsize",
            self.figsize or histogram_figsize_for_preset(normalized_preset),
        )
        HistogramConfig._validate_qubits(self.qubits)
        HistogramConfig._validate_top_k(self.top_k)
        HistogramConfig._validate_result_index(self.result_index)
        HistogramConfig._validate_hover(self.hover)
        HistogramConfig._validate_show(self.show)
        HistogramConfig._validate_figsize(self.figsize)

    @staticmethod
    def _normalize_sort(value: HistogramCompareSort | str) -> HistogramCompareSort:
        try:
            return (
                value
                if isinstance(value, HistogramCompareSort)
                else HistogramCompareSort(str(value))
            )
        except ValueError as exc:
            choices = ", ".join(sort.value for sort in HistogramCompareSort)
            raise ValueError(f"sort must be one of: {choices}") from exc


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


def _is_positive_dimension(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and float(value) > 0.0


def _is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


__all__ = [
    "HistogramCompareConfig",
    "HistogramCompareMetrics",
    "HistogramCompareResult",
    "HistogramCompareSort",
    "HistogramConfig",
    "HistogramDrawStyle",
    "HistogramKind",
    "HistogramMode",
    "HistogramResult",
    "HistogramSort",
    "HistogramStateLabelMode",
]
