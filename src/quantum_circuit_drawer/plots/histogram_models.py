"""Histogram models, enums, and public configuration objects."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .._ipython_display import display_figures_in_ipython
from .._validation import (
    is_non_negative_integer as _is_non_negative_integer,
)
from .._validation import (
    is_positive_integer as _is_positive_integer,
)
from .._validation import (
    validate_bool as _validate_bool,
)
from .._validation import (
    validate_instance as _validate_instance,
)
from .._validation import (
    validate_str_tuple as _validate_str_tuple,
)
from ..config import OutputOptions, validate_output_options
from ..export.figures import save_matplotlib_figure
from ..presets import (
    StylePreset,
    histogram_draw_style_for_preset,
    histogram_figsize_for_preset,
    histogram_theme_for_preset,
    normalize_style_preset,
)
from ..result import _resolved_output_path, diagnostics_to_dicts
from ..style.theme import resolve_theme
from ..typing import OutputPath

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..diagnostics import RenderDiagnostic
    from ..style.theme import DrawTheme


class HistogramKind(StrEnum):
    """How histogram input values should be interpreted.

    Values:
        ``AUTO`` infers counts from non-negative integer values and otherwise uses
        quasi-probabilities. ``COUNTS`` requires non-negative integer counts.
        ``QUASI`` accepts probability-like weights, including negative values.
    """

    AUTO = "auto"
    COUNTS = "counts"
    QUASI = "quasi"


class HistogramMode(StrEnum):
    """Rendering mode for ``plot_histogram(...)``.

    Values:
        ``AUTO`` chooses static mode for hidden outputs, interactive mode for normal
        visible scripts and widget notebook backends, and static output in inline
        notebooks. ``STATIC`` draws a normal Matplotlib histogram. ``INTERACTIVE``
        adds the managed slider, buttons, hover, and marginal controls.
    """

    AUTO = "auto"
    STATIC = "static"
    INTERACTIVE = "interactive"


class HistogramStateLabelMode(StrEnum):
    """Display style for x-axis state labels.

    Values:
        ``BINARY`` keeps bitstring labels such as ``"101"``. ``DECIMAL`` converts each
        register to base-10 text; space-separated registers are converted independently.
    """

    BINARY = "binary"
    DECIMAL = "decimal"


class HistogramSort(StrEnum):
    """Ordering choices for a single histogram.

    Values:
        ``STATE`` sorts state labels ascending. ``STATE_DESC`` sorts state labels
        descending. ``VALUE_DESC`` and ``VALUE_ASC`` order bins by value with a stable
        state-label tie break.
    """

    STATE = "state"
    STATE_DESC = "state_desc"
    VALUE_DESC = "value_desc"
    VALUE_ASC = "value_asc"


class HistogramDrawStyle(StrEnum):
    """Bar styles for static and saved histogram figures.

    Values:
        ``SOLID`` uses filled bars, ``OUTLINE`` emphasizes edges with lighter fills,
        and ``SOFT`` uses the softer preset-friendly bar treatment.
    """

    SOLID = "solid"
    OUTLINE = "outline"
    SOFT = "soft"


class HistogramCompareSort(StrEnum):
    """Ordering choices for ``compare_histograms(...)``.

    Values:
        ``STATE`` and ``STATE_DESC`` sort by normalized state labels. ``DELTA_DESC``
        puts states with the largest absolute left-minus-right difference first.
    """

    STATE = "state"
    STATE_DESC = "state_desc"
    DELTA_DESC = "delta_desc"


@dataclass(frozen=True, slots=True)
class HistogramDataOptions:
    """Data-selection options shared by histogram plot and comparison calls.

    Attributes:
        kind: ``HistogramKind`` or one of ``"auto"``, ``"counts"``, and ``"quasi"``.
        top_k: Optional positive integer limiting the plot to the highest-ranked bins
            after the selected ordering is applied.
        qubits: Optional tuple of qubit indices for a joint marginal. The tuple order is
            preserved in the returned state labels.
        result_index: Non-negative index used when the input is a tuple/list or a
            framework result container with several histogram payloads.
        data_key: Optional Qiskit ``DataBin`` field name when several measurement data
            fields are present.
    """

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
    """View options specific to ``plot_histogram(...)``.

    Attributes:
        mode: ``HistogramMode`` or one of ``"auto"``, ``"static"``, and
            ``"interactive"``.
        sort: ``HistogramSort`` or one of ``"state"``, ``"state_desc"``,
            ``"value_desc"``, and ``"value_asc"``.
        state_label_mode: ``HistogramStateLabelMode`` or ``"binary"`` / ``"decimal"``
            for visible x-axis labels.
    """

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
    """Advanced histogram appearance and interaction options.

    Attributes:
        preset: Optional shared ``StylePreset`` or preset string. Valid strings are
            ``"paper"``, ``"notebook"``, ``"compact"``, ``"presentation"``, and
            ``"accessible"``.
        theme: Optional theme name or ``DrawTheme`` override. ``None`` uses the preset
            or default theme.
        draw_style: ``HistogramDrawStyle`` or ``"solid"``, ``"outline"``, or
            ``"soft"``.
        hover: Whether interactive histogram bin/control hover is enabled.
        show_uniform_reference: Whether to draw a uniform reference line in static and
            saved histogram figures.
    """

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
        _validate_bool("hover", self.hover)
        _validate_bool("show_uniform_reference", self.show_uniform_reference)


@dataclass(frozen=True, slots=True)
class HistogramCompareOptions:
    """Presentation options specific to ``compare_histograms(...)``.

    Attributes:
        sort: ``HistogramCompareSort`` or one of ``"state"``, ``"state_desc"``, and
            ``"delta_desc"``.
        left_label: Legend label for the first distribution.
        right_label: Legend label for the second distribution.
        hover: Whether comparison hover labels are enabled.
        preset: Optional shared style preset name.
        theme: Optional theme name or ``DrawTheme`` override.
        series_labels: Optional label for each distribution when comparing three or
            more series.
    """

    sort: HistogramCompareSort = HistogramCompareSort.STATE
    left_label: str = "Left"
    right_label: str = "Right"
    hover: bool = True
    preset: StylePreset | str | None = None
    theme: DrawTheme | str | None = None
    series_labels: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        normalized_preset = normalize_style_preset(self.preset)
        preset_theme = (
            self.theme if self.theme is not None else histogram_theme_for_preset(normalized_preset)
        )
        object.__setattr__(self, "sort", _normalize_compare_sort(self.sort))
        object.__setattr__(self, "preset", normalized_preset)
        object.__setattr__(self, "theme", resolve_theme(preset_theme))
        if self.series_labels is not None:
            _validate_str_tuple("series_labels", self.series_labels)
        _validate_bool("hover", self.hover)


@dataclass(frozen=True, slots=True)
class HistogramConfig:
    """Advanced configuration object for ``plot_histogram(...)``.

    Attributes:
        data: ``HistogramDataOptions`` for input interpretation, top-k filtering,
            result selection, data key selection, and qubit marginals.
        view: ``HistogramViewOptions`` for mode, bin ordering, and visible label style.
        appearance: ``HistogramAppearanceOptions`` for hover, presets, themes, bar
            style, and uniform reference lines.
        output: ``OutputOptions`` for ``show``, ``output_path``, and ``figsize``.
            Direct kwargs on ``plot_histogram(...)`` override only matching fields when
            they are not ``None``.
    """

    data: HistogramDataOptions = field(default_factory=HistogramDataOptions)
    view: HistogramViewOptions = field(default_factory=HistogramViewOptions)
    appearance: HistogramAppearanceOptions = field(default_factory=HistogramAppearanceOptions)
    output: OutputOptions = field(default_factory=OutputOptions)

    def __post_init__(self) -> None:
        _validate_instance("data", self.data, HistogramDataOptions)
        _validate_instance("view", self.view, HistogramViewOptions)
        _validate_instance("appearance", self.appearance, HistogramAppearanceOptions)
        validate_output_options(self.output)
        preset_figsize = histogram_figsize_for_preset(
            cast("StylePreset | None", self.appearance.preset)
        )
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
        return cast("StylePreset | None", self.appearance.preset)

    @property
    def theme(self) -> DrawTheme:
        return cast("DrawTheme", self.appearance.theme)

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
    """Result returned by ``plot_histogram(...)``.

    Attributes:
        figure: Matplotlib figure containing the histogram.
        axes: Matplotlib axes used for the histogram.
        kind: Resolved ``HistogramKind`` after input normalization.
        state_labels: Normalized state labels in the returned order. These stay binary
            even if ``state_label_mode="decimal"`` changes the visible tick labels.
        values: Numeric values aligned with ``state_labels``.
        qubits: Selected marginal qubits, or ``None`` when the full register is shown.
        diagnostics: Non-fatal diagnostics emitted while normalizing or rendering.
        saved_path: Absolute saved path when ``output_path`` was used.
    """

    figure: Figure
    axes: Axes
    kind: HistogramKind
    state_labels: tuple[str, ...]
    values: tuple[float, ...]
    qubits: tuple[int, ...] | None
    diagnostics: tuple[RenderDiagnostic, ...] = ()
    saved_path: str | None = None
    _ipython_display_enabled: bool = field(default=True, repr=False, compare=False)
    _ipython_close_after_display: bool = field(default=False, repr=False, compare=False)

    def _ipython_display_(self) -> None:
        """Display the histogram figure in IPython without showing the dataclass repr."""

        if not self._ipython_display_enabled:
            return
        display_figures_in_ipython(
            (self.figure,),
            close_after_display=self._ipython_close_after_display,
        )

    def save(self, path: OutputPath) -> str:
        """Save the histogram figure to disk.

        Args:
            path: Destination image path accepted by Matplotlib, such as ``"hist.png"``
                or ``Path("hist.svg")``.

        Returns:
            The absolute path written.
        """

        save_matplotlib_figure(self.figure, path)
        return _resolved_output_path(path)

    def to_dict(self) -> dict[str, object]:
        """Return histogram data without Matplotlib objects.

        Returns:
            A JSON-friendly dictionary containing kind, state labels, values, selected
            qubits, saved path, and diagnostics.
        """

        return {
            "kind": self.kind.value,
            "state_labels": self.state_labels,
            "values": self.values,
            "qubits": self.qubits,
            "saved_path": self.saved_path,
            "diagnostics": diagnostics_to_dicts(self.diagnostics),
        }

    def to_csv(self, path: OutputPath) -> str:
        """Write state/value rows to CSV.

        Args:
            path: Destination CSV path.

        Returns:
            The absolute path written.
        """

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(("state", "value"))
            writer.writerows(zip(self.state_labels, self.values, strict=True))
        return _resolved_output_path(path)


@dataclass(frozen=True, slots=True)
class HistogramCompareConfig:
    """Advanced configuration object for ``compare_histograms(...)``.

    Attributes:
        data: Shared ``HistogramDataOptions`` applied to every input distribution.
        compare: ``HistogramCompareOptions`` controlling ordering, legend labels,
            hover, presets, and multi-series labels.
        output: ``OutputOptions`` for ``show``, ``output_path``, and ``figsize``.
            Direct kwargs on ``compare_histograms(...)`` override only matching fields
            when they are not ``None``.
    """

    data: HistogramDataOptions = field(default_factory=HistogramDataOptions)
    compare: HistogramCompareOptions = field(default_factory=HistogramCompareOptions)
    output: OutputOptions = field(default_factory=OutputOptions)

    def __post_init__(self) -> None:
        _validate_instance("data", self.data, HistogramDataOptions)
        _validate_instance("compare", self.compare, HistogramCompareOptions)
        validate_output_options(self.output)
        preset_figsize = histogram_figsize_for_preset(
            cast("StylePreset | None", self.compare.preset)
        )
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
    def series_labels(self) -> tuple[str, ...] | None:
        return self.compare.series_labels

    @property
    def hover(self) -> bool:
        return self.compare.hover

    @property
    def preset(self) -> StylePreset | None:
        return cast("StylePreset | None", self.compare.preset)

    @property
    def theme(self) -> DrawTheme:
        return cast("DrawTheme", self.compare.theme)

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
    """Numeric distance summary for aligned histogram comparisons.

    Attributes:
        total_variation_distance: Half the sum of absolute bin differences between the
            first two aligned distributions.
        max_absolute_delta: Largest absolute per-bin difference between the first two
            aligned distributions.
    """

    total_variation_distance: float
    max_absolute_delta: float


@dataclass(frozen=True, slots=True)
class HistogramCompareResult:
    """Result returned by ``compare_histograms(...)``.

    Attributes:
        figure: Matplotlib figure containing the comparison plot.
        axes: Matplotlib axes used for the comparison.
        kind: Resolved common ``HistogramKind`` for the displayed data.
        state_labels: Aligned state labels shared by every series.
        left_values: Values for the first distribution.
        right_values: Values for the second distribution.
        delta_values: ``left_values - right_values`` for each aligned state.
        metrics: ``HistogramCompareMetrics`` for the first two distributions.
        qubits: Selected marginal qubits, or ``None`` for full-register comparison.
        series_labels: Labels for all compared series.
        series_values: Values for all compared series, including any additional inputs.
        diagnostics: Non-fatal diagnostics emitted while normalizing or rendering.
        saved_path: Absolute saved path when ``output_path`` was used.
    """

    figure: Figure
    axes: Axes
    kind: HistogramKind
    state_labels: tuple[str, ...]
    left_values: tuple[float, ...]
    right_values: tuple[float, ...]
    delta_values: tuple[float, ...]
    metrics: HistogramCompareMetrics
    qubits: tuple[int, ...] | None
    series_labels: tuple[str, ...] = ()
    series_values: tuple[tuple[float, ...], ...] = ()
    diagnostics: tuple[RenderDiagnostic, ...] = ()
    saved_path: str | None = None
    _ipython_display_enabled: bool = field(default=True, repr=False, compare=False)
    _ipython_close_after_display: bool = field(default=False, repr=False, compare=False)

    def _ipython_display_(self) -> None:
        """Display the comparison figure in IPython without showing the dataclass repr."""

        if not self._ipython_display_enabled:
            return
        display_figures_in_ipython(
            (self.figure,),
            close_after_display=self._ipython_close_after_display,
        )

    def save(self, path: OutputPath) -> str:
        """Save the comparison figure to disk.

        Args:
            path: Destination image path accepted by Matplotlib.

        Returns:
            The absolute path written.
        """

        save_matplotlib_figure(self.figure, path)
        return _resolved_output_path(path)

    def to_dict(self) -> dict[str, object]:
        """Return comparison values and metadata without Matplotlib objects.

        Returns:
            A JSON-friendly dictionary with aligned values, metrics, labels, qubits,
            saved path, and diagnostics.
        """

        return {
            "kind": self.kind.value,
            "state_labels": self.state_labels,
            "left_values": self.left_values,
            "right_values": self.right_values,
            "delta_values": self.delta_values,
            "series_labels": self._resolved_series_labels(),
            "series_values": self._resolved_series_values(),
            "metrics": {
                "total_variation_distance": self.metrics.total_variation_distance,
                "max_absolute_delta": self.metrics.max_absolute_delta,
            },
            "qubits": self.qubits,
            "saved_path": self.saved_path,
            "diagnostics": diagnostics_to_dicts(self.diagnostics),
        }

    def to_csv(self, path: OutputPath) -> str:
        """Write aligned comparison rows to CSV.

        Args:
            path: Destination CSV path.

        Returns:
            The absolute path written.
        """

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            series_values = self._resolved_series_values()
            series_labels = self._resolved_series_labels()
            if len(series_values) <= 2:
                writer.writerow(("state", "left", "right", "delta"))
                writer.writerows(
                    zip(
                        self.state_labels,
                        self.left_values,
                        self.right_values,
                        self.delta_values,
                        strict=True,
                    )
                )
            else:
                writer.writerow(("state", *series_labels))
                writer.writerows(
                    (state_label, *(values[index] for values in series_values))
                    for index, state_label in enumerate(self.state_labels)
                )
        return _resolved_output_path(path)

    def _resolved_series_labels(self) -> tuple[str, ...]:
        return self.series_labels or ("Left", "Right")

    def _resolved_series_values(self) -> tuple[tuple[float, ...], ...]:
        return self.series_values or (self.left_values, self.right_values)


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
