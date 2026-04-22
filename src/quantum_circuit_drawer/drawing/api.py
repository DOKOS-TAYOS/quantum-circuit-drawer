"""Public API orchestration for drawing supported circuit objects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..circuit_compare import CircuitCompareConfig, CircuitCompareResult
from ..config import DrawConfig
from ..renderers._render_support import figure_backend_name as _figure_backend_name
from ..result import DrawResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes

# Kept as a lightweight compatibility alias for tests and internal monkeypatching.
figure_backend_name = _figure_backend_name


def draw_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult:
    """Draw a supported circuit with the current public API contract."""

    from .managed_modes import draw_result_from_prepared_call
    from .preparation import prepare_draw_call

    prepared = prepare_draw_call(circuit, config=config, ax=ax)
    return draw_result_from_prepared_call(prepared)


def compare_circuits(
    left_circuit: object,
    right_circuit: object,
    *,
    config: CircuitCompareConfig | None = None,
    axes: tuple[Axes, Axes] | None = None,
) -> CircuitCompareResult:
    """Render two circuits side by side and return structural comparison data."""

    from .compare import compare_circuits as _compare_circuits

    return _compare_circuits(
        left_circuit,
        right_circuit,
        config=config,
        axes=axes,
    )
