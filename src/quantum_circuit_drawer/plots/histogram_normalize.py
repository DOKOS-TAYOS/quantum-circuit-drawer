"""Normalization helpers for histogram-like inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, SupportsFloat, cast, runtime_checkable

from .histogram_models import HistogramKind


@runtime_checkable
class _SupportsLenAndGetItem(Protocol):
    """Minimal protocol for objects that behave like a sequence."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> object: ...


@runtime_checkable
class _SupportsInt(Protocol):
    """Minimal protocol for objects with a working ``int()`` conversion."""

    def __int__(self) -> int: ...


@dataclass(frozen=True, slots=True)
class _NormalizedHistogramData:
    values_by_state: dict[str, float]
    bit_width: int
    kind: HistogramKind


def normalize_histogram_data(
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
            HistogramKind.COUNTS,
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
        if not isinstance(mapping, Mapping):
            raise TypeError("binary_probabilities() must return a mapping")
        return mapping, _infer_mapping_bit_width(mapping), HistogramKind.QUASI
    int_outcomes = getattr(data, "int_outcomes", None)
    if callable(int_outcomes):
        mapping = int_outcomes()
        if not isinstance(mapping, Mapping):
            raise TypeError("int_outcomes() must return a mapping")
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

    return cast(Mapping[object, object], counts), max(total_width, 1), HistogramKind.COUNTS


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
        return cast(Mapping[object, object], {"0": 0.0}), 1, HistogramKind.COUNTS

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
    if not isinstance(state, _SupportsInt):
        return None
    try:
        return int(state)
    except (TypeError, ValueError):
        return None


def _extract_array_like_distribution(
    data: object,
) -> tuple[Mapping[object, object], int | None, HistogramKind] | None:
    python_data = _to_python_sequence(data)
    if python_data is None:
        return None

    probability_vector = _coerce_probability_vector(python_data)
    if probability_vector is not None:
        return (
            cast(
                Mapping[object, object],
                {index: value for index, value in enumerate(probability_vector)},
            ),
            _bit_width_from_vector_length(len(probability_vector)),
            HistogramKind.QUASI,
        )

    sample_vector = _coerce_sample_vector(python_data)
    if sample_vector is not None:
        sample_vector_rows = tuple((bit,) for bit in sample_vector)
        return (
            cast(Mapping[object, object], _mapping_from_sample_rows(sample_vector_rows)),
            1,
            HistogramKind.COUNTS,
        )

    sample_rows = _coerce_sample_rows(python_data)
    if sample_rows is not None:
        return (
            cast(Mapping[object, object], _mapping_from_sample_rows(sample_rows)),
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


def _coerce_probability_vector(data: Sequence[object]) -> tuple[float, ...] | None:
    if not data or not _bit_width_for_sequence_length(len(data)):
        return None
    if any(isinstance(value, Sequence) and not isinstance(value, str | bytes) for value in data):
        return None

    numeric_values: list[float] = []
    for value in data:
        if not isinstance(value, SupportsFloat):
            return None
        numeric_values.append(float(value))

    if any(value < 0.0 for value in numeric_values):
        return tuple(numeric_values)
    if any(not value.is_integer() for value in numeric_values):
        return tuple(numeric_values)
    if abs(sum(numeric_values) - 1.0) <= 1e-9:
        return tuple(numeric_values)
    return None


def _coerce_sample_vector(data: Sequence[object]) -> tuple[int, ...] | None:
    if not data or not all(_is_bit_like(value) for value in data):
        return None
    return tuple(_coerce_bit_value(value) for value in data)


def _coerce_sample_rows(data: object) -> tuple[tuple[int, ...], ...] | None:
    python_rows = _to_python_sequence(data)
    if python_rows is None or not python_rows:
        return None

    rows: list[tuple[int, ...]] = []
    row_width: int | None = None
    for raw_row in python_rows:
        row_values = _to_python_sequence(raw_row)
        if row_values is None or not row_values:
            return None
        normalized_row = _coerce_sample_vector(row_values)
        if normalized_row is None:
            return None
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


def _coerce_bit_value(value: object) -> int:
    if value is True:
        return 1
    if value is False:
        return 0
    if isinstance(value, int) and value in {0, 1}:
        return value
    raise TypeError("sample values must be bits")


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


def _is_bit_array(candidate: object) -> bool:
    return hasattr(candidate, "get_counts") and hasattr(candidate, "num_bits")


def _mapping_from_bit_array(bit_array: object) -> Mapping[object, object]:
    get_counts = getattr(bit_array, "get_counts", None)
    if not callable(get_counts):
        raise TypeError("bit-array inputs must provide get_counts()")
    mapping = get_counts()
    if not isinstance(mapping, Mapping):
        raise TypeError("bit-array get_counts() must return a mapping")
    return mapping


def _bit_width_from_bit_array(bit_array: object) -> int:
    num_bits = getattr(bit_array, "num_bits", None)
    if not isinstance(num_bits, int) or num_bits < 0:
        raise ValueError("bit-array inputs must provide a non-negative num_bits")
    return max(num_bits, 1)


def _is_data_bin_like(candidate: object) -> bool:
    return (
        not isinstance(candidate, Mapping)
        and hasattr(candidate, "items")
        and hasattr(candidate, "keys")
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


__all__ = ["normalize_histogram_data"]
