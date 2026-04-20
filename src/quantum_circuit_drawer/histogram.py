"""Public histogram plotting API for counts and quasi-probability data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import product
from typing import TYPE_CHECKING

from .exceptions import RenderingError

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .typing import OutputPath


class HistogramKind(StrEnum):
    """Public histogram data modes."""

    AUTO = "auto"
    COUNTS = "counts"
    QUASI = "quasi"


@dataclass(frozen=True, slots=True)
class HistogramConfig:
    """Public configuration for ``plot_histogram``."""

    kind: HistogramKind = HistogramKind.AUTO
    qubits: tuple[int, ...] | None = None
    result_index: int = 0
    data_key: str | None = None
    show: bool = True
    output_path: OutputPath | None = None
    figsize: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", self._normalize_kind(self.kind))
        self._validate_qubits(self.qubits)
        self._validate_result_index(self.result_index)
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
    def _validate_qubits(qubits: tuple[int, ...] | None) -> None:
        if qubits is None:
            return
        if not isinstance(qubits, tuple):
            raise ValueError("qubits must be a tuple of non-negative integers")
        if any(not isinstance(qubit, int) or qubit < 0 for qubit in qubits):
            raise ValueError("qubits must be a tuple of non-negative integers")
        if len(set(qubits)) != len(qubits):
            raise ValueError("qubits must not contain duplicates")

    @staticmethod
    def _validate_result_index(value: int) -> None:
        if isinstance(value, int) and value >= 0:
            return
        raise ValueError("result_index must be a non-negative integer")

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
        if not isinstance(width, int | float) or not isinstance(height, int | float):
            raise ValueError("figsize must be a 2-item tuple of positive numbers")
        if float(width) <= 0.0 or float(height) <= 0.0:
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
    state_labels = tuple(values_by_state)
    values = tuple(float(value) for value in values_by_state.values())
    figure, axes = _resolve_figure_and_axes(ax=ax, figsize=resolved_config.figsize)

    colors = _bar_colors(values=values, kind=normalized.kind)
    axes.bar(state_labels, values, color=colors)
    axes.set_xlabel("State")
    axes.set_ylabel("Counts" if normalized.kind is HistogramKind.COUNTS else "Quasi-probability")
    if normalized.kind is HistogramKind.QUASI:
        axes.axhline(0.0, color="#94a3b8", linewidth=1.0)

    _save_histogram_if_requested(figure, output_path=resolved_config.output_path)
    if resolved_config.show:
        figure.show()

    return HistogramResult(
        figure=figure,
        axes=axes,
        kind=normalized.kind,
        state_labels=state_labels,
        values=values,
        qubits=resolved_config.qubits,
    )


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
        quasi_dists = getattr(data, "quasi_dists")
        selected = _select_result_item(
            quasi_dists,
            result_index=result_index,
            label="SamplerResult.quasi_dists",
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
    if hasattr(data, "binary_probabilities") and callable(getattr(data, "binary_probabilities")):
        mapping = getattr(data, "binary_probabilities")()
        return mapping, _infer_mapping_bit_width(mapping), HistogramKind.QUASI
    if hasattr(data, "int_outcomes") and callable(getattr(data, "int_outcomes")):
        mapping = getattr(data, "int_outcomes")()
        return mapping, _infer_mapping_bit_width(mapping), HistogramKind.COUNTS
    return data, None, None


def _normalize_distribution_mapping(
    raw_mapping: Mapping[object, object],
    *,
    bit_width: int | None,
) -> tuple[dict[str, float], int]:
    entries = [(key, float(value)) for key, value in raw_mapping.items()]
    if not entries:
        return {"0": 0.0}, 1

    resolved_bit_width = max(bit_width or 0, _infer_entries_bit_width(entries), 1)
    normalized: dict[str, float] = {}
    for raw_key, value in entries:
        state_label = _normalize_state_label(raw_key, bit_width=resolved_bit_width)
        normalized[state_label] = value

    ordered_labels = sorted(normalized, key=lambda label: int(label, 2))
    return {label: normalized[label] for label in ordered_labels}, resolved_bit_width


def _normalize_state_label(key: object, *, bit_width: int) -> str:
    if isinstance(key, int):
        if key < 0:
            raise ValueError("histogram state keys must be non-negative")
        return format(key, f"0{bit_width}b")
    if isinstance(key, str):
        state = key.replace(" ", "")
        if state.startswith(("0x", "0X")):
            state = format(int(state, 16), f"0{bit_width}b")
        if not state:
            raise ValueError("histogram state keys must not be empty")
        if any(bit not in {"0", "1"} for bit in state):
            raise ValueError("histogram state keys must be binary strings")
        return state.zfill(bit_width)
    raise TypeError("histogram state keys must be strings or integers")


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
    if ax is not None:
        return ax.figure, ax

    import matplotlib.pyplot as plt

    return plt.subplots(figsize=figsize)


def _bar_colors(
    *,
    values: tuple[float, ...],
    kind: HistogramKind,
) -> tuple[str, ...]:
    if kind is HistogramKind.COUNTS:
        return tuple("#2563eb" for _ in values)
    return tuple("#2563eb" if value >= 0.0 else "#dc2626" for value in values)


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
        selected_label = "".join(state_label[-(qubit + 1)] for qubit in qubits)
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
    fields = dict(items_method())
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
    if not hasattr(sequence, "__len__") or not hasattr(sequence, "__getitem__"):
        raise TypeError(f"{label} is not indexable")
    length = len(sequence)  # type: ignore[arg-type]
    if result_index >= length:
        raise ValueError(f"result_index {result_index} is out of range for {label}")
    return sequence[result_index]  # type: ignore[index]


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
    if output_path is None:
        return
    try:
        figure.savefig(output_path)
    except OSError as exc:
        raise RenderingError(str(exc)) from exc
