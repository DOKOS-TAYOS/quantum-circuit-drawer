"""Public histogram plotting API for counts and quasi-probability data."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import product
from typing import TYPE_CHECKING, Protocol, SupportsFloat, runtime_checkable

from ..drawing.runtime import detect_runtime_context
from ..export.figures import save_matplotlib_figure
from ..style.theme import resolve_theme

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.container import BarContainer
    from matplotlib.figure import Figure

    from ..style.theme import DrawTheme
    from ..typing import OutputPath


@runtime_checkable
class _SupportsLenAndGetItem(Protocol):
    """Minimal protocol for objects that behave like a sequence."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> object: ...


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
    theme: DrawTheme | str | None = None
    draw_style: HistogramDrawStyle = HistogramDrawStyle.SOLID
    state_label_mode: HistogramStateLabelMode = HistogramStateLabelMode.BINARY
    hover: bool = True
    show_uniform_reference: bool = False
    show: bool = True
    output_path: OutputPath | None = None
    figsize: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", self._normalize_kind(self.kind))
        object.__setattr__(self, "mode", self._normalize_mode(self.mode))
        object.__setattr__(self, "sort", self._normalize_sort(self.sort))
        object.__setattr__(self, "theme", resolve_theme(self.theme))
        object.__setattr__(self, "draw_style", self._normalize_draw_style(self.draw_style))
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


@dataclass(frozen=True, slots=True)
class _NormalizedHistogramData:
    values_by_state: dict[str, float]
    bit_width: int
    kind: HistogramKind


