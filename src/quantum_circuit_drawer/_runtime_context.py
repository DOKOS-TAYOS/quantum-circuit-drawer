"""Runtime context detection and draw-mode resolution."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .config import DrawConfig, DrawMode, ResolvedDrawConfig
from .renderers._render_support import NOTEBOOK_INTERACTIVE_BACKENDS, pyplot_backend_name

if TYPE_CHECKING:
    from matplotlib.axes import Axes


_INTERACTIVE_DRAW_MODES = frozenset({DrawMode.PAGES_CONTROLS, DrawMode.SLIDER})


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Observed execution context used for auto mode selection."""

    is_notebook: bool
    pyplot_backend: str

    @property
    def notebook_backend_active(self) -> bool:
        """Return whether the current backend is notebook-interactive."""

        return self.pyplot_backend in NOTEBOOK_INTERACTIVE_BACKENDS


def detect_runtime_context() -> RuntimeContext:
    """Inspect the current Python runtime and Matplotlib backend."""

    return RuntimeContext(
        is_notebook=_running_inside_notebook(),
        pyplot_backend=pyplot_backend_name(),
    )


def resolve_draw_config(
    config: DrawConfig | None,
    *,
    ax: Axes | None,
) -> ResolvedDrawConfig:
    """Resolve runtime-dependent draw defaults for one public call."""

    resolved_config = DrawConfig() if config is None else config
    runtime_context = detect_runtime_context()
    mode = _resolve_draw_mode(resolved_config, runtime_context=runtime_context, ax=ax)
    interactive_mode_allowed = (
        not runtime_context.is_notebook
        or runtime_context.notebook_backend_active
        or mode not in _INTERACTIVE_DRAW_MODES
    )
    return ResolvedDrawConfig(
        config=resolved_config,
        mode=mode,
        interactive_mode_allowed=interactive_mode_allowed,
        notebook_backend_active=runtime_context.notebook_backend_active,
        caller_axes=ax,
    )


def _resolve_draw_mode(
    config: DrawConfig,
    *,
    runtime_context: RuntimeContext,
    ax: Axes | None,
) -> DrawMode:
    if config.mode is not DrawMode.AUTO:
        return config.mode
    if ax is not None:
        if config.view == "3d":
            return DrawMode.FULL
        return DrawMode.PAGES
    if runtime_context.is_notebook:
        return DrawMode.PAGES
    return DrawMode.PAGES_CONTROLS


def _running_inside_notebook() -> bool:
    try:
        ipython_module = importlib.import_module("IPython")
    except ImportError:
        return False

    get_ipython = getattr(ipython_module, "get_ipython", None)
    if not callable(get_ipython):
        return False
    shell = get_ipython()
    if shell is None:
        return False
    shell_name = type(shell).__name__
    if shell_name == "ZMQInteractiveShell":
        return True
    config = getattr(shell, "config", None)
    return bool(config is not None and "IPKernelApp" in config)
