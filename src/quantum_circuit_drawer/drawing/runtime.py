"""Runtime context detection and draw-mode resolution."""

from __future__ import annotations

import builtins
import os
import platform
import sys
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from ..config import DrawConfig, DrawMode, ResolvedDrawConfig
from ..diagnostics import DiagnosticSeverity, RenderDiagnostic
from ..renderers._render_support import (
    NON_INTERACTIVE_BACKENDS,
    NOTEBOOK_INTERACTIVE_BACKENDS,
    pyplot_backend_name,
)

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
    diagnostics: list[RenderDiagnostic] = []
    if resolved_config.mode is DrawMode.AUTO:
        diagnostics.append(
            RenderDiagnostic(
                code="auto_mode_resolved",
                message=f"Resolved draw mode {mode.value!r} from mode='auto'.",
                severity=DiagnosticSeverity.INFO,
            )
        )
    diagnostics.extend(
        show_requested_without_interactive_backend_diagnostics(
            show=resolved_config.show,
            runtime_context=runtime_context,
            caller_axes=ax,
        )
    )
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
        diagnostics=tuple(diagnostics),
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


@lru_cache(maxsize=1)
def _running_inside_notebook() -> bool:
    shell = _resolve_ipython_shell()
    if shell is None:
        return False
    shell_name = type(shell).__name__
    if shell_name == "ZMQInteractiveShell":
        return True
    config = getattr(shell, "config", None)
    return bool(config is not None and "IPKernelApp" in config)


def _resolve_ipython_shell() -> object | None:
    get_ipython = getattr(builtins, "get_ipython", None)
    if callable(get_ipython):
        return get_ipython()

    ipython_module = sys.modules.get("IPython")
    if ipython_module is None:
        return None
    get_ipython = getattr(ipython_module, "get_ipython", None)
    if not callable(get_ipython):
        return None
    return get_ipython()


def show_requested_without_interactive_backend_diagnostics(
    *,
    show: bool,
    runtime_context: RuntimeContext,
    caller_axes: Axes | None = None,
) -> tuple[RenderDiagnostic, ...]:
    """Return a warning when ``show=True`` cannot open an interactive window."""

    if not show or caller_axes is not None or runtime_context.is_notebook:
        return ()
    if runtime_context.pyplot_backend not in NON_INTERACTIVE_BACKENDS:
        return ()
    return (
        RenderDiagnostic(
            code="show_requested_without_interactive_backend",
            message=_noninteractive_backend_show_message(runtime_context.pyplot_backend),
            severity=DiagnosticSeverity.WARNING,
        ),
    )


def _noninteractive_backend_show_message(backend_name: str) -> str:
    """Build a user-facing explanation for non-interactive Matplotlib backends."""

    message = (
        f"show=True requested an interactive Matplotlib window, but backend {backend_name!r} "
        "is non-interactive so no window will open."
    )
    if _running_in_wsl():
        return (
            message
            + " In WSL2, install the system Tk package instead of relying on pip alone "
            + "(Ubuntu/Debian: sudo apt install python3-tk), make sure WSLg GUI support is "
            + "available, and test with python3 -m tkinter."
        )
    if _platform_system() == "Linux":
        return (
            message
            + " On Linux, install a GUI toolkit such as Tk; on Ubuntu/Debian, run sudo apt "
            + "install python3-tk and test with python3 -m tkinter."
        )
    return message + " Use show=False or save to output_path for headless runs."


def _platform_system() -> str:
    """Return the current operating-system family."""

    return platform.system()


def _running_in_wsl() -> bool:
    """Return whether the current Linux process is running inside WSL."""

    if _platform_system() != "Linux":
        return False
    wsl_markers = (
        os.environ.get("WSL_DISTRO_NAME", ""),
        os.environ.get("WSL_INTEROP", ""),
        platform.release(),
        platform.version(),
    )
    return any("microsoft" in marker.lower() or "wsl" in marker.lower() for marker in wsl_markers)


__all__ = [
    "DiagnosticSeverity",
    "DrawConfig",
    "DrawMode",
    "NOTEBOOK_INTERACTIVE_BACKENDS",
    "RenderDiagnostic",
    "ResolvedDrawConfig",
    "RuntimeContext",
    "TYPE_CHECKING",
    "_INTERACTIVE_DRAW_MODES",
    "_resolve_draw_mode",
    "_resolve_ipython_shell",
    "_running_inside_notebook",
    "annotations",
    "builtins",
    "dataclass",
    "detect_runtime_context",
    "lru_cache",
    "pyplot_backend_name",
    "resolve_draw_config",
    "show_requested_without_interactive_backend_diagnostics",
    "sys",
]
