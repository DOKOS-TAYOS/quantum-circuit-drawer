"""Rendering helpers for static histogram plots."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product
from math import cos, isfinite, radians
from typing import TYPE_CHECKING

from ..export.figures import save_matplotlib_figure
from ..style.theme import DrawTheme
from .histogram_models import (
    HistogramDrawStyle,
    HistogramKind,
    HistogramSort,
    HistogramStateLabelMode,
)
from .histogram_normalize import _flatten_state_label, _state_sort_key

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.container import BarContainer
    from matplotlib.figure import Figure

    from ..typing import OutputPath

_HISTOGRAM_VALUE_LABEL_MAX_FONT_SIZE = 8.0
_HISTOGRAM_VALUE_LABEL_MIN_FONT_SIZE = 3.0
_HISTOGRAM_VALUE_LABEL_WIDTH_FRACTION = 0.86
_HISTOGRAM_VALUE_LABEL_CHAR_WIDTH = 0.58
_HISTOGRAM_VALUE_LABEL_MAX_BIN_COUNT = 64
_HISTOGRAM_X_LABEL_ROTATION = 35.0
_HISTOGRAM_X_LABEL_MAX_FONT_SIZE = 9.0
_HISTOGRAM_X_LABEL_MIN_FONT_SIZE = 3.0
_HISTOGRAM_X_LABEL_WIDTH_FRACTION = 0.9
_HISTOGRAM_X_LABEL_CHAR_WIDTH = 0.94


def resolve_figure_and_axes(
    *,
    ax: Axes | None,
    figsize: tuple[float, float] | None,
) -> tuple[Figure, Axes]:
    """Resolve a caller-managed or freshly created Matplotlib figure."""

    from matplotlib.figure import SubFigure

    if ax is not None:
        parent_figure = ax.figure
        if isinstance(parent_figure, SubFigure):
            parent_figure = parent_figure.figure
        return parent_figure, ax

    import matplotlib.pyplot as plt

    return plt.subplots(figsize=figsize)


def draw_histogram_axes(
    *,
    figure: Figure,
    axes: Axes,
    state_labels: tuple[str, ...],
    display_labels: tuple[str, ...],
    values: tuple[float, ...],
    kind: HistogramKind,
    theme: DrawTheme,
    draw_style: HistogramDrawStyle,
    uniform_reference_value: float | None,
    thin_xlabels: bool,
    y_limits: tuple[float, float] | None = None,
) -> BarContainer:
    """Draw one histogram on an axes and return the resulting bars."""

    apply_histogram_theme(figure=figure, axes=axes, theme=theme)
    positions = tuple(range(len(state_labels)))
    bars = axes.bar(
        positions,
        values,
        color=bar_colors(values=values, kind=kind, theme=theme),
        edgecolor=theme.gate_edgecolor,
        linewidth=1.2,
        width=0.9,
    )
    apply_bar_style(
        bars=bars,
        values=values,
        draw_style=draw_style,
        theme=theme,
    )
    axes.set_xlabel("State")
    axes.set_ylabel("Counts" if kind is HistogramKind.COUNTS else "Quasi-probability")
    if kind is HistogramKind.QUASI:
        axes.axhline(0.0, color=reference_line_color(theme), linewidth=1.0, linestyle="--")
    if uniform_reference_value is not None:
        uniform_line = axes.axhline(
            uniform_reference_value,
            color=reference_line_color(theme),
            linewidth=1.2,
            linestyle=":",
        )
        uniform_line.set_gid("histogram-uniform-reference-line")
    axes.set_xticks(list(positions))
    if positions:
        axes.set_xlim(-0.5, len(positions) - 0.5)
    if y_limits is None:
        y_limits = resolved_histogram_y_limits(
            values,
            kind=kind,
            uniform_reference_value=uniform_reference_value,
        )
    axes.set_ylim(*y_limits)
    axes.margins(x=0.02)
    axes.set_xticklabels(tick_labels_for_states(display_labels, thin=thin_xlabels))
    fit_histogram_x_tick_labels(axes, bin_count=len(positions))
    if should_draw_histogram_value_labels(bin_count=len(positions)):
        draw_histogram_value_labels(axes, bars=bars, values=values, kind=kind, theme=theme)
    return bars


def order_histogram_values(
    values_by_state: Mapping[str, float],
    *,
    sort: HistogramSort,
    top_k: int | None,
) -> dict[str, float]:
    """Order histogram values deterministically according to the requested mode."""

    items = list(values_by_state.items())
    if sort is HistogramSort.STATE:
        items.sort(key=lambda item: _state_sort_key(item[0]))
    elif sort is HistogramSort.STATE_DESC:
        items.sort(key=lambda item: _state_sort_key(item[0]), reverse=True)
    elif sort is HistogramSort.VALUE_DESC:
        items.sort(key=lambda item: (-item[1], _state_sort_key(item[0])))
    else:
        items.sort(key=lambda item: (item[1], _state_sort_key(item[0])))
    if top_k is not None:
        items = items[:top_k]
    return dict(items)


def display_labels_for_states(
    state_labels: tuple[str, ...],
    *,
    mode: HistogramStateLabelMode,
) -> tuple[str, ...]:
    """Convert stored state labels into the requested display format."""

    return tuple(display_state_label(label, mode=mode) for label in state_labels)


def display_state_label(
    state_label: str,
    *,
    mode: HistogramStateLabelMode,
) -> str:
    """Render one state label in binary or decimal form."""

    if mode is HistogramStateLabelMode.BINARY:
        return state_label
    return decimal_state_label(state_label)


def apply_bit_order(
    values_by_state: Mapping[str, float],
    *,
    reverse_bits: bool,
) -> dict[str, float]:
    """Return values keyed by the requested bit order."""

    if not reverse_bits:
        return dict(values_by_state)

    reordered_values: dict[str, float] = {}
    for state_label, value in values_by_state.items():
        reordered_label = reverse_state_label_bits(state_label)
        reordered_values[reordered_label] = reordered_values.get(reordered_label, 0.0) + value
    return reordered_values


def reverse_state_label_bits(state_label: str) -> str:
    """Reverse each binary register group in one state label."""

    groups = state_label.split(" ") if " " in state_label else [state_label]
    return " ".join(group[::-1] for group in groups)


def decimal_state_label(state_label: str) -> str:
    """Convert one binary or grouped-binary label to decimal text."""

    groups = state_label.split(" ") if " " in state_label else [state_label]
    return " ".join(str(int(group, 2)) for group in groups)


def tick_labels_for_states(
    state_labels: tuple[str, ...],
    *,
    thin: bool,
) -> tuple[str, ...]:
    """Thin tick labels on dense histograms to keep them readable."""

    if not thin or len(state_labels) <= 16:
        return state_labels
    step = max(1, len(state_labels) // 12)
    return tuple(label if index % step == 0 else "" for index, label in enumerate(state_labels))


def draw_histogram_value_labels(
    axes: Axes,
    *,
    bars: BarContainer,
    values: tuple[float, ...],
    kind: HistogramKind,
    theme: DrawTheme,
) -> None:
    """Draw compact numeric labels above bars while fitting each bin width."""

    for bar, value in zip(bars, values, strict=True):
        label = format_histogram_value(value, kind)
        fontsize = _fit_text_font_size_for_data_width(
            axes,
            text=label,
            data_width=float(bar.get_width()) * _HISTOGRAM_VALUE_LABEL_WIDTH_FRACTION,
            max_font_size=_HISTOGRAM_VALUE_LABEL_MAX_FONT_SIZE,
            min_font_size=_HISTOGRAM_VALUE_LABEL_MIN_FONT_SIZE,
            char_width_factor=_HISTOGRAM_VALUE_LABEL_CHAR_WIDTH,
        )
        bar_top = float(bar.get_y() + bar.get_height())
        y_padding = _histogram_value_label_y_padding(axes)
        axes.text(
            float(bar.get_x() + (bar.get_width() / 2.0)),
            bar_top + (y_padding if value >= 0.0 else -y_padding),
            label,
            ha="center",
            va="bottom" if value >= 0.0 else "top",
            fontsize=fontsize,
            color=theme.text_color,
            clip_on=False,
        )


def should_draw_histogram_value_labels(*, bin_count: int) -> bool:
    """Return whether per-bin value labels remain useful and affordable."""

    return bin_count <= _HISTOGRAM_VALUE_LABEL_MAX_BIN_COUNT


def fit_histogram_x_tick_labels(axes: Axes, *, bin_count: int) -> None:
    """Rotate and shrink x tick labels so dense state labels stay separated."""

    if bin_count <= 0:
        return

    tick_labels = tuple(label for label in axes.get_xticklabels() if label.get_text())
    if not tick_labels:
        return

    font_size = _fit_text_font_size_for_data_width(
        axes,
        text=max((label.get_text() for label in tick_labels), key=len),
        data_width=_HISTOGRAM_X_LABEL_WIDTH_FRACTION,
        max_font_size=_HISTOGRAM_X_LABEL_MAX_FONT_SIZE,
        min_font_size=_HISTOGRAM_X_LABEL_MIN_FONT_SIZE,
        char_width_factor=(
            _HISTOGRAM_X_LABEL_CHAR_WIDTH / max(0.35, cos(radians(_HISTOGRAM_X_LABEL_ROTATION)))
        ),
    )
    for label in tick_labels:
        label.set_rotation(_HISTOGRAM_X_LABEL_ROTATION)
        label.set_rotation_mode("anchor")
        label.set_horizontalalignment("right")
        label.set_fontsize(font_size)


def _fit_text_font_size_for_data_width(
    axes: Axes,
    *,
    text: str,
    data_width: float,
    max_font_size: float,
    min_font_size: float,
    char_width_factor: float,
) -> float:
    if not text:
        return min(max_font_size, max(min_font_size, max_font_size))

    available_pixels = _data_width_to_pixels(axes, data_width)
    if available_pixels <= 0.0:
        return min_font_size
    fitted_size = available_pixels / max(1.0, len(text) * char_width_factor)
    return min(max_font_size, max(min_font_size, fitted_size))


def _data_width_to_pixels(axes: Axes, data_width: float) -> float:
    left_pixel = axes.transData.transform((0.0, 0.0))[0]
    right_pixel = axes.transData.transform((data_width, 0.0))[0]
    return abs(float(right_pixel - left_pixel))


def _histogram_value_label_y_padding(axes: Axes) -> float:
    y_min, y_max = axes.get_ylim()
    return max(1e-9, abs(float(y_max - y_min)) * 0.012)


def resolved_histogram_bit_width(
    *,
    bit_width: int,
    qubits: tuple[int, ...] | None,
) -> int:
    """Resolve the effective bit width after an optional marginal selection."""

    if qubits is None:
        return bit_width
    return len(qubits)


def uniform_reference_value(
    values_by_state: Mapping[str, float],
    *,
    kind: HistogramKind,
    bit_width: int,
    show_uniform_reference: bool,
) -> float | None:
    """Return the uniform reference level when requested by the caller."""

    if not show_uniform_reference:
        return None
    domain_size = 2**bit_width
    if kind is HistogramKind.COUNTS:
        return sum(values_by_state.values()) / float(domain_size)
    return 1.0 / float(domain_size)


def resolved_histogram_y_limits(
    values: tuple[float, ...],
    *,
    kind: HistogramKind,
    uniform_reference_value: float | None,
) -> tuple[float, float]:
    """Compute stable Y-axis limits for counts and quasi histograms."""

    if kind is HistogramKind.COUNTS:
        upper_bound = max((float(value) for value in values), default=0.0)
        if uniform_reference_value is not None:
            upper_bound = max(upper_bound, float(uniform_reference_value))
        if upper_bound <= 0.0:
            return 0.0, 1.0
        return 0.0, upper_bound * 1.05

    lower_bound = min((float(value) for value in values), default=0.0)
    upper_bound = max((float(value) for value in values), default=0.0)
    if uniform_reference_value is not None and float(uniform_reference_value) >= 0.0:
        upper_bound = max(upper_bound, float(uniform_reference_value))
    if lower_bound >= 0.0:
        if upper_bound <= 0.0:
            return 0.0, 1.0
        return 0.0, upper_bound * 1.05
    lower_bound = min(lower_bound, 0.0)
    upper_bound = max(upper_bound, 0.0)
    if uniform_reference_value is not None:
        lower_bound = min(lower_bound, float(uniform_reference_value))
        upper_bound = max(upper_bound, float(uniform_reference_value))
    if lower_bound == upper_bound:
        if lower_bound == 0.0:
            return -1.0, 1.0
        padding = abs(lower_bound) * 0.05
        return lower_bound - padding, upper_bound + padding
    padding = (upper_bound - lower_bound) * 0.05
    return lower_bound - padding, upper_bound + padding


def apply_histogram_theme(
    *,
    figure: Figure,
    axes: Axes,
    theme: DrawTheme,
) -> None:
    """Apply the standard histogram theme to a Matplotlib figure and axes."""

    figure.patch.set_facecolor(theme.figure_facecolor)
    axes.set_facecolor(theme.axes_facecolor)
    axes.tick_params(axis="x", colors=theme.text_color)
    axes.tick_params(axis="y", colors=theme.text_color)
    axes.xaxis.label.set_color(theme.text_color)
    axes.yaxis.label.set_color(theme.text_color)
    for spine in axes.spines.values():
        spine.set_color(theme.ui_surface_edgecolor or theme.gate_edgecolor)
    axes.grid(
        axis="y",
        color=theme.ui_surface_edgecolor or theme.barrier_color,
        linewidth=0.8,
        linestyle="--",
        alpha=0.35,
    )
    axes.set_axisbelow(True)


def apply_bar_style(
    *,
    bars: BarContainer,
    values: tuple[float, ...],
    draw_style: HistogramDrawStyle,
    theme: DrawTheme,
) -> None:
    """Apply the requested bar appearance without changing semantics."""

    del theme
    if draw_style is HistogramDrawStyle.SOLID:
        for bar in bars:
            bar.set_alpha(0.95)
        return
    if draw_style is HistogramDrawStyle.SOFT:
        for bar in bars:
            bar.set_alpha(0.55)
            bar.set_linewidth(1.0)
        return
    for bar, value in zip(bars, values, strict=True):
        bar.set_fill(False)
        bar.set_facecolor("none")
        bar.set_alpha(1.0)
        bar.set_linewidth(1.8)
        if value < 0.0:
            bar.set_edgecolor("#dc2626")


def bar_colors(
    *,
    values: tuple[float, ...],
    kind: HistogramKind,
    theme: DrawTheme,
) -> tuple[str, ...]:
    """Resolve bar colors for counts and quasi-probability histograms."""

    if kind is HistogramKind.COUNTS:
        return tuple(theme.accent_color for _ in values)
    return tuple(
        theme.accent_color if value >= 0.0 else negative_bar_color(theme) for value in values
    )


def reference_line_color(theme: DrawTheme) -> str:
    """Resolve the color of the reference baseline overlays."""

    return theme.ui_secondary_text_color or theme.barrier_color


def format_histogram_value(value: float, kind: HistogramKind) -> str:
    """Return a compact user-facing histogram number string."""

    del kind
    numeric_value = float(value)
    if numeric_value == 0.0:
        return "0"
    if not isfinite(numeric_value):
        return str(numeric_value)
    return _normalize_histogram_scientific_notation(f"{numeric_value:.4g}")


def _normalize_histogram_scientific_notation(text: str) -> str:
    mantissa, separator, exponent = text.partition("e")
    if not separator:
        return text
    exponent_sign = "-" if exponent.startswith("-") else ""
    exponent_digits = exponent.lstrip("+-").lstrip("0") or "0"
    return f"{mantissa}e{exponent_sign}{exponent_digits}"


def negative_bar_color(theme: DrawTheme) -> str:
    """Resolve the negative-value color for quasi histograms."""

    if theme.name == "paper":
        return "#b91c1c"
    if theme.name == "accessible":
        return "#D55E00"
    if theme.name == "light":
        return "#dc2626"
    return "#f87171"


def comparison_secondary_color(theme: DrawTheme) -> str:
    """Resolve the secondary comparison color for overlay plots."""

    if theme.name == "paper":
        return "#2563eb"
    if theme.name == "accessible":
        return "#D55E00"
    if theme.name == "light":
        return "#1d4ed8"
    return "#38bdf8"


def apply_joint_marginal(
    values_by_state: Mapping[str, float],
    *,
    qubits: tuple[int, ...] | None,
    bit_width: int,
) -> dict[str, float]:
    """Collapse the full distribution onto the requested qubit subset."""

    if qubits is None:
        return dict(values_by_state)
    if any(qubit >= bit_width for qubit in qubits):
        raise ValueError("qubits must reference indices within the available state width")

    marginal_labels = basis_state_labels(len(qubits))
    marginal = {label: 0.0 for label in marginal_labels}
    for state_label, value in values_by_state.items():
        flattened_state_label = _flatten_state_label(state_label)
        selected_label = "".join(flattened_state_label[-(qubit + 1)] for qubit in qubits)
        marginal[selected_label] += value
    return marginal


def basis_state_labels(bit_width: int) -> tuple[str, ...]:
    """Return every basis label for the requested bit width."""

    if bit_width == 0:
        return ("",)
    return tuple("".join(bits) for bits in product("01", repeat=bit_width))


def save_histogram_if_requested(
    figure: Figure,
    *,
    output_path: OutputPath | None,
) -> None:
    """Save the histogram if the caller requested an output path."""

    save_matplotlib_figure(
        figure,
        output_path,
        error_message_prefix="failed to save histogram to",
    )


__all__ = [
    "apply_joint_marginal",
    "apply_bit_order",
    "display_labels_for_states",
    "display_state_label",
    "draw_histogram_axes",
    "order_histogram_values",
    "reverse_state_label_bits",
    "resolve_figure_and_axes",
    "resolved_histogram_bit_width",
    "resolved_histogram_y_limits",
    "save_histogram_if_requested",
    "uniform_reference_value",
]