def _is_positive_dimension(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and float(value) > 0.0


def _is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_positive_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def plot_histogram(
    data: object,
    *,
    config: HistogramConfig | None = None,
    ax: Axes | None = None,
) -> HistogramResult:
    """Plot a histogram from counts or quasi-probability data."""

    resolved_config = config or HistogramConfig()
    if ax is not None and resolved_config.figsize is not None:
        raise ValueError("figsize cannot be used with ax")
    runtime_context = detect_runtime_context()
    resolved_mode = _resolve_histogram_mode(
        resolved_config.mode,
        runtime_context=runtime_context,
        ax=ax,
    )
    if (
        resolved_mode is HistogramMode.INTERACTIVE
        and runtime_context.is_notebook
        and not runtime_context.notebook_backend_active
    ):
        raise ValueError(
            "mode='interactive' requires a notebook widget backend such as nbagg, ipympl, or widget"
        )
    if ax is not None and resolved_mode is HistogramMode.INTERACTIVE:
        raise ValueError(
            "mode='interactive' requires a Matplotlib-managed figure and cannot be used with ax"
        )

    normalized = _normalize_histogram_data(
        data,
        requested_kind=resolved_config.kind,
        result_index=resolved_config.result_index,
        data_key=resolved_config.data_key,
    )
    values_by_state = _apply_joint_marginal(
        normalized.values_by_state,
        qubits=resolved_config.qubits,
        bit_width=normalized.bit_width,
    )
    resolved_bit_width = _resolved_histogram_bit_width(
        bit_width=normalized.bit_width,
        qubits=resolved_config.qubits,
    )
    theme = resolve_theme(resolved_config.theme)
    uniform_reference_value = _uniform_reference_value(
        values_by_state,
        kind=normalized.kind,
        bit_width=resolved_bit_width,
        show_uniform_reference=resolved_config.show_uniform_reference,
    )
    ordered_values_by_state = _order_histogram_values(
        values_by_state,
        sort=resolved_config.sort,
        top_k=resolved_config.top_k,
    )
    state_labels = tuple(ordered_values_by_state)
    values = tuple(float(value) for value in ordered_values_by_state.values())
    figure, axes = _resolve_figure_and_axes(ax=ax, figsize=resolved_config.figsize)

    if resolved_mode is HistogramMode.INTERACTIVE:
        from .histogram_interactive import attach_histogram_interactivity

        attach_histogram_interactivity(
            figure=figure,
            axes=axes,
            values_by_state=normalized.values_by_state,
            bit_width=normalized.bit_width,
            kind=normalized.kind,
            config=resolved_config,
        )
    else:
        _draw_histogram_axes(
            figure=figure,
            axes=axes,
            state_labels=state_labels,
            display_labels=_display_labels_for_states(
                state_labels,
                mode=resolved_config.state_label_mode,
            ),
            values=values,
            kind=normalized.kind,
            theme=theme,
            draw_style=resolved_config.draw_style,
            uniform_reference_value=uniform_reference_value,
            thin_xlabels=False,
        )
        _save_histogram_if_requested(figure, output_path=resolved_config.output_path)
    if resolved_config.show:
        from ..renderers._render_support import show_figure_if_supported

        show_figure_if_supported(figure, show=True)

    return HistogramResult(
        figure=figure,
        axes=axes,
        kind=normalized.kind,
        state_labels=state_labels,
        values=values,
        qubits=resolved_config.qubits,
    )


def _resolve_histogram_mode(
    mode: HistogramMode,
    *,
    runtime_context: object,
    ax: Axes | None,
) -> HistogramMode:
    if mode is not HistogramMode.AUTO:
        return mode
    if ax is not None:
        return HistogramMode.STATIC
    if getattr(runtime_context, "is_notebook", False):
        if getattr(runtime_context, "notebook_backend_active", False):
            return HistogramMode.INTERACTIVE
        return HistogramMode.STATIC
    return HistogramMode.INTERACTIVE


def _normalize_histogram_data(
    data: object,
    *,
    requested_kind: HistogramKind,
    result_index: int,
    data_key: str | None,
) -> _NormalizedHistogramData:
    raw_mapping, bit_width, source_kind = _extract_raw_distribution(
        data,
        result_index=result_index,
        data_key=data_key,
    )
    values_by_state, resolved_bit_width = _normalize_distribution_mapping(
        raw_mapping,
        bit_width=bit_width,
    )
    resolved_kind = _resolve_kind(
        values_by_state,
        requested_kind=requested_kind,
        source_kind=source_kind,
    )
    return _NormalizedHistogramData(
        values_by_state=values_by_state,
        bit_width=resolved_bit_width,
        kind=resolved_kind,
    )


def _extract_raw_distribution(
    data: object,
    *,
    result_index: int,
    data_key: str | None,
) -> tuple[Mapping[object, object], int | None, HistogramKind | None]:
    if isinstance(data, Mapping):
        return _mapping_from_distribution_object(data)

    if _is_bit_array(data):
        return _mapping_from_bit_array(data), _bit_width_from_bit_array(data), HistogramKind.COUNTS

    items_mapping = _items_mapping_from_object(data)
    if items_mapping is not None:
        bit_array_fields = {
            key: value for key, value in items_mapping.items() if _is_bit_array(value)
        }
        if bit_array_fields:
            selected_field = _select_data_bin_field_from_fields(items_mapping, data_key=data_key)
            return (
                _mapping_from_bit_array(selected_field),
                _bit_width_from_bit_array(selected_field),
                HistogramKind.COUNTS,
            )
        return _mapping_from_distribution_object(items_mapping)

    cirq_distribution = _extract_cirq_measurement_distribution(data)
    if cirq_distribution is not None:
        return cirq_distribution

    myqlm_distribution = _extract_myqlm_raw_data_distribution(data)
    if myqlm_distribution is not None:
        return myqlm_distribution

    array_like_distribution = _extract_array_like_distribution(data)
    if array_like_distribution is not None:
        return array_like_distribution

    if _is_data_bin_like(data):
        selected_field = _select_data_bin_field(data, data_key=data_key)
        return (
            _mapping_from_bit_array(selected_field),
            _bit_width_from_bit_array(selected_field),
            (HistogramKind.COUNTS),
        )

    if hasattr(data, "data") and hasattr(data, "metadata"):
        return _extract_raw_distribution(data.data, result_index=result_index, data_key=data_key)

    if hasattr(data, "quasi_dists") and hasattr(data, "metadata"):
        quasi_dists = data.quasi_dists
        selected = _select_result_item(
            quasi_dists,
            result_index=result_index,
            label="SamplerResult.quasi_dists",
        )
        if not isinstance(selected, Mapping):
            raise TypeError(
                "SamplerResult.quasi_dists entries must be mappings from states to probabilities"
            )
        return _mapping_from_distribution_object(selected)

    if (
        hasattr(data, "__getitem__")
        and hasattr(data, "__len__")
        and not isinstance(data, str | bytes)
    ):
        try:
            selected = _select_result_item(data, result_index=result_index, label="result sequence")
        except TypeError:
            pass
        else:
            return _extract_raw_distribution(selected, result_index=0, data_key=data_key)

    raise TypeError(f"plot_histogram does not support objects of type {type(data).__name__!r}")


def _mapping_from_distribution_object(
    data: Mapping[object, object],
) -> tuple[Mapping[object, object], int | None, HistogramKind | None]:
    binary_probabilities = getattr(data, "binary_probabilities", None)
    if callable(binary_probabilities):
        mapping = binary_probabilities()
        return mapping, _infer_mapping_bit_width(mapping), HistogramKind.QUASI
    int_outcomes = getattr(data, "int_outcomes", None)
    if callable(int_outcomes):
        mapping = int_outcomes()
        return mapping, _infer_mapping_bit_width(mapping), HistogramKind.COUNTS
    return data, None, None


def _items_mapping_from_object(data: object) -> dict[object, object] | None:
    items_method = getattr(data, "items", None)
    if not callable(items_method):
        return None
    try:
        return dict(items_method())
    except (TypeError, ValueError):
        return None


def _extract_cirq_measurement_distribution(
    data: object,
) -> tuple[Mapping[object, object], int | None, HistogramKind] | None:
    measurements = getattr(data, "measurements", None)
    if not isinstance(measurements, Mapping) or not measurements:
        return None

    rows_by_register: list[tuple[str, tuple[tuple[int, ...], ...]]] = []
    repetition_count: int | None = None
    total_width = 0
    for register_name, raw_rows in measurements.items():
        rows = _coerce_sample_rows(raw_rows)
        if rows is None:
            return None
        if repetition_count is None:
            repetition_count = len(rows)
        elif len(rows) != repetition_count:
            raise ValueError("measurement registers must contain the same number of repetitions")
        register_width = len(rows[0]) if rows else 0
        total_width += register_width
        rows_by_register.append((str(register_name), rows))

    if repetition_count is None or repetition_count == 0:
        return {"0": 0.0}, 1, HistogramKind.COUNTS

    counts: dict[str, float] = {}
    for repetition_index in range(repetition_count):
        groups = [
            "".join(str(bit) for bit in rows[repetition_index]) for _, rows in rows_by_register
        ]
        state_label = " ".join(group for group in groups if group)
        counts[state_label or "0"] = counts.get(state_label or "0", 0.0) + 1.0

    return counts, max(total_width, 1), HistogramKind.COUNTS


def _extract_myqlm_raw_data_distribution(
    data: object,
) -> tuple[Mapping[object, object], int | None, HistogramKind | None] | None:
    raw_data = getattr(data, "raw_data", None)
    if raw_data is None:
        return None

    try:
        samples = tuple(raw_data)
    except TypeError:
        return None
    if not samples:
        return {"0": 0.0}, 1, HistogramKind.COUNTS

    mapping: dict[object, float] = {}
    for sample in samples:
        state_key = _extract_state_like_key(getattr(sample, "state", None))
        probability = getattr(sample, "probability", None)
        if state_key is None or not isinstance(probability, SupportsFloat):
            return None
        mapping[state_key] = mapping.get(state_key, 0.0) + float(probability)

    bit_width = getattr(data, "nbqbits", None)
    resolved_bit_width = bit_width if isinstance(bit_width, int) and bit_width >= 0 else None
    return mapping, resolved_bit_width, None


def _extract_state_like_key(state: object) -> int | str | None:
    if isinstance(state, int | str) and not isinstance(state, bool):
        return state

    for attribute_name in ("bitstring", "bits", "binary", "value", "int", "index", "lsb_int"):
        attribute_value = getattr(state, attribute_name, None)
        if isinstance(attribute_value, int | str) and not isinstance(attribute_value, bool):
            return attribute_value

    if state is None:
        return None
    try:
        integer_value = int(state)
    except (TypeError, ValueError):
        return None
    return integer_value


def _extract_array_like_distribution(
    data: object,
) -> tuple[Mapping[object, object], int | None, HistogramKind] | None:
    python_data = _to_python_sequence(data)
    if python_data is None:
        return None

    if _looks_like_probability_vector(python_data):
        return (
            {index: float(value) for index, value in enumerate(python_data)},
            _bit_width_from_vector_length(len(python_data)),
            HistogramKind.QUASI,
        )

    if _looks_like_sample_vector(python_data):
        return (
            _mapping_from_sample_rows((int(bit),) for bit in python_data),
            1,
            HistogramKind.COUNTS,
        )

    sample_rows = _coerce_sample_rows(python_data)
    if sample_rows is not None:
        return (
            _mapping_from_sample_rows(sample_rows),
            max((len(sample_rows[0]) if sample_rows else 0), 1),
            HistogramKind.COUNTS,
        )
    return None


def _to_python_sequence(data: object) -> Sequence[object] | None:
    if isinstance(data, str | bytes | Mapping):
        return None
    if isinstance(data, Sequence):
        return data
    tolist_method = getattr(data, "tolist", None)
    if callable(tolist_method):
        try:
            converted = tolist_method()
        except TypeError:
            return None
        if isinstance(converted, Sequence) and not isinstance(converted, str | bytes):
            return converted
    return None


def _looks_like_probability_vector(data: Sequence[object]) -> bool:
    if not data or not _bit_width_for_sequence_length(len(data)):
        return False
    if any(isinstance(value, Sequence) and not isinstance(value, str | bytes) for value in data):
        return False
    if any(not isinstance(value, SupportsFloat) for value in data):
        return False

    numeric_values = tuple(float(value) for value in data)
    if any(value < 0.0 for value in numeric_values):
        return True
    if any(not value.is_integer() for value in numeric_values):
        return True
    return abs(sum(numeric_values) - 1.0) <= 1e-9


def _looks_like_sample_vector(data: Sequence[object]) -> bool:
    return bool(data) and all(_is_bit_like(value) for value in data)


def _coerce_sample_rows(data: object) -> tuple[tuple[int, ...], ...] | None:
    python_rows = _to_python_sequence(data)
    if python_rows is None or not python_rows:
        return None

    rows: list[tuple[int, ...]] = []
    row_width: int | None = None
    for raw_row in python_rows:
        row_values = _to_python_sequence(raw_row)
        if (
            row_values is None
            or not row_values
            or not all(_is_bit_like(value) for value in row_values)
        ):
            return None
        normalized_row = tuple(int(value) for value in row_values)
        if row_width is None:
            row_width = len(normalized_row)
        elif len(normalized_row) != row_width:
            raise ValueError("sample rows must all have the same width")
        rows.append(normalized_row)
    return tuple(rows)


def _mapping_from_sample_rows(sample_rows: Sequence[Sequence[int]]) -> dict[str, float]:
    counts: dict[str, float] = {}
    for row in sample_rows:
        state_label = "".join(str(bit) for bit in row)
        counts[state_label] = counts.get(state_label, 0.0) + 1.0
    return counts


def _is_bit_like(value: object) -> bool:
    return isinstance(value, bool) or (
        isinstance(value, int) and not isinstance(value, bool) and value in {0, 1}
    )


def _bit_width_from_vector_length(length: int) -> int:
    bit_width = _bit_width_for_sequence_length(length)
    if bit_width is None:
        raise ValueError("probability vectors must have a power-of-two length")
    return max(bit_width, 1)


def _bit_width_for_sequence_length(length: int) -> int | None:
    if length <= 0 or length & (length - 1):
        return None
    return max(length.bit_length() - 1, 1)


def _normalize_distribution_mapping(
    raw_mapping: Mapping[object, object],
    *,
    bit_width: int | None,
) -> tuple[dict[str, float], int]:
    entries: list[tuple[object, float]] = []
    for key, value in raw_mapping.items():
        if not isinstance(value, SupportsFloat):
            raise TypeError("histogram state values must be numeric")
        entries.append((key, float(value)))
    if not entries:
        return {"0": 0.0}, 1

    resolved_bit_width = max(bit_width or 0, _infer_entries_bit_width(entries), 1)
    normalized: dict[str, float] = {}
    for raw_key, value in entries:
        state_label = _normalize_state_label(raw_key, bit_width=resolved_bit_width)
        normalized[state_label] = value

    ordered_labels = sorted(normalized, key=_state_sort_key)
    return {label: normalized[label] for label in ordered_labels}, resolved_bit_width


def _normalize_state_label(key: object, *, bit_width: int) -> str:
    if isinstance(key, int):
        if key < 0:
            raise ValueError("histogram state keys must be non-negative")
        return format(key, f"0{bit_width}b")
    if isinstance(key, str):
        return _normalize_string_state_label(key, bit_width=bit_width)
    raise TypeError("histogram state keys must be strings or integers")


def _normalize_string_state_label(key: str, *, bit_width: int) -> str:
    stripped_key = key.strip()
    if not stripped_key:
        raise ValueError("histogram state keys must not be empty")

    flattened_state = _flatten_state_label(stripped_key)
    if flattened_state.startswith(("0x", "0X")):
        return format(int(flattened_state, 16), f"0{bit_width}b")
    if any(bit not in {"0", "1"} for bit in flattened_state):
        raise ValueError("histogram state keys must be binary strings")
    if " " not in stripped_key:
        return flattened_state.zfill(bit_width)

    groups = _normalized_binary_state_groups(stripped_key)
    total_group_width = sum(len(group) for group in groups)
    padded_state = flattened_state.zfill(bit_width)
    widths = (
        len(groups[0]) + (bit_width - total_group_width),
        *[len(group) for group in groups[1:]],
    )
    slices: list[str] = []
    cursor = 0
    for width in widths:
        slices.append(padded_state[cursor : cursor + width])
        cursor += width
    return " ".join(slices)


def _normalized_binary_state_groups(state_label: str) -> tuple[str, ...]:
    groups = tuple(group.strip() for group in state_label.split(" ") if group.strip())
    if not groups:
        raise ValueError("histogram state keys must not be empty")
    if any(any(bit not in {"0", "1"} for bit in group) for group in groups):
        raise ValueError("histogram state keys must be binary strings")
    return groups


def _flatten_state_label(state_label: str) -> str:
    return state_label.replace(" ", "")


def _state_sort_key(state_label: str) -> int:
    return int(_flatten_state_label(state_label), 2)


def _display_labels_for_states(
    state_labels: tuple[str, ...],
    *,
    mode: HistogramStateLabelMode,
) -> tuple[str, ...]:
    return tuple(_display_state_label(label, mode=mode) for label in state_labels)


def _display_state_label(
    state_label: str,
    *,
    mode: HistogramStateLabelMode,
) -> str:
    if mode is HistogramStateLabelMode.BINARY:
        return state_label
    return _decimal_state_label(state_label)


def _decimal_state_label(state_label: str) -> str:
    groups = state_label.split(" ") if " " in state_label else [state_label]
    return " ".join(str(int(group, 2)) for group in groups)


def _resolve_kind(
    values_by_state: Mapping[str, float],
    *,
    requested_kind: HistogramKind,
    source_kind: HistogramKind | None = None,
) -> HistogramKind:
    if requested_kind is HistogramKind.COUNTS:
        if any(value < 0.0 or not float(value).is_integer() for value in values_by_state.values()):
            raise ValueError("counts histograms require non-negative integer values")
        return HistogramKind.COUNTS
    if requested_kind is HistogramKind.QUASI:
        return HistogramKind.QUASI
    if source_kind is not None:
        return source_kind
    if all(value >= 0.0 and float(value).is_integer() for value in values_by_state.values()):
        return HistogramKind.COUNTS
    return HistogramKind.QUASI


def _resolve_figure_and_axes(
    *,
    ax: Axes | None,
    figsize: tuple[float, float] | None,
) -> tuple[Figure, Axes]:
    from matplotlib.figure import SubFigure

    if ax is not None:
        parent_figure = ax.figure
        if isinstance(parent_figure, SubFigure):
            parent_figure = parent_figure.figure
        return parent_figure, ax

    import matplotlib.pyplot as plt

    return plt.subplots(figsize=figsize)


def _draw_histogram_axes(
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
    _apply_histogram_theme(figure=figure, axes=axes, theme=theme)
    positions = tuple(range(len(state_labels)))
    bars = axes.bar(
        positions,
        values,
        color=_bar_colors(values=values, kind=kind, theme=theme),
        edgecolor=theme.gate_edgecolor,
        linewidth=1.2,
        width=0.9,
    )
    _apply_bar_style(
        bars=bars,
        values=values,
        draw_style=draw_style,
        theme=theme,
    )
    axes.set_xlabel("State")
    axes.set_ylabel("Counts" if kind is HistogramKind.COUNTS else "Quasi-probability")
    if kind is HistogramKind.QUASI:
        axes.axhline(0.0, color=_reference_line_color(theme), linewidth=1.0, linestyle="--")
    if uniform_reference_value is not None:
        axes.axhline(
            uniform_reference_value,
            color=_reference_line_color(theme),
            linewidth=1.2,
            linestyle=":",
        )
    axes.set_xticks(list(positions))
    axes.set_xticklabels(_tick_labels_for_states(display_labels, thin=thin_xlabels))
    if positions:
        axes.set_xlim(-0.5, len(positions) - 0.5)
    if y_limits is None:
        y_limits = _resolved_histogram_y_limits(
            values,
            kind=kind,
            uniform_reference_value=uniform_reference_value,
        )
    axes.set_ylim(*y_limits)
    axes.margins(x=0.02)
    return bars


def _bar_colors(
    *,
    values: tuple[float, ...],
    kind: HistogramKind,
    theme: DrawTheme,
) -> tuple[str, ...]:
    if kind is HistogramKind.COUNTS:
        return tuple(theme.accent_color for _ in values)
    return tuple(
        theme.accent_color if value >= 0.0 else _negative_bar_color(theme) for value in values
    )


def _order_histogram_values(
    values_by_state: Mapping[str, float],
    *,
    sort: HistogramSort,
    top_k: int | None,
) -> dict[str, float]:
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


def _tick_labels_for_states(
    state_labels: tuple[str, ...],
    *,
    thin: bool,
) -> tuple[str, ...]:
    if not thin or len(state_labels) <= 16:
        return state_labels
    step = max(1, len(state_labels) // 12)
    return tuple(label if index % step == 0 else "" for index, label in enumerate(state_labels))


def _resolved_histogram_bit_width(
    *,
    bit_width: int,
    qubits: tuple[int, ...] | None,
) -> int:
    if qubits is None:
        return bit_width
    return len(qubits)


def _uniform_reference_value(
    values_by_state: Mapping[str, float],
    *,
    kind: HistogramKind,
    bit_width: int,
    show_uniform_reference: bool,
) -> float | None:
    if not show_uniform_reference:
        return None
    domain_size = 2**bit_width
    if kind is HistogramKind.COUNTS:
        return sum(values_by_state.values()) / float(domain_size)
    return 1.0 / float(domain_size)


def _resolved_histogram_y_limits(
    values: tuple[float, ...],
    *,
    kind: HistogramKind,
    uniform_reference_value: float | None,
) -> tuple[float, float]:
    if kind is HistogramKind.COUNTS:
        upper_bound = max((float(value) for value in values), default=0.0)
        if uniform_reference_value is not None:
            upper_bound = max(upper_bound, float(uniform_reference_value))
        if upper_bound <= 0.0:
            return 0.0, 1.0
        return 0.0, upper_bound * 1.05

    lower_bound = min((float(value) for value in values), default=0.0)
    upper_bound = max((float(value) for value in values), default=0.0)
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


def _apply_histogram_theme(
    *,
    figure: Figure,
    axes: Axes,
    theme: DrawTheme,
) -> None:
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


def _apply_bar_style(
    *,
    bars: BarContainer,
    values: tuple[float, ...],
    draw_style: HistogramDrawStyle,
    theme: DrawTheme,
) -> None:
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


def _reference_line_color(theme: DrawTheme) -> str:
    return theme.ui_secondary_text_color or theme.barrier_color


def _negative_bar_color(theme: DrawTheme) -> str:
    if theme.name == "paper":
        return "#b91c1c"
    if theme.name == "light":
        return "#dc2626"
    return "#f87171"


def _apply_joint_marginal(
    values_by_state: Mapping[str, float],
    *,
    qubits: tuple[int, ...] | None,
    bit_width: int,
) -> dict[str, float]:
    if qubits is None:
        return dict(values_by_state)
    if any(qubit >= bit_width for qubit in qubits):
        raise ValueError("qubits must reference indices within the available state width")

    marginal_labels = _basis_state_labels(len(qubits))
    marginal = {label: 0.0 for label in marginal_labels}
    for state_label, value in values_by_state.items():
        flattened_state_label = _flatten_state_label(state_label)
        selected_label = "".join(flattened_state_label[-(qubit + 1)] for qubit in qubits)
        marginal[selected_label] += value
    return marginal


def _basis_state_labels(bit_width: int) -> tuple[str, ...]:
    if bit_width == 0:
        return ("",)
    return tuple("".join(bits) for bits in product("01", repeat=bit_width))


def _is_bit_array(candidate: object) -> bool:
    return hasattr(candidate, "get_counts") and hasattr(candidate, "num_bits")


def _mapping_from_bit_array(bit_array: object) -> Mapping[object, object]:
    get_counts = getattr(bit_array, "get_counts", None)
    if not callable(get_counts):
        raise TypeError("bit-array inputs must provide get_counts()")
    return get_counts()


def _bit_width_from_bit_array(bit_array: object) -> int:
    num_bits = getattr(bit_array, "num_bits", None)
    if not isinstance(num_bits, int) or num_bits < 0:
        raise ValueError("bit-array inputs must provide a non-negative num_bits")
    return max(num_bits, 1)


def _is_data_bin_like(candidate: object) -> bool:
    return (
        not isinstance(candidate, Mapping)
        and hasattr(candidate, "items")
        and hasattr(
            candidate,
            "keys",
        )
    )


def _select_data_bin_field(data_bin: object, *, data_key: str | None) -> object:
    items_method = getattr(data_bin, "items", None)
    if not callable(items_method):
        raise TypeError("data containers must provide items()")
    return _select_data_bin_field_from_fields(dict(items_method()), data_key=data_key)


def _select_data_bin_field_from_fields(
    fields: Mapping[object, object],
    *,
    data_key: str | None,
) -> object:
    bit_array_fields = {key: value for key, value in fields.items() if _is_bit_array(value)}
    if data_key is not None:
        if data_key not in fields:
            raise ValueError(f"data_key {data_key!r} is not available in the histogram data")
        selected = fields[data_key]
        if not _is_bit_array(selected):
            raise ValueError(f"data_key {data_key!r} does not reference a bit-array field")
        return selected
    if len(bit_array_fields) != 1:
        raise ValueError(
            "data_key is required when histogram data contains multiple bit-array fields"
        )
    return next(iter(bit_array_fields.values()))


def _select_result_item(sequence: object, *, result_index: int, label: str) -> object:
    if not isinstance(sequence, _SupportsLenAndGetItem):
        raise TypeError(f"{label} is not indexable")
    length = len(sequence)
    if result_index >= length:
        raise ValueError(f"result_index {result_index} is out of range for {label}")
    return sequence[result_index]


def _infer_mapping_bit_width(mapping: Mapping[object, object]) -> int:
    if not mapping:
        return 1
    return max(_infer_state_width(key) for key in mapping)


def _infer_entries_bit_width(entries: list[tuple[object, float]]) -> int:
    return max(_infer_state_width(key) for key, _ in entries)


def _infer_state_width(key: object) -> int:
    if isinstance(key, int):
        if key < 0:
            raise ValueError("histogram state keys must be non-negative")
        return max(key.bit_length(), 1)
    if isinstance(key, str):
        state = key.replace(" ", "")
        if state.startswith(("0x", "0X")):
            return max((len(state) - 2) * 4, 1)
        if not state:
            raise ValueError("histogram state keys must not be empty")
        if any(bit not in {"0", "1"} for bit in state):
            raise ValueError("histogram state keys must be binary strings")
        return len(state)
    raise TypeError("histogram state keys must be strings or integers")


def _save_histogram_if_requested(
    figure: Figure,
    *,
    output_path: OutputPath | None,
) -> None:
    save_matplotlib_figure(
        figure,
        output_path,
        error_message_prefix="failed to save histogram to",
    )
